# Tests

Integration tests that call a **running API** connected to a **separate test Supabase project**.
They create and delete users, events, bookings and tickets, so never point them at your real project.

## One-time setup
1. Create a second Supabase project (free tier is fine). Run migrations `001`-`014` in its SQL Editor.
2. Copy `.env.test.example` to `.env.test` and fill in the TEST project's URL and keys.
3. Install dev dependencies: `pip install -r requirements-dev.txt` (use a virtualenv).

## Run
Terminal 1 (API against the test project):
```
docker compose -f docker-compose.test.yml up --build
```
Terminal 2:
```
pytest                       # everything
pytest tests/test_concurrency.py   # the double-booking race
pytest -k webhook            # one area
```
Use `CONCURRENCY_USERS=20 pytest tests/test_concurrency.py` for a bigger race.

## What is covered
- `test_auth.py`: 401/403 rules, admin-only routes, `image_url` update
- `test_events.py`: listing, availability stats, drafts hidden
- `test_booking_rules.py`: holds, release, cancel, ownership, confirm, expiry, sweeper
- `test_concurrency.py`: N simultaneous holds on one seat, exactly one wins
- `test_payments_webhook.py`: signature check, idempotent replay, expired hold
- `test_rls.py`: row-level security and function permissions checked as each role
