-- Milestone 1 init schema for Job Intelligence
-- Tables: companies, jobs, job_analysis, job_scores, applications, resume_versions
-- Idempotent: remote may already have this schema from the SQL editor.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  domain text,
  country text,
  created_at timestamptz not null default timezone('utc', now()),
  constraint companies_name_unique unique (name)
);

create index if not exists companies_country_idx on public.companies (country);

-- ---------------------------------------------------------------------------
-- jobs
-- ---------------------------------------------------------------------------

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references public.companies (id) on delete set null,
  title text not null,
  location text,
  country text,
  remote_type text not null default 'unknown'
    check (remote_type in ('remote', 'hybrid', 'onsite', 'unknown')),
  source text not null default 'manual',
  source_job_id text,
  url text,
  description text not null,
  posted_at timestamptz,
  discovered_at timestamptz not null default timezone('utc', now()),
  status text not null default 'new'
    check (status in (
      'new', 'analyzed', 'shortlisted', 'cv_ready',
      'applied', 'interview', 'offer', 'rejected', 'archived'
    )),
  content_hash text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint jobs_url_unique unique (url),
  constraint jobs_content_hash_unique unique (content_hash)
);

create index if not exists jobs_status_idx on public.jobs (status);
create index if not exists jobs_country_idx on public.jobs (country);
create index if not exists jobs_discovered_at_idx on public.jobs (discovered_at desc);
create index if not exists jobs_company_id_idx on public.jobs (company_id);

drop trigger if exists jobs_set_updated_at on public.jobs;
create trigger jobs_set_updated_at
before update on public.jobs
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- job_analysis
-- ---------------------------------------------------------------------------

create table if not exists public.job_analysis (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  role_family text,
  seniority text,
  required_skills jsonb not null default '[]'::jsonb,
  preferred_skills jsonb not null default '[]'::jsonb,
  responsibilities jsonb not null default '[]'::jsonb,
  minimum_years_experience integer,
  education_requirement text,
  language_requirements jsonb not null default '[]'::jsonb,
  location_requirements jsonb not null default '[]'::jsonb,
  visa_notes text,
  salary_text text,
  analysis_json jsonb not null default '{}'::jsonb,
  llm_provider text,
  llm_model text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists job_analysis_job_id_idx on public.job_analysis (job_id);
create index if not exists job_analysis_role_family_idx on public.job_analysis (role_family);

-- ---------------------------------------------------------------------------
-- job_scores
-- ---------------------------------------------------------------------------

create table if not exists public.job_scores (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  total_score numeric(5,2) not null check (total_score >= 0 and total_score <= 100),
  skill_score numeric(5,2) not null default 0,
  experience_score numeric(5,2) not null default 0,
  role_score numeric(5,2) not null default 0,
  seniority_score numeric(5,2) not null default 0,
  location_score numeric(5,2) not null default 0,
  domain_score numeric(5,2) not null default 0,
  explanation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists job_scores_job_id_idx on public.job_scores (job_id);
create index if not exists job_scores_total_score_idx on public.job_scores (total_score desc);

-- ---------------------------------------------------------------------------
-- applications
-- ---------------------------------------------------------------------------

create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  status text not null default 'new'
    check (status in (
      'new', 'analyzed', 'shortlisted', 'cv_ready',
      'applied', 'interview', 'offer', 'rejected', 'archived'
    )),
  resume_version integer,
  applied_at timestamptz,
  response_at timestamptz,
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists applications_job_id_idx on public.applications (job_id);
create index if not exists applications_status_idx on public.applications (status);

drop trigger if exists applications_set_updated_at on public.applications;
create trigger applications_set_updated_at
before update on public.applications
for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- resume_versions
-- ---------------------------------------------------------------------------

create table if not exists public.resume_versions (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  version integer not null,
  content_json jsonb not null default '{}'::jsonb,
  content_markdown text not null default '',
  model text,
  created_at timestamptz not null default timezone('utc', now()),
  constraint resume_versions_job_version_unique unique (job_id, version)
);

create index if not exists resume_versions_job_id_idx on public.resume_versions (job_id);

-- ---------------------------------------------------------------------------
-- Row Level Security (single-user MVP)
-- Deny anon by default. Authenticated users get full access.
-- Service role bypasses RLS.
-- ---------------------------------------------------------------------------

alter table public.companies enable row level security;
alter table public.jobs enable row level security;
alter table public.job_analysis enable row level security;
alter table public.job_scores enable row level security;
alter table public.applications enable row level security;
alter table public.resume_versions enable row level security;

drop policy if exists companies_authenticated_all on public.companies;
create policy companies_authenticated_all
  on public.companies
  for all
  to authenticated
  using (true)
  with check (true);

drop policy if exists jobs_authenticated_all on public.jobs;
create policy jobs_authenticated_all
  on public.jobs
  for all
  to authenticated
  using (true)
  with check (true);

drop policy if exists job_analysis_authenticated_all on public.job_analysis;
create policy job_analysis_authenticated_all
  on public.job_analysis
  for all
  to authenticated
  using (true)
  with check (true);

drop policy if exists job_scores_authenticated_all on public.job_scores;
create policy job_scores_authenticated_all
  on public.job_scores
  for all
  to authenticated
  using (true)
  with check (true);

drop policy if exists applications_authenticated_all on public.applications;
create policy applications_authenticated_all
  on public.applications
  for all
  to authenticated
  using (true)
  with check (true);

drop policy if exists resume_versions_authenticated_all on public.resume_versions;
create policy resume_versions_authenticated_all
  on public.resume_versions
  for all
  to authenticated
  using (true)
  with check (true);
