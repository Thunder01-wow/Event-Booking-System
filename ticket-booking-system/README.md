# Event Ticket Booking System

FastAPI backend for event ticketing, using Supabase (Postgres + Auth + RLS) as the data layer.

## Stack
- **FastAPI** — API layer
- **Supabase** — Postgres, Auth, Row Level Security
- **Docker / docker-compose** — local dev environment

## Project layout

```
app/
  main.py              # FastAPI app entrypoint
  core/
    config.py          # settings loaded from env vars
  db/
    supabase_client.py  # Supabase client singleton
  routers/
    health.py          # health check route
  schemas/              # Pydantic request/response models (empty, ready to fill)
  models/               # domain models / DB row types (empty, ready to fill)
requirements.txt
Dockerfile
docker-compose.yml
.env.example
```

## Getting started

1. Create a Supabase project (or reuse the one from your Notes app).
2. Copy `.env.example` to `.env` and fill in your Supabase URL + keys.
3. Build and run:

   ```bash
   docker compose up --build
   ```

4. Visit `http://localhost:8000/docs` for the interactive API docs.
5. Confirm the scaffold is alive: `GET /health` should return `{"status": "ok"}`.

## Database schema

`supabase/migrations/` has the full schema, run in order:

| File | What it does |
|---|---|
| `001_extensions.sql` | enables `pgcrypto` for UUID generation |
| `002_profiles.sql` | `profiles` — 1:1 with `auth.users`, holds `role` (`customer`/`admin`) |
| `003_venues_events.sql` | `venues`, `events` |
| `004_bookings.sql` | `bookings` — one row per checkout attempt |
| `005_seats.sql` | `seats` — the concurrency-sensitive table (see below) |
| `006_tickets_payments.sql` | `tickets`, `payments`, `webhook_events` |
| `007_functions.sql` | `hold_seat`, `confirm_booking`, `cancel_booking`, `release_expired_holds` |
| `008_rls_policies.sql` | RLS on every table + the `is_admin()` helper |
| `009_triggers.sql` | auto-create a profile on signup; `updated_at` maintenance |

**Run them:** paste each file's contents into the Supabase Dashboard → SQL Editor, in order — or, if you have the Supabase CLI linked to your project, `supabase db push`.

### How seat concurrency actually works

`seats.status` moves through `available -> held -> booked` (or back to `available` on expiry/cancel). The only way to move a seat out of `available` is the `hold_seat()` function, which does:

```sql
update seats set status = 'held', ...
where id = p_seat_id and status = 'available'
returning *;
```

If two requests race for the same seat, only one `UPDATE` matches the `status = 'available'` condition — Postgres serializes the two `UPDATE`s and the loser gets zero rows back, so the function raises `seat_unavailable`. No explicit locking needed; the `WHERE status = 'available'` clause *is* the concurrency control.

Flow: create a `pending` booking → call `hold_seat()` for each chosen seat → on payment webhook success, call `confirm_booking()` (marks seats `booked`, issues `tickets`) → a scheduled job calls `release_expired_holds()` periodically to free seats whose hold window passed unpaid.

## API routes

| Route | What it does |
|---|---|
| `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` | Supabase Auth, wrapped for `/docs`'s Authorize button |
| `GET /events`, `GET /events/{id}`, `GET /events/{id}/seats` | public browsing, anon key |
| `POST /bookings` | start a checkout — creates a `pending` booking |
| `POST /bookings/{id}/hold-seat` | lock one seat (10 min); 409 if someone else got it first |
| `POST /bookings/{id}/cancel` | cancel and release held/booked seats |
| `GET /bookings`, `GET /bookings/{id}` | your own bookings, with seats + tickets |
| `POST /bookings/{id}/create-payment-order` | create a Razorpay Order for the booking's current total |
| `POST /webhooks/razorpay` | Razorpay calls this on payment events |
| `POST /bookings/{id}/dev-confirm` | **dev only** — skips payment, calls `confirm_booking()` directly |
| `POST /admin/venues`, `PATCH /admin/venues/{id}`, `DELETE /admin/venues/{id}` | manage venues — admin only |
| `POST /admin/events`, `PATCH /admin/events/{id}`, `DELETE /admin/events/{id}` | manage events — admin only |
| `POST /admin/events/{id}/seats`, `PATCH /admin/seats/{id}`, `DELETE /admin/seats/{id}` | manage seats (bulk-create supported) — admin only |

## Payments (Razorpay)

1. Get your **Key Id** / **Key Secret** from Razorpay Dashboard → Settings → API Keys, and put them in `.env` as `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`.
2. The checkout flow: client calls `POST /bookings/{id}/hold-seat` for each seat, then `POST /bookings/{id}/create-payment-order`, which returns `{order_id, amount, currency, key_id}`. Hand those to Razorpay's Checkout widget on the frontend — this backend never touches card details.
3. On payment success, Razorpay calls `POST /webhooks/razorpay`. That handler:
   - verifies the request is genuinely from Razorpay (HMAC signature over the raw body, via the SDK's `verify_webhook_signature`)
   - inserts a row into `webhook_events` keyed by Razorpay's `x-razorpay-event-id` header **before** doing anything else — since the insert fails on a retried delivery (unique constraint), a retry is a no-op and returns `already_processed` immediately
   - on `payment.captured`, updates the matching `payments` row and calls `confirm_booking()` via the service role, which is the only thing allowed to call it (see `007_functions.sql`)
   - on `payment.failed`, marks the payment row `failed` and leaves the booking `pending` so `release_expired_holds()` eventually frees its seats

**To actually receive webhooks locally**, Razorpay needs a public URL, so tunnel your local port 8000 (e.g. with `ngrok http 8000`), then register `https://<your-tunnel>.ngrok.app/webhooks/razorpay` in Razorpay Dashboard → Settings → Webhooks, select the `payment.captured` and `payment.failed` events, and copy the webhook secret it gives you into `RAZORPAY_WEBHOOK_SECRET`.

**To test without Razorpay at all**, use `POST /bookings/{id}/dev-confirm` instead — it calls `confirm_booking()` directly and is disabled automatically unless `APP_ENV=development`.

## Admin routes

Gated by `require_admin` (checks `profiles.role` via the service role, so a non-admin gets a clean 403), **and** independently by the `*_write_admin` RLS policies from `008_rls_policies.sql` — the route itself writes through the calling user's own client, not the service role, so RLS is a second line of defense even if the dependency check had a bug.

Example: creating an event and its seats in one go.

```
POST /admin/events
{"venue_id": "...", "title": "Winter Fest", "starts_at": "2026-12-20T18:00:00Z",
 "ends_at": "2026-12-20T21:00:00Z", "status": "published"}

POST /admin/events/{event_id}/seats
{"seats": [
  {"seat_label": "A1", "category": "vip", "price": 1500},
  {"seat_label": "A2", "category": "vip", "price": 1500}
]}
```

To make your own account an admin: `update profiles set role = 'admin' where id = auth.uid();` run once in the SQL Editor while logged in as that user, or by email as shown earlier in setup.

## Expired hold cleanup

`012_schedule_release_expired_holds.sql` schedules `release_expired_holds()` to run every minute via `pg_cron`, so a seat whose 10-minute hold passed without payment is freed automatically — no external scheduler needed. Check it's running:

```sql
select * from cron.job;               -- should show 'release-expired-holds'
select * from cron.job_run_details    -- recent run history
order by start_time desc limit 5;
```

### Still to build
- A `GET /payments/{booking_id}` route to check payment status from the frontend
- Rate limiting on `/auth/login` and `/bookings/{id}/hold-seat`
- Tests (nothing here has an automated test suite yet)

## Migration 013
Run `supabase/migrations/013_image_url_event_stats_release_seat.sql` in the Supabase SQL Editor. It adds `events.image_url`, the `event_stats` view (price/availability on the events list) and `release_seat()` (un-hold one seat via `POST /bookings/{id}/release-seat`).
