-- A booking is a single checkout attempt by a user for one or more seats
-- on one event. Seats are linked to it via seats.held_by_booking_id while
-- held, and via tickets once confirmed.
create table if not exists bookings (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references profiles (id) on delete cascade,
    event_id        uuid not null references events (id) on delete restrict,
    status          text not null default 'pending'
                        check (status in ('pending', 'confirmed', 'cancelled', 'expired')),
    total_amount    numeric(10, 2) not null default 0 check (total_amount >= 0),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists idx_bookings_user_id on bookings (user_id);
create index if not exists idx_bookings_event_id on bookings (event_id);
create index if not exists idx_bookings_status on bookings (status);
