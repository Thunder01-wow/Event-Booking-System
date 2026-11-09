-- One row per bookable seat per event. Status transitions:
--   available -> held    (hold_seat(), atomic, expires after a short window)
--   held      -> booked  (confirm_booking(), on payment success)
--   held      -> available (release_expired_holds() or explicit cancel)
--   booked    -> available (cancel_booking(), e.g. refund)
create table if not exists seats (
    id                  uuid primary key default gen_random_uuid(),
    event_id            uuid not null references events (id) on delete cascade,
    seat_label          text not null,           -- e.g. 'A12', or 'GA-042' for general admission
    category            text not null default 'general',
    price               numeric(10, 2) not null check (price >= 0),
    status              text not null default 'available'
                            check (status in ('available', 'held', 'booked')),
    held_by_booking_id  uuid references bookings (id) on delete set null,
    hold_expires_at     timestamptz,
    version             integer not null default 0,  -- optimistic-concurrency guard
    created_at          timestamptz not null default now(),

    unique (event_id, seat_label)
);

create index if not exists idx_seats_event_id_status on seats (event_id, status);
create index if not exists idx_seats_held_by_booking_id on seats (held_by_booking_id)
    where held_by_booking_id is not null;
-- Speeds up the periodic sweep for expired holds.
create index if not exists idx_seats_hold_expires_at on seats (hold_expires_at)
    where status = 'held';
