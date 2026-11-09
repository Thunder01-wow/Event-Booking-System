"""
Integration tests: they talk to a RUNNING API (API_BASE_URL) that is connected
to a TEST Supabase project. See tests/README.md for setup.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env.test")

API = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
PASSWORD = "Test-pass-123!"


def pytest_sessionstart(session):
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY") if not os.getenv(k)]
    if missing:
        pytest.exit(f"Missing {', '.join(missing)}. Copy .env.test.example to .env.test and fill it in.", returncode=2)
    try:
        httpx.get(f"{API}/health", timeout=5).raise_for_status()
    except Exception as e:  # noqa: BLE001
        pytest.exit(f"API not reachable at {API}/health ({e}). Start it first (see tests/README.md).", returncode=2)


@pytest.fixture(scope="session")
def admin_db():
    """Service-role Supabase client (bypasses RLS) for test setup/teardown and assertions."""
    return create_client(SUPABASE_URL, SERVICE_KEY)


class TestUser:
    def __init__(self, id, email, token):
        self.id, self.email, self.token = id, email, token

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}


def _make_user(admin_db, label="user", role=None) -> TestUser:
    email = f"test-{label}-{uuid.uuid4().hex[:10]}@example.com"
    created = admin_db.auth.admin.create_user({"email": email, "password": PASSWORD, "email_confirm": True})
    uid = str(created.user.id)
    if role:
        admin_db.table("profiles").update({"role": role}).eq("id", uid).execute()
    r = httpx.post(f"{API}/auth/login", data={"username": email, "password": PASSWORD}, timeout=20)
    r.raise_for_status()
    return TestUser(uid, email, r.json()["access_token"])


@pytest.fixture(scope="session")
def created_users(admin_db):
    ids = []
    yield ids
    for uid in ids:
        try:
            admin_db.auth.admin.delete_user(uid)
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture(scope="session")
def make_user(admin_db, created_users):
    def factory(label="user", role=None):
        u = _make_user(admin_db, label, role)
        created_users.append(u.id)
        return u
    return factory


@pytest.fixture(scope="session")
def alice(make_user):
    return make_user("alice")


@pytest.fixture(scope="session")
def bob(make_user):
    return make_user("bob")


@pytest.fixture(scope="session")
def admin_user(make_user):
    return make_user("admin", role="admin")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=API, timeout=30) as c:
        yield c


@pytest.fixture()
def event(admin_db):
    """A fresh published event with 4 general seats (A1-A4, 500) and 1 premium (B1, 1000). Cleaned up after."""
    venue = admin_db.table("venues").insert({"name": f"Test Venue {uuid.uuid4().hex[:6]}", "city": "Testville", "capacity": 10}).execute().data[0]
    start = datetime.now(timezone.utc) + timedelta(days=7)
    ev = admin_db.table("events").insert({
        "venue_id": venue["id"], "title": "Test Event", "category": "Music",
        "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=3)).isoformat(),
        "status": "published",
    }).execute().data[0]
    seats = [{"event_id": ev["id"], "seat_label": f"A{i}", "category": "general", "price": 500} for i in range(1, 5)]
    seats.append({"event_id": ev["id"], "seat_label": "B1", "category": "premium", "price": 1000})
    rows = admin_db.table("seats").insert(seats).execute().data
    ev["seats"] = {s["seat_label"]: s for s in rows}
    yield ev
    try:
        bookings = admin_db.table("bookings").select("id").eq("event_id", ev["id"]).execute().data
        for b in bookings:
            admin_db.table("tickets").delete().eq("booking_id", b["id"]).execute()
        admin_db.table("bookings").delete().eq("event_id", ev["id"]).execute()
        admin_db.table("events").delete().eq("id", ev["id"]).execute()  # seats cascade
        admin_db.table("venues").delete().eq("id", venue["id"]).execute()
    except Exception:  # noqa: BLE001
        pass


# ---- small API helpers -------------------------------------------------------
def new_booking(client, user, event_id) -> str:
    r = client.post("/bookings", json={"event_id": event_id}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def hold(client, user, booking_id, seat_id):
    return client.post(f"/bookings/{booking_id}/hold-seat", json={"seat_id": seat_id}, headers=user.headers)
