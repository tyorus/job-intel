-- Tracker additions: client prospects + progress timeline
-- Additive on Milestone 1 (companies / jobs / applications remain unchanged)

-- ---------------------------------------------------------------------------
-- prospects (freelance services pipeline)
-- ---------------------------------------------------------------------------

create table public.prospects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  company text,
  country text,
  role text,
  source text,
  potential_problem text,
  date_contacted date,
  channel text,
  proposal_sent boolean not null default false,
  response text,
  status text not null default 'new'
    check (status in (
      'new', 'contacted', 'replied', 'call_booked',
      'proposal', 'won', 'lost', 'nurture'
    )),
  package text not null default 'unknown'
    check (package in ('audit', 'brief', 'retainer', 'unknown')),
  follow_up_date date,
  next_action text,
  value_estimate_usd numeric(10,2),
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index prospects_status_idx on public.prospects (status);
create index prospects_package_idx on public.prospects (package);
create index prospects_follow_up_date_idx on public.prospects (follow_up_date);
create index prospects_created_at_idx on public.prospects (created_at desc);

create trigger prospects_set_updated_at
before update on public.prospects
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- progress_events (job or prospect status timeline)
-- ---------------------------------------------------------------------------

create table public.progress_events (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null
    check (entity_type in ('job', 'prospect')),
  entity_id uuid not null,
  status text not null,
  note text,
  created_at timestamptz not null default timezone('utc', now())
);

create index progress_events_entity_idx
  on public.progress_events (entity_type, entity_id, created_at desc);
create index progress_events_created_at_idx
  on public.progress_events (created_at desc);

-- ---------------------------------------------------------------------------
-- Row Level Security (single-user MVP, same pattern as init)
-- ---------------------------------------------------------------------------

alter table public.prospects enable row level security;
alter table public.progress_events enable row level security;

create policy prospects_authenticated_all
  on public.prospects
  for all
  to authenticated
  using (true)
  with check (true);

create policy progress_events_authenticated_all
  on public.progress_events
  for all
  to authenticated
  using (true)
  with check (true);
