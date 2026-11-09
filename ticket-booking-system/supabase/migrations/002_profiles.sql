-- Profiles extend auth.users with app-specific fields (role, display name).
-- One row per Supabase Auth user, created automatically via trigger (see 008_triggers.sql).
create table if not exists profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    full_name   text,
    role        text not null default 'customer' check (role in ('customer', 'admin')),
    created_at  timestamptz not null default now()
);

comment on table profiles is 'App-level user profile + role, 1:1 with auth.users.';
