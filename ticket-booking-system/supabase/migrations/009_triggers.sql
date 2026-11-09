-- Automatically create a profiles row whenever someone signs up via
-- Supabase Auth, so every auth.users row has a matching profile with a
-- default 'customer' role.
create or replace function handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into profiles (id, full_name)
    values (new.id, new.raw_user_meta_data ->> 'full_name');
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function handle_new_user();


-- Keep bookings.updated_at current on every row update.
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists bookings_set_updated_at on bookings;
create trigger bookings_set_updated_at
    before update on bookings
    for each row execute function set_updated_at();
