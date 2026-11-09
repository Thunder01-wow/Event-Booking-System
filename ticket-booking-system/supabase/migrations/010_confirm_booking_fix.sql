-- Fix for confirm_booking (from 007): it must refuse to confirm a booking that
-- has no held seats, or whose holds have already expired. Without this, a late
-- payment could confirm seats the sweep hasn't released yet, or confirm an
-- empty booking.
create or replace function confirm_booking(p_booking_id uuid)
returns bookings
language plpgsql
security definer
set search_path = public
as $$
declare
    v_booking bookings;
    v_count   integer;
begin
    select * into v_booking from bookings where id = p_booking_id for update;

    if v_booking.id is null then
        raise exception 'booking_not_found';
    end if;
    if v_booking.status <> 'pending' then
        raise exception 'booking_not_pending';
    end if;

    if exists (
        select 1 from seats
        where held_by_booking_id = p_booking_id
          and status = 'held'
          and hold_expires_at <= now()
    ) then
        raise exception 'hold_expired';
    end if;

    update seats
        set status = 'booked'
        where held_by_booking_id = p_booking_id
          and status = 'held';

    get diagnostics v_count = row_count;
    if v_count = 0 then
        raise exception 'no_seats_held';
    end if;

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
