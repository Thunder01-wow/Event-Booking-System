def test_events_list_has_stats(client, event):
    ev = next(e for e in client.get("/events").json() if e["id"] == event["id"])
    assert ev["total_seats"] == 5
    assert ev["available_seats"] == 5
    assert float(ev["min_price"]) == 500


def test_seats_listing(client, event):
    seats = client.get(f"/events/{event['id']}/seats").json()
    assert {s["seat_label"] for s in seats} == {"A1", "A2", "A3", "A4", "B1"}
    assert all(s["status"] == "available" for s in seats)


def test_draft_event_is_not_listed(client, admin_db, event):
    admin_db.table("events").update({"status": "draft"}).eq("id", event["id"]).execute()
    assert event["id"] not in [e["id"] for e in client.get("/events").json()]


def test_stats_follow_holds(client, alice, event):
    from conftest import new_booking, hold
    b = new_booking(client, alice, event["id"])
    assert hold(client, alice, b, event["seats"]["A1"]["id"]).status_code == 200
    ev = next(e for e in client.get("/events").json() if e["id"] == event["id"])
    assert ev["available_seats"] == 4
