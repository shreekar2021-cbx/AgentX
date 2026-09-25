# 🌾 AgriVision AI — Master Build Plan

> **Agentic AI Farmer Decision Intelligence Platform**
>
> Not just a crop disease detector — a full decision-support system that helps farmers
> identify problems, protect crops, prevent outbreaks, choose seeds, manage soil,
> understand markets, and maximize profitability.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Frontend["Frontend — React + Vite + TailwindCSS"]
        UI["Farmer UI / Admin UI"]
        Voice["Web Speech API"]
        Map["Leaflet + OSM"]
        Charts["Recharts"]
    end

    subgraph Backend["Backend — Python FastAPI"]
        API["REST API Layer"]
        Orchestrator["Agent Orchestrator"]
        CropAgent["Crop Intelligence Agent"]
        MarketAgent["Market Intelligence Agent"]
        SeedAgent["Seed Recommendation Agent"]
        FertAgent["Fertilizer Agent"]
        AlertAgent["Outbreak Alert Agent"]
    end

    subgraph External["External Services"]
        Gemini["Gemini API / Vision"]
        Weather["Open-Meteo API"]
        Mandi["AGMARKNET / data.gov.in"]
        FCM["Firebase Cloud Messaging"]
    end

    subgraph Data["Data Layer — Supabase"]
        DB["PostgreSQL"]
        Auth["Supabase Auth"]
        Storage["Supabase Storage"]
    end

    UI -->|HTTP / fetch| API
    Voice -->|transcript| API
    API --> Orchestrator
    Orchestrator --> CropAgent & MarketAgent & SeedAgent & FertAgent & AlertAgent
    CropAgent --> Gemini
    MarketAgent --> Mandi
    AlertAgent --> FCM
    API --> Weather
    API --> DB
    API --> Auth
    CropAgent --> Storage
    Map --> UI
    Charts --> UI
```

---

## Tech Stack (Locked)

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React 18 + Vite 5 + TailwindCSS 3 | Fast builds, utility-first styling, hackathon speed |
| **Backend** | Python 3.11 + FastAPI + Uvicorn | Async, auto-docs, Pydantic validation, ML-ready |
| **Database** | Supabase PostgreSQL | Managed Postgres + Auth + Storage in one platform |
| **Auth** | Supabase Auth | JWT-based, social logins, row-level security |
| **File Storage** | Supabase Storage | Signed URLs, image uploads, CDN-backed |
| **Primary AI** | Google Gemini 2.0 Flash | Multimodal (text + image), structured JSON output |
| **Weather** | Open-Meteo (free, no key) | Current + forecast + historical, geocoding |
| **Maps** | Leaflet + OpenStreetMap | Free, offline-capable tiles, marker clustering |
| **Market Data** | AGMARKNET / data.gov.in | Official Indian mandi commodity prices |
| **ML Prediction** | scikit-learn → XGBoost | Price trend prediction, lightweight models |
| **Notifications** | Firebase Cloud Messaging | Push notifications to mobile web |
| **Voice** | Web Speech API | Browser-native, no external dependency |
| **Charts** | Recharts | React-native, composable, responsive |
| **Distance** | Haversine formula | Pure math, no API dependency |
| **Languages** | English + Telugu | Core audience in Andhra Pradesh / Telangana |

---

## Folder Structure

```
agrivision/
├── frontend/                      # React + Vite
│   ├── public/
│   │   └── icons/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── common/            # Button, Card, Modal, Toast, Skeleton
│   │   │   ├── layout/            # Navbar, Sidebar, Footer, MobileNav
│   │   │   ├── crop/              # ImageUpload, DiagnosisCard, VoiceInput
│   │   │   ├── market/            # PriceTable, PriceChart, MandiMap
│   │   │   ├── farm/              # SoilForm, SeedCard, FertilizerCard
│   │   │   ├── alerts/            # AlertCard, AlertMap, NotificationBell
│   │   │   └── admin/             # ReportTable, StatusBadge, StatsGrid
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── ReportProblem.jsx
│   │   │   ├── CropResult.jsx
│   │   │   ├── MyCrops.jsx
│   │   │   ├── NearbyAlerts.jsx
│   │   │   ├── MyReports.jsx
│   │   │   ├── MarketIntelligence.jsx
│   │   │   ├── SeedFertilizer.jsx
│   │   │   └── AdminDashboard.jsx
│   │   ├── hooks/                 # useAuth, useLocation, useVoice, useApi
│   │   ├── services/              # api.js (axios/fetch wrapper)
│   │   ├── context/               # AuthContext, LanguageContext
│   │   ├── utils/                 # haversine.js, formatters.js
│   │   ├── i18n/                  # en.json, te.json
│   │   ├── App.jsx
│   │   ├── Router.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.js
│   ├── postcss.config.js
│   └── package.json
│
├── backend/                       # Python FastAPI
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, lifespan
│   │   ├── config.py              # Pydantic Settings (.env loader)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── auth.py
│   │   │   ├── crops.py
│   │   │   ├── reports.py
│   │   │   ├── alerts.py
│   │   │   ├── weather.py
│   │   │   ├── market.py
│   │   │   ├── farm.py
│   │   │   ├── notifications.py
│   │   │   └── admin.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # Intent detection → route to agent
│   │   │   ├── crop_agent.py      # Gemini text + vision analysis
│   │   │   ├── market_agent.py    # Mandi prices + prediction + best market
│   │   │   ├── seed_agent.py      # Seed recommendation via Gemini
│   │   │   ├── fertilizer_agent.py
│   │   │   └── alert_agent.py     # Outbreak risk scoring
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_service.py
│   │   │   ├── supabase_service.py
│   │   │   ├── weather_service.py
│   │   │   ├── mandi_service.py
│   │   │   ├── location_service.py
│   │   │   ├── notification_service.py
│   │   │   └── prediction_service.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py         # Pydantic request/response models
│   │   │   └── enums.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── haversine.py
│   │       └── error_handlers.py
│   ├── ml/
│   │   ├── train_price_model.py
│   │   ├── models/                # Saved .joblib models
│   │   └── data/                  # Training CSVs
│   ├── requirements.txt
│   └── .env.example
│
├── docs/
│   ├── API.md
│   ├── DATABASE.md
│   └── DEMO_SCRIPT.md
├── .gitignore
├── README.md
└── docker-compose.yml             # Optional: local dev with Supabase
```

---

## Database Schema (Supabase PostgreSQL)

```mermaid
erDiagram
    farmers ||--o{ farms : owns
    farmers ||--o{ reports : submits
    farmers ||--o{ notifications : receives
    farms ||--o{ crops : grows
    farms ||--o{ soil_tests : has
    reports ||--o{ alerts : triggers
    crops ||--|{ market_prices : has

    farmers {
        uuid id PK
        text full_name
        text phone
        text email
        text language "en | te"
        float latitude
        float longitude
        text district
        text state
        timestamptz created_at
    }

    farms {
        uuid id PK
        uuid farmer_id FK
        text farm_name
        float area_acres
        text irrigation_type "rainfed | drip | sprinkler | flood"
        float latitude
        float longitude
        text address
        timestamptz created_at
    }

    crops {
        uuid id PK
        uuid farm_id FK
        text crop_name
        text variety
        text season "kharif | rabi | zaid"
        date sowing_date
        date expected_harvest
        text growth_stage
        text status "active | harvested | failed"
        timestamptz created_at
    }

    reports {
        uuid id PK
        uuid farmer_id FK
        uuid crop_id FK
        text description
        text image_url
        text voice_transcript
        text language "en | te"
        jsonb ai_diagnosis
        float confidence
        text severity "low | medium | high | critical"
        text status "pending | verified | resolved"
        float latitude
        float longitude
        timestamptz created_at
    }

    alerts {
        uuid id PK
        uuid source_report_id FK
        text alert_type "disease_outbreak | pest_warning | weather_risk"
        text crop_affected
        text disease_name
        text severity "low | medium | high | critical"
        float center_lat
        float center_lng
        float radius_km
        int affected_farmer_count
        text status "active | monitoring | resolved"
        jsonb weather_context
        timestamptz created_at
        timestamptz expires_at
    }

    soil_tests {
        uuid id PK
        uuid farm_id FK
        float ph
        float nitrogen_kg_ha
        float phosphorus_kg_ha
        float potassium_kg_ha
        float organic_carbon_pct
        text soil_type "clay | loam | sandy | silt | red | black"
        text previous_crop
        date test_date
        timestamptz created_at
    }

    market_prices {
        uuid id PK
        text crop_name
        text market_name
        text district
        text state
        float min_price
        float max_price
        float modal_price
        text unit "quintal | kg"
        date price_date
        timestamptz fetched_at
    }

    recommendations {
        uuid id PK
        uuid farmer_id FK
        uuid farm_id FK
        text type "seed | fertilizer | market | general"
        jsonb input_context
        jsonb recommendation
        text model_used
        timestamptz created_at
    }

    notifications {
        uuid id PK
        uuid farmer_id FK
        uuid alert_id FK
        text title
        text body
        text type "alert | recommendation | market | system"
        bool is_read
        timestamptz created_at
    }
```

---

## Phase-by-Phase Build Plan

> [!IMPORTANT]
> **Golden Rule:** Build one phase → run it → test it → fix it → commit → then move to the next.
> Never skip phases or build multiple phases at once.

---

### Phase 1 · Project Foundation

**Goal:** React frontend talks to FastAPI backend via a health check endpoint.

**Build:**
| Component | Details |
|---|---|
| Frontend | `npm create vite@latest frontend -- --template react` + Tailwind + React Router |
| Backend | FastAPI app with CORS, health endpoint, Uvicorn |
| Connection | Frontend `fetch('/api/health')` → Backend returns `{ status: "healthy" }` |
| Config | `.env` files for both, `vite.config.js` proxy to port 8000 |

**Files to create:**

```
frontend/  → Vite scaffold + tailwind.config.js + postcss.config.js
backend/app/main.py        → FastAPI app with CORS
backend/app/config.py      → Settings from .env
backend/app/api/health.py  → GET /api/health
backend/requirements.txt   → fastapi, uvicorn, python-dotenv, pydantic-settings
.env.example               → Template for all env vars
```

**Success criteria:**
- [ ] `npm run dev` → React app on `localhost:5173`
- [ ] `uvicorn app.main:app --reload` → FastAPI on `localhost:8000`
- [ ] Browser shows "✅ Backend Connected" fetched from `/api/health`
- [ ] FastAPI docs accessible at `/docs`

**Estimated time:** 30–45 minutes

---

### Phase 2 · Farmer UI (Dummy Data)

**Goal:** Complete, clickable application with all major screens — zero API calls.

**Screens to build:**

| # | Screen | Key Components | Dummy Data |
|---|---|---|---|
| 1 | **Home** | Welcome card, quick actions grid, recent activity | 3 recent reports, 2 alerts |
| 2 | **Report Problem** | Image upload zone, text input, voice button (UI only), crop selector | N/A (form) |
| 3 | **Crop Result** | Diagnosis card, confidence bar, severity badge, action plan list | Tomato early blight, 89% |
| 4 | **My Crops** | Crop cards with status chips, growth stage progress | 3 crops: tomato, rice, chili |
| 5 | **Nearby Alerts** | Alert cards, mini Leaflet map with markers | 2 alerts within 10 km |
| 6 | **My Reports** | Report history list, status filters, date sort | 5 past reports |
| 7 | **Market Intelligence** | Price table, trend sparklines, mandi comparison | 4 mandis, tomato prices |
| 8 | **Seed & Fertilizer** | Soil info card, seed recommendation card, fertilizer card | Pre-filled soil data |
| 9 | **Admin Dashboard** | Stats grid, report table, severity heatmap, status actions | 20 reports across districts |

**UI design system:**

| Element | Specification |
|---|---|
| Colors | Green-700 primary, Amber-500 warning, Red-500 critical, Gray-50 background |
| Font | Inter (headings), system-ui (body) |
| Radius | `rounded-xl` cards, `rounded-lg` buttons |
| Spacing | `p-4` cards, `gap-4` grids, `space-y-3` stacks |
| Mobile | Bottom tab navigation (Home, Report, Alerts, Market, Profile) |
| Desktop | Left sidebar navigation |

**Success criteria:**
- [ ] All 9 screens render with dummy data
- [ ] React Router navigation between all pages works
- [ ] Responsive on mobile (375px) and desktop (1280px)
- [ ] No console errors

**Estimated time:** 4–6 hours

---

### Phase 3 · Supabase Integration

**Goal:** Real database, auth, and file storage replace all dummy data.

**Setup steps:**
1. Create Supabase project → get `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_KEY`
2. Run SQL migrations to create all 9 tables (see schema above)
3. Enable Row Level Security (RLS) on all tables
4. Configure Supabase Auth (email + phone)
5. Create `crop-images` storage bucket (public read, authenticated write)

**Backend integration:**

```python
# backend/app/services/supabase_service.py
from supabase import create_client, Client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
```

**API endpoints to build:**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/signup` | Register farmer |
| POST | `/api/auth/login` | Login, return JWT |
| GET | `/api/farmers/me` | Get current farmer profile |
| PUT | `/api/farmers/me` | Update profile + location |
| POST | `/api/reports` | Create crop problem report |
| GET | `/api/reports` | List farmer's reports |
| GET | `/api/reports/{id}` | Single report with diagnosis |
| POST | `/api/farms` | Add a farm |
| GET | `/api/farms` | List farmer's farms |
| POST | `/api/crops` | Add crop to farm |
| GET | `/api/crops` | List crops |

**Frontend integration:**
- `AuthContext` wrapping the app with login/signup flow
- Protected routes (redirect to login if not authenticated)
- Replace all dummy data with `useEffect` + `fetch` from API

**Success criteria:**
- [ ] Farmer can sign up, log in, log out
- [ ] Creating a report persists to Supabase `reports` table
- [ ] Refreshing the page retains auth state (JWT in localStorage)
- [ ] RLS prevents farmer A from seeing farmer B's data

**Estimated time:** 3–4 hours

---

### Phase 4 · Gemini Text Analysis

**Goal:** Farmer describes a problem in text → Gemini returns structured diagnosis.

**Backend service:**

```python
# backend/app/services/gemini_service.py
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

CROP_DIAGNOSIS_PROMPT = """
You are an expert agricultural scientist. Analyze the following crop problem 
described by a farmer. Respond ONLY with valid JSON:

{
  "possible_problem": "Disease or pest name",
  "confidence": 0.0 to 1.0,
  "severity": "low | medium | high | critical",
  "symptoms_identified": ["symptom1", "symptom2"],
  "possible_causes": ["cause1", "cause2"],
  "immediate_actions": ["action1", "action2"],
  "preventive_measures": ["measure1", "measure2"],
  "needs_expert": true/false
}

Farmer's description: {description}
Crop: {crop_name}
Location: {district}, {state}
Season: {season}
"""
```

**API endpoint:**

| Method | Endpoint | Body | Response |
|---|---|---|---|
| POST | `/api/analyze/text` | `{ description, crop_name, district, state, season }` | `{ diagnosis: {...} }` |

**Success criteria:**
- [ ] `"My tomato leaves have black spots"` → returns structured JSON
- [ ] Confidence score is between 0 and 1
- [ ] Severity is one of the 4 allowed values
- [ ] Response time < 5 seconds
- [ ] Graceful error if Gemini is unreachable

**Estimated time:** 1–2 hours

---

### Phase 5 · Crop Image Analysis

**Goal:** Upload a leaf photo → Gemini Vision identifies the disease.

**Flow:**

```mermaid
sequenceDiagram
    participant F as Farmer (Browser)
    participant API as FastAPI
    participant S as Supabase Storage
    participant G as Gemini Vision

    F->>API: POST /api/analyze/image (multipart)
    API->>S: Upload image to crop-images bucket
    S-->>API: Public URL
    API->>G: Send image + prompt
    G-->>API: Structured diagnosis JSON
    API->>API: Save report to DB
    API-->>F: { image_url, diagnosis }
```

**Image handling rules:**
- Max file size: 5 MB
- Accepted formats: JPEG, PNG, WebP
- Resize to max 1024px on longest side before sending to Gemini (saves tokens)
- Store original in Supabase Storage

**Gemini Vision prompt addition:**

```text
Analyze the attached image of a crop leaf/plant. Identify:
1. The crop species (if identifiable)
2. Visible symptoms (discoloration, spots, wilting, holes, etc.)
3. Probable disease or pest
4. Confidence level

Combine with the farmer's text description if provided.
```

**API endpoint:**

| Method | Endpoint | Body | Response |
|---|---|---|---|
| POST | `/api/analyze/image` | `multipart: image, crop_name?, description?` | `{ image_url, diagnosis }` |

**Success criteria:**
- [ ] Upload a tomato leaf image with black spots → correct disease identification
- [ ] Image is saved to Supabase Storage, URL stored in `reports.image_url`
- [ ] Works with and without text description
- [ ] Rejects files > 5 MB with clear error message

**Estimated time:** 2–3 hours

---

### Phase 6 · Voice Input

**Goal:** Farmer speaks into microphone → text transcription → Gemini analysis.

**Implementation:**

```javascript
// frontend/src/hooks/useVoice.js
const useVoice = (language = 'en-IN') => {
  const recognition = new webkitSpeechRecognition();
  recognition.lang = language;  // 'en-IN' or 'te-IN'
  recognition.continuous = false;
  recognition.interimResults = true;
  // ...
};
```

**UI flow:**
1. Farmer taps 🎤 button → recording indicator appears
2. Browser shows "Listening..." with interim transcript
3. Farmer stops speaking → final transcript shown
4. Farmer reviews/edits text → taps "Analyze"
5. Text sent to `/api/analyze/text`

**Language support:**
- Phase 6a: English (`en-IN`) — build and verify
- Phase 6b: Telugu (`te-IN`) — add after Phase 21

**Success criteria:**
- [ ] Microphone permission prompt appears
- [ ] Interim transcript updates in real-time
- [ ] Final transcript is editable before submission
- [ ] Works on Chrome mobile and desktop
- [ ] Graceful fallback if Speech API unavailable ("Please type your problem instead")

**Estimated time:** 1–2 hours

---

### Phase 7 · Weather Integration

**Goal:** Fetch current + forecast weather for farmer's location, feed into AI context.

**Open-Meteo endpoints (no API key needed):**

| Purpose | URL |
|---|---|
| Current + Forecast | `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,rain,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,rain_sum,wind_speed_10m_max&timezone=Asia/Kolkata` |
| Historical | `https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lng}&start_date={start}&end_date={end}&daily=temperature_2m_max,rain_sum` |
| Geocoding | `https://geocoding-api.open-meteo.com/v1/search?name={city}&count=5&language=en&format=json` |

**Backend service:**

```python
# backend/app/services/weather_service.py
async def get_weather(lat: float, lng: float) -> WeatherData:
    """Returns current conditions + 7-day forecast."""

async def get_weather_context_for_ai(lat: float, lng: float) -> str:
    """Returns a natural-language weather summary for Gemini prompt injection."""
    # Example output:
    # "Current: 32°C, 78% humidity, no rain. 
    #  Forecast: Rain expected in 2 days (15mm). 
    #  Risk: High humidity favors fungal diseases."
```

**API endpoint:**

| Method | Endpoint | Query Params | Response |
|---|---|---|---|
| GET | `/api/weather` | `lat, lng` | `{ current, forecast_7day, ai_summary }` |

**Enhanced Gemini prompt (inject weather):**

```text
Weather at farmer's location:
{weather_context}

Consider weather conditions when assessing disease risk and recommending actions.
```

**Success criteria:**
- [ ] Weather card on Home page shows current temperature, humidity, rain, wind
- [ ] 7-day forecast renders as a simple chart or card row
- [ ] Weather context is included in Gemini crop diagnosis prompts
- [ ] Works without location (shows "Set your location to see weather")

**Estimated time:** 1.5–2 hours

---

### Phase 8 · Location Services

**Goal:** Detect or manually set farmer location; show on Leaflet map.

**Two-track approach:**

| Track | Implementation |
|---|---|
| **Auto-detect** | `navigator.geolocation.getCurrentPosition()` with permission prompt |
| **Manual fallback** | Searchable dropdown (Open-Meteo geocoding) or map pin |

**Storage:** Save `latitude`, `longitude`, `district` in `farmers` table.

**Leaflet map integration:**
- Add to: Nearby Alerts, Market Intelligence, Admin Dashboard
- Markers for: farmer location (blue), alerts (red), mandis (green)
- Tile layer: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`

**API endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| PUT | `/api/farmers/me/location` | Update farmer's lat/lng/district |
| GET | `/api/geocode?q={query}` | Search for a place (proxied Open-Meteo) |

**Success criteria:**
- [ ] Browser location permission → auto-fills lat/lng
- [ ] Manual search "Warangal" → returns coordinates
- [ ] Leaflet map renders with farmer's position marker
- [ ] Location persists across sessions

**Estimated time:** 1.5–2 hours

---

### Phase 9 · Nearby Farmer Matching

**Goal:** Find farmers within 10 km growing the same crop who reported similar problems.

**Haversine implementation:**

```python
# backend/app/utils/haversine.py
import math

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

**Query strategy (efficient):**
1. First: bounding-box filter in SQL (fast, eliminates 99% of rows)
2. Then: Haversine on the remaining rows (accurate)

```sql
-- Step 1: Bounding box (±0.09° ≈ 10 km)
SELECT * FROM reports
WHERE latitude BETWEEN {lat - 0.09} AND {lat + 0.09}
  AND longitude BETWEEN {lng - 0.09} AND {lng + 0.09}
  AND crop_name = {crop_name}
  AND created_at > NOW() - INTERVAL '30 days';
```

**API endpoint:**

| Method | Endpoint | Query Params | Response |
|---|---|---|---|
| GET | `/api/nearby/reports` | `lat, lng, crop, radius_km=10` | `[{ report, distance_km, farmer_name }]` |

**Success criteria:**
- [ ] Returns only reports within specified radius
- [ ] Filters by matching crop
- [ ] Distance calculation is accurate (±0.1 km)
- [ ] Returns 0 results gracefully when no nearby matches

**Estimated time:** 1–1.5 hours

---

### Phase 10 · Outbreak Alert Agent

**Goal:** Automatically detect when multiple nearby reports indicate an outbreak.

**Risk scoring formula:**

```python
def calculate_outbreak_risk(
    disease_confidence: float,   # 0.0 – 1.0
    severity: str,               # low=0.25, medium=0.5, high=0.75, critical=1.0
    humidity: float,             # > 80% increases fungal risk
    recent_rain: bool,           # rain in last 48h
    nearby_report_count: int,    # same disease within 10 km, last 14 days
    spread_rate: str             # known spread rate for this disease
) -> float:
    base = disease_confidence * severity_score
    weather_multiplier = 1.0
    if humidity > 80: weather_multiplier += 0.2
    if recent_rain: weather_multiplier += 0.15
    
    community_factor = min(nearby_report_count * 0.15, 0.5)
    
    risk = base * weather_multiplier + community_factor
    return min(risk, 1.0)  # Clamp to 0–1
```

**Thresholds:**

| Risk Score | Action |
|---|---|
| 0.0 – 0.3 | No alert. Log for monitoring. |
| 0.3 – 0.6 | Create **advisory** alert (low priority) |
| 0.6 – 0.8 | Create **warning** alert (medium priority, notify nearby farmers) |
| 0.8 – 1.0 | Create **critical outbreak** alert (high priority, notify all in radius) |

**Trigger:** Runs automatically after every new report is created (POST `/api/reports`).

**Success criteria:**
- [ ] 3+ nearby reports of same disease within 14 days → creates alert
- [ ] Alert has correct radius and affected farmer count
- [ ] Weather context influences risk score appropriately
- [ ] Alert saved to `alerts` table with `source_report_id`

**Estimated time:** 2–3 hours

---

### Phase 11 · Notifications

**Goal:** In-app notification bell + Firebase push notifications.

**Phase 11a — In-app notifications:**
- Notification bell icon with unread count badge
- Dropdown/page showing notification history
- Mark as read on click
- Polling: fetch every 30 seconds (or Supabase Realtime subscription)

**Phase 11b — Firebase Cloud Messaging:**

```javascript
// frontend/src/services/firebase.js
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

// Store FCM token in farmers table
// Backend sends push via Firebase Admin SDK
```

**Notification flow:**

```mermaid
sequenceDiagram
    participant A as Farmer A
    participant API as FastAPI
    participant Alert as Alert Agent
    participant DB as Supabase
    participant FCM as Firebase
    participant B as Farmer B

    A->>API: Submit report (high severity)
    API->>Alert: Evaluate outbreak risk
    Alert->>Alert: Risk score = 0.75 (WARNING)
    Alert->>DB: Create alert + find farmers in radius
    Alert->>DB: Create notification for each farmer
    Alert->>FCM: Send push to all affected
    FCM->>B: 🔔 "Tomato Early Blight detected 3 km from you"
```

**Success criteria:**
- [ ] Notification bell shows unread count
- [ ] Clicking notification navigates to relevant alert/report
- [ ] Push notification received on mobile Chrome (requires HTTPS)
- [ ] Notification includes: crop, disease, distance, severity

**Estimated time:** 2–3 hours

---

### Phase 12 · Mandi Price API

**Goal:** Fetch live commodity prices from AGMARKNET / data.gov.in.

**Primary data source:**

```
https://api.data.gov.in/resource/{resource_id}
?api-key={DATA_GOV_API_KEY}
&format=json
&filters[commodity]={crop}
&filters[state]={state}
&limit=50
```

> [!WARNING]
> **Fallback strategy:** data.gov.in API can be unreliable. Build a fallback:
> 1. Try live API
> 2. If timeout (5s) → return cached data from Supabase
> 3. If no cache → return sample data with "prices may not be current" warning

**API endpoint:**

| Method | Endpoint | Query Params | Response |
|---|---|---|---|
| GET | `/api/market/prices` | `crop, state, district?` | `[{ market, min_price, max_price, modal_price, date }]` |

**Frontend display:**

| Column | Example |
|---|---|
| Mandi | Warangal |
| Min ₹ | ₹2,100/qtl |
| Max ₹ | ₹2,800/qtl |
| Modal ₹ | ₹2,450/qtl |
| Date | 25 Sep 2026 |
| Trend | ↑ Rising |

**Success criteria:**
- [ ] Prices display for at least 3 mandis for the selected crop
- [ ] Data is no older than 7 days
- [ ] Fallback to cached data works when API is down
- [ ] Prices stored in `market_prices` table for history

**Estimated time:** 2–3 hours

---

### Phase 13 · Market Price History

**Goal:** Store fetched prices over time, display trend charts.

**Data storage:** Every API fetch appends to `market_prices` table (deduplicated by market + crop + date).

**Chart implementation (Recharts):**

```jsx
<LineChart data={priceHistory}>
  <XAxis dataKey="date" />
  <YAxis unit="₹" />
  <Line type="monotone" dataKey="modal_price" stroke="#16a34a" />
  <Tooltip />
</LineChart>
```

**API endpoint:**

| Method | Endpoint | Query Params | Response |
|---|---|---|---|
| GET | `/api/market/history` | `crop, market, days=30` | `[{ date, min, max, modal }]` |

**Scheduled fetch:** Backend cron job (or manual trigger) fetches prices daily for tracked crops.

**Success criteria:**
- [ ] Line chart shows price trend for last 30 days
- [ ] At least 10 data points plotted
- [ ] Multiple mandis can be compared on same chart
- [ ] Chart is responsive on mobile

**Estimated time:** 1.5–2 hours

---

### Phase 14 · Market Price Prediction

**Goal:** Predict short-term price trend (Rising / Stable / Falling) using ML.

**Model approach:**

| Aspect | Choice |
|---|---|
| Algorithm | XGBoost (or Random Forest as fallback) |
| Features | Last 7 days' modal prices, day-of-week, month, rolling avg, price volatility |
| Target | 3-class: Rising (+5%), Stable (±5%), Falling (−5%) |
| Training data | Historical prices from `market_prices` table (min 60 days) |
| Retraining | Weekly or on-demand |

**Implementation:**

```python
# backend/ml/train_price_model.py
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
import joblib

def train_model(crop: str, market: str):
    # Feature engineering from price history
    # Train with TimeSeriesSplit (not random split!)
    # Save model as .joblib
    pass
```

**API endpoint:**

| Method | Endpoint | Query Params | Response |
|---|---|---|---|
| GET | `/api/market/predict` | `crop, market` | `{ trend: "rising", confidence: 0.72, predicted_price_range }` |

> [!CAUTION]
> **Disclaimer required in UI:** "Price predictions are estimates based on historical patterns. Actual prices may vary. Not financial advice."

**Success criteria:**
- [ ] Model trains without errors on 60+ days of data
- [ ] Prediction returns one of 3 trend classes
- [ ] Confidence score is meaningful (>50% for correct class)
- [ ] API response < 200ms (model loaded in memory)
- [ ] Graceful fallback: "Insufficient data for prediction" if < 30 data points

**Estimated time:** 3–4 hours

---

### Phase 15 · Best Mandi Agent

**Goal:** Calculate the best market for selling, accounting for all real costs.

**Net return calculation:**

```python
def calculate_net_return(
    quantity_quintals: float,
    price_per_quintal: float,
    distance_km: float,
    transport_cost_per_km: float = 15,   # ₹15/km for tempo
    loading_cost_per_quintal: float = 50, # ₹50/qtl
    commission_pct: float = 0.02,         # 2% mandi commission
    spoilage_pct: float = 0.0,           # Depends on crop + distance
    storage_days: int = 0,
    storage_cost_per_day: float = 100
) -> dict:
    gross = quantity_quintals * price_per_quintal
    transport = distance_km * transport_cost_per_km * 2  # Round trip
    loading = quantity_quintals * loading_cost_per_quintal
    commission = gross * commission_pct
    spoilage = gross * spoilage_pct
    storage = storage_days * storage_cost_per_day

    net = gross - transport - loading - commission - spoilage - storage
    return {
        "gross_revenue": gross,
        "transport_cost": transport,
        "loading_cost": loading,
        "commission": commission,
        "spoilage_loss": spoilage,
        "storage_cost": storage,
        "net_return": net,
        "return_per_quintal": net / quantity_quintals
    }
```

**API endpoint:**

| Method | Endpoint | Body | Response |
|---|---|---|---|
| POST | `/api/market/best` | `{ crop, quantity, farmer_lat, farmer_lng }` | `{ rankings: [{ market, net_return, breakdown, trend }] }` |

**UI output:**

```
🏆 Best Market: Warangal Mandi
   Net Return: ₹19,700
   Trend: ↗ Possibly Rising

2. Hyderabad Market Yard
   Net Return: ₹18,200
   Trend: → Stable

3. Karimnagar Mandi
   Net Return: ₹17,900
   Trend: ↘ Possibly Falling
```

**Success criteria:**
- [ ] Ranks at least 3 mandis by net return
- [ ] Cost breakdown is transparent and itemized
- [ ] Distance calculated via Haversine from farmer's location
- [ ] Price trend from Phase 14 is integrated

**Estimated time:** 2–3 hours

---

### Phase 16 · Farm & Soil Information

**Goal:** Farmer enters farm and soil details for personalized recommendations.

**Form fields:**

| Field | Type | Validation |
|---|---|---|
| Farm Area | Number (acres) | > 0, ≤ 1000 |
| Current Crop | Select | From crop list |
| Season | Select | Kharif / Rabi / Zaid |
| Soil Type | Select | Clay / Loam / Sandy / Silt / Red / Black |
| pH | Number | 3.0 – 10.0 |
| Nitrogen (N) | Number (kg/ha) | 0 – 500 |
| Phosphorus (P) | Number (kg/ha) | 0 – 200 |
| Potassium (K) | Number (kg/ha) | 0 – 500 |
| Organic Carbon % | Number | 0 – 5 |
| Previous Crop | Select | From crop list |
| Irrigation Type | Select | Rainfed / Drip / Sprinkler / Flood |

**API endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/farms/{id}/soil-test` | Save soil test data |
| GET | `/api/farms/{id}/soil-test` | Get latest soil test |

**Success criteria:**
- [ ] Form validates all inputs with clear error messages
- [ ] Data saves to `soil_tests` table linked to farm
- [ ] Soil data card displays on Seed & Fertilizer page
- [ ] NPK values shown with status indicators (Low / Normal / High)

**Estimated time:** 1.5–2 hours

---

### Phase 17 · Seed Recommendation Agent

**Goal:** Gemini generates personalized seed recommendations based on farm context.

**Gemini prompt:**

```text
You are an expert Indian agricultural advisor. Based on the following farm data,
recommend suitable seed varieties. Respond ONLY with valid JSON.

Farm Data:
- Location: {district}, {state}
- Season: {season}
- Soil Type: {soil_type}, pH: {ph}
- Irrigation: {irrigation}
- Previous Crop: {previous_crop}
- Farm Area: {area} acres
- Target Crop: {crop}

Weather Context:
{weather_summary}

Respond with:
{
  "recommended_seeds": [
    {
      "variety_name": "...",
      "type": "hybrid | open-pollinated | desi",
      "maturity_days": 90,
      "yield_potential": "high | medium",
      "disease_resistance": ["early blight", "..."],
      "water_requirement": "low | medium | high",
      "suitability_score": 0.0–1.0,
      "reason": "Why this variety suits this farm"
    }
  ],
  "sowing_window": "June 15 – July 15",
  "seed_rate_kg_per_acre": 0.4,
  "seed_treatment": "...",
  "spacing": "60cm x 45cm"
}
```

> [!NOTE]
> Gemini may suggest generic varieties. For production, ground recommendations
> with ICAR / SAU data for the specific agro-climatic zone.

**Success criteria:**
- [ ] Returns 2–4 seed variety recommendations
- [ ] Each has a clear suitability reason
- [ ] Recommendations consider soil pH, season, and irrigation
- [ ] Response saved to `recommendations` table

**Estimated time:** 2–3 hours

---

### Phase 18 · Fertilizer Recommendation Agent

**Goal:** Generate nutrient management plan based on soil test + crop requirements.

**Nutrient assessment logic:**

```python
# Crop-specific NPK requirements (kg/ha) — reference ranges
CROP_REQUIREMENTS = {
    "tomato":  {"N": (120, 150), "P": (60, 80),  "K": (100, 120)},
    "rice":    {"N": (100, 120), "P": (40, 60),  "K": (60, 80)},
    "cotton":  {"N": (80, 100),  "P": (40, 50),  "K": (40, 60)},
    "chili":   {"N": (100, 120), "P": (50, 60),  "K": (80, 100)},
}

def assess_nutrient(current: float, required_range: tuple) -> str:
    if current < required_range[0] * 0.6: return "deficient"
    if current < required_range[0]: return "low"
    if current <= required_range[1]: return "adequate"
    return "high"
```

**Gemini prompt includes:** soil test data + crop requirements + weather + growth stage.

**Output format:**

```json
{
  "nutrient_status": {
    "nitrogen": { "level": "low", "current": 85, "required": 120 },
    "phosphorus": { "level": "adequate", "current": 55, "required": 60 },
    "potassium": { "level": "deficient", "current": 30, "required": 100 }
  },
  "priority_nutrients": ["potassium", "nitrogen"],
  "fertilizer_plan": [
    {
      "fertilizer": "Muriate of Potash (MOP)",
      "quantity_kg_per_acre": 35,
      "application_time": "Basal (at sowing)",
      "method": "Broadcasting + incorporation"
    }
  ],
  "organic_alternatives": ["Vermicompost @ 2 tonnes/acre"],
  "caution": "Do not over-apply nitrogen — increases disease susceptibility"
}
```

> [!CAUTION]
> **Safety rule:** Keep all chemical dosing recommendations conservative.
> Always include "Consult your local agricultural extension officer for precise dosing."

**Success criteria:**
- [ ] Correctly identifies deficient nutrients from soil test data
- [ ] Recommends specific fertilizer names and quantities
- [ ] Includes both chemical and organic options
- [ ] Safety disclaimer displayed prominently in UI

**Estimated time:** 2–3 hours

---

### Phase 19 · Agent Orchestrator

**Goal:** Single entry point that detects user intent and routes to the correct agent.

**Implementation:**

```python
# backend/app/agents/orchestrator.py

INTENT_PROMPT = """
Classify the farmer's question into exactly one category:
- crop_problem: Disease, pest, leaf damage, crop health issues
- market_query: Prices, where to sell, market trends, best mandi
- seed_query: Which seed to plant, varieties, sowing
- fertilizer_query: Nutrients, fertilizer, soil health, NPK
- weather_query: Weather, rain, temperature, forecast
- general: Greeting, help, unclear intent

Respond with ONLY the category name.

Question: {question}
"""

AGENT_MAP = {
    "crop_problem": crop_agent,
    "market_query": market_agent,
    "seed_query": seed_agent,
    "fertilizer_query": fertilizer_agent,
    "weather_query": weather_service,
    "general": general_handler,
}
```

**API endpoint:**

| Method | Endpoint | Body | Response |
|---|---|---|---|
| POST | `/api/ask` | `{ question, image?, farmer_id }` | `{ intent, agent_used, response }` |

**Example routing:**

| Farmer says | Detected intent | Agent |
|---|---|---|
| "My leaves are turning yellow" | `crop_problem` | Crop Agent |
| "Where should I sell tomato?" | `market_query` | Market Agent |
| "Which seed should I use for rabi?" | `seed_query` | Seed Agent |
| "How much urea for rice?" | `fertilizer_query` | Fertilizer Agent |
| "Will it rain tomorrow?" | `weather_query` | Weather Service |

**Success criteria:**
- [ ] Intent classification accuracy > 90% on test cases
- [ ] Correct agent is invoked and response returned
- [ ] Works with both English and Telugu input
- [ ] UI shows which agent is processing (with animation)

**Estimated time:** 2–3 hours

---

### Phase 20 · Admin / Expert Dashboard

**Goal:** Agricultural officers can review reports, verify diagnoses, manage outbreaks.

**Dashboard sections:**

| Section | Components |
|---|---|
| **Overview** | Total reports (24h / 7d / 30d), active alerts, verified %, high-risk count |
| **Report Queue** | Filterable table: crop, severity, confidence, status, date |
| **Report Detail** | Image, farmer description, AI diagnosis, weather context, nearby reports |
| **Alert Map** | Leaflet map with outbreak circles, color-coded by severity |
| **Actions** | Buttons: Verify ✓, Needs Review ?, Resolve ✓✓ — updates report status |

**Admin API endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/admin/reports` | All reports with filters (severity, status, date range, crop) |
| PUT | `/api/admin/reports/{id}/status` | Update report status (verified/review/resolved) |
| GET | `/api/admin/alerts` | All active alerts |
| PUT | `/api/admin/alerts/{id}/status` | Update alert status |
| GET | `/api/admin/stats` | Dashboard statistics |

**Access control:** Admin role check via Supabase Auth metadata.

**Success criteria:**
- [ ] Dashboard loads with real aggregated statistics
- [ ] Report table supports filtering + sorting
- [ ] Status update reflects immediately in farmer's "My Reports"
- [ ] Map shows all active alerts with severity-colored circles

**Estimated time:** 3–4 hours

---

### Phase 21 · Telugu Language Support

**Goal:** Full Telugu support for voice, text, and AI responses.

**Three layers:**

| Layer | Implementation |
|---|---|
| **UI strings** | `i18n/te.json` — all labels, buttons, headers in Telugu |
| **Voice** | Web Speech API with `lang: 'te-IN'` |
| **AI responses** | Gemini prompt suffix: `"Respond in Telugu (తెలుగు)"` |

**Language toggle:** Switch in navbar, persisted in localStorage + farmer profile.

**UI translation file structure:**

```json
// frontend/src/i18n/te.json
{
  "home": { "title": "హోమ్", "welcome": "నమస్కారం, {name}" },
  "report": { "title": "సమస్యను నివేదించండి", "upload": "ఫోటో అప్‌లోడ్ చేయండి" },
  "market": { "title": "మార్కెట్ ధరలు", "best_market": "ఉత్తమ మండి" }
}
```

**Success criteria:**
- [ ] All UI text switches to Telugu when toggled
- [ ] Voice input works in Telugu (`te-IN`)
- [ ] Gemini responses come back in Telugu
- [ ] No layout breakage with Telugu characters (wider glyphs)

**Estimated time:** 2–3 hours

---

### Phase 22 · Error Handling & Resilience

**Goal:** Every external dependency has loading, error, retry, and fallback states.

**Error handling matrix:**

| Service | Timeout | Retry | Fallback |
|---|---|---|---|
| Gemini API | 15s | 2× with backoff | "AI analysis temporarily unavailable. Please try again." |
| Open-Meteo | 5s | 1× | Show last cached weather + "Last updated: {time}" |
| data.gov.in | 5s | 1× | Show cached prices + "Prices from {date}" |
| Supabase DB | 5s | 2× | Show error, don't lose user's form data |
| Supabase Storage | 10s | 1× | "Image upload failed. You can describe the problem in text." |
| Firebase FCM | 3s | 1× | Silent fail (in-app notification still works) |
| Speech API | N/A | N/A | Show text input + "Voice not available on this device" |

**Frontend patterns:**

```jsx
// Every API call follows this pattern:
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);

// UI renders: loading skeleton → data → error with retry button
```

**Backend patterns:**

```python
# backend/app/utils/error_handlers.py
from fastapi import HTTPException
import httpx

async def safe_external_call(url, timeout=5, retries=1, fallback=None):
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.get(url)
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == retries and fallback:
                return fallback
    raise HTTPException(503, "External service unavailable")
```

**Success criteria:**
- [ ] No unhandled promise rejections in browser console
- [ ] Every API call shows a loading skeleton
- [ ] Failed API calls show a user-friendly message + retry button
- [ ] Form data is preserved when an API call fails (user doesn't re-enter)
- [ ] Backend returns proper HTTP status codes (400, 401, 404, 500, 503)

**Estimated time:** 2–3 hours

---

### Phase 23 · UI Polish

**Goal:** Production-quality visual polish — this is what judges see first.

**Polish checklist:**

| Category | Items |
|---|---|
| **Loading** | Skeleton screens for cards, tables, charts; shimmer animation |
| **Feedback** | Toast notifications (success green, error red, info blue) |
| **Animations** | Page transitions (fade), card entrance (slide-up), button press (scale) |
| **Agent UX** | "🤖 Analyzing..." progress with animated dots, step-by-step reveal |
| **Icons** | Lucide React icon set (consistent line style) |
| **Charts** | Gradient fills, custom tooltips, responsive sizing |
| **Mobile** | Bottom nav with active indicator, swipeable cards, touch-friendly targets (48px min) |
| **Dark mode** | Optional — only if time permits (Tailwind `dark:` variant) |
| **Empty states** | Illustrated SVG + message for "No reports yet", "No alerts nearby" |
| **Micro-copy** | Helpful placeholder text, tooltip explanations, ₹ formatting |

**Key animations for demo impact:**

```css
/* Agent thinking animation */
@keyframes pulse-dot {
  0%, 80%, 100% { opacity: 0; }
  40% { opacity: 1; }
}

/* Card entrance */
@keyframes slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
```

**Success criteria:**
- [ ] No layout shifts (CLS ≈ 0)
- [ ] All interactive elements have hover/active states
- [ ] Consistent spacing, colors, and typography throughout
- [ ] Mobile experience feels native-app-like

**Estimated time:** 3–5 hours

---

### Phase 24 · Demo Preparation

**Goal:** Three flawless, rehearsed demo flows that showcase the full platform.

---

#### Demo A — Crop Disease Intelligence (3 minutes)

```mermaid
flowchart LR
    A["📸 Upload leaf photo"] --> B["🤖 Gemini Vision analyzes"]
    B --> C["🦠 Early Blight detected\n89% confidence"]
    C --> D["🌤 Weather: High humidity\nfavors fungal spread"]
    D --> E["⚠️ Risk Score: 0.75\nOutbreak Warning"]
    E --> F["🔔 3 nearby farmers notified"]
    F --> G["🗺 Alert shown on map"]
```

**Talking points:**
- "Farmer photographs a diseased leaf"
- "AI identifies the disease in seconds"
- "Weather context increases the risk assessment"
- "Nearby farmers are automatically warned"
- "Agricultural officer sees this in the admin dashboard"

**Pre-loaded data needed:**
- 2–3 existing reports for nearby farmers (same crop, same area)
- Weather showing high humidity
- Test image of tomato early blight

---

#### Demo B — Market Intelligence (3 minutes)

```mermaid
flowchart LR
    A["🍅 Select: Tomato\n5 quintals"] --> B["📊 Live mandi prices\n4 nearby mandis"]
    B --> C["📈 Price trend chart\n30-day history"]
    C --> D["🤖 ML prediction:\nRising trend"]
    D --> E["🏆 Best Market:\nWarangal Mandi\nNet ₹19,700"]
    E --> F["💰 Cost breakdown:\nTransport, commission,\nspoilage"]
```

**Talking points:**
- "Farmer wants to sell tomatoes"
- "We show live prices from government data"
- "ML model predicts the trend direction"
- "We calculate the REAL net return including all costs"
- "Farmer makes a data-driven decision"

**Pre-loaded data needed:**
- 30+ days of price history for tomato in 3–4 mandis
- Trained XGBoost model
- Farmer location set (for distance calculation)

---

#### Demo C — Seed & Soil Intelligence (2 minutes)

```mermaid
flowchart LR
    A["🧪 Enter soil test:\npH 6.5, N: Low, K: Low"] --> B["🌱 Seed Agent:\n3 variety recommendations"]
    B --> C["🧬 Best: Arka Rakshak\nDisease resistant\nHigh yield"]
    C --> D["🪴 Fertilizer Agent:\nPriority: K then N"]
    D --> E["📋 Application plan:\nMOP 35 kg/acre basal\nUrea 40 kg/acre split"]
```

**Talking points:**
- "Farmer enters soil test results"
- "AI recommends disease-resistant varieties suited to their soil"
- "Fertilizer plan addresses specific nutrient deficiencies"
- "Dosing is conservative and includes organic alternatives"

**Pre-loaded data needed:**
- Farm with soil test data
- Crop set to tomato, season to kharif

---

#### Bonus Demo — Voice + Telugu (1 minute)

```
🎤 Farmer speaks in Telugu:
"నా టమాటో ఆకులు పసుపు రంగులోకి మారుతున్నాయి"

→ Transcribed to text
→ Farmer verifies
→ Gemini responds in Telugu
→ 🦠 "ఎర్లీ బ్లైట్ సమస్యగా ఉండవచ్చు"
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| data.gov.in API down during demo | **High** | High | Pre-cache 30 days of prices; show cached data with timestamp |
| Gemini rate limit hit | Medium | High | Cache frequent diagnoses; use `gemini-2.0-flash` (higher limits) |
| Web Speech API fails on demo laptop | Medium | Medium | Pre-record a demo audio; have text fallback ready |
| Supabase free tier limits | Low | Medium | Seed only demo data; cleanup test data before demo |
| Telugu voice recognition poor | **High** | Low | Have text input pre-filled as fallback; focus demo on English |
| Browser location blocked | Medium | Low | Pre-set location via manual search |
| Slow internet at venue | Medium | High | Deploy backend on a cloud VM; use local WiFi hotspot |

---

## Environment Variables

```bash
# .env.example — Complete list of all required environment variables

# === Supabase ===
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# === Google Gemini ===
GEMINI_API_KEY=AIza...

# === data.gov.in (Mandi Prices) ===
DATA_GOV_API_KEY=xxxxx

# === Firebase (Push Notifications) ===
FIREBASE_PROJECT_ID=agrivision-ai
FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@...

# === Frontend (VITE_ prefix required) ===
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_FIREBASE_API_KEY=AIza...
VITE_FIREBASE_MESSAGING_SENDER_ID=123456
VITE_FIREBASE_APP_ID=1:123456:web:abc
VITE_FIREBASE_VAPID_KEY=BPq...

# === App Config ===
CORS_ORIGINS=http://localhost:5173
DEFAULT_LANGUAGE=en
ALERT_RADIUS_KM=10
OUTBREAK_RISK_THRESHOLD=0.6
```

---

## Time Estimates Summary

| Phase | Task | Estimated Hours |
|---|---|---|
| 1 | Foundation | 0.5 – 0.75 |
| 2 | UI (dummy data) | 4 – 6 |
| 3 | Supabase integration | 3 – 4 |
| 4 | Gemini text analysis | 1 – 2 |
| 5 | Crop image analysis | 2 – 3 |
| 6 | Voice input | 1 – 2 |
| 7 | Weather API | 1.5 – 2 |
| 8 | Location services | 1.5 – 2 |
| 9 | Nearby farmer matching | 1 – 1.5 |
| 10 | Outbreak alert agent | 2 – 3 |
| 11 | Notifications | 2 – 3 |
| 12 | Mandi price API | 2 – 3 |
| 13 | Price history + charts | 1.5 – 2 |
| 14 | Market prediction (ML) | 3 – 4 |
| 15 | Best mandi agent | 2 – 3 |
| 16 | Farm & soil form | 1.5 – 2 |
| 17 | Seed recommendation | 2 – 3 |
| 18 | Fertilizer recommendation | 2 – 3 |
| 19 | Agent orchestrator | 2 – 3 |
| 20 | Admin dashboard | 3 – 4 |
| 21 | Telugu support | 2 – 3 |
| 22 | Error handling | 2 – 3 |
| 23 | UI polish | 3 – 5 |
| 24 | Demo preparation | 2 – 3 |
| | **TOTAL** | **~46 – 68 hours** |

---

## Critical Path (Minimum Viable Demo)

If pressed for time, this is the **absolute minimum** to build for a compelling demo:

```mermaid
flowchart LR
    P1["1. Foundation\n(30 min)"] --> P2["2. UI\n(4 hrs)"]
    P2 --> P3["3. Supabase\n(3 hrs)"]
    P3 --> P4["4. Gemini Text\n(1 hr)"]
    P4 --> P5["5. Gemini Image\n(2 hrs)"]
    P5 --> P7["7. Weather\n(1.5 hrs)"]
    P7 --> P8["8. Location\n(1.5 hrs)"]
    P8 --> P12["12. Mandi Prices\n(2 hrs)"]
    P12 --> P19["19. Orchestrator\n(2 hrs)"]
    P19 --> P23["23. Polish\n(3 hrs)"]

    style P1 fill:#22c55e,color:#fff
    style P4 fill:#22c55e,color:#fff
    style P5 fill:#22c55e,color:#fff
    style P19 fill:#22c55e,color:#fff
```

**Minimum viable path: ~20 hours** — gives you crop AI + market prices + orchestrator + polish.

---

> [!TIP]
> **When prompting AI to build each phase:**
> Copy the specific phase section from this plan and paste it as your prompt.
> Each phase is self-contained with exact files, endpoints, success criteria, and code snippets.

---

*Built for hackathon speed. Engineered for real-world impact.* 🌾🤖
