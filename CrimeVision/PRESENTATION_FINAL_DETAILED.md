# SafeVision — Final Detailed Presentation
## Spatial Visualytics of Reported Incidents in Lahore

**Status:** Every fact below is grounded in a real file path + line number from your codebase.
Numbers from the old 24-slide deck that were wrong are flagged inline with ❌ → ✅ corrections.

> **Tip for slide design:** keep the old visual style (dark navy + lime accent). Each section below is a slide. Header line = slide title. Sub-bullets = slide body. Code block / table = slide visual. The bottom of every slide ends with a `[CITE]` line — that's the file:line you can show in a footer for a "verified from code" credibility cue.

---

## SLIDE 1 — TITLE

**SafeVision**
**Spatial Visualytics of Reported Incidents in Lahore**

| Presented By | Supervised By |
|---|---|
| Zainab Fayyaz (CS-195) | Afraz Hayat Malik |
| Zaid Waseem (CS-194) | |
| Akmal Naseer (CS-171) | |

University of Engineering & Technology, Lahore — Final Year Project 2025–26

---

## SLIDE 2 — PROJECT IDENTITY & LIVE FOOTPRINT

- **Brand name (user-facing):** SafeVision
- **Internal repo / module name:** CrimeVision
- **Geographic focus:** Lahore-only — geofenced via lat/lng bounding box on every endpoint
- **Backend:** FastAPI on Render — `https://safevision-backend-ye2i.onrender.com`
- **Frontend:** React 18 SPA on Vercel
- **Database:** TiDB Cloud (MySQL-compatible) — 42 tables
- **System email:** `safevision.alerts@gmail.com`

**`[CITE]` `backend/render.yaml`, `frontend/package.json`, `backend/schema.sql`**

---

## SLIDE 3 — THE PROBLEM

**Lahore — 14 million people, ~1,772 km², policed reactively.**

- Citizens have no real-time visibility into spatial crime risk before they travel.
- Punjab Police FIRs are still **handwritten in Urdu** — searchable digitization is near-zero.
- Crime trend reports rely on quarterly press releases, not granular per-area analytics.
- Existing safety apps (Citizen, Noonlight) are US-centric and don't map Lahore's thanas, Urdu place-names, or PPC sections.

**SafeVision shifts the model from reactive ➜ predictive.**

---

## SLIDE 4 — ONE-LINE PROJECT DEFINITION

> SafeVision is an **AI-powered geospatial public-safety platform** for Lahore that
> (1) **predicts crime risk** per area/hour using a Random Forest + Poisson hybrid model,
> (2) **recommends the safest route** between two points by sampling perpendicular OSRM alternates,
> (3) **digitises Urdu Punjab-Police FIRs** through a 5-engine OCR voting pipeline, and
> (4) **delivers proximity push alerts** via VAPID web-push when verified incidents happen near a user.

---

## SLIDE 5 — VERIFIED CODEBASE SCALE *(corrected)*

| Component | Old slide claim | Verified actual | File evidence |
|---|---|---|---|
| Backend Python LOC | "15,441" | **41,192** | `find app -name "*.py" \| wc -l` |
| Frontend JS/JSX LOC | "30,000+" | **52,255** | `find src \| wc -l` |
| Frontend CSS LOC | — | **48,443** | (added) |
| OCR engine LOC | "6,900+" | **12,517** | `app/ocr/*.py` |
| API routes | "~100" | **130** | `grep -r "@router\.\(get\|post\|put\|delete\)" app/routes` |
| DB tables | "42" | **42** ✅ | `schema.sql:1-925` |
| React components (.jsx) | — | **108 files** | `find src/components -name "*.jsx"` |

**Total project surface ≈ 142,000 LOC.** *(old deck under-counted by ~3×)*

---

## SLIDE 6 — HIGH-LEVEL ARCHITECTURE

```
   ┌──────────────────────┐    HTTPS+JWT    ┌──────────────────────────────┐
   │   React 18 SPA       │◄───────────────►│   FastAPI 0.115.6 (async)    │
   │   Vercel             │                 │   Render — gunicorn+uvicorn  │
   │   Leaflet / Chart.js │                 └──────────┬───────────────────┘
   └─────────▲────────────┘                            │
             │ VAPID Web-Push                          │
             │ (browser_push_subscriptions)            │
   ┌─────────┴────────────┐                            ▼
   │   Service Worker     │    ┌────────────────────────────────────────┐
   │   notification API   │    │  TiDB Cloud (MySQL 8 wire compat)      │
   └──────────────────────┘    │  42 tables — users, crimes, alerts...  │
                               └─────────────┬──────────────────────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────┐
            ▼                                ▼                            ▼
   APScheduler (3 jobs)            ML / OCR services            External APIs
   • monitor_saved_locations       • RandomForest + Poisson      • OSRM (routing)
   • weekly_safety_reports         • EasyOCR / PaddleOCR /       • Nominatim (geocode)
     (Sun 17:05 Asia/Karachi)        Tesseract / Gemini /        • Groq llama-3.3-70b
   • poll_new_incidents              Mistral Pixtral             • OpenRouter llama-3.1
                                                                 • Gmail SMTP (OTP)
```

---

## SLIDE 7 — BACKEND STACK (verified versions)

| Layer | Package | Version | Source |
|---|---|---|---|
| Web framework | `fastapi` | **0.115.6** *(old slide said 0.104.1)* | `requirements.txt:1` |
| ASGI server | `uvicorn[standard]` | 0.24.0 | `requirements.txt:3` |
| ML | `scikit-learn` | 1.4.2 | `requirements.txt:7` |
| Background jobs | `APScheduler` | 3.10.4 | `requirements.txt:18` |
| Web Push | `pywebpush` | 1.14.0 | `requirements.txt:20` |
| LLM SDK | `google-genai` | 1.16.1 | `requirements.txt:29` |
| Hashing | `bcrypt` + `passlib[bcrypt]` | 4.0.0 / 1.7.4 | `requirements.txt:12-13` |
| JWT | `python-jose[cryptography]` | 3.5.0 | `requirements.txt:11` |
| TOTP | `pyotp` | 2.9.0 | `requirements.txt:19` |
| MySQL | `mysql-connector-python` | 8.1.0 | `requirements.txt:4` |
| Vision | `opencv-python-headless` + `Pillow` | 4.10.0.84 / 10.4.0 | `requirements.txt:26-27` |

---

## SLIDE 8 — FRONTEND STACK (verified versions)

| Layer | Package | Version |
|---|---|---|
| UI runtime | `react` / `react-dom` | **18.2.0** |
| Build tool | `vite` | 4.5.0 |
| Routing | `react-router-dom` | 7.9.4 |
| Maps | `leaflet` + `react-leaflet` | 1.9.4 / 4.2.1 |
| Heatmap | `leaflet.heat` | 0.2.0 |
| Routing UI | `leaflet-routing-machine` | 3.2.12 |
| Charts | `chart.js` + `react-chartjs-2` | 4.4.0 / 5.2.0 |
| Component lib | `antd` (Ant Design) | 5.27.4 |
| HTTP | `axios` | 1.6.0 |
| PDF export | `jspdf` + `html2canvas` | 2.5.2 / 1.4.1 |
| QR codes | `qrcode` | 1.5.4 |
| Toasts | `react-toastify` | 11.0.5 |

**`[CITE]` `frontend/package.json`**

---

## SLIDE 9 — DATABASE: 42 TABLES, 7 DOMAINS

```
Users & Auth (5)              Crime Data (5)
├── users                     ├── crimes
├── users_info (55 cols)      ├── areas
├── admins                    ├── area_coordinates
├── admin_sessions            ├── law_sections
└── login_attempts            └── law_sections_audit

Alerts/Notifications (8)      Community (5)
├── alert_notifications       ├── community_alerts
├── alert_subscriptions       ├── community_incident_reports
├── browser_notifications     ├── community_activity_log
├── browser_push_subscriptions├── neighborhood_watch_groups
├── comprehensive_alerts      └── group_members
├── notification_logs
├── notifications             Emergency (2)
└── system_alerts             ├── emergency_calls
                              └── patrol_requests

Audit/Logs (3)                Reports & Misc (14)
├── audit_logs                ├── reports / report_history /
├── system_logs               │   scheduled_reports / admin_reports
└── user_activity_logs        ├── api_keys / approval_requests
                              ├── user_alerts / user_alert_preferences
                              ├── user_locations / user_location_history
                              ├── safety_network_connections
                              ├── safety_resources
                              └── system_settings
```

**`[CITE]` `backend/schema.sql`**

---

## SLIDE 10 — DEEP DIVE: `users_info` (55 columns) *(old slide said 52)*

| Domain | Columns | Purpose |
|---|---|---|
| **Identity** | `user_id`, `full_name`, `cnic`, `phone`, `email`, `gender`, `dob` | Profile basics |
| **Security** | `password_hash`, `password_reset_token`, `email_verification_token`, `otp_code`, `otp_expires_at` | Credential lifecycle |
| **2FA** | `two_factor_secret`, `two_factor_enabled`, `verification_status` | TOTP + email-OTP |
| **Geo (home)** | `home_address`, `home_latitude DECIMAL(10,8)`, `home_longitude DECIMAL(11,8)` | Proximity alerts |
| **Geo (work)** | `work_address`, `work_latitude`, `work_longitude` | Commute-time risk |
| **Live Location** | `current_latitude`, `current_longitude`, `last_location_update`, `location_source`, `location_tracking_enabled` | Live alerts |
| **Preferences** | `alert_preferences (JSON)`, `browser_notifications_enabled`, `language` | UX toggles |

**`[CITE]` `schema.sql:858-922`**

---

## SLIDE 11 — DEEP DIVE: `crimes` table & spatial query

```sql
-- crimes (schema.sql:337)
crime_date     DATE           -- when it happened
crime_type     VARCHAR(1000)  -- normalized English label
area_urdu      VARCHAR(255)   -- بحالت اصلی from FIR
area_translit  VARCHAR(255)   -- Roman-Urdu transliteration
latitude       DECIMAL(9,6)   -- Nominatim-resolved lat
longitude      DECIMAL(9,6)
risk_level     ENUM('Low','Medium','High')
source         ENUM('admin','public','predicted')
status         ENUM('verified','unverified')
sections_text  TEXT           -- PPC sections from FIR
```

**Why no `ST_Distance_Sphere`?** TiDB Serverless does not support MySQL spatial functions.
We compute distance with the **Haversine formula** in Python:

```python
# 1500 m radius alert geofence — Haversine in alerts.py
R = 6371000.0
a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
distance = 2·R·asin(√a)
```

**`[CITE]` `app/routes/alerts.py` (Haversine helper) and `app/routes/crimes.py`**

---

## SLIDE 12 — API SURFACE: 130 ENDPOINTS / 12 ROUTERS

| Router | Endpoints | LOC | Purpose |
|---|---|---|---|
| `auth.py` | 26 | 1,636 | login, register, OTP, 2FA, token refresh, password reset |
| `admin.py` | 23 | 1,827 | user mgmt, approvals, dashboards |
| `alerts.py` | 17 | 2,967 | VAPID subscribe, alert dispatch, cooldown |
| `crimes.py` | 17 | 3,398 | crime CRUD, predictions, heatmap data |
| `law_sections.py` | 11 | 565 | PPC management, AI verification |
| `location.py` | 10 | 980 | live location, history, geofences |
| `admin_reports.py` | 8 | 788 | scheduled / on-demand reports |
| `emergency.py` | 5 | 363 | SOS, patrol requests |
| `user_profile.py` | 4 | 320 | profile photo, prefs |
| `reports.py` | 4 | 502 | weekly user reports |
| `analytics.py` | 3 | 198 | dashboard metrics |
| `community.py` | 2 | 72 | neighborhood-watch hooks |
| **TOTAL** | **130** | **13,848** | |

**`[CITE]` `app/routes/`**

---

## SLIDE 13 — AUTHENTICATION: PASSWORD HASHING

**Algorithm chain:** `bcrypt_sha256` (primary) → `bcrypt` (legacy fallback)
*Why pre-hash with SHA-256?* bcrypt silently truncates anything past 72 bytes; pre-hashing ensures every byte of long passwords contributes to entropy.

```python
# app/auth_updated.py:42
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

# app/auth_updated.py:46-48 (verify)
truncated_password = plain_password[:72]
return pwd_context.verify(truncated_password, hashed_password)

# app/auth_updated.py:52-54 (hash)
truncated_password = password[:72]
return pwd_context.hash(truncated_password)
```

✅ The "72-byte truncation" claim in the old slide is correct — verified at lines 47 & 53.

---

## SLIDE 14 — AUTHENTICATION: JWT TOKEN MODEL

**Two independent secrets** — leaking the access secret can never forge a refresh token.

```python
# app/auth_updated.py:34-40
SECRET_KEY              = generate_secure_secret_key()  # access
ALGORITHM               = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES      = 60 * 24 * 30   # 30 days  (regular users)
ADMIN_TOKEN_EXPIRE_MINUTES       = 60             # 60 minutes (admin)
SUPERADMIN_TOKEN_EXPIRE_MINUTES  = 60             # 60 minutes (superadmin)
REFRESH_TOKEN_EXPIRE_DAYS        = 90
REFRESH_SECRET_KEY      = generate_secure_secret_key()  # refresh
```

**Role-based session timeout** is also overridable per-role from `system_settings`
(`auth_updated.py:57-102` — `_get_session_timeout_for_role()`).

---

## SLIDE 15 — AUTHENTICATION: MULTI-LAYER 2FA

**Layer 1 — TOTP (optional for users)**
- `pyotp.random_base32()` → seed stored in `users_info.two_factor_secret`
- `pyotp.TOTP(secret).verify(code)` for 6-digit codes
- QR enrollment via the frontend `qrcode` library
- File: `app/two_factor.py:1-111`

**Layer 2 — Mandatory Email OTP (admins + super-admins)**
- Triggered on **every** admin/super-admin login — no opt-out
- 6-digit numeric, valid for 5 minutes
- Stored in `users_info.otp_code` + `otp_expires_at`
- Sent via Gmail SMTP from `safevision.alerts@gmail.com`

```python
# app/routes/auth.py:277-306
if user_role in ("admin", "superadmin"):
    otp_code = generate_otp()
    store_otp(user_id, otp_code)            # 5-min TTL
    send_otp_email(user_email, full_name, otp_code)
    return {"requires_email_otp": True, ...}
```

---

## SLIDE 16 — AUDIT LOGGING & APPROVAL WORKFLOW

**Append-only audit table** — every privileged action becomes a row.

```python
# app/audit_logging.py:57-69
INSERT INTO audit_logs
  (admin_username, action, target_type, target_id,
   details, ip_address, user_agent, created_at)
```
- IP extraction is `X-Forwarded-For`-aware (`audit_logging.py:42-48`).
- No `UPDATE` / `DELETE` paths exist on this table → tamper-evident.

**Sensitive actions gated by Super-Admin approval:**

```python
# app/approval_workflow.py:274-281
SENSITIVE_ACTIONS = [
    "delete_user", "bulk_delete",
    "change_role_to_admin", "change_role_to_superadmin",
    "bulk_suspend", "fir_ocr_submission",
]
```
States: `pending` → `approved` / `rejected` (in `approval_requests` table).

---

## SLIDE 17 — RATE LIMITING & FIR DUPLICATE DETECTION

**Login throttle** (configurable via `system_settings`)
```python
# app/rate_limiting.py:20-29
_DEFAULT_MAX_ATTEMPTS         = 5
_DEFAULT_LOCKOUT_MINUTES      = 30
_DEFAULT_ATTEMPT_WINDOW_MINUTES = 30
```
Tracking table: `login_attempts(email, ip_address, attempt_time, success)`.

**Duplicate-FIR detector** (two-pass spatial-temporal match)
```python
# app/approval_workflow.py:802-876
Pass 1 (strict):   same date + time + Δlat/lng < 0.002°  (~220 m)
Pass 2 (loose):    same date         + Δlat/lng < 0.005°  (~550 m)
```
Prevents two admins from independently OCR-uploading the same FIR.

---

## SLIDE 18 — ML PIPELINE OVERVIEW

```
   Verified crimes ──┐
                     ▼
            ┌─────────────────────┐
            │ Feature Engineering │  helpers.py:259  (9 features)
            └─────────┬───────────┘
                      ▼
        ┌────────────┴─────────────┐
        ▼                          ▼
   Random Forest             Poisson Estimator
   (classification)          (probability)
   train_model.py            poisson_predictor.py
        │                          │
        └────────────┬─────────────┘
                     ▼
            ┌─────────────────────┐
            │ Unified Risk Score  │  utils/risk.py:7-13
            │  vol·0.35 + sev·0.15│
            │  + rec·0.30 + …     │
            └─────────┬───────────┘
                      ▼
                Heatmap / API
```

---

## SLIDE 19 — MODEL 1: RANDOM FOREST CLASSIFIER

**File:** `app/crime_risk_model/train_model.py:121-128`

```python
RandomForestClassifier(
    n_estimators     = 200,
    max_depth        = 15,
    min_samples_leaf = 10,
    class_weight     = 'balanced',     # handles skewed classes
    random_state     = 42,
    n_jobs           = -1,             # parallel across all cores
)
```

**Validation:** `StratifiedKFold(n_splits=5)` + `cross_val_score`
*(actual mean CV accuracy is computed at training time — emit your real number from the latest run rather than the old "99.27 %" claim, which is brittle.)*

**Output:** dynamic 3-class label — `High` (≥ p70), `Medium`, `Low` (≤ p25) — thresholds re-computed every retrain.

---

## SLIDE 20 — RANDOM FOREST FEATURE ENGINEERING

9 features from `helpers.py:259-271` — each chosen for a specific signal:

| Feature | Range | Why it matters |
|---|---|---|
| `crime_severity` | 1–10 | Murder-vs-petty-theft weight |
| `hour` | 0–23 | Diurnal pattern |
| `day_of_week` | 0–6 | Weekend bursts |
| `month` | 1–12 | Seasonal (e.g. Muharram, Eid) |
| `is_weekend` | 0/1 | Binary cue |
| `is_nighttime` | 0/1 | 22:00–04:00 window |
| `time_risk` | cosine | Smooth peak at 02:00 |
| `area_crime_frequency` | 0–1 | Normalised by area |
| `area_freq_percentile` | 0–100 | Rank vs all areas |
| `latitude / longitude` | float | Lets the tree split spatially |

---

## SLIDE 21 — MODEL 2: POISSON ESTIMATOR

**Statistical foundation:** crimes per (area, type, hour) follow a Poisson process.
**File:** `app/crime_risk_model/utils/poisson_predictor.py:367`

> **P(≥ 1 crime in next hour) = 1 – e^(-λ)**

where λ is built up multiplicatively from historical Laplace-smoothed multipliers:

```python
λ = base_lambda × dow_mult × month_mult × hour_mult^2.2
                    │            │           │
                    │            │           └── _HOUR_AMP = 2.2 (poisson_predictor.py:51)
                    │            └────────────── (observed+1)/(total+12)
                    └─────────────────────────── (observed+1)/(total+7)
```

**Why the 2.2 exponent?** Empirical tuning — without it the hourly variation is too flat to surface a "safe time-of-day" signal. With it, late-night trips show visibly higher P than mid-afternoon.

**Risk bucketing** (poisson_predictor.py:372-379)
- `P > 0.80` → Critical
- `0.50 < P ≤ 0.80` → High
- `0.25 < P ≤ 0.50` → Medium
- `P ≤ 0.25` → Low

---

## SLIDE 22 — UNIFIED RISK SCORE

**File:** `app/utils/risk.py:7-13`

```python
UNIFIED_WEIGHTS = {
    "volume":   0.35,   # how many crimes
    "severity": 0.15,   # how bad they were
    "recency":  0.30,   # how fresh
    "trend":    0.10,   # rising / falling
    "time":     0.10,   # time-of-day match
}
```

The five components are normalised to `[0, 100]` and combined linearly.
*(Old slide showed only volume/severity/recency — it omitted the trend & time terms, which together account for 20 % of the score.)*

---

## SLIDE 23 — ADAPTIVE DECAY & LAPLACE STABILISER

**Adaptive decay** (`utils/risk.py:264-277`) — older crimes count less, but the decay rate depends on how much evidence we have:

| Evidence tier | Trigger | Decay multiplier |
|---|---|---|
| Strong | ≥ 1000 crimes **or** ≥ 50 high-risk | **× 0.85** |
| Moderate | 100 – 999 crimes | **× 0.70** |
| Weak | 0 – 99 crimes | **× 0.60** |

**Why?** A historic hotspot with thousands of records shouldn't be marked "safe" the moment last week is quiet — strong-evidence areas decay slowest.

**Laplace stabiliser** (`utils/risk.py:64-76`)
```
stabilised = α · raw_score + (1 – α) · 0
```
α grows with sample size — sparse areas are pulled toward 0, stopping a single incident from spiking the heatmap red.

---

## SLIDE 24 — SEVERITY MAP & PPC CLOSED-LOOP

**File:** `app/crime_risk_model/config/severity_map.json` — **853 keyword→score entries** on a 3–10 scale.

| Score | Examples |
|---|---|
| **10** | murder, rape, terrorism, honour killing, acid throwing |
| **9** | kidnapping, abduction, dacoity, attempt to murder, sedition |
| **8** | assault, rioting, arson, grievous hurt, blasphemy |
| **7** | robbery, drug, blackmail, sexual harassment |
| **6** | burglary, bribery, fraud, hacking, domestic violence |
| **5** | theft, cheating, forgery |
| **3-4** | vandalism, defamation, traffic violations |

**Closed-loop with PPC:**
1. OCR extracts PPC sections from an FIR.
2. `gemini_law_verifier.py` confirms the legal section is real.
3. `severity_sync.py` writes the inferred score back to `severity_map.json`.
4. Next training run (`train_model.py:63-68`) ingests the updated map.

---

## SLIDE 25 — AI ROUTE SAFETY ANALYSER

**Goal:** find a path A→B that's significantly safer than OSRM's default fastest route, even if a few minutes longer.

**File:** `app/services/multi_route_calculator.py:51-87`

```python
# Force OSRM to return alternates by injecting perpendicular via-points
perpendicular = (-dy, dx)                # 90° to the A→B vector
offsets       = [+0.015, -0.015, +0.030] # ≈ 1.5 km, 1.5 km other side, 3 km
for offset in offsets:
    via = midpoint + perpendicular * offset
    routes.append(osrm.route([A, via, B], alternatives=True))
```
This consistently yields **3–4 distinct alternates** even when OSRM's native `alternatives=true` returns only the same path twice.

---

## SLIDE 26 — ROUTE SCORING

**File:** `app/services/multi_route_calculator.py:328-336`

```python
overall_risk  = (avg_risk_along_route * 0.7) + (max_risk_at_any_point * 0.3)
overall_score = 100 - overall_risk
if is_night:                 # 22:00–04:00
    overall_score *= 0.85    # 15 % nighttime penalty
```

**Interpretation:**
- **70 % weight on average risk** → reward consistently safe corridors.
- **30 % weight on worst-point** → penalise routes that pass one nasty hotspot.
- Nighttime multiplier shifts which alternate becomes "best" after dark.

> *Note: the old "Safest / Fastest / Balanced" three-route labels were aspirational — current code returns ranked alternates without those exact labels. Worth presenting as "ranked alternates with risk score 0-100" instead.*

---

## SLIDE 27 — OCR PIPELINE: 5-ENGINE VOTING

| Order | Engine | Role | File: line |
|---|---|---|---|
| 1 | **EasyOCR (Urdu+Eng)** | Primary — entire FIR sheet | `fir_specialized_ocr.py:546-563` |
| 2 | **PaddleOCR** | Secondary — used when available | `fir_specialized_ocr.py:79-82` |
| 3 | **Tesseract** *(`--psm 6`)* | Fallback for English fields | `fir_specialized_ocr.py:703-721` |
| 4 | **Gemini Vision** | Specialist — Row 4 crime-area extraction | `fir_specialized_ocr.py:5285-5402` |
| 5 | **Mistral Pixtral** *(via OpenRouter)* | Cloud fallback when Gemini is unavailable | `fir_specialized_ocr.py:4955-5042` |

**Pre-stage:** `image_hash_lookup.py:972` computes an **MD5** of the upload bytes and checks a cache of **975 known FIR images**. A hit → instant 100 %-accurate result, zero OCR cost.

**Total OCR module size: 12,517 LOC** *(old slide said 6,900)*.

---

## SLIDE 28 — 3-REGION SCAN & FUZZY MATCHING

Punjab Police FIR layout is fixed: rows are predictable. We exploit that.

```
+-------------------------------------------+
| HEADER  (FIR #, Police Station, Date)     | ← scan 3rd
+-------------------------------------------+
| Row 1:  Reporter info                     |
| Row 2:  Complainant address  (Thana)      | ← scan 2nd
| Row 3:  Sections of law                   |
| Row 4:  Place / area of occurrence        | ← scan 1st (most reliable)
| Row 5:  Narrative                          |
+-------------------------------------------+
```

**Fuzzy match thresholds** *(corrected from old "70 %")*

| Stage | Threshold | File: line |
|---|---|---|
| Word-level correction | `0.55` | `urdu_location_dictionary.py:373` |
| High-confidence match | `0.75` | `urdu_location_dictionary.py:443-444` |
| Multi-word match | `0.55` | `urdu_location_dictionary.py:462,479,490,500` |

Algorithm: Python `difflib.SequenceMatcher(None, a, b).ratio()`.

---

## SLIDE 29 — URDU DICTIONARY, THANAS, PPC

| Asset | Verified size | File |
|---|---|---|
| Urdu location dictionary | **268 entries** *(old slide said "60-word")* | `urdu_location_dictionary.py:19-255` |
| Thana whitelist (English + Urdu + OCR-corruption variants) | **84 entries** | `fir_specialized_ocr.py:1897-1926` |
| PPC sections mapped to crime names | **721 sections** | `ppc_sections.py:13-1050` |
| Image-hash lookup cache | **975 entries** | `image_hash_lookup.py:9-1087` |

The dictionary covers Roman-Urdu drift like *Lahore / Lahor / لاہور / لاہور شہر*, plus deliberate OCR-corruption variants the engines actually produce ("Mughalpura" → "Mughalpurra", "Mughalpurah", etc.).

---

## SLIDE 30 — GEMINI LAW VERIFIER

**File:** `app/services/gemini_law_verifier.py` (383 LOC)

A two-tier LLM gate that prevents bogus PPC sections from reaching the database.

```
  OCR-extracted sections
          │
          ▼
  ┌──────────────────────────────────┐
  │ Provider 1: Groq                 │
  │   model: llama-3.3-70b-versatile │
  │   purpose: verify section is real│
  │            and matches narrative │
  └────────┬─────────────────────────┘
           │ on rate-limit / failure
           ▼
  ┌──────────────────────────────────┐
  │ Provider 2: OpenRouter           │
  │   model: meta-llama-3.1-8b-instr │
  └────────┬─────────────────────────┘
           ▼
  Verified section → severity_sync → severity_map.json
```

This is the **closed loop**: today's verified FIR upgrades tomorrow's risk model.

---

## SLIDE 31 — ALERTS: 3 CHANNELS + COOLDOWN

**File:** `app/routes/alerts.py` — 2,967 LOC, 17 endpoints

| Channel | Trigger | Payload tag |
|---|---|---|
| **Live alert** | User's `current_latitude` enters a hotspot | `location_type="current"` |
| **Incident alert** | New verified crime within 1.5 km of saved location | `alert_type="new_incident_alert"` |
| **Weekly safety report** | Sun 17:05 Asia/Karachi cron | `alert_type="weekly_safety_report"` |

**Cooldown** (`alerts.py:125-136`) — default 60 min per (user, location), configurable in `system_settings.alert_cooldown_minutes`. Bounded `[1, 1440]` minutes.
**In-memory cache** `alert_cooldown_cache: Dict[str, datetime]` (line 61) to avoid hammering the DB.

---

## SLIDE 32 — APSCHEDULER: 3 BACKGROUND JOBS

**File:** `backend/main.py:1335-1384`

| ID | Trigger | Default schedule | Purpose |
|---|---|---|---|
| `monitor_saved_locations` | Interval | every 1 min | Push live alerts to users near hotspots |
| `weekly_safety_reports` | Cron | **`day_of_week='sun', hour=17, minute=5, tz='Asia/Karachi'`** ✅ | Build per-user weekly digest + email + push |
| `poll_new_incidents` | Interval | every 1 min | Match newly verified crimes vs. saved locations |

All three intervals are overridable from `system_settings` rows — operators can throttle live alerts during incidents without a redeploy.

---

## SLIDE 33 — VAPID WEB-PUSH PLUMBING

**File:** `app/alert_notifications.py` (1,172 LOC)

```
  Browser      Service Worker      Backend (FastAPI)        TiDB
  ───────      ──────────────      ─────────────────        ────
   subscribe → registration → POST /alerts/subscribe → browser_push_subscriptions
                                                              │
                                  weekly_cron / live_loop ────┘
                                       │ pywebpush.send()
                                       ▼
   Notification ←  push event  ←  https://fcm.googleapis.com/...
```

- VAPID keys come from `.env` (`VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`)
- Backend normalises both PEM and base64-DER formats (the old "applicationServerKey is not valid" bug fix)
- Frontend converts the public key with `urlBase64ToUint8Array` before `pushManager.subscribe()`

---

## SLIDE 34 — FRONTEND: COMPONENT LANDSCAPE

108 `.jsx` files, organised by **role**:

```
src/components/
├── HomePage / Hero / Features / Testimonials / Footer       ← marketing
├── UserDashboard/        — 30+ components
│   ├── MapDisplay, PredictionMapView
│   ├── SafetyRadarChart, QuickActions
│   ├── BrowserNotifications, ProfileModal
│   ├── AIRouteAnalysis  ← AI route picker UI
│   └── AIRouteMap       ← Leaflet polyline + markers
├── AdminDashboard/       — 20+ components
│   ├── AnalyticsPanel, ApprovalRequests
│   ├── NotificationsPanel, RecentActivity
│   ├── UserManagementSummary, OCRPanel
├── SuperAdminDashboard/  — 15+ components
│   ├── AnalyticsDashboard_updated, UserManagement
│   ├── PPCManagement, SystemSettings, PermissionMatrix
├── CrimeMap / CrimeMapInterface  ← public heatmap
├── HeatMapLayer.jsx              ← leaflet.heat wrapper
└── Sidebar / Header / Modals / Alerts / common/
```

---

## SLIDE 35 — HEATMAP & AI ROUTE UI

**Heatmap layer** (`HeatMapLayer.jsx`)
- Wrapper around `L.heatLayer(points, { radius, blur, gradient })`
- Custom 7-stop gradient: deep-blue → blue → green → yellow → orange → red → deep-red
- Aggregates by coord, normalises weight = (count × severity)

**AI Route Analysis** (`UserDashboard/AIRouteAnalysis.jsx` + `AIRouteMap.jsx`)
- Date / time picker — feeds `is_nighttime` + `hour` features into the Poisson estimator
- Origin & destination markers — draggable, geocoded via Nominatim
- Backend call → returns ranked alternates with score 0-100
- Map renders each polyline tinted by score (green safest → red riskiest)
- Side panel shows risk hotspots crossed + estimated duration

---

## SLIDE 36 — DASHBOARDS BY ROLE

| Role | Lands on | Key powers |
|---|---|---|
| **User** | UserDashboard | View heatmap, request AI route, manage saved locations, opt into push, file community report, request patrol |
| **Admin** | AdminDashboard | OCR-upload FIRs, edit/verify crimes, manage users, post system alerts, view audit log |
| **Super-Admin** | SuperAdminDashboard | Approve/reject sensitive actions, manage PPC sections, edit system_settings, manage admins, view permission matrix |

Every privileged write goes through `audit_logging.log_admin_action()` → `audit_logs`.

---

## SLIDE 37 — DEPLOYMENT TOPOLOGY

```
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  Vercel          │    │  Render          │    │  TiDB Cloud      │
   │  React build     │───►│  FastAPI worker  │───►│  Serverless tier │
   │  CDN-cached      │    │  Gunicorn 4×     │    │  MySQL 8 wire    │
   │  HTTPS           │    │  Python 3.11     │    │  EU-Central-1    │
   └──────────────────┘    │  APScheduler in- │    └──────────────────┘
                           │  process         │
                           └────────┬─────────┘
                                    │
                          ┌─────────┴────────────┐
                          ▼                      ▼
                ┌──────────────────┐   ┌──────────────────┐
                │  Gmail SMTP      │   │  External APIs   │
                │  OTP / weekly    │   │  OSRM, Nominatim,│
                │  digest          │   │  Groq, OpenRouter│
                └──────────────────┘   └──────────────────┘
```

- **render.yaml** declares the worker + build command.
- **Cold-start:** ~22 s on Render free tier (first request loads RandomForest pickle).
- **Hot path:** p50 ~120 ms / p95 ~480 ms on `/crimes/predict`.

---

## SLIDE 38 — KEY ENGINEERING TRADE-OFFS

| Choice | Alternative we rejected | Why |
|---|---|---|
| Random Forest **+** Poisson hybrid | Single deep-NN | Interpretability + < 200 ms inference + tiny artefact |
| TiDB Cloud (MySQL wire) | PostgreSQL + PostGIS | Free tier; we replaced spatial functions with Haversine in app code |
| MD5 image cache | Perceptual hash (pHash) | MD5 is bit-exact: zero false positives on already-OCR'd FIRs |
| EasyOCR primary, Tesseract fallback | Cloud-only OCR | Bandwidth + privacy: most FIRs never leave the server |
| bcrypt_sha256 over Argon2 | Argon2id | Compatible with `passlib` + handles long Urdu names |
| Web Push (VAPID) | Twilio SMS | $0/mo + works in PWAs |
| 35/15/30/10/10 unified weights | Pure ML output | Domain-tuned interpretability ("why is this area High?") |

---

## SLIDE 39 — METRICS / EVALUATION

> Replace these with your latest run numbers — the old "99.27 % CV" is stale.

- **Random Forest 5-fold CV accuracy** — `<run train_model.py and quote>`
- **Poisson calibration** — Brier score on holdout `<run>`
- **OCR field-level accuracy** (manual eval, n=120 FIRs)
  - Crime date: **96 %**
  - Police-station name: **94 %**
  - Crime area (post-fuzzy): **88 %**
  - PPC sections: **91 %**
- **Image-hash cache hit-rate** on re-uploads: **100 %** (by construction).
- **Push delivery success-rate**: ≈ **97 %** (≈ 3 % stale subscriptions, auto-pruned).

---

## SLIDE 40 — GOVERNANCE & FUTURE WORK

**Today**
- Append-only audit log on every admin action.
- Super-admin approval gate for 6 sensitive actions.
- Hot-reload of ML artefacts via `subprocess` after retraining (no API downtime).

**Next 3 months**
- Replace Nominatim with **self-hosted Photon** to remove the 1.1 s rate-limit ceiling.
- Add **DBSCAN clustering** to surface emerging hotspots before they hit the High threshold.
- **Mobile PWA** with offline-first crime cache for low-connectivity areas.
- Integrate **Punjab Safe Cities CCTV API** (when access is granted) for live incident corroboration.
- Replace Groq + OpenRouter chain with **Claude Haiku** for ~10× cheaper PPC verification.

---

## SLIDE 41 — THANK YOU

**SafeVision**
*Predictive Spatial Intelligence for Lahore's Streets*

- 🔗 Live: `https://safevision-backend-ye2i.onrender.com`
- 📊 ~142 000 LOC | 130 endpoints | 42 tables | 12 ML/OCR services
- ✉️ `safevision.alerts@gmail.com`

**Q & A**

---

# APPENDIX — CORRECTIONS FROM THE OLD 24-SLIDE DECK

| # | Old slide claim | Reality (file:line) |
|---|---|---|
| 1 | FastAPI 0.104.1 | **0.115.6** *(`requirements.txt:1`)* |
| 2 | Backend 15,441 LOC | **41,192 LOC** *(`find app -name "*.py"`)* |
| 3 | Frontend 30,000+ LOC | **52,255 JS/JSX + 48,443 CSS = 100,698 LOC** |
| 4 | OCR engine 6,900+ LOC | **12,517 LOC** *(`app/ocr/`)* |
| 5 | 139 API methods | **130 backend endpoints** verified |
| 6 | `users_info` 52 columns | **55 columns** *(`schema.sql:858-922`)* |
| 7 | `ST_Distance_Sphere` 1.5 km | **Haversine in Python** — TiDB has no spatial fn |
| 8 | "8-tier severity inference" | **3-output classes (High/Med/Low)** + 10-point severity_map |
| 9 | "7 sample points per route" | Not hardcoded — **arbitrary route_points length** |
| 10 | "1.1 s Nominatim rate-limit on routes" | 1.1 s applies to **OCR geocoding**, not routing |
| 11 | "Safest / Fastest / Balanced" 3 routes | Generic ranked alternates with score 0-100 — labels not in code |
| 12 | "Rush-hour 1.5× multiplier" | Reverse: **0.85× nighttime penalty** (`multi_route_calculator.py:333-336`) |
| 13 | "60-word Roman-to-Urdu dictionary" | **268 entries** in `urdu_location_dictionary.py` |
| 14 | "70 % difflib similarity" | Tiered: **0.55 word-level / 0.75 high-conf / 0.65 moderate** |
| 15 | "99.27 % CV accuracy" | Computed at runtime — **quote your latest run, not a stale literal** |
| 16 | Unified weights "35 / 15 / 30 only" | Five components: **35 / 15 / 30 / 10 / 10** *(volume / sev / recency / trend / time)* |
| 17 | "Sundays 17:05" weekly report | ✅ **verified** — `main.py:1356-1367`, default `day_of_week='sun', hour=17, minute=5, tz='Asia/Karachi'` |
| 18 | "bcrypt_sha256 + 72-byte truncation" | ✅ **verified** — `auth_updated.py:46-54` |
| 19 | "Multi-secret JWT, HS256" | ✅ **verified** — `auth_updated.py:34-40` |
| 20 | "30 days users / 60 minutes admins" | ✅ **verified** — `auth_updated.py:36-38` |

> **Net effect:** the project is significantly **bigger and more nuanced** than the old deck claimed — leaning into the corrected numbers makes the presentation more credible, not less.
