from fastapi import HTTPException
from postgrest.exceptions import APIError

# Errors raised by our SQL functions (raise exception '...') -> HTTP responses.
_ERROR_MAP = {
    "booking_not_found": (404, "Booking not found"),
    "not_your_booking": (403, "This booking belongs to another user"),
    "booking_not_pending": (409, "Booking is not pending"),
    "booking_not_cancellable": (409, "Booking cannot be cancelled in its current state"),
    "seat_unavailable": (409, "Seat is not available"),
    "no_seats_held": (409, "No seats are held for this booking"),
    "seat_not_held": (409, "That seat isn't currently held by this booking"),
    "hold_expired": (409, "A seat hold has expired; please hold the seats again"),
}


def raise_from_api_error(e: APIError):
    text = f"{getattr(e, 'message', '')} {e}"
    for key, (code, message) in _ERROR_MAP.items():
        if key in text:
            raise HTTPException(status_code=code, detail=message)
    raise HTTPException(status_code=400, detail=f"Database error: {getattr(e, 'message', str(e))}")
