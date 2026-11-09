import json
from datetime import datetime, timezone
from uuid import UUID

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request
from postgrest.exceptions import APIError
from razorpay.errors import SignatureVerificationError

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.errors import raise_from_api_error
from app.db.supabase_client import get_supabase_admin, get_user_client

router = APIRouter(tags=["payments"])


def _razorpay_client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/bookings/{booking_id}/create-payment-order")
def create_payment_order(booking_id: UUID, user: CurrentUser = Depends(get_current_user)):
    """
    Creates a Razorpay Order for a pending booking's current total (so you
    must hold at least one seat first) and records a matching 'pending'
    payments row. The frontend hands {order_id, amount, key_id} to Razorpay
    Checkout to actually collect payment; this endpoint never touches card
    details itself.
    """
    client_db = get_user_client(user.token)
    booking_res = (
        client_db.table("bookings")
        .select("*")
        .eq("id", str(booking_id))
        .eq("user_id", user.id)
        .execute()
    )
    if not booking_res.data:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking = booking_res.data[0]

    if booking["status"] != "pending":
        raise HTTPException(status_code=409, detail="Booking is not pending")
    total = float(booking["total_amount"])
    if total <= 0:
        raise HTTPException(status_code=400, detail="Hold at least one seat before paying")

    amount_paise = int(round(total * 100))
    try:
        order = _razorpay_client().order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "notes": {"booking_id": str(booking_id)},
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {e}")

    admin = get_supabase_admin()
    try:
        # order["id"] sits in provider_payment_id as a placeholder until the
        # webhook swaps it for the real payment id on success.
        admin.table("payments").insert(
            {
                "booking_id": str(booking_id),
                "provider": "razorpay",
                "provider_payment_id": order["id"],
                "amount": total,
                "status": "pending",
            }
        ).execute()
    except APIError as e:
        raise_from_api_error(e)

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": settings.razorpay_key_id,
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """
    Razorpay POSTs here on payment events. Verified with the SDK's HMAC
    check against the raw body, recorded in webhook_events keyed by
    Razorpay's own delivery id BEFORE any processing (so a retried
    delivery — Razorpay resends until it gets a 2xx — is a no-op the
    second time), then confirm_booking() is called via the service role.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    event_id = request.headers.get("x-razorpay-event-id", "")

    if not settings.razorpay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    try:
        razorpay.Utility().verify_webhook_signature(
            raw_body.decode("utf-8"), signature, settings.razorpay_webhook_secret
        )
    except SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    body = json.loads(raw_body)
    event_type = body.get("event", "")
    if not event_id:
        # Razorpay always sends this header in production; this fallback
        # only matters for manual/local testing without it.
        event_id = f"{event_type}:{hash(raw_body)}"

    admin = get_supabase_admin()

    try:
        admin.table("webhook_events").insert(
            {"provider": "razorpay", "provider_event_id": event_id, "payload": body}
        ).execute()
    except APIError as e:
        if getattr(e, "code", "") == "23505" or "duplicate key" in str(e).lower():
            return {"status": "already_processed"}
        raise_from_api_error(e)

    if event_type == "payment.captured":
        _handle_payment_captured(admin, body)
    elif event_type == "payment.failed":
        _handle_payment_failed(admin, body)
    # Unrecognised event types: already logged to webhook_events above,
    # nothing further to do — ack with 200 so Razorpay stops retrying.

    admin.table("webhook_events").update({"processed_at": _now_iso()}).eq(
        "provider", "razorpay"
    ).eq("provider_event_id", event_id).execute()

    return {"status": "ok"}


def _handle_payment_captured(admin, body: dict) -> None:
    payment = body.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")
    payment_id = payment.get("id")
    amount = float(payment.get("amount", 0)) / 100
    booking_id = (payment.get("notes") or {}).get("booking_id")

    # Razorpay copies an Order's notes onto its Payment, so this is normally
    # already set. Fall back to the row create_payment_order() wrote, keyed
    # by the order id, in case notes didn't come through.
    if not booking_id and order_id:
        existing = (
            admin.table("payments")
            .select("booking_id")
            .eq("provider", "razorpay")
            .eq("provider_payment_id", order_id)
            .execute()
        )
        if existing.data:
            booking_id = existing.data[0]["booking_id"]

    if not booking_id:
        return  # Nothing we can tie this payment to; already logged above.

    if order_id:
        admin.table("payments").update(
            {"provider_payment_id": payment_id, "status": "succeeded", "amount": amount}
        ).eq("provider", "razorpay").eq("provider_payment_id", order_id).execute()
    else:
        admin.table("payments").insert(
            {
                "booking_id": booking_id,
                "provider": "razorpay",
                "provider_payment_id": payment_id,
                "amount": amount,
                "status": "succeeded",
            }
        ).execute()

    try:
        admin.rpc("confirm_booking", {"p_booking_id": booking_id}).execute()
    except APIError:
        # Already confirmed, or the seat hold expired before payment
        # cleared. Either way we don't fail the webhook ack over it —
        # Razorpay would just keep retrying — this needs a human look,
        # which is exactly what the webhook_events row now on file is for.
        pass


def _handle_payment_failed(admin, body: dict) -> None:
    payment = body.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")
    if order_id:
        admin.table("payments").update({"status": "failed"}).eq(
            "provider", "razorpay"
        ).eq("provider_payment_id", order_id).execute()
