-- Fixes infinite recursion (Postgres error 54001, "stack depth limit
-- exceeded") caused by is_admin() querying `profiles` while `profiles`'s own
-- RLS policy calls is_admin() to decide whether to allow that same query.
-- SECURITY DEFINER makes this function run with the privileges of its owner
-- (bypassing RLS internally) instead of the calling user's, so its internal
-- read of `profiles` no longer re-triggers `profiles`'s RLS policy.
create or replace function is_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
    select exists (
        select 1 from profiles where id = auth.uid() and role = 'admin'
    );
$$;
