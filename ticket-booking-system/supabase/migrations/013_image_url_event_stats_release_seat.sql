-- 013: event images, per-event stats view, and releasing a single held seat.

alter table events add column if not exists image_url text;

-- security_invoker keeps RLS in force for whoever queries the view.
create or replace view event_stats with (security_invoker = true) as
select
    event_id,
    min(price)                                   as min_price,
    count(*)                                     as total_seats,
    count(*) filter (where status = 'available') as available_seats
from seats
group by event_id;

grant select on event_stats to anon, authenticated, service_role;

create or replace function release_seat(p_seat_id uuid, p_booking_id uuid)
returns seats
language plpgsql
security definer
set search_path = public
as $$
declare
    v_booking bookings;
    v_seat    seats;
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
        set status = 'available', held_by_booking_id = null, hold_expires_at = null,
            version = version + 1
        where id = p_seat_id
          and held_by_booking_id = p_booking_id
          and status = 'held'
        returning * into v_seat;

    if v_seat.id is null then
        raise exception 'seat_not_held';
    end if;

    return v_seat;
end;
$$;

revoke execute on function release_seat(uuid, uuid) from public;
grant execute on function release_seat(uuid, uuid) to authenticated;
