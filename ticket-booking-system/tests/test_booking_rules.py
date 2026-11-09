import uuid

from conftest import hold, new_booking


def test_hold_returns_db_price_and_total(client, alice, event):
    b = new_booking(client, alice, event["id"])
    r = hold(client, alice, b, event["seats"]["A1"]["id"])
    assert r.status_code == 200, r.text
    assert float(r.json()["price"]) == 500 and float(r.json()["booking_total"]) == 500
    r = hold(client, alice, b, event["seats"]["B1"]["id"])
    assert float(r.json()["booking_total"]) == 1500


def test_cannot_hold_same_seat_twice(client, alice, bob, event):
    seat = event["seats"]["A1"]["id"]
    assert hold(client, alice, new_booking(client, alice, event["id"]), seat).status_code == 200
    r = hold(client, bob, new_booking(client, bob, event["id"]), seat)
    assert r.status_code == 409


def test_cannot_hold_on_someone_elses_booking(client, alice, bob, event):
    b = new_booking(client, alice, event["id"])
    r = hold(client, bob, b, event["seats"]["A1"]["id"])
    assert r.status_code in (403, 404)


def test_cannot_read_someone_elses_booking(client, alice, bob, event):
    b = new_booking(client, alice, event["id"])
    assert client.get(f"/bookings/{b}", headers=bob.headers).status_code == 404
    assert b not in [x["id"] for x in client.get("/bookings", headers=bob.headers).json()]


def test_unknown_event_is_404(client, alice):
    r = client.post("/bookings", json={"event_id": str(uuid.uuid4())}, headers=alice.headers)
    assert r.status_code == 404


def test_release_seat_frees_it_and_updates_total(client, alice, bob, event):
    a1, a2 = event["seats"]["A1"]["id"], event["seats"]["A2"]["id"]
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, a1); hold(client, alice, b, a2)
    r = client.post(f"/bookings/{b}/release-seat", json={"seat_id": a1}, headers=alice.headers)
    assert r.status_code == 200 and float(r.json()["booking_total"]) == 500
    # now bob can take it
    assert hold(client, bob, new_booking(client, bob, event["id"]), a1).status_code == 200


def test_cannot_release_a_seat_you_do_not_hold(client, alice, bob, event):
    seat = event["seats"]["A1"]["id"]
    hold(client, alice, new_booking(client, alice, event["id"]), seat)
    bb = new_booking(client, bob, event["id"])
    r = client.post(f"/bookings/{bb}/release-seat", json={"seat_id": seat}, headers=bob.headers)
    assert r.status_code == 409  # seat_not_held


def test_cancel_frees_seats(client, alice, bob, event):
    seat = event["seats"]["A1"]["id"]
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, seat)
    assert client.post(f"/bookings/{b}/cancel", headers=alice.headers).status_code == 200
    assert hold(client, bob, new_booking(client, bob, event["id"]), seat).status_code == 200


def test_cannot_hold_on_cancelled_booking(client, alice, event):
    b = new_booking(client, alice, event["id"])
    client.post(f"/bookings/{b}/cancel", headers=alice.headers)
    assert hold(client, alice, b, event["seats"]["A1"]["id"]).status_code == 409


def test_cannot_cancel_twice(client, alice, event):
    b = new_booking(client, alice, event["id"])
    client.post(f"/bookings/{b}/cancel", headers=alice.headers)
    assert client.post(f"/bookings/{b}/cancel", headers=alice.headers).status_code == 409


def test_dev_confirm_books_seats_and_issues_tickets(client, alice, bob, event):
    seat = event["seats"]["A1"]["id"]
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, seat)
    assert client.post(f"/bookings/{b}/dev-confirm", headers=alice.headers).status_code == 200
    full = client.get(f"/bookings/{b}", headers=alice.headers).json()
    assert full["status"] == "confirmed" and len(full["tickets"]) == 1
    # booked seat can't be held by anyone else
    assert hold(client, bob, new_booking(client, bob, event["id"]), seat).status_code == 409
    listed = client.get("/bookings", headers=alice.headers).json()
    mine = next(x for x in listed if x["id"] == b)
    assert mine["events"]["title"] == "Test Event" and mine["tickets"][0]["ticket_code"]


def test_confirm_with_no_seats_is_rejected(client, alice, event):
    b = new_booking(client, alice, event["id"])
    assert client.post(f"/bookings/{b}/dev-confirm", headers=alice.headers).status_code == 409


def test_expired_hold_cannot_be_confirmed(client, alice, admin_db, event):
    seat = event["seats"]["A1"]["id"]
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, seat)
    past = "2000-01-01T00:00:00+00:00"
    admin_db.table("seats").update({"hold_expires_at": past}).eq("id", seat).execute()
    assert client.post(f"/bookings/{b}/dev-confirm", headers=alice.headers).status_code == 409


def test_sweeper_releases_expired_holds(client, alice, bob, admin_db, event):
    seat = event["seats"]["A1"]["id"]
    hold(client, alice, new_booking(client, alice, event["id"]), seat)
    admin_db.table("seats").update({"hold_expires_at": "2000-01-01T00:00:00+00:00"}).eq("id", seat).execute()
    admin_db.rpc("release_expired_holds").execute()
    row = admin_db.table("seats").select("status").eq("id", seat).execute().data[0]
    assert row["status"] == "available"
    assert hold(client, bob, new_booking(client, bob, event["id"]), seat).status_code == 200
