-- Schedules release_expired_holds() to run every minute via pg_cron, so
-- seats whose hold window passed without payment are freed automatically
-- instead of only being released the next time something happens to call
-- the function manually.
-- pg_cron's own extension script fixes its schema to `cron`, so no
-- `WITH SCHEMA` clause is used here — specifying a different one would
-- conflict with that and fail.
create extension if not exists pg_cron;

-- Drop any existing schedule with this name first, so re-running this
-- migration doesn't create a duplicate job.
select cron.unschedule('release-expired-holds')
where exists (
    select 1 from cron.job where jobname = 'release-expired-holds'
);

select cron.schedule(
    'release-expired-holds',
    '* * * * *',  -- every minute
    $$ select release_expired_holds(); $$
);
