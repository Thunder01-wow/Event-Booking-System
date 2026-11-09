create table if not exists venues (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    address     text,
    city        text,
    capacity    integer check (capacity is null or capacity > 0),
    created_at  timestamptz not null default now()
);

create table if not exists events (
    id          uuid primary key default gen_random_uuid(),
    venue_id    uuid not null references venues (id) on delete restrict,
    title       text not null,
    description text,
    category    text,
    starts_at   timestamptz not null,
    ends_at     timestamptz not null,
    status      text not null default 'draft' check (status in ('draft', 'published', 'cancelled')),
    created_by  uuid references profiles (id) on delete set null,
    created_at  timestamptz not null default now(),
    constraint events_time_order check (ends_at > starts_at)
);

create index if not exists idx_events_venue_id on events (venue_id);
create index if not exists idx_events_status_starts_at on events (status, starts_at);
