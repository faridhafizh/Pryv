-- Microdata Privacy Guard: skema + Row Level Security.
-- Jalankan di Supabase SQL Editor (atau supabase db push).

create table if not exists public.anonymization_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  original_filename text not null,
  rows_in integer not null,
  rows_out integer not null,
  rows_dropped integer not null,
  k integer not null,
  quasi_identifiers text[] not null default '{}',
  created_at timestamptz not null default now()
);

alter table public.anonymization_jobs enable row level security;

-- Hanya pegawai (user terautentikasi) yang bisa melihat/menambah job miliknya sendiri.
create policy "insert own jobs" on public.anonymization_jobs
  for insert to authenticated with check (auth.uid() = user_id);

create policy "select own jobs" on public.anonymization_jobs
  for select to authenticated using (auth.uid() = user_id);

create policy "update own jobs" on public.anonymization_jobs
  for update to authenticated using (auth.uid() = user_id);

create policy "delete own jobs" on public.anonymization_jobs
  for delete to authenticated using (auth.uid() = user_id);

-- Riwayat per pegawai, terbaru di atas
create index if not exists anonymization_jobs_user_idx
  on public.anonymization_jobs (user_id, created_at desc);
