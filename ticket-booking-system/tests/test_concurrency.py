"""The headline test: many users race for ONE seat; exactly one may win."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from conftest import API, new_booking

N = int(os.getenv("CONCURRENCY_USERS", "10"))


@pytest.mark.slow
def test_only_one_of_many_simultaneous_holds_wins(client, make_user, admin_db, event):
    seat = event["seats"]["A1"]["id"]
    users = [make_user(f"racer{i}") for i in range(N)]
    bookings = [new_booking(client, u, event["id"]) for u in users]

    barrier = threading.Barrier(N)

    def attempt(i):
        with httpx.Client(base_url=API, timeout=60) as c:
            barrier.wait()  # release all requests at the same moment
            return c.post(f"/bookings/{bookings[i]}/hold-seat", json={"seat_id": seat}, headers=users[i].headers).status_code

    with ThreadPoolExecutor(max_workers=N) as pool:
        codes = list(pool.map(attempt, range(N)))

    assert codes.count(200) == 1, f"expected exactly 1 winner, got {codes}"
    assert codes.count(409) == N - 1, f"expected {N - 1} conflicts, got {codes}"

    row = admin_db.table("seats").select("status, held_by_booking_id").eq("id", seat).execute().data[0]
    assert row["status"] == "held"
    assert row["held_by_booking_id"] in bookings
