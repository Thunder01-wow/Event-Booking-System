-- One ticket is issued per seat once a booking is confirmed.
create table if not exists tickets (
    id              uuid primary key default gen_random_uuid(),
    booking_id      uuid not null references bookings (id) on delete cascade,
    seat_id         uuid not null unique references seats (id) on delete restrict,
    ticket_code     text not null unique default encode(gen_random_bytes(8), 'hex'),
    issued_at       timestamptz not null default now(),
    checked_in_at   timestamptz
);

create index if not exists idx_tickets_booking_id on tickets (booking_id);

-- One row per payment attempt against a booking.
create table if not exists payments (
    id                  uuid primary key default gen_random_uuid(),
    booking_id          uuid not null references bookings (id) on delete cascade,
    provider            text not null,             -- e.g. 'razorpay', 'stripe'
    provider_payment_id text not null,
    amount              numeric(10, 2) not null check (amount >= 0),
    status              text not null default 'pending'
                            check (status in ('pending', 'succeeded', 'failed', 'refunded')),
    created_at          timestamptz not null default now(),

    unique (provider, provider_payment_id)
);

create index if not exists idx_payments_booking_id on payments (booking_id);

-- Raw webhook deliveries, kept for idempotency + audit/debugging.
-- The unique constraint on (provider, provider_event_id) is what makes
-- webhook processing idempotent against provider retries.
create table if not exists webhook_events (
    id                  uuid primary key default gen_random_uuid(),
    provider            text not null,
    provider_event_id   text not null,
    payload             jsonb not null,
    processed_at        timestamptz,
    received_at         timestamptz not null default now(),

    unique (provider, provider_event_id)
);
