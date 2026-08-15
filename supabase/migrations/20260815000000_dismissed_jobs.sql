-- Fingerprints for jobs marked not related, so scrapes do not re-insert them.

create table if not exists public.dismissed_jobs (
  id uuid primary key default gen_random_uuid(),
  url text,
  content_hash text,
  created_at timestamptz not null default timezone('utc', now()),
  constraint dismissed_jobs_url_unique unique (url),
  constraint dismissed_jobs_content_hash_unique unique (content_hash)
);

create index if not exists dismissed_jobs_url_idx on public.dismissed_jobs (url);
create index if not exists dismissed_jobs_content_hash_idx on public.dismissed_jobs (content_hash);

alter table public.dismissed_jobs enable row level security;

drop policy if exists dismissed_jobs_authenticated_all on public.dismissed_jobs;
create policy dismissed_jobs_authenticated_all
  on public.dismissed_jobs
  for all
  to authenticated
  using (true)
  with check (true);
