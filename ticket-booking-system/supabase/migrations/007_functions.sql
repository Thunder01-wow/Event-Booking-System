-- ============================================================================
-- hold_seat: the single atomic operation that prevents double-booking.
-- Called by an authenticated user via RPC once they've created a pending
-- booking and want to lock in a specific seat while they pay.
-- The UPDATE ... WHERE status = 'available' is what makes this safe under
-- concurrency: only one of two simultaneous callers can win the row.
-- ============================================================================
create or replace function hold_seat(
    p_seat_id uuid,
    p_booking_id uuid,
    p_hold_seconds integer default 600
)
returns seats
language plpgsql
security definer
set search_path = public
as $$
declare
    v_seat    seats;
    v_booking bookings;
begin
    select * into v_booking from bookings where id = p_booking_id;

    if v_booking.id is null then
        raise exception 'booking_not_found';
    end if;
    if v_booking.user_id <> auth.uid() then
        raise exception 'not_your_booking';
    end if;
    if v_booking.status <> 'pending' then
        raise exception 'booking_not_pending';
    end if;

    update seats
        set status             = 'held',
            held_by_booking_id = p_booking_id,
            hold_expires_at    = now() + make_interval(secs => p_hold_seconds),
            version            = version + 1
        where id = p_seat_id
          and event_id = v_booking.event_id
          and status = 'available'
        returning * into v_seat;

    if v_seat.id is null then
        raise exception 'seat_unavailable';
    end if;

    return v_seat;
end;
$$;

revoke execute on function hold_seat(uuid, uuid, integer) from public;
grant execute on function hold_seat(uuid, uuid, integer) to authenticated;


-- ============================================================================
-- confirm_booking: called server-side (service role) after a payment
-- provider confirms success. Converts held seats -> booked, issues tickets,
-- and marks the booking confirmed. Only seats still held by THIS booking
-- are touched, so an expired/stolen hold can't be confirmed after the fact.
-- ============================================================================
create or replace function confirm_booking(p_booking_id uuid)
returns bookings
language plpgsql
security definer
set search_path = public
as $$
declare
    v_booking bookings;
begin
    select * into v_booking from bookings where id = p_booking_id for update;

    if v_booking.id is null then
        raise exception 'booking_not_found';
    end if;
    if v_booking.status <> 'pending' then
        raise exception 'booking_not_pending';
    end if;

    update seats
        set status = 'booked'
        where held_by_booking_id = p_booking_id
          and status = 'held';

    insert into tickets (booking_id, seat_id)
    select p_booking_id, id
    from seats
    where held_by_booking_id = p_booking_id
      and status = 'booked'
      and id not in (select seat_id from tickets);

    update bookings
        set status = 'confirmed', updated_at = now()
        where id = p_booking_id
        returning * into v_booking;

    return v_booking;
end;
$$;

revoke execute on function confirm_booking(uuid) from public, authenticated, anon;
grant execute on function confirm_booking(uuid) to service_role;


-- ============================================================================
-- cancel_booking: callable by the owning user. Releases any held/booked
-- seats back to available and marks the booking cancelled. Refund handling
-- (if the booking was already paid) is the caller's responsibility.
-- ============================================================================
create or replace function cancel_booking(p_booking_id uuid)
returns bookings
language plpgsql
security definer
set search_path = public
as $$
declare
    v_booking bookings;
begin
    select * into v_booking from bookings where id = p_booking_id for update;

    if v_booking.id is null then
        raise exception 'booking_not_found';
    end if;
    if v_booking.user_id <> auth.uid() then
        raise exception 'not_your_booking';
    end if;
    if v_booking.status not in ('pending', 'confirmed') then
        raise exception 'booking_not_cancellable';
    end if;

    update seats
        set status = 'available', held_by_booking_id = null, hold_expires_at = null
        where held_by_booking_id = p_booking_id;

    update bookings
        set status = 'cancelled', updated_at = now()
        where id = p_booking_id
        returning * into v_booking;

    return v_booking;
end;
$$;

revoke execute on function cancel_booking(uuid) from public;
grant execute on function cancel_booking(uuid) to authenticated;


-- ============================================================================
-- release_expired_holds: sweep for seats whose hold window passed without
-- payment. Meant to be run on a schedule (pg_cron or a scheduled Edge
-- Function using the service role key) — not exposed to end users.
-- ============================================================================
create or replace function release_expired_holds()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    v_count integer;
begin
    with expired as (
        update seats
            set status = 'available', held_by_booking_id = null, hold_expires_at = null
            where status = 'held'
              and hold_expires_at < now()
            returning 1
    )
    select count(*) into v_count from expired;

    update bookings
        set status = 'expired', updated_at = now()
        where status = 'pending'
          and id not in (select held_by_booking_id from seats where held_by_booking_id is not null)
          and created_at < now() - interval '1 hour';

    return v_count;
end;
$$;

revoke execute on function release_expired_holds() from public, authenticated, anon;
grant execute on function release_expired_holds() to service_role;
