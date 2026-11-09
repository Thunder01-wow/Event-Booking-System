# Marquee — Event Ticket Booking Frontend

React (Vite) frontend for the Event Ticket Booking System backend.

## Stack
- React 19 + react-router-dom 7
- Plain CSS (design tokens in `src/index.css`), light box-office theme — no UI framework
- Fetch-based API client in `src/lib/api.js`
- Toast notifications (`src/context/ToastContext.jsx`) for transient action feedback — seat-hold failures, payment errors, cancellations
- Skeleton loaders (`src/components/Skeleton.jsx`) instead of plain "Loading…" text
- Client-side search + category/city filters on the events list

## Setup

1. `npm install`
2. `cp .env.example .env` and set `VITE_API_BASE_URL` if your backend isn't on `http://localhost:8000`.
3. Make sure the backend's `.env` has `FRONTEND_ORIGINS=http://localhost:5173` (or whatever port you run this on) — otherwise the browser will block every request with a CORS error.
4. `npm run dev`, then open `http://localhost:5173`.

## Pages

| Route | What it is |
|---|---|
| `/` | Browse published events |
| `/events/:id` | Seat map — click an available seat to hold it immediately (each click is a real API call, not a local-only selection — the hold timer starts the moment you click) |
| `/checkout/:bookingId` | Summary, hold countdown, pay with Razorpay or the `dev-confirm` fallback |
| `/tickets/:bookingId` | Ticket stub with seat + ticket code |
| `/bookings` | Your booking history |
| `/login`, `/signup` | Auth |

## How seat holding works here

Clicking an available seat calls `POST /bookings/{id}/hold-seat` immediately — there's no "add to cart then confirm" step, because the backend's hold starts a real 10-minute timer at the moment of the call, so staging seats client-side first would be misleading about when the clock actually starts. If someone else grabs a seat first, the backend returns `409` and the UI shows that seat's real status.

There's no partial "undo" for a single seat — the backend only supports cancelling the whole booking (`cancel_booking`), not releasing one held seat. "Cancel selection" does that and lets you start over.

## Payments

If `POST /bookings/{id}/create-payment-order` returns `503` (Razorpay not configured on the backend yet), the checkout page automatically falls back to a "Simulate payment (test mode)" button that calls `dev-confirm` instead. Once Razorpay is configured server-side, this fallback stops appearing on its own — no frontend changes needed.

When Razorpay *is* configured: after a successful payment in the Razorpay widget, the frontend polls `GET /bookings/{id}` every 2 seconds (up to 30s) waiting for `status: "confirmed"`, rather than trusting Razorpay's client-side callback directly — the backend's webhook is the actual source of truth for whether payment succeeded.

## Error display: toast vs inline

Transient action failures (seat-hold conflicts, payment errors, cancel failures) show as **toasts** — they don't block the page and clear on their own. Failures that leave the page unable to function (an event that doesn't exist, a booking that failed to load, an expired hold, a cancelled booking) stay as **inline banners**, since those need to stay visible until the user does something about them. Form validation (login/signup) stays inline too, attached to the form itself.

## A known rough edge

`MyBookingsPage` fetches all published events separately to look up each booking's event title. If an event gets unpublished or deleted after you booked it, its title won't resolve and the row just shows "Event" instead. A dedicated endpoint that returns booking + event data joined would fix this properly — not built yet.

## Seatly redesign
- Routes: `/` Discover, `/events/:id`, `/login`, `/signup`, `/about`, `/checkout/:bookingId`, `/tickets`.
- Event images: set `image_url` on an event (`PATCH /admin/events/{id}` with `{"image_url": "https://..."}`). Events without one show a gradient placeholder.
- Requires backend migration `013_image_url_event_stats_release_seat.sql`.
