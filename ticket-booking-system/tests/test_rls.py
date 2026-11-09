"""Row Level Security, checked directly against the database as different roles."""
import pytest
from supabase import create_client

from conftest import ANON_KEY, SUPABASE_URL, new_booking, hold


def _user_client(token):
    c = create_client(SUPABASE_URL, ANON_KEY)
    c.postgrest.auth(token)
    return c


def test_user_cannot_read_other_users_bookings(client, alice, bob, event):
    b = new_booking(client, alice, event["id"])
    rows = _user_client(bob.token).table("bookings").select("id").eq("id", b).execute().data
    assert rows == []


def test_anonymous_can_read_published_events_but_not_write(event):
    anon = create_client(SUPABASE_URL, ANON_KEY)
    assert anon.table("events").select("id").eq("id", event["id"]).execute().data
    with pytest.raises(Exception):
        anon.table("events").insert({"title": "x"}).execute()


def test_normal_user_cannot_write_events_directly(alice, event):
    c = _user_client(alice.token)
    res = c.table("events").update({"title": "pwned"}).eq("id", event["id"]).execute()
    assert res.data == []  # RLS filters the row: nothing updated


def test_authenticated_cannot_call_confirm_booking(client, alice, event):
    b = new_booking(client, alice, event["id"])
    hold(client, alice, b, event["seats"]["A1"]["id"])
    with pytest.raises(Exception):
        _user_client(alice.token).rpc("confirm_booking", {"p_booking_id": b}).execute()


def test_authenticated_cannot_call_release_expired_holds(alice):
    with pytest.raises(Exception):
        _user_client(alice.token).rpc("release_expired_holds").execute()


def test_user_cannot_set_own_role_to_admin(alice, admin_db):
    try:
        _user_client(alice.token).table("profiles").update({"role": "admin"}).eq("id", alice.id).execute()
    except Exception:  # noqa: BLE001  (the database rejects it: that's the goal)
        pass
    role = admin_db.table("profiles").select("role").eq("id", alice.id).execute().data[0]["role"]
    assert role != "admin"


def test_user_can_still_update_own_name(alice, admin_db):
    _user_client(alice.token).table("profiles").update({"full_name": "Alice Test"}).eq("id", alice.id).execute()
    name = admin_db.table("profiles").select("full_name").eq("id", alice.id).execute().data[0]["full_name"]
    assert name == "Alice Test"
