-- Add dismissed / cancelled pipeline statuses

alter table public.jobs drop constraint if exists jobs_status_check;
alter table public.jobs
  add constraint jobs_status_check
  check (status in (
    'new', 'analyzed', 'shortlisted', 'cv_ready',
    'applied', 'interview', 'offer', 'rejected', 'archived', 'not_related'
  ));

alter table public.applications drop constraint if exists applications_status_check;
alter table public.applications
  add constraint applications_status_check
  check (status in (
    'new', 'analyzed', 'shortlisted', 'cv_ready',
    'applied', 'interview', 'offer', 'rejected', 'archived', 'not_related'
  ));

alter table public.prospects drop constraint if exists prospects_status_check;
alter table public.prospects
  add constraint prospects_status_check
  check (status in (
    'new', 'contacted', 'replied', 'call_booked',
    'proposal', 'won', 'lost', 'nurture', 'cancelled'
  ));
