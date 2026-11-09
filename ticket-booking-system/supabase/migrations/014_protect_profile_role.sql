-- 014: close a privilege-escalation hole.
-- The "profiles_update_own" policy lets a user update their own row, which
-- included the `role` column, so any logged-in user could make themselves admin.
-- RLS can't restrict individual columns, so a trigger blocks role changes made
-- by a signed-in user. Changes from the SQL Editor or the service role key
-- (where auth.uid() is null) still work, which is how you promote an admin.

create or replace function prevent_role_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if new.role is distinct from old.role and auth.uid() is not null then
        raise exception 'role_change_forbidden' using errcode = '42501';
    end if;
    return new;
end;
$$;

drop trigger if exists profiles_prevent_role_change on profiles;
create trigger profiles_prevent_role_change
    before update on profiles
    for each row execute function prevent_role_change();
