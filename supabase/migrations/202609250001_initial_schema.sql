-- Initial AgriVision schema. Apply with the Supabase CLI or SQL editor.
-- Private tables use RLS; public user writes are limited to editable fields.

begin;

create extension if not exists pgcrypto with schema extensions;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.farmers (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  phone text,
  email text,
  language text not null default 'en' check (language in ('en', 'te')),
  latitude double precision,
  longitude double precision,
  district text,
  state text,
  location_source text check (location_source in ('gps', 'manual')),
  location_updated_at timestamptz,
  alerts_opt_in boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint farmers_latitude_range check (latitude is null or latitude between -90 and 90),
  constraint farmers_longitude_range check (longitude is null or longitude between -180 and 180),
  constraint farmers_coordinate_pair check ((latitude is null) = (longitude is null))
);

create table public.farms (
  id uuid primary key default gen_random_uuid(),
  farmer_id uuid not null references public.farmers(id) on delete cascade,
  farm_name text not null check (length(trim(farm_name)) between 1 and 120),
  area_acres numeric(10, 2) not null check (area_acres > 0 and area_acres <= 1000),
  irrigation_type text not null check (irrigation_type in ('rainfed', 'drip', 'sprinkler', 'flood')),
  latitude double precision,
  longitude double precision,
  address text,
  district text,
  state text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint farms_latitude_range check (latitude is null or latitude between -90 and 90),
  constraint farms_longitude_range check (longitude is null or longitude between -180 and 180),
  constraint farms_coordinate_pair check ((latitude is null) = (longitude is null))
);

create table public.commodities (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (code = lower(code)),
  name_en text not null,
  name_te text,
  provider_aliases jsonb not null default '{}'::jsonb check (jsonb_typeof(provider_aliases) = 'object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.crops (
  id uuid primary key default gen_random_uuid(),
  farm_id uuid not null references public.farms(id) on delete restrict,
  commodity_id uuid not null references public.commodities(id) on delete restrict,
  variety text,
  season text not null check (season in ('kharif', 'rabi', 'zaid')),
  sowing_date date,
  expected_harvest date,
  growth_stage text,
  status text not null default 'active' check (status in ('active', 'harvested', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint crops_harvest_after_sowing check (expected_harvest is null or sowing_date is null or expected_harvest >= sowing_date)
);

create table public.soil_tests (
  id uuid primary key default gen_random_uuid(),
  farm_id uuid not null references public.farms(id) on delete restrict,
  ph numeric(4, 2) check (ph is null or ph between 3 and 10),
  nitrogen_kg_ha numeric(8, 2) check (nitrogen_kg_ha is null or nitrogen_kg_ha between 0 and 500),
  phosphorus_kg_ha numeric(8, 2) check (phosphorus_kg_ha is null or phosphorus_kg_ha between 0 and 200),
  potassium_kg_ha numeric(8, 2) check (potassium_kg_ha is null or potassium_kg_ha between 0 and 500),
  phosphorus_basis text not null default 'unknown' check (phosphorus_basis in ('P', 'P2O5', 'unknown')),
  potassium_basis text not null default 'unknown' check (potassium_basis in ('K', 'K2O', 'unknown')),
  organic_carbon_pct numeric(5, 2) check (organic_carbon_pct is null or organic_carbon_pct between 0 and 5),
  soil_type text check (soil_type is null or soil_type in ('clay', 'loam', 'sandy', 'silt', 'red', 'black')),
  previous_commodity_id uuid references public.commodities(id) on delete restrict,
  test_date date not null check (test_date <= current_date),
  lab_name text,
  method text,
  created_at timestamptz not null default now()
);

create table public.mandis (
  id uuid primary key default gen_random_uuid(),
  provider_key text not null unique,
  market_name text not null,
  district text,
  state text not null,
  latitude double precision,
  longitude double precision,
  coordinate_source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint mandis_latitude_range check (latitude is null or latitude between -90 and 90),
  constraint mandis_longitude_range check (longitude is null or longitude between -180 and 180),
  constraint mandis_coordinate_pair check ((latitude is null) = (longitude is null))
);

create table public.market_prices (
  id uuid primary key default gen_random_uuid(),
  mandi_id uuid not null references public.mandis(id) on delete restrict,
  commodity_id uuid not null references public.commodities(id) on delete restrict,
  variety_code text not null default 'unspecified',
  grade text not null default 'unspecified',
  min_price numeric(14, 2) not null check (min_price >= 0),
  max_price numeric(14, 2) not null check (max_price >= 0),
  modal_price numeric(14, 2) not null check (modal_price >= 0),
  currency text not null default 'INR' check (currency = 'INR'),
  unit text not null default 'quintal' check (unit = 'quintal'),
  price_date date not null,
  source text not null,
  source_record_id text,
  fetched_at timestamptz not null default now(),
  original_unit text,
  created_at timestamptz not null default now(),
  constraint market_prices_order check (min_price <= modal_price and modal_price <= max_price)
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  farmer_id uuid not null references public.farmers(id) on delete cascade,
  crop_id uuid references public.crops(id) on delete set null,
  commodity_id uuid references public.commodities(id) on delete restrict,
  client_request_id uuid not null,
  description text check (description is null or length(description) <= 4000),
  voice_transcript text check (voice_transcript is null or length(voice_transcript) <= 4000),
  language text not null default 'en' check (language in ('en', 'te')),
  image_path text,
  image_checksum text,
  image_state text not null default 'none' check (image_state in ('none', 'uploaded')),
  latitude double precision,
  longitude double precision,
  district text,
  state text,
  analysis_state text not null default 'draft' check (analysis_state in ('draft', 'queued', 'running', 'succeeded', 'failed')),
  review_status text not null default 'pending' check (review_status in ('pending', 'verified', 'needs_review', 'resolved')),
  ai_diagnosis jsonb,
  diagnosis_schema_version text,
  disease_code text,
  confidence double precision check (confidence is null or confidence between 0 and 1),
  severity text check (severity is null or severity in ('low', 'medium', 'high', 'critical')),
  model_used text,
  prompt_version text,
  weather_context jsonb,
  analysis_error_code text,
  analysis_attempt integer not null default 0 check (analysis_attempt >= 0),
  analyzed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (farmer_id, client_request_id),
  constraint reports_latitude_range check (latitude is null or latitude between -90 and 90),
  constraint reports_longitude_range check (longitude is null or longitude between -180 and 180),
  constraint reports_coordinate_pair check ((latitude is null) = (longitude is null)),
  constraint reports_image_consistency check ((image_state = 'none' and image_path is null) or (image_state = 'uploaded' and image_path is not null))
);

create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  farmer_id uuid not null references public.farmers(id) on delete cascade,
  farm_id uuid references public.farms(id) on delete set null,
  crop_id uuid references public.crops(id) on delete set null,
  soil_test_id uuid references public.soil_tests(id) on delete set null,
  client_request_id uuid not null,
  type text not null check (type in ('seed', 'fertilizer', 'market', 'general')),
  input_context jsonb not null default '{}'::jsonb,
  recommendation jsonb not null,
  schema_version text not null default '1',
  sources jsonb not null default '[]'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  model_used text,
  rule_version text,
  created_at timestamptz not null default now(),
  unique (farmer_id, client_request_id)
);

create table public.alerts (
  id uuid primary key default gen_random_uuid(),
  source_report_id uuid references public.reports(id) on delete set null,
  commodity_id uuid references public.commodities(id) on delete restrict,
  disease_code text,
  alert_type text not null check (alert_type in ('disease_outbreak', 'pest_warning', 'weather_risk')),
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  risk_score double precision not null check (risk_score between 0 and 1),
  level text not null check (level in ('advisory', 'warning', 'critical')),
  center_lat double precision not null check (center_lat between -90 and 90),
  center_lng double precision not null check (center_lng between -180 and 180),
  radius_km numeric(8, 2) not null check (radius_km > 0 and radius_km <= 500),
  affected_farmer_count integer not null default 0 check (affected_farmer_count >= 0),
  status text not null default 'active' check (status in ('active', 'monitoring', 'resolved')),
  weather_context jsonb,
  evidence_summary jsonb not null default '{}'::jsonb,
  rule_version text not null,
  revision integer not null default 1 check (revision > 0),
  last_evidence_at timestamptz not null default now(),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.alert_reports (
  alert_id uuid not null references public.alerts(id) on delete cascade,
  report_id uuid not null references public.reports(id) on delete cascade,
  linked_at timestamptz not null default now(),
  primary key (alert_id, report_id)
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  farmer_id uuid not null references public.farmers(id) on delete cascade,
  alert_id uuid references public.alerts(id) on delete set null,
  alert_revision integer,
  title text not null,
  body text not null,
  language text not null default 'en' check (language in ('en', 'te')),
  type text not null check (type in ('alert', 'recommendation', 'market', 'system')),
  destination_path text,
  dedupe_key text not null unique,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.notification_devices (
  id uuid primary key default gen_random_uuid(),
  farmer_id uuid not null references public.farmers(id) on delete cascade,
  fcm_token text not null unique,
  enabled boolean not null default true,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.report_reviews (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  reviewer_id uuid not null references public.farmers(id) on delete restrict,
  previous_status text check (previous_status is null or previous_status in ('pending', 'verified', 'needs_review', 'resolved')),
  new_status text not null check (new_status in ('pending', 'verified', 'needs_review', 'resolved')),
  note text not null check (length(trim(note)) > 0),
  corrected_diagnosis jsonb,
  created_at timestamptz not null default now()
);

create table public.service_cache (
  cache_key text primary key,
  provider text not null,
  schema_version text not null,
  payload jsonb not null,
  fetched_at timestamptz not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint service_cache_expiry_after_fetch check (expires_at >= fetched_at)
);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('diagnose_report', 'evaluate_outbreak', 'deliver_push', 'refresh_market_prices', 'expire_alerts')),
  resource_id uuid,
  dedupe_key text not null unique,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (status in ('pending', 'running', 'succeeded', 'failed')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 5 check (max_attempts > 0),
  run_after timestamptz not null default now(),
  locked_until timestamptz,
  last_error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint jobs_attempt_limit check (attempts <= max_attempts)
);

-- Report images are private. The backend validates uploads and issues short-lived
-- signed URLs; browser clients receive no direct Storage object policy here.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'crop-images',
  'crop-images',
  false,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']::text[]
)
on conflict (id) do update set
  name = excluded.name,
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Stable crop identities are application data, not live provider responses.
insert into public.commodities (code, name_en, name_te, provider_aliases)
values
  ('tomato', 'Tomato', 'టమాటా', '{"data.gov.in":["Tomato"]}'),
  ('rice', 'Rice', 'వరి', '{"data.gov.in":["Paddy(Dhan)(Common)","Rice"]}'),
  ('chili', 'Chilli', 'మిరప', '{"data.gov.in":["Green Chilli","Chilli Red"]}'),
  ('cotton', 'Cotton', 'పత్తి', '{"data.gov.in":["Cotton"]}')
on conflict (code) do nothing;

create index farms_farmer_id_idx on public.farms (farmer_id);
create index crops_farm_id_idx on public.crops (farm_id);
create index crops_commodity_status_idx on public.crops (commodity_id, status);
create index soil_tests_farm_test_date_idx on public.soil_tests (farm_id, test_date desc);
create index soil_tests_previous_commodity_idx on public.soil_tests (previous_commodity_id);
create index reports_farmer_created_idx on public.reports (farmer_id, created_at desc);
create index reports_crop_id_idx on public.reports (crop_id);
create index reports_commodity_id_idx on public.reports (commodity_id);
create index reports_commodity_disease_created_idx on public.reports (commodity_id, disease_code, created_at desc);
create index reports_analysis_state_created_idx on public.reports (analysis_state, created_at);
create index recommendations_farmer_created_idx on public.recommendations (farmer_id, created_at desc);
create index recommendations_farm_id_idx on public.recommendations (farm_id);
create index recommendations_crop_id_idx on public.recommendations (crop_id);
create index recommendations_soil_test_id_idx on public.recommendations (soil_test_id);
create index market_prices_series_date_idx on public.market_prices (commodity_id, mandi_id, variety_code, grade, price_date desc);
create index market_prices_mandi_id_idx on public.market_prices (mandi_id);
create index mandis_state_district_idx on public.mandis (state, district);
create unique index market_prices_observation_key on public.market_prices (mandi_id, commodity_id, variety_code, grade, price_date, source);
create index alerts_status_expiry_idx on public.alerts (status, expires_at);
create index alerts_commodity_disease_evidence_idx on public.alerts (commodity_id, disease_code, last_evidence_at desc);
create index alerts_source_report_id_idx on public.alerts (source_report_id);
create index alert_reports_report_id_idx on public.alert_reports (report_id);
create index notifications_farmer_read_created_idx on public.notifications (farmer_id, read_at, created_at desc);
create index notification_devices_farmer_enabled_idx on public.notification_devices (farmer_id, enabled);
create index report_reviews_report_created_idx on public.report_reviews (report_id, created_at desc);
create index jobs_status_run_after_idx on public.jobs (status, run_after);
create index jobs_running_lease_idx on public.jobs (locked_until) where status = 'running';

create trigger farmers_set_updated_at before update on public.farmers for each row execute function public.set_updated_at();
create trigger farms_set_updated_at before update on public.farms for each row execute function public.set_updated_at();
create trigger commodities_set_updated_at before update on public.commodities for each row execute function public.set_updated_at();
create trigger crops_set_updated_at before update on public.crops for each row execute function public.set_updated_at();
create trigger reports_set_updated_at before update on public.reports for each row execute function public.set_updated_at();
create trigger mandis_set_updated_at before update on public.mandis for each row execute function public.set_updated_at();
create trigger alerts_set_updated_at before update on public.alerts for each row execute function public.set_updated_at();
create trigger notification_devices_set_updated_at before update on public.notification_devices for each row execute function public.set_updated_at();
create trigger jobs_set_updated_at before update on public.jobs for each row execute function public.set_updated_at();

create or replace function public.create_farmer_profile()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  insert into public.farmers (id, full_name, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    new.email
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created_create_farmer
  after insert on auth.users
  for each row execute function public.create_farmer_profile();

alter table public.farmers enable row level security;
alter table public.farms enable row level security;
alter table public.commodities enable row level security;
alter table public.crops enable row level security;
alter table public.soil_tests enable row level security;
alter table public.mandis enable row level security;
alter table public.market_prices enable row level security;
alter table public.reports enable row level security;
alter table public.recommendations enable row level security;
alter table public.alerts enable row level security;
alter table public.alert_reports enable row level security;
alter table public.notifications enable row level security;
alter table public.notification_devices enable row level security;
alter table public.report_reviews enable row level security;
alter table public.service_cache enable row level security;
alter table public.jobs enable row level security;

create policy farmers_select_self on public.farmers for select to authenticated using (id = (select auth.uid()));
create policy farmers_update_self on public.farmers for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy farms_select_owner on public.farms for select to authenticated using (farmer_id = (select auth.uid()));
create policy farms_insert_owner on public.farms for insert to authenticated with check (farmer_id = (select auth.uid()));
create policy farms_update_owner on public.farms for update to authenticated using (farmer_id = (select auth.uid())) with check (farmer_id = (select auth.uid()));

create policy commodities_select_authenticated on public.commodities for select to authenticated using (true);

create policy crops_select_owner on public.crops for select to authenticated using (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
);
create policy crops_insert_owner on public.crops for insert to authenticated with check (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
);
create policy crops_update_owner on public.crops for update to authenticated using (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
) with check (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
);

create policy soil_tests_select_owner on public.soil_tests for select to authenticated using (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
);
create policy soil_tests_insert_owner on public.soil_tests for insert to authenticated with check (
  exists (select 1 from public.farms f where f.id = farm_id and f.farmer_id = (select auth.uid()))
);

create policy mandis_select_authenticated on public.mandis for select to authenticated using (true);
create policy market_prices_select_authenticated on public.market_prices for select to authenticated using (true);

create policy reports_select_owner on public.reports for select to authenticated using (farmer_id = (select auth.uid()));
create policy reports_insert_draft_owner on public.reports for insert to authenticated with check (
  farmer_id = (select auth.uid()) and analysis_state = 'draft' and review_status = 'pending'
  and (crop_id is null or exists (
    select 1 from public.crops c join public.farms f on f.id = c.farm_id
    where c.id = reports.crop_id and f.farmer_id = (select auth.uid())
      and (reports.commodity_id is null or reports.commodity_id = c.commodity_id)
  ))
);
create policy reports_update_editable_owner on public.reports for update to authenticated
  using (farmer_id = (select auth.uid()) and analysis_state in ('draft', 'failed') and review_status = 'pending')
  with check (
    farmer_id = (select auth.uid()) and analysis_state in ('draft', 'failed') and review_status = 'pending'
    and (crop_id is null or exists (
      select 1 from public.crops c join public.farms f on f.id = c.farm_id
      where c.id = reports.crop_id and f.farmer_id = (select auth.uid())
        and (reports.commodity_id is null or reports.commodity_id = c.commodity_id)
    ))
  );

create policy recommendations_select_owner on public.recommendations for select to authenticated using (farmer_id = (select auth.uid()));

create policy notifications_select_owner on public.notifications for select to authenticated using (farmer_id = (select auth.uid()));
create policy notifications_mark_read_owner on public.notifications for update to authenticated
  using (farmer_id = (select auth.uid())) with check (farmer_id = (select auth.uid()));

create policy notification_devices_select_owner on public.notification_devices for select to authenticated using (farmer_id = (select auth.uid()));
create policy notification_devices_insert_owner on public.notification_devices for insert to authenticated with check (farmer_id = (select auth.uid()));
create policy notification_devices_delete_owner on public.notification_devices for delete to authenticated using (farmer_id = (select auth.uid()));

-- Reset Supabase default table grants before adding column-level permissions.
-- Otherwise an inherited table-wide UPDATE can bypass the column allowlists.
-- Only application tables are affected; unrelated public tables are untouched.
revoke all on public.farmers, public.farms, public.commodities, public.crops,
  public.soil_tests, public.mandis, public.market_prices, public.reports,
  public.recommendations, public.alerts, public.alert_reports, public.notifications,
  public.notification_devices, public.report_reviews, public.service_cache,
  public.jobs from public, anon, authenticated;
-- The API serves privacy-filtered alert projections; users cannot query evidence tables.
grant usage on schema public to authenticated, service_role;

grant select, update (full_name, phone, language, latitude, longitude, district, state,
  location_source, location_updated_at, alerts_opt_in) on public.farmers to authenticated;
grant select, insert (farmer_id, farm_name, area_acres, irrigation_type, latitude,
  longitude, address, district, state), update (farm_name, area_acres, irrigation_type,
  latitude, longitude, address, district, state) on public.farms to authenticated;
grant select on public.commodities to authenticated;
grant select, insert (farm_id, commodity_id, variety, season, sowing_date,
  expected_harvest, growth_stage, status), update (variety, season, sowing_date,
  expected_harvest, growth_stage, status) on public.crops to authenticated;
grant select, insert (farm_id, ph, nitrogen_kg_ha, phosphorus_kg_ha, potassium_kg_ha,
  phosphorus_basis, potassium_basis, organic_carbon_pct, soil_type,
  previous_commodity_id, test_date, lab_name, method) on public.soil_tests to authenticated;
grant select on public.mandis, public.market_prices to authenticated;
grant select on public.reports to authenticated;
grant insert (farmer_id, crop_id, commodity_id, client_request_id, description,
  voice_transcript, language, latitude, longitude, district, state) on public.reports to authenticated;
grant update (crop_id, commodity_id, description, voice_transcript, language,
  latitude, longitude, district, state) on public.reports to authenticated;
grant select on public.recommendations to authenticated;
grant select on public.notifications to authenticated;
grant update (read_at) on public.notifications to authenticated;
grant select, insert (farmer_id, fcm_token, enabled, last_seen_at), delete
  on public.notification_devices to authenticated;

grant all privileges on public.farmers, public.farms, public.commodities,
  public.crops, public.soil_tests, public.mandis, public.market_prices,
  public.reports, public.recommendations, public.alerts, public.alert_reports,
  public.notifications, public.notification_devices, public.report_reviews,
  public.service_cache, public.jobs to service_role;
revoke all on function public.set_updated_at() from public, anon, authenticated;
revoke all on function public.create_farmer_profile() from public, anon, authenticated;
grant execute on function public.set_updated_at() to service_role;
grant execute on function public.create_farmer_profile() to service_role;

commit;
