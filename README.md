# LaneGuard — Weather-Aware Truck Routing

React + Django app that helps a truck driver pick the safest route using weather, load weight, and travel time.

Built for the Spotter full-stack assessment.

## Features (assessment requirements)

- Inputs: **origin**, **destination**, **departure date/time**, **load weight**
- **3 route options** via OpenRouteService
- Weather sampled every **10 / 25 / 50 miles** (adaptive by trip length) at each checkpoint **ETA**
- Risk from PDF wind / rain / snow tables + load rules
- Recommendation order: **No Travel miles → Severe → High → avg risk → travel time**
- Map shows all routes, checkpoints, risk levels, ETAs, and route summaries
- Corridor **weather heatmap** with **0–48 hour** forecast slider

## Stack (free / free-key only)

| Layer | Choice |
|-------|--------|
| Frontend | React + Vite + TypeScript + Leaflet + leaflet.heat |
| Backend | Django + Django REST Framework |
| Routing / geocoding | [OpenRouteService](https://openrouteservice.org/) (free API key) |
| Weather | [Open-Meteo](https://open-meteo.com/) (no key) |
| Map tiles | OpenStreetMap (dark-filtered, no tile API key) |

## Project layout

```
backend/
  config/                 Django settings, URLs
  routing/
    risk.py / geometry.py Risk tables, sampling, recommendation
    services/             ORS, Open-Meteo, analyze orchestration
    tests/                Pytest suite
    views.py              /api endpoints
frontend/
  src/
    components/           Form, map, results, departure picker, loader
    api.ts / types.ts     API client + shared types
LOOM_WALKTHROUGH.md
.env.example
```

## Local setup

### 1. Free ORS API key

Sign up at https://openrouteservice.org/dev/#/signup (free, no paid plan required).

### 2. Backend

```bash
cd /path/to/spotter-assessment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

cp .env.example .env
# Edit .env and set ORS_API_KEY=your_key_here

cd backend
python manage.py migrate
python manage.py runserver 8000
```

API health: `http://127.0.0.1:8000/api/health/`

### 3. Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` → `http://127.0.0.1:8000`. Optional: copy `frontend/.env.example` to `frontend/.env` to override `VITE_API_BASE`.


Open http://127.0.0.1:5173

**Tip:** Use a freight lane (e.g. Chicago → Detroit). Routing is **truck-first** (`driving-hgv`) with size/weight restrictions from your load.

- **Regional truck runs ≲ 100 km:** ORS native HGV `alternative_routes` (one call).
- **Line-haul > 100 km:** three HGV variants — **recommended**, **shortest (truck-legal)**, **avoid tollways**. We never “avoid highways” (not truck-aligned).

### 4. Tests

```bash
source .venv/bin/activate
cd backend
python -m pytest routing/tests/ -q
```

### Departure date rules

- **Not in the past** (5-minute grace)
- **Up to 7 days ahead** by default (`DEPARTURE_MAX_HOURS_AHEAD=168`) — best balance of planning flexibility vs Open-Meteo accuracy
- **ETA weather** uses an 8-day hourly forecast so later departures still get checkpoint risk
- **Heatmap slider stays 0–48h** from departure (assessment requirement; highest confidence band)

| Horizon | Accuracy for truck risk |
|---------|-------------------------|
| 0–48h | Best (heatmap + near-term ETAs) |
| 2–7 days | Good enough for planning |
| &gt;7 days | Not recommended (noisy precip/wind rates) |

### Rate limits (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `RATE_LIMIT_GEOCODE` | `20/min` | Per-IP geocode/autocomplete |
| `RATE_LIMIT_ANALYZE` | `6/min` | Per-IP route analyze |
| `RATE_LIMIT_DEFAULT` | `60/min` | Fallback scoped rate |
| `ORS_RATE_LIMIT_PER_MINUTE` | `35` | Outbound ORS calls (before ORS 429) |

Exceeded limits return **HTTP 429** with `detail` + `retry_after`.

## Risk rules (from assessment)

**Wind (mph):** Low &lt;25 · Moderate 25–34 · High 35–44 · Severe 45–54 · No Travel ≥55  

**Rain (in/hr):** Low &lt;0.10 · Moderate 0.10–0.25 · High 0.25–0.50 · Severe 0.50–1.00 · No Travel &gt;1.00  

**Snow (in/hr):** Low &lt;0.5 · Moderate 0.5–1.0 · High 1.0–2.0 · Severe 2.0–3.0 · No Travel &gt;3.0  

**Load rules:** ≥55 mph → No Travel any load · 45–54 mph + &gt;30,000 lb → No Travel · 35–44 mph + &gt;40,000 lb → Severe  

Checkpoint severity = max(wind-with-load, rain, snow). Segment miles inherit the worse endpoint.

### Sampling

| Trip distance | Interval |
|---------------|----------|
| &lt; 150 mi | every 10 mi |
| 150–400 mi | every 25 mi |
| &gt; 400 mi | every 50 mi |

## API

`POST /api/routes/analyze/`

```json
{
  "origin": "Chicago, IL",
  "destination": "Detroit, MI",
  "departure_at": "2026-06-01T12:00:00+00:00",
  "load_lbs": 35000
}
```

`GET /api/geocode/?q=Chicago`

## Recommendation rationale

Routes are sorted by:

1. Fewest No Travel miles (safer than Severe; PDF defines the level)
2. Fewest Severe miles
3. Fewest High miles
4. Lowest average risk (distance-weighted)
5. Shortest travel time

## Loom

See [LOOM_WALKTHROUGH.md](LOOM_WALKTHROUGH.md) for a 5–10 min recording script. Paste the Loom URL here when ready:

- **Loom:** _(your link)_
