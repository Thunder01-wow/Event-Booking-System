from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.errors import raise_from_api_error
from app.db.supabase_client import get_supabase, get_supabase_admin, get_user_client
from app.schemas.schemas import BookingCreate, HoldSeatRequest

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _recalculate_total(booking_id: UUID) -> float:
    """
    Set bookings.total_amount = sum of prices of seats currently held by it.
    Runs with the service role (users have no UPDATE policy on bookings), and
    the prices come from the database, never from the client.
    """
    admin = get_supabase_admin()
    rows = (
        admin.table("seats")
        .select("price")
        .eq("held_by_booking_id", str(booking_id))
        .execute()
        .data
    )
    total = sum(float(r["price"]) for r in rows)
    admin.table("bookings").update({"total_amount": total}).eq("id", str(booking_id)).execute()
    return total


def _get_own_booking(client, booking_id: UUID, user: CurrentUser) -> dict:
    res = (
        client.table("bookings")
        .select("*")
        .eq("id", str(booking_id))
        .eq("user_id", user.id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Booking not found")
    return res.data[0]


@router.post("", status_code=201)
def create_booking(body: BookingCreate, user: CurrentUser = Depends(get_current_user)):
    """Start a checkout: creates a 'pending' booking for a published event."""
    event = (
        get_supabase()
        .table("events")
        .select("id")
        .eq("id", str(body.event_id))
        .eq("status", "published")
        .execute()
    )
    if not event.data:
        raise HTTPException(status_code=404, detail="Event not found")

    client = get_user_client(user.token)
    try:
        res = (
            client.table("bookings")
            .insert({"user_id": user.id, "event_id": str(body.event_id)})
            .execute()
        )
    except APIError as e:
        raise_from_api_error(e)
    return res.data[0]


@router.get("")
def my_bookings(user: CurrentUser = Depends(get_current_user)):
    client = get_user_client(user.token)
    return (
        client.table("bookings")
        .select(
            "*, events(title, starts_at, venues(name, city)), "
            "tickets(id, ticket_code, seats(seat_label, category, price))"
        )
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@router.get("/{booking_id}")
def get_booking(booking_id: UUID, user: CurrentUser = Depends(get_current_user)):
    client = get_user_client(user.token)
    booking = _get_own_booking(client, booking_id, user)
    seats = (
        client.table("seats")
        .select("id, seat_label, category, price, status, hold_expires_at")
        .eq("held_by_booking_id", str(booking_id))
        .execute()
        .data
    )
    tickets = (
        client.table("tickets")
        .select("id, seat_id, ticket_code, issued_at")
        .eq("booking_id", str(booking_id))
        .execute()
        .data
    )
    return {**booking, "seats": seats, "tickets": tickets}


@router.post("/{booking_id}/hold-seat")
def hold_seat(
    booking_id: UUID, body: HoldSeatRequest, user: CurrentUser = Depends(get_current_user)
):
    """Lock one seat for this booking (10 min). 409 if someone else got it first."""
    client = get_user_client(user.token)
    try:
        res = client.rpc(
            "hold_seat",
            {"p_seat_id": str(body.seat_id), "p_booking_id": str(booking_id)},
        ).execute()
    except APIError as e:
        raise_from_api_error(e)

    seat = res.data[0] if isinstance(res.data, list) else res.data
    total = _recalculate_total(booking_id)
    return {
        "seat_label": seat["seat_label"],
        "price": seat["price"],
        "status": seat["status"],
        "hold_expires_at": seat["hold_expires_at"],
        "booking_total": total,
    }


@router.post("/{booking_id}/release-seat")
def release_seat(
    booking_id: UUID, body: HoldSeatRequest, user: CurrentUser = Depends(get_current_user)
):
    """Un-hold one seat of a pending booking."""
    client = get_user_client(user.token)
    try:
        client.rpc(
            "release_seat",
            {"p_seat_id": str(body.seat_id), "p_booking_id": str(booking_id)},
        ).execute()
    except APIError as e:
        raise_from_api_error(e)
    return {"booking_total": _recalculate_total(booking_id)}


@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: UUID, user: CurrentUser = Depends(get_current_user)):
    """Cancel your booking and release its seats."""
    client = get_user_client(user.token)
    try:
        res = client.rpc("cancel_booking", {"p_booking_id": str(booking_id)}).execute()
    except APIError as e:
        raise_from_api_error(e)
    _recalculate_total(booking_id)
    return res.data[0] if isinstance(res.data, list) else res.data


@router.post("/{booking_id}/dev-confirm")
def dev_confirm(booking_id: UUID, user: CurrentUser = Depends(get_current_user)):
    """
    DEVELOPMENT ONLY: pretends the payment succeeded so you can test the
    full flow. In production, confirm_booking() is called only by the payment
    webhook. Disabled unless APP_ENV=development.
    """
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Not found")

    _get_own_booking(get_user_client(user.token), booking_id, user)
    try:
        res = get_supabase_admin().rpc(
            "confirm_booking", {"p_booking_id": str(booking_id)}
        ).execute()
    except APIError as e:
        raise_from_api_error(e)
    return res.data[0] if isinstance(res.data, list) else res.data
