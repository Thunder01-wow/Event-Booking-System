from uuid import UUID

from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError

from app.core.errors import raise_from_api_error
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/events", tags=["events"])


def _attach_stats(events: list[dict]) -> list[dict]:
    """Merge min_price / total_seats / available_seats from the event_stats view.
    Falls back to nulls if migration 013 hasn't been run yet."""
    try:
        rows = get_supabase().table("event_stats").select("*").execute().data
    except APIError:
        rows = []
    by_id = {r["event_id"]: r for r in rows}
    for ev in events:
        st = by_id.get(ev["id"], {})
        ev["min_price"] = st.get("min_price")
        ev["total_seats"] = st.get("total_seats")
        ev["available_seats"] = st.get("available_seats")
    return events


@router.get("")
def list_events():
    """All published events, soonest first."""
    try:
        res = (
            get_supabase()
            .table("events")
            .select("*, venues(name, city)")
            .eq("status", "published")
            .order("starts_at")
            .execute()
        )
    except APIError as e:
        raise_from_api_error(e)
    return _attach_stats(res.data)


@router.get("/{event_id}")
def get_event(event_id: UUID):
    try:
        res = (
            get_supabase()
            .table("events")
            .select("*, venues(name, city, address)")
            .eq("id", str(event_id))
            .execute()
        )
    except APIError as e:
        raise_from_api_error(e)
    if not res.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return res.data[0]


@router.get("/{event_id}/seats")
def list_seats(event_id: UUID, status: str | None = None):
    """Seat map for an event. Optional ?status=available|held|booked."""
    query = (
        get_supabase()
        .table("seats")
        .select("id, seat_label, category, price, status")
        .eq("event_id", str(event_id))
    )
    if status:
        query = query.eq("status", status)
    try:
        res = query.order("seat_label").execute()
    except APIError as e:
        raise_from_api_error(e)
    return res.data
