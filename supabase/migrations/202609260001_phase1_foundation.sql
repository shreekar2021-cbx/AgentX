-- AgriVision AI Phase 1 schema. Apply through Supabase migrations as a privileged migration role.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;
create extension if not exists postgis with schema extensions;

create type public.report_status as enum ('draft','pending_sync','submitted','processing','completed','failed');
create type public.severity_level as enum ('low','moderate','high','critical');
create type public.source_status as enum ('live','cached','fallback','demo');
create type public.sync_status as enum ('pending','syncing','completed','conflict','failed');

create or replace function public.is_platform_admin() returns boolean
language sql stable security invoker set search_path = '' as $$
  select coalesce((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin', false)
$$;

create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_seen_at timestamptz
);
create table public.profiles (
  user_id uuid primary key references public.users(id) on delete cascade,
  display_name text not null default '',
  preferred_language text not null default 'en' check (preferred_language in ('en','te')),
  phone_e164 text,
  district text,
  state text not null default 'Telangana',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table public.farms (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  village text,
  district text not null,
  state text not null default 'Telangana',
  area_acres numeric(10,2) not null default 0 check (area_acres >= 0),
  centroid extensions.geography(Point,4326),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,owner_id)
);
create table public.fields (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  farm_id uuid not null,
  name text not null,
  area_acres numeric(10,2) not null check (area_acres > 0),
  boundary extensions.geography(Polygon,4326),
  centroid extensions.geography(Point,4326),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,owner_id),
  foreign key(farm_id,owner_id) references public.farms(id,owner_id) on delete cascade
);
create table public.crops (
  id uuid primary key default gen_random_uuid(),
  common_name text not null unique,
  scientific_name text,
  local_name_te text,
  category text,
  created_at timestamptz not null default now()
);
create table public.crop_cycles (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  field_id uuid not null,
  crop_id uuid not null references public.crops(id),
  variety text,
  season text,
  planted_on date,
  harvested_on date,
  status text not null default 'active' check(status in ('planned','active','harvested','cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,owner_id),
  foreign key(field_id,owner_id) references public.fields(id,owner_id) on delete cascade
);
create table public.soil_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  field_id uuid not null,
  sampled_on date,
  ph numeric(4,2) check(ph between 0 and 14),
  organic_carbon_pct numeric(5,2),
  nitrogen_kg_ha numeric(9,2),
  phosphorus_kg_ha numeric(9,2),
  potassium_kg_ha numeric(9,2),
  texture text,
  source text,
  verified boolean not null default false,
  created_at timestamptz not null default now(),
  foreign key(field_id,owner_id) references public.fields(id,owner_id) on delete cascade
);
create table public.crop_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  field_id uuid not null,
  crop_cycle_id uuid,
  crop_id uuid not null references public.crops(id),
  symptom_description text not null check(char_length(symptom_description) between 10 and 4000),
  notes text check(notes is null or char_length(notes) <= 4000),
  observed_at timestamptz not null,
  location extensions.geography(Point,4326),
  status public.report_status not null default 'draft',
  severity public.severity_level,
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,user_id),
  foreign key(field_id,user_id) references public.fields(id,owner_id) on delete cascade,
  foreign key(crop_cycle_id,user_id) references public.crop_cycles(id,owner_id) on delete set null (crop_cycle_id)
);
create table public.crop_images (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  report_id uuid not null,
  storage_path text not null unique,
  mime_type text not null check(mime_type in ('image/jpeg','image/png','image/webp')),
  size_bytes integer not null check(size_bytes between 1 and 10485760),
  captured_at timestamptz,
  created_at timestamptz not null default now(),
  foreign key(report_id,user_id) references public.crop_reports(id,user_id) on delete cascade
);
create table public.crop_analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  report_id uuid not null,
  provider text,
  model_version text,
  possible_problem text,
  confidence numeric(4,3) check(confidence between 0 and 1),
  severity public.severity_level,
  symptoms jsonb not null default '[]',
  causes jsonb not null default '[]',
  actions jsonb not null default '[]',
  precautions jsonb not null default '[]',
  provenance jsonb not null default '{}',
  created_at timestamptz not null default now(),
  foreign key(report_id,user_id) references public.crop_reports(id,user_id) on delete cascade
);
create table public.risk_assessments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  farm_id uuid not null,
  crop_cycle_id uuid,
  risk_type text not null,
  severity public.severity_level not null,
  score numeric(5,2) check(score between 0 and 100),
  factors jsonb not null default '[]',
  valid_until timestamptz,
  source public.source_status not null default 'live',
  created_at timestamptz not null default now(),
  foreign key(farm_id,user_id) references public.farms(id,owner_id) on delete cascade,
  foreign key(crop_cycle_id,user_id) references public.crop_cycles(id,owner_id) on delete set null (crop_cycle_id)
);
create table public.outbreak_clusters (
  id uuid primary key default gen_random_uuid(),
  crop_id uuid not null references public.crops(id),
  district text not null,
  center extensions.geography(Point,4326) not null,
  radius_m integer not null check(radius_m > 0),
  severity public.severity_level not null,
  report_count integer not null default 0 check(report_count >= 0),
  status text not null default 'candidate' check(status in ('candidate','verified','resolved')),
  first_seen_at timestamptz not null,
  last_seen_at timestamptz not null,
  created_at timestamptz not null default now()
);
create table public.alerts (
  id uuid primary key default gen_random_uuid(),
  cluster_id uuid references public.outbreak_clusters(id) on delete set null,
  crop_id uuid references public.crops(id),
  district text not null,
  title text not null,
  summary text not null,
  severity public.severity_level not null,
  location extensions.geography(Point,4326),
  radius_m integer check(radius_m > 0),
  published_at timestamptz not null default now(),
  expires_at timestamptz,
  created_at timestamptz not null default now()
);
create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  alert_id uuid references public.alerts(id) on delete set null,
  title text not null,
  body text not null,
  channel text not null check(channel in ('in_app','push','sms','email')),
  status text not null default 'pending' check(status in ('pending','sent','failed','read')),
  read_at timestamptz,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);
create table public.market_prices (
  id uuid primary key default gen_random_uuid(),
  crop_id uuid not null references public.crops(id),
  commodity text not null,
  mandi_name text not null,
  district text not null,
  price_date date not null,
  modal_price_inr numeric(12,2) not null check(modal_price_inr >= 0),
  min_price_inr numeric(12,2),
  max_price_inr numeric(12,2),
  source public.source_status not null,
  provider_ref text,
  fetched_at timestamptz not null default now(),
  unique(crop_id,mandi_name,price_date,source)
);
create table public.weather_cache (
  id uuid primary key default gen_random_uuid(),
  geohash text not null,
  forecast_at timestamptz not null,
  payload jsonb not null,
  provider text not null,
  fetched_at timestamptz not null default now(),
  expires_at timestamptz not null,
  unique(geohash,forecast_at,provider)
);
create table public.market_cache (
  id uuid primary key default gen_random_uuid(),
  cache_key text not null unique,
  payload jsonb not null,
  provider text not null,
  fetched_at timestamptz not null default now(),
  expires_at timestamptz not null
);
create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  field_id uuid not null,
  crop_cycle_id uuid,
  kind text not null check(kind in ('seed','fertilizer','crop_action','market')),
  title text not null,
  rationale text not null,
  payload jsonb not null default '{}',
  source public.source_status not null default 'live',
  agent_run_id uuid,
  created_at timestamptz not null default now(),
  foreign key(field_id,user_id) references public.fields(id,owner_id) on delete cascade,
  foreign key(crop_cycle_id,user_id) references public.crop_cycles(id,owner_id) on delete set null (crop_cycle_id)
);
create table public.offline_sync_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  device_id text not null,
  client_mutation_id uuid not null,
  entity_type text not null,
  entity_id uuid,
  operation text not null check(operation in ('create','update','delete')),
  status public.sync_status not null default 'pending',
  conflict_payload jsonb,
  attempted_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  unique(user_id,device_id,client_mutation_id)
);
create table public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete set null,
  agent_name text not null,
  status text not null check(status in ('queued','running','succeeded','failed','cancelled')),
  provider_name text,
  model_name text,
  input_ref uuid,
  output_ref uuid,
  duration_ms integer,
  token_count integer,
  error_code text,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);
alter table public.recommendations add constraint recommendations_agent_run_fkey foreign key(agent_run_id) references public.agent_runs(id) on delete set null;
create table public.provider_health (
  id uuid primary key default gen_random_uuid(),
  provider_name text not null unique,
  category text not null check(category in ('ai','weather','market','notification','database')),
  status text not null check(status in ('healthy','degraded','unavailable','unconfigured')),
  last_checked_at timestamptz not null default now(),
  latency_ms integer,
  failure_count integer not null default 0,
  details jsonb not null default '{}'
);

create index farms_owner_idx on public.farms(owner_id,created_at desc);
create index farms_district_idx on public.farms(district);
create index farms_centroid_gix on public.farms using gist(centroid);
create index fields_farm_idx on public.fields(farm_id,created_at desc);
create index fields_owner_idx on public.fields(owner_id);
create index fields_centroid_gix on public.fields using gist(centroid);
create index cycles_owner_crop_idx on public.crop_cycles(owner_id,crop_id,status);
create index cycles_field_idx on public.crop_cycles(field_id,created_at desc);
create index soil_field_date_idx on public.soil_profiles(field_id,sampled_on desc);
create index reports_user_status_time_idx on public.crop_reports(user_id,status,created_at desc);
create index reports_crop_severity_idx on public.crop_reports(crop_id,severity,created_at desc);
create index reports_location_gix on public.crop_reports using gist(location);
create index images_report_idx on public.crop_images(report_id,created_at desc);
create index analyses_report_idx on public.crop_analyses(report_id,created_at desc);
create index risk_farm_severity_idx on public.risk_assessments(farm_id,severity,created_at desc);
create index clusters_district_crop_idx on public.outbreak_clusters(district,crop_id,severity,last_seen_at desc);
create index clusters_center_gix on public.outbreak_clusters using gist(center);
create index alerts_district_severity_idx on public.alerts(district,severity,published_at desc);
create index alerts_crop_idx on public.alerts(crop_id,published_at desc);
create index alerts_location_gix on public.alerts using gist(location);
create index notifications_user_time_idx on public.notifications(user_id,created_at desc);
create index market_prices_crop_date_idx on public.market_prices(crop_id,price_date desc);
create index market_prices_district_date_idx on public.market_prices(district,price_date desc);
create index weather_cache_expiry_idx on public.weather_cache(expires_at);
create index market_cache_expiry_idx on public.market_cache(expires_at);
create index recommendations_user_kind_idx on public.recommendations(user_id,kind,created_at desc);
create index offline_sync_user_status_idx on public.offline_sync_records(user_id,status,created_at desc);
create index agent_runs_user_time_idx on public.agent_runs(user_id,started_at desc);
create index agent_runs_status_idx on public.agent_runs(status,started_at desc);
create index provider_health_checked_idx on public.provider_health(last_checked_at desc);

-- RLS: data ownership is anchored to auth.uid(); JWT app_metadata carries admin role.
alter table public.users enable row level security;
alter table public.profiles enable row level security;
alter table public.farms enable row level security;
alter table public.fields enable row level security;
alter table public.crops enable row level security;
alter table public.crop_cycles enable row level security;
alter table public.soil_profiles enable row level security;
alter table public.crop_reports enable row level security;
alter table public.crop_images enable row level security;
alter table public.crop_analyses enable row level security;
alter table public.risk_assessments enable row level security;
alter table public.outbreak_clusters enable row level security;
alter table public.alerts enable row level security;
alter table public.notifications enable row level security;
alter table public.market_prices enable row level security;
alter table public.weather_cache enable row level security;
alter table public.market_cache enable row level security;
alter table public.recommendations enable row level security;
alter table public.offline_sync_records enable row level security;
alter table public.agent_runs enable row level security;
alter table public.provider_health enable row level security;

create policy users_self_select on public.users for select to authenticated using(id = (select auth.uid()) or (select public.is_platform_admin()));
create policy users_self_update on public.users for update to authenticated using(id = (select auth.uid())) with check(id = (select auth.uid()));
create policy profiles_self_all on public.profiles for all to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin())) with check(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy farms_owner_all on public.farms for all to authenticated using(owner_id = (select auth.uid()) or (select public.is_platform_admin())) with check(owner_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy fields_owner_all on public.fields for all to authenticated using(owner_id = (select auth.uid()) or (select public.is_platform_admin())) with check(owner_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy crops_authenticated_read on public.crops for select to authenticated using(true);
create policy cycles_owner_all on public.crop_cycles for all to authenticated using(owner_id = (select auth.uid()) or (select public.is_platform_admin())) with check(owner_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy soil_owner_all on public.soil_profiles for all to authenticated using(owner_id = (select auth.uid()) or (select public.is_platform_admin())) with check(owner_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy reports_owner_all on public.crop_reports for all to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin())) with check(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy images_owner_all on public.crop_images for all to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin())) with check(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy analyses_owner_read on public.crop_analyses for select to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy risk_owner_read on public.risk_assessments for select to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy clusters_authenticated_read on public.outbreak_clusters for select to authenticated using(status = 'verified' or (select public.is_platform_admin()));
create policy alerts_authenticated_read on public.alerts for select to authenticated using(expires_at is null or expires_at > now());
create policy notifications_owner_read on public.notifications for select to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy notifications_owner_update on public.notifications for update to authenticated using(user_id = (select auth.uid())) with check(user_id = (select auth.uid()));
create policy market_prices_authenticated_read on public.market_prices for select to authenticated using(true);
create policy weather_cache_admin_read on public.weather_cache for select to authenticated using((select public.is_platform_admin()));
create policy market_cache_admin_read on public.market_cache for select to authenticated using((select public.is_platform_admin()));
create policy recommendations_owner_read on public.recommendations for select to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy offline_sync_owner_all on public.offline_sync_records for all to authenticated using(user_id = (select auth.uid()) or (select public.is_platform_admin())) with check(user_id = (select auth.uid()) or (select public.is_platform_admin()));
create policy agent_runs_admin_read on public.agent_runs for select to authenticated using((select public.is_platform_admin()));
create policy provider_health_admin_read on public.provider_health for select to authenticated using((select public.is_platform_admin()));

-- Storage bucket is private. Object paths must begin with the authenticated user ID.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('crop-images','crop-images',false,10485760,array['image/jpeg','image/png','image/webp'])
on conflict(id) do nothing;
create policy crop_images_owner_read on storage.objects for select to authenticated
using(bucket_id = 'crop-images' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy crop_images_owner_insert on storage.objects for insert to authenticated
with check(bucket_id = 'crop-images' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy crop_images_owner_delete on storage.objects for delete to authenticated
using(bucket_id = 'crop-images' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- Keep a minimal public user row in sync with Supabase Auth.
create or replace function public.handle_new_auth_user() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.users(id) values(new.id) on conflict(id) do nothing;
  insert into public.profiles(user_id,display_name) values(new.id,coalesce(new.raw_user_meta_data ->> 'display_name','')) on conflict(user_id) do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_auth_user();
insert into public.users(id,created_at)
select id,created_at from auth.users on conflict(id) do nothing;
insert into public.profiles(user_id,display_name)
select id,coalesce(raw_user_meta_data ->> 'display_name','') from auth.users on conflict(user_id) do nothing;
