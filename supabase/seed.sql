-- AgriVision AI Comprehensive Supabase Demo Seed Script

DO $$
DECLARE
  v_demo_user_id uuid := '00000000-0000-4000-8000-000000000001';
  v_farm_id uuid := '11111111-1111-4000-8000-000000000001';
  v_field_cotton_id uuid := '22222222-2222-4000-8000-000000000001';
  v_field_paddy_id uuid := '22222222-2222-4000-8000-000000000002';
  v_field_chilli_id uuid := '22222222-2222-4000-8000-000000000003';
  v_crop_cotton_id uuid;
  v_crop_paddy_id uuid;
  v_crop_chilli_id uuid;
  v_crop_maize_id uuid;
  v_crop_turmeric_id uuid;
  v_cycle_cotton_id uuid := '33333333-3333-4000-8000-000000000001';
  v_cycle_paddy_id uuid := '33333333-3333-4000-8000-000000000002';
  v_report_cotton_id uuid := '44444444-4444-4000-8000-000000000001';
  v_report_paddy_id uuid := '44444444-4444-4000-8000-000000000002';
  v_cluster_id uuid := '55555555-5555-4000-8000-000000000001';
  v_alert_id uuid := '66666666-6666-4000-8000-000000000001';
BEGIN

  -- 1. Create / Ensure Demo User in auth.users
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = v_demo_user_id) THEN
    INSERT INTO auth.users (
      id, instance_id, aud, role, email, encrypted_password, email_confirmed_at,
      raw_app_meta_data, raw_user_meta_data, created_at, updated_at
    ) VALUES (
      v_demo_user_id,
      '00000000-0000-0000-0000-000000000000',
      'authenticated',
      'authenticated',
      'demo@agrivision.ai',
      crypt('DemoPassword123!', gen_salt('bf')),
      now(),
      '{"provider":"email","providers":["email"],"role":"farmer"}'::jsonb,
      '{"display_name":"Srikanth Reddy","district":"Rangareddy","preferred_language":"te"}'::jsonb,
      now(),
      now()
    );
  END IF;

  -- 2. Ensure public.users and public.profiles
  INSERT INTO public.users(id, created_at, updated_at, last_seen_at)
  VALUES (v_demo_user_id, now(), now(), now())
  ON CONFLICT (id) DO UPDATE SET last_seen_at = now();

  INSERT INTO public.profiles(user_id, display_name, preferred_language, phone_e164, district, state)
  VALUES (v_demo_user_id, 'Srikanth Reddy', 'te', '+919876543210', 'Rangareddy', 'Telangana')
  ON CONFLICT (user_id) DO UPDATE 
  SET display_name = 'Srikanth Reddy', preferred_language = 'te', district = 'Rangareddy';

  -- 3. Crops Catalog
  INSERT INTO public.crops(id, common_name, scientific_name, local_name_te, category)
  VALUES
    (gen_random_uuid(), 'Cotton', 'Gossypium hirsutum', 'ప్రత్తి', 'commercial'),
    (gen_random_uuid(), 'Paddy', 'Oryza sativa', 'వరి', 'foodgrain'),
    (gen_random_uuid(), 'Chilli', 'Capsicum annuum', 'మిరప', 'spice'),
    (gen_random_uuid(), 'Maize', 'Zea mays', 'మొక్కజొన్న', 'coarse_cereal'),
    (gen_random_uuid(), 'Turmeric', 'Curcuma longa', 'పసుపు', 'spice'),
    (gen_random_uuid(), 'Groundnut', 'Arachis hypogaea', 'వేరుశనగ', 'oilseed'),
    (gen_random_uuid(), 'Red Gram', 'Cajanus cajan', 'కందులు', 'pulse'),
    (gen_random_uuid(), 'Soybean', 'Glycine max', 'సోయాబీన్', 'oilseed')
  ON CONFLICT (common_name) DO NOTHING;

  SELECT id INTO v_crop_cotton_id FROM public.crops WHERE common_name = 'Cotton' LIMIT 1;
  SELECT id INTO v_crop_paddy_id FROM public.crops WHERE common_name = 'Paddy' LIMIT 1;
  SELECT id INTO v_crop_chilli_id FROM public.crops WHERE common_name = 'Chilli' LIMIT 1;
  SELECT id INTO v_crop_maize_id FROM public.crops WHERE common_name = 'Maize' LIMIT 1;
  SELECT id INTO v_crop_turmeric_id FROM public.crops WHERE common_name = 'Turmeric' LIMIT 1;

  -- 4. Farms
  INSERT INTO public.farms(id, owner_id, name, village, district, state, area_acres, centroid)
  VALUES (
    v_farm_id,
    v_demo_user_id,
    'Sri Lakshmi Narasimha Farms',
    'Shamshabad',
    'Rangareddy',
    'Telangana',
    12.40,
    extensions.st_point(78.3893, 17.2517)::extensions.geography
  )
  ON CONFLICT (id, owner_id) DO NOTHING;

  -- 5. Fields
  INSERT INTO public.fields(id, owner_id, farm_id, name, area_acres, centroid)
  VALUES
    (v_field_cotton_id, v_demo_user_id, v_farm_id, 'North Field (Cotton Plot)', 5.20, extensions.st_point(78.3885, 17.2525)::extensions.geography),
    (v_field_paddy_id, v_demo_user_id, v_farm_id, 'East Field (Samba Masuri)', 4.10, extensions.st_point(78.3905, 17.2510)::extensions.geography),
    (v_field_chilli_id, v_demo_user_id, v_farm_id, 'South Field (Guntur Teja Chilli)', 3.10, extensions.st_point(78.3890, 17.2500)::extensions.geography)
  ON CONFLICT (id, owner_id) DO NOTHING;

  -- 6. Crop Cycles
  INSERT INTO public.crop_cycles(id, owner_id, field_id, crop_id, variety, season, planted_on, status)
  VALUES
    (v_cycle_cotton_id, v_demo_user_id, v_field_cotton_id, v_crop_cotton_id, 'RCH-659 BG II', 'Kharif 2026', '2026-06-15', 'active'),
    (v_cycle_paddy_id, v_demo_user_id, v_field_paddy_id, v_crop_paddy_id, 'BPT-5204 (Samba Masuri)', 'Kharif 2026', '2026-07-01', 'active')
  ON CONFLICT (id, owner_id) DO NOTHING;

  -- 7. Soil Profiles
  INSERT INTO public.soil_profiles(owner_id, field_id, sampled_on, ph, organic_carbon_pct, nitrogen_kg_ha, phosphorus_kg_ha, potassium_kg_ha, texture, verified)
  VALUES
    (v_demo_user_id, v_field_cotton_id, '2026-05-20', 7.20, 0.58, 245.00, 36.50, 290.00, 'Clay loam', true),
    (v_demo_user_id, v_field_paddy_id, '2026-05-22', 6.85, 0.64, 275.00, 41.20, 265.00, 'Black cotton soil', true)
  ON CONFLICT DO NOTHING;

  -- 8. Crop Reports
  INSERT INTO public.crop_reports(
    id, user_id, field_id, crop_cycle_id, crop_id, symptom_description, notes, observed_at,
    location, status, severity, submitted_at
  )
  VALUES
    (
      v_report_cotton_id,
      v_demo_user_id,
      v_field_cotton_id,
      v_cycle_cotton_id,
      v_crop_cotton_id,
      'Whitefly colonies visible on undersides of leaves with chlorotic yellow spots and honeydew secretion.',
      'Noticed during morning inspection. Weather was humid and cloudy.',
      now() - interval '2 days',
      extensions.st_point(78.3885, 17.2525)::extensions.geography,
      'completed',
      'moderate',
      now() - interval '2 days'
    ),
    (
      v_report_paddy_id,
      v_demo_user_id,
      v_field_paddy_id,
      v_cycle_paddy_id,
      v_crop_paddy_id,
      'Brown plant hopper nymph cluster observed at tillering stage near the waterline.',
      'Water level lowered immediately as a precaution.',
      now() - interval '4 days',
      extensions.st_point(78.3905, 17.2510)::extensions.geography,
      'completed',
      'low',
      now() - interval '4 days'
    )
  ON CONFLICT (id, user_id) DO NOTHING;

  -- 9. Crop Analyses
  INSERT INTO public.crop_analyses(
    user_id, report_id, provider, model_version, possible_problem, confidence, severity,
    symptoms, causes, actions, precautions
  )
  VALUES
    (
      v_demo_user_id,
      v_report_cotton_id,
      'mistral-ai',
      'pixtral-12b-2409',
      'Whitefly Infestation (Bemisia tabaci)',
      0.895,
      'moderate',
      '["Underside leaf clustering", "Honeydew secretion", "Yellow speckling on foliage"]'::jsonb,
      '["High relative humidity and dense vegetative canopy favoring nymph development"]'::jsonb,
      '["Install yellow sticky traps @ 10-12 per acre", "Spray Neem oil (Azadirachtin 10000 ppm) @ 2ml/L"]'::jsonb,
      '["Avoid excessive synthetic nitrogen application", "Maintain recommended field spacing for aeration"]'::jsonb
    ),
    (
      v_demo_user_id,
      v_report_paddy_id,
      'mistral-ai',
      'pixtral-12b-2409',
      'Brown Plant Hopper (Nilaparvata lugens)',
      0.920,
      'low',
      '["Nymph activity at stem base", "Initial basal leaf drying"]'::jsonb,
      '["Excessive stagnant water and heavy early nitrogen fertilizer use"]'::jsonb,
      '["Alternate wetting and drying (AWD) irrigation", "Apply Triflumezopyrim 10% SC @ 94ml/acre if threshold exceeds"]'::jsonb,
      '["Drain field water for 3-4 days to expose hopper population to natural predators"]'::jsonb
    )
  ON CONFLICT DO NOTHING;

  -- 10. Outbreak Clusters
  INSERT INTO public.outbreak_clusters(
    id, crop_id, district, center, radius_m, severity, report_count, status, first_seen_at, last_seen_at
  )
  VALUES (
    v_cluster_id,
    v_crop_cotton_id,
    'Rangareddy',
    extensions.st_point(78.3893, 17.2517)::extensions.geography,
    10000,
    'moderate',
    16,
    'verified',
    now() - interval '5 days',
    now()
  )
  ON CONFLICT (id) DO NOTHING;

  -- 11. Alerts
  INSERT INTO public.alerts(
    id, cluster_id, crop_id, district, title, summary, severity, location, radius_m, published_at
  )
  VALUES (
    v_alert_id,
    v_cluster_id,
    v_crop_cotton_id,
    'Rangareddy',
    'Whitefly advisory for Rangareddy cotton farmers',
    'Multiple farms in Shamshabad & Rajendranagar mandals report early whitefly resurgence. Inspect undersides of leaves immediately.',
    'moderate',
    extensions.st_point(78.3893, 17.2517)::extensions.geography,
    10000,
    now() - interval '1 day'
  )
  ON CONFLICT (id) DO NOTHING;

  -- 12. In-App Notifications
  INSERT INTO public.notifications(user_id, alert_id, title, body, channel, status)
  VALUES
    (
      v_demo_user_id,
      v_alert_id,
      'Nearby Alert: Cotton Whitefly',
      'A cluster of 16 observations has been verified within 10 km of your Shamshabad field.',
      'in_app',
      'pending'
    ),
    (
      v_demo_user_id,
      NULL,
      'Weather Advisory: Optimal Spray Window',
      'Clear skies and mild wind speed (8 km/h) forecasted for tomorrow morning between 6:00 AM - 9:30 AM.',
      'in_app',
      'sent'
    )
  ON CONFLICT DO NOTHING;

  -- 13. Market Mandi Prices
  INSERT INTO public.market_prices(crop_id, commodity, mandi_name, district, price_date, modal_price_inr, min_price_inr, max_price_inr, source)
  VALUES
    (v_crop_cotton_id, 'Cotton (Medium Staple)', 'Badepally Mandi', 'Rangareddy', CURRENT_DATE, 7450.00, 7100.00, 7680.00, 'live'),
    (v_crop_cotton_id, 'Cotton (Long Staple)', 'Warangal Enamamula', 'Warangal', CURRENT_DATE, 7820.00, 7350.00, 8100.00, 'live'),
    (v_crop_paddy_id, 'Paddy (Common)', 'Suryapet Market', 'Suryapet', CURRENT_DATE, 2320.00, 2203.00, 2350.00, 'live'),
    (v_crop_paddy_id, 'Paddy (Grade A)', 'Miryalaguda Mandi', 'Nalgonda', CURRENT_DATE, 2480.00, 2350.00, 2520.00, 'live'),
    (v_crop_chilli_id, 'Chilli (Teja / Dry Red)', 'Khammam APMC', 'Khammam', CURRENT_DATE, 19600.00, 17500.00, 21200.00, 'live'),
    (v_crop_maize_id, 'Maize (Hybrid)', 'Nizamabad Mandi', 'Nizamabad', CURRENT_DATE, 2180.00, 2050.00, 2240.00, 'live'),
    (v_crop_turmeric_id, 'Turmeric (Finger)', 'Nizamabad Mandi', 'Nizamabad', CURRENT_DATE, 14500.00, 13200.00, 15800.00, 'live')
  ON CONFLICT (crop_id, mandi_name, price_date, source) DO NOTHING;

END $$;
