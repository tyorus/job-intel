-- Article / content posts (web + LinkedIn publish tracking)
-- Additive: jobs / prospects / applications unchanged
-- Idempotent: remote may already have this schema from the SQL editor.

-- ---------------------------------------------------------------------------
-- posts
-- ---------------------------------------------------------------------------

create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  summary text,
  body text,
  tags text[] not null default '{}',
  cover_url text,
  canonical_url text,
  notes text,
  metadata_json jsonb not null default '{}'::jsonb,
  media_json jsonb not null default '[]'::jsonb,
  channels text[] not null default '{}',
  web_url text,
  linkedin_url text,
  scheduled_at timestamptz,
  published_at timestamptz,
  status text not null default 'idea'
    check (status in ('idea', 'draft', 'scheduled', 'published', 'archived')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint posts_channels_valid check (
    channels <@ array['web', 'linkedin']::text[]
  )
);

create index if not exists posts_status_idx on public.posts (status);
create index if not exists posts_published_at_idx on public.posts (published_at desc nulls last);
create index if not exists posts_scheduled_at_idx on public.posts (scheduled_at asc nulls last);
create index if not exists posts_created_at_idx on public.posts (created_at desc);
create index if not exists posts_channels_idx on public.posts using gin (channels);

drop trigger if exists posts_set_updated_at on public.posts;
create trigger posts_set_updated_at
before update on public.posts
for each row execute function public.set_updated_at();

alter table public.posts enable row level security;

drop policy if exists posts_authenticated_all on public.posts;
create policy posts_authenticated_all
  on public.posts
  for all
  to authenticated
  using (true)
  with check (true);

-- ---------------------------------------------------------------------------
-- progress_events: allow post entity_type
-- ---------------------------------------------------------------------------

alter table public.progress_events
  drop constraint if exists progress_events_entity_type_check;

alter table public.progress_events
  add constraint progress_events_entity_type_check
  check (entity_type in ('job', 'prospect', 'post'));
