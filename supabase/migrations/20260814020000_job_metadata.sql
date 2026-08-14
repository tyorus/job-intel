-- Job listing metadata: deadline, salary, tags, apply URL, etc.

alter table public.jobs add column if not exists apply_url text;
alter table public.jobs add column if not exists deadline_at timestamptz;
alter table public.jobs add column if not exists salary_text text;
alter table public.jobs add column if not exists employment_type text;
alter table public.jobs add column if not exists department text;
alter table public.jobs add column if not exists seniority text;
alter table public.jobs add column if not exists tags jsonb not null default '[]'::jsonb;
alter table public.jobs add column if not exists metadata_json jsonb not null default '{}'::jsonb;

create index if not exists jobs_posted_at_idx on public.jobs (posted_at desc nulls last);
create index if not exists jobs_deadline_at_idx on public.jobs (deadline_at asc nulls last);
