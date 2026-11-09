import hashlib
import hmac
import json
import os
import uuid

import pytest

from conftest import hold, new_booking

SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")


def _post_event(client, body: dict, secret=SECRET, event_id=None, signature=None):
    raw = json.dumps(body).encode()
    sig = signature if signature is not None else hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": event_id or f"evt_{uuid.uuid4().hex}", "content-type": "application/json"}
    return client.post("/webhooks/razorpay", content=raw, headers=headers)


def _captured(booking_id, order_id=None):
    return {"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": f"pay_{uuid.uuid4().hex[:12]}", "order_id": order_id or f"order_{uuid.uuid4().hex[:12]}",
        "amount": 50000, "notes": {"booking_id": booking_id}}}}}


@pytest.fixture(autouse=True)
def _need_secret(client):
    if not SECRET:
        pytest.skip("RAZORPAY_WEBHOOK_SECRET not set")


def test_bad_signature_is_rejected(client, alice, event):
    b = new_booking(client, alice, event["id"])
    r = _post_event(client, _captured(b), signature="deadbeef")
    assert r.status_code == 400


def test_missing_signature_is_rejected(client, alice, event):
    b = new_booking(client, alice, event["id"])
    r = _post_event(client, _captured(b), signature="")
    assert r.status_code == 400


def test_valid_webhook_confirms_booking(client, alice, event):
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, event["seats"]["A1"]["id"])
    r = _post_event(client, _captured(b))
    assert r.status_code == 200, r.text
    full = client.get(f"/bookings/{b}", headers=alice.headers).json()
    assert full["status"] == "confirmed" and len(full["tickets"]) == 1


def test_replayed_webhook_is_idempotent(client, alice, admin_db, event):
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, event["seats"]["A1"]["id"])
    hold(client, alice, b, event["seats"]["A2"]["id"])
    body, eid = _captured(b), f"evt_{uuid.uuid4().hex}"
    assert _post_event(client, body, event_id=eid).json()["status"] == "ok"
    assert _post_event(client, body, event_id=eid).json()["status"] == "already_processed"
    tickets = admin_db.table("tickets").select("id").eq("booking_id", b).execute().data
    assert len(tickets) == 2  # one per seat, no duplicates


def test_webhook_for_expired_hold_does_not_confirm(client, alice, admin_db, event):
    seat = event["seats"]["A1"]["id"]
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, seat)
    admin_db.table("seats").update({"hold_expires_at": "2000-01-01T00:00:00+00:00"}).eq("id", seat).execute()
    assert _post_event(client, _captured(b)).status_code == 200  # acked so Razorpay stops retrying
    assert client.get(f"/bookings/{b}", headers=alice.headers).json()["status"] == "pending"


def test_unknown_event_type_is_acked(client):
    assert _post_event(client, {"event": "refund.created", "payload": {}}).status_code == 200


def test_create_payment_order_needs_a_held_seat_or_config(client, alice, event):
    b = new_booking(client, alice, event["id"])
    r = client.post(f"/bookings/{b}/create-payment-order", headers=alice.headers)
    assert r.status_code in (400, 503)  # 400 no seats held / 503 Razorpay not configured
