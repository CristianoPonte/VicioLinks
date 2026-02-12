-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. Users Table
create table public.users (
  username text primary key,
  hashed_password text not null,
  role text not null check (role in ('admin', 'user', 'viewer')),
  disabled boolean default false
);

-- 2. Source Configs (UPDATED LOGIC)
-- Stores JSON structure where Source dictates everything.
-- JSONB Structure Proposal:
-- {
--   "mediums": ["cpc", "organic", "referral"],
--   "contents": ["banner_home", "sidebar", "footer"],
--   "term_config": "standard" | "no_date" | "manual",
--   "required_fields": ["date", "term"]
-- }
create table public.source_configs (
  slug text primary key, -- e.g., 'instagram', 'google', 'site'
  name text not null,
  config jsonb -- Stores the rules: mediums list, contents list, term rules.
);

-- 3. Products
create table public.products (
  slug text primary key,
  nome text not null
);

-- 4. Turmas
create table public.turmas (
  slug text primary key,
  nome text not null
);

-- 5. Launch Types
create table public.launch_types (
  slug text primary key,
  nome text not null
);

-- 6. Launches (Campaigns)
create table public.launches (
  slug text primary key,
  nome text not null,
  owner text,
  status text
);

-- 7. Settings (for global counters)
create table public.settings (
  id text primary key,
  count integer default 0
);

-- 8. Links
create table public.links (
  id text primary key, -- 'lnk_XXXXXX'
  link_type text,
  base_url text,
  path text,
  full_url text not null,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  utm_term text,
  src text,
  sck text,
  xcode text,
  custom_params jsonb,
  notes text,
  created_by text,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

-- 9. Audits
create table public.audits (
  event_id text primary key,
  link_id text references public.links(id),
  actor text,
  action text,
  timestamp timestamp with time zone default timezone('utc'::text, now())
);

-- Helper function for atomic counter increment (RPC)
create or replace function increment_link_counter(row_id text)
returns integer
language plpgsql
as $$
declare
  current_count integer;
begin
  insert into public.settings (id, count)
  values (row_id, 1)
  on conflict (id) do update
  set count = settings.count + 1
  returning count into current_count;
  
  return current_count;
end;
$$;

-- RLS Policies (Open by default for authenticated service role)
alter table public.users enable row level security;
alter table public.links enable row level security;
alter table public.source_configs enable row level security;

create policy "Enable access to all users" on public.users for all using (true);
create policy "Enable access to all links" on public.links for all using (true);
create policy "Enable access to all configs" on public.source_configs for all using (true);
