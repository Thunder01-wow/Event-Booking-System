from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.core.auth import CurrentUser, require_admin
from app.core.errors import raise_from_api_error
from app.db.supabase_client import get_user_client
from app.schemas.schemas import (
    EventCreate,
    EventUpdate,
    SeatBulkCreate,
    SeatUpdate,
    VenueCreate,
    VenueUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _client(user: CurrentUser):
    # The user's own client, not the service role — writes still go through
    # the admin-only RLS policies (seats_write_admin etc.), so require_admin
    # above isn't the only thing standing between a non-admin and these
    # routes; RLS enforces it independently as a second layer.
    return get_user_client(user.token)


# --------------------------------------------------------------------------
# Venues
# --------------------------------------------------------------------------
@router.post("/venues", status_code=201)
def create_venue(body: VenueCreate, user: CurrentUser = Depends(require_admin)):
    try:
        res = _client(user).table("venues").insert(body.model_dump(exclude_none=True)).execute()
    except APIError as e:
        raise_from_api_error(e)
    return res.data[0]


@router.patch("/venues/{venue_id}")
def update_venue(venue_id: UUID, body: VenueUpdate, user: CurrentUser = Depends(require_admin)):
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        res = (
            _client(user)
            .table("venues")
            .update(patch)
            .eq("id", str(venue_id))
            .execute()
        )
    except APIError as e:
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Venue not found")
    return res.data[0]


@router.delete("/venues/{venue_id}", status_code=204)
def delete_venue(venue_id: UUID, user: CurrentUser = Depends(require_admin)):
    try:
        res = _client(user).table("venues").delete().eq("id", str(venue_id)).execute()
    except APIError as e:
        # A venue with events pointing at it is protected by
        # `on delete restrict` in 003_venues_events.sql — surface that
        # clearly instead of a raw foreign-key error.
        if "foreign key" in str(e).lower() or getattr(e, "code", "") == "23503":
            raise HTTPException(
                status_code=409, detail="Venue has events and cannot be deleted"
            )
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Venue not found")


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------
@router.post("/events", status_code=201)
def create_event(body: EventCreate, user: CurrentUser = Depends(require_admin)):
    if body.ends_at <= body.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    payload = body.model_dump(exclude_none=True, mode="json")
    payload["venue_id"] = str(body.venue_id)
    payload["created_by"] = user.id
    try:
        res = _client(user).table("events").insert(payload).execute()
    except APIError as e:
        raise_from_api_error(e)
    return res.data[0]


@router.patch("/events/{event_id}")
def update_event(event_id: UUID, body: EventUpdate, user: CurrentUser = Depends(require_admin)):
    patch = body.model_dump(exclude_none=True, mode="json")
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        res = (
            _client(user)
            .table("events")
            .update(patch)
            .eq("id", str(event_id))
            .execute()
        )
    except APIError as e:
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return res.data[0]


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: UUID, user: CurrentUser = Depends(require_admin)):
    # events -> seats and events -> bookings both cascade/restrict per
    # 003/004/005's FK definitions; a conflict here usually means existing
    # bookings, which is worth a clearer message than a raw DB error too.
    try:
        res = _client(user).table("events").delete().eq("id", str(event_id)).execute()
    except APIError as e:
        if "foreign key" in str(e).lower() or getattr(e, "code", "") == "23503":
            raise HTTPException(
                status_code=409, detail="Event has bookings and cannot be deleted"
            )
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Event not found")


# --------------------------------------------------------------------------
# Seats
# --------------------------------------------------------------------------
@router.post("/events/{event_id}/seats", status_code=201)
def create_seats(event_id: UUID, body: SeatBulkCreate, user: CurrentUser = Depends(require_admin)):
    """Bulk-add seats to an event, e.g. A1..A50 in one call."""
    if not body.seats:
        raise HTTPException(status_code=400, detail="No seats provided")
    rows = [
        {"event_id": str(event_id), **s.model_dump()} for s in body.seats
    ]
    try:
        res = _client(user).table("seats").insert(rows).execute()
    except APIError as e:
        # Most likely a duplicate seat_label for this event (unique
        # (event_id, seat_label) from 005_seats.sql).
        if "duplicate key" in str(e).lower() or getattr(e, "code", "") == "23505":
            raise HTTPException(
                status_code=409, detail="One or more seat labels already exist for this event"
            )
        raise_from_api_error(e)
    return res.data


@router.patch("/seats/{seat_id}")
def update_seat(seat_id: UUID, body: SeatUpdate, user: CurrentUser = Depends(require_admin)):
    """Admin-only edit of category/price. Status changes go through the
    booking functions (hold_seat/confirm_booking/cancel_booking), not here."""
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        res = _client(user).table("seats").update(patch).eq("id", str(seat_id)).execute()
    except APIError as e:
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Seat not found")
    return res.data[0]


@router.delete("/seats/{seat_id}", status_code=204)
def delete_seat(seat_id: UUID, user: CurrentUser = Depends(require_admin)):
    try:
        res = _client(user).table("seats").delete().eq("id", str(seat_id)).execute()
    except APIError as e:
        if "foreign key" in str(e).lower() or getattr(e, "code", "") == "23503":
            raise HTTPException(
                status_code=409, detail="Seat has a ticket and cannot be deleted"
            )
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Seat not found")
