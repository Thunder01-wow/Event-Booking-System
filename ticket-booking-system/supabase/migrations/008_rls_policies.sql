-- Helper: is the current JWT's user an admin? Used throughout the policies
-- below instead of repeating the same subquery everywhere.
create or replace function is_admin()
returns boolean
language sql
stable
as $$
    select exists (
        select 1 from profiles where id = auth.uid() and role = 'admin'
    );
$$;

alter table profiles           enable row level security;
alter table venues             enable row level security;
alter table events             enable row level security;
alter table seats              enable row level security;
alter table bookings           enable row level security;
alter table tickets            enable row level security;
alter table payments           enable row level security;
alter table webhook_events     enable row level security;

-- ---------------------------------------------------------------------------
-- profiles: a user can read/update their own row; admins can read everyone's.
-- Row creation happens via the handle_new_user trigger (SECURITY DEFINER),
-- so there is deliberately no public INSERT policy here.
-- ---------------------------------------------------------------------------
create policy "profiles_select_own_or_admin" on profiles
    for select using (id = auth.uid() or is_admin());

create policy "profiles_update_own" on profiles
    for update using (id = auth.uid());

-- ---------------------------------------------------------------------------
-- venues: public read (browsing needs no auth); writes are admin-only.
-- ---------------------------------------------------------------------------
create policy "venues_select_all" on venues
    for select using (true);

create policy "venues_write_admin" on venues
    for all using (is_admin()) with check (is_admin());

-- ---------------------------------------------------------------------------
-- events: published events are public; drafts are visible to their creator
-- and admins only. Writes are admin-only.
-- ---------------------------------------------------------------------------
create policy "events_select_published_or_owner" on events
    for select using (
        status = 'published' or is_admin() or created_by = auth.uid()
    );

create policy "events_write_admin" on events
    for all using (is_admin()) with check (is_admin());

-- ---------------------------------------------------------------------------
-- seats: readable for any published event (need the seat map to book);
-- direct writes are admin-only — normal status changes go through the
-- hold_seat / confirm_booking / cancel_booking functions, which run as
-- SECURITY DEFINER and bypass these policies entirely.
-- ---------------------------------------------------------------------------
create policy "seats_select_for_visible_events" on seats
    for select using (
        exists (
            select 1 from events e
            where e.id = seats.event_id
              and (e.status = 'published' or is_admin())
        )
    );

create policy "seats_write_admin" on seats
    for all using (is_admin()) with check (is_admin());

-- ---------------------------------------------------------------------------
-- bookings: a user sees and creates only their own; admins see all.
-- Status transitions (confirm/cancel/expire) happen through functions,
-- so there is no generic UPDATE policy for end users.
-- ---------------------------------------------------------------------------
create policy "bookings_select_own_or_admin" on bookings
    for select using (user_id = auth.uid() or is_admin());

create policy "bookings_insert_own" on bookings
    for insert with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- tickets: visible to the booking's owner (and admins). No direct writes —
-- confirm_booking() issues tickets as SECURITY DEFINER.
-- ---------------------------------------------------------------------------
create policy "tickets_select_via_booking" on tickets
    for select using (
        exists (
            select 1 from bookings b
            where b.id = tickets.booking_id
              and (b.user_id = auth.uid() or is_admin())
        )
    );

-- ---------------------------------------------------------------------------
-- payments: read-only visibility into your own booking's payment status.
-- All writes come from the webhook handler via the service-role key, which
-- bypasses RLS entirely, so no insert/update policy is needed here.
-- ---------------------------------------------------------------------------
create policy "payments_select_via_booking" on payments
    for select using (
        exists (
            select 1 from bookings b
            where b.id = payments.booking_id
              and (b.user_id = auth.uid() or is_admin())
        )
    );

-- ---------------------------------------------------------------------------
-- webhook_events: no policies for anon/authenticated at all. Only the
-- service role (which bypasses RLS) reads or writes this table.
-- ---------------------------------------------------------------------------
