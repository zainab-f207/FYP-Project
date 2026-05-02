# CrimeVision (SafeVision) — Complete Project Presentation Guide

A complete, slide-by-slide presentation script for your Final Year Project. Everything is written in **simple, easy words** so you can read it directly or paraphrase it. Each section maps to one or more presentation slides.

---

## TABLE OF CONTENTS

1. Title & Project Identity
2. Problem Statement (The Pain Point)
3. Our Solution — What CrimeVision Is
4. Project Objectives (What We Wanted to Achieve)
5. System Roles — Who Uses the System
6. Technology Stack — What We Built It With
7. Complete System Architecture (How Everything Connects)
8. Database — How Data Is Stored (42 Tables)
9. Backend Modules — All Folders Explained
10. Authentication & Security (How Login Works)
11. ML Model #1 — Crime Risk Prediction (Random Forest)
12. ML Model #2 — Poisson Probability Predictor (Time-aware)
13. ML Model #3 — Route Safety Analyzer (Rule-based + AI)
14. OCR Pipeline — Reading Urdu FIR Documents
15. Alert System (Email + Browser Push + SMS)
16. Real-time Location Tracking
17. Crime Heatmap & Map Interface
18. Emergency SOS & Patrol Requests
19. Community Watch & Safety Network
20. Reports Generation (PDF / Excel / CSV)
21. Law Sections Module (PPC + AI Verification)
22. Background Jobs & Schedulers
23. Frontend — All Three Dashboards
24. API Endpoints — Complete List (60+)
25. Tricks, Techniques & Smart Decisions
26. Challenges Faced & Solutions
27. Future Scope
28. Conclusion / Demo Tips

---

## 1. TITLE & PROJECT IDENTITY

**Project Name:** CrimeVision (also branded as **SafeVision**)
**Type:** Final Year Project (Web-based AI System)
**Domain:** Crime Prevention, Public Safety, Smart City, Predictive Policing
**Target City:** Lahore, Pakistan (designed to extend to all of Punjab/Pakistan)

**One-line pitch (memorize this):**
*"CrimeVision is an AI-powered safety platform that predicts crime risk for any area, suggests the safest routes to travel, sends real-time alerts to citizens, lets police digitize FIR documents in Urdu using OCR, and gives administrators a complete control panel — all in one web application."*

---

## 2. PROBLEM STATEMENT

**Tell the audience the pain points in simple words:**

- People don't know which areas of the city are dangerous.
- Crime data exists, but it's locked in paper FIRs and not searchable.
- There is no public tool to plan a "safe route" before traveling.
- Citizens have no quick way to call for help, report a crime, or warn neighbors.
- Police and admins don't have a single dashboard to see crime patterns.
- Existing apps (Google Maps, etc.) only show shortest routes — they ignore safety.

**Real-world example to say in the demo:**
*"Imagine a woman wants to travel from Johar Town to Anarkali at 9 PM. Google Maps will show the fastest route — but what if that route passes through 4 high-risk crime spots? Our system will warn her, suggest a safer alternative, and even alert her family if she enters a dangerous zone."*

---

## 3. OUR SOLUTION — WHAT CRIMEVISION IS

A **complete web platform** with three connected parts:

1. **Public Side (Citizens):** Crime map, risk prediction, safe-route planner, emergency SOS, community alerts.
2. **Admin Side (Police/Officers):** Add crimes, OCR-based FIR scanning, view reports, manage users, send alerts.
3. **Super-Admin Side:** Manage admins, audit logs, system settings, PPC law database, full analytics.

**Powered by:**
- **3 ML models** (Random Forest + Poisson Probability + Rule-based Route Safety)
- **OCR engine** (reads Urdu/English FIR scanned documents)
- **Real-time alerts** (Email + Browser Push + SMS gateway)
- **Live geolocation tracking** (with privacy controls)

---

## 4. PROJECT OBJECTIVES

Say each one as a clear goal:

1. Build a **single platform** that combines crime data, AI predictions, maps, and alerts.
2. Use **machine learning** to predict whether an area is High / Medium / Low risk.
3. Let police **scan FIR images** and auto-extract crime details (date, area, sections).
4. Give every citizen a **safe-route planner** that compares 3 routes by safety score.
5. Send **real-time alerts** when a user enters a dangerous area.
6. Provide **admins** complete control over data, users, reports, and law sections.
7. Make everything **free, fast, and accessible** through any browser (mobile or desktop).

---

## 5. SYSTEM ROLES — WHO USES THE SYSTEM

The system has **three user roles** stored in the `users_info` table (column `role`):

| Role | What They Can Do |
|---|---|
| **User (citizen)** | View map, predict risk, plan routes, get alerts, SOS, join community |
| **Admin (police/officer)** | All user features + add crimes, OCR FIRs, generate reports, manage incidents |
| **Super-Admin** | All admin features + create/remove admins, audit logs, system settings, PPC law database |

**Tip for slide:** Show three icons (citizen, police, super-admin) with arrows pointing to features they each have.

---

## 6. TECHNOLOGY STACK — TOOLS WE USED

### Backend (the brain of the system)
| Layer | Tool / Library | Why We Chose It |
|---|---|---|
| Language | **Python 3** | Best for AI / ML, easy to read |
| Framework | **FastAPI 0.104** | Async, fast, auto-generates API docs |
| Server | **Uvicorn** | High-performance ASGI server |
| Database driver | **mysql-connector-python** | Official MySQL connector |
| Authentication | **python-jose (JWT)** + **bcrypt** | Industry-standard token-based login |
| Scheduler | **APScheduler** | Runs background jobs (alerts, reports) |
| ML | **scikit-learn 1.4** | Random Forest, label encoders, scaler |
| Data | **pandas + numpy** | Data cleaning + numeric operations |
| ML model save | **joblib** | Persist `.pkl` model files |
| OCR | **EasyOCR + PaddleOCR + Tesseract + Google Gemini API** | Multi-engine OCR for Urdu+English |
| Image processing | **OpenCV + Pillow** | Crop, deskew, enhance FIR images |
| Push notifications | **pywebpush** (VAPID keys) | Browser push without third-party servers |
| 2FA | **pyotp** | Time-based one-time passwords (Google Authenticator) |
| Email | **smtplib (built-in)** | Send transactional emails |
| Reports | **reportlab + openpyxl** | Generate PDF and Excel files |
| Geocoding | **geopy + Nominatim (OpenStreetMap)** | Convert area name → lat/lng |
| Routing | **OSRM API** | Free routing service (Open Source Routing Machine) |
| Reverse Geocoding | **OpenStreetMap Nominatim** | Convert lat/lng → readable address |
| AI Provider | **Groq API + OpenRouter API + Google Gemini** | Free LLMs to verify Pakistani law sections |

### Frontend (what the user sees)
| Layer | Tool | Purpose |
|---|---|---|
| Framework | **React 18** | Component-based UI |
| Build | **Vite 4** | Fast dev server + production build |
| Routing | **react-router-dom 7** | Multi-page navigation |
| Maps | **Leaflet + react-leaflet** | Free, open-source maps |
| Heat layer | **leaflet.heat** | Crime density heatmap |
| Routing UI | **leaflet-routing-machine + leaflet-polylinedecorator** | Draw routes with arrows |
| Charts | **Chart.js + react-chartjs-2** | Bar / line / radar charts |
| UI library | **Ant Design + Bootstrap 5** | Pre-built modal, tables, forms |
| HTTP client | **Axios** | API calls with auto token injection |
| Notifications | **react-toastify** | Toast popups |
| PDF on client | **jspdf + html2canvas** | Save dashboard as PDF |
| QR codes | **qrcode** | 2FA setup display |

### Database
- **MySQL 8** — Primary relational database
- **TiDB Cloud** (alternative deployment) — distributed MySQL-compatible cloud DB
- **42 tables** total

### Deployment
- Backend: **Render.com** (Python web service)
- Frontend: **Vercel** (static React build)
- Environment variables loaded via `.env` (using `python-dotenv`)

---

## 7. SYSTEM ARCHITECTURE — HOW EVERYTHING CONNECTS

**Tell it as a story for the slide:**

```
[ Browser (React App) ]
        ↓  (HTTPS + JWT token in headers)
[ FastAPI Backend on Render ]
        ↓
        ├──→ MySQL Database (42 tables)
        ├──→ Random Forest Model (rf_model.pkl)
        ├──→ Poisson Artifacts (poisson_artifacts.json)
        ├──→ OCR Engine (EasyOCR / PaddleOCR / Tesseract / Gemini)
        ├──→ APScheduler (background jobs every 5/15/60 min)
        ├──→ External APIs:
        │      • OSRM (route calculation)
        │      • Nominatim (geocoding)
        │      • Groq / OpenRouter (AI law verification)
        │      • SMTP (email alerts)
        │      • Web Push (browser notifications)
        └──→ Service Worker (sw.js) for offline + push notifications
```

**Key architectural decisions:**
- **Stateless backend:** Every request carries a JWT token; the server stores no session.
- **Single MySQL DB** + many indexed tables = simple yet scalable.
- **Models are loaded once at startup** and reused (fast inference).
- **CORS middleware** allows the React frontend (different origin) to call the API safely.

---

## 8. DATABASE — 42 TABLES EXPLAINED IN GROUPS

Your database has 42 tables. We grouped them so each slide is digestible:

### A) USER & AUTHENTICATION (8 tables)
| Table | Purpose |
|---|---|
| `users_info` | Master user table — username, email, password hash, role, home/work area, GPS, 2FA secret, profile photo, alert preferences, location-tracking flags |
| `users` | Legacy user table (kept for backward-compat) |
| `admins` | Police / officer accounts with permissions JSON |
| `admin_sessions` | Active admin login sessions (with IP & user agent) |
| `login_attempts` | Track every login attempt (for brute-force lockout) |
| `user_activity_logs` | Every user action saved as JSON for audit |
| `admin_messages` | Internal messaging between admins |
| `api_keys` | API keys for external integrations (rate-limited) |

### B) CRIME DATA (3 tables)
| Table | Purpose |
|---|---|
| `crimes` | **Main table** — 25,000+ records: date, time, area, crime_type, lat/lng, risk_level (Low/Med/High), source (admin/public/predicted), status (verified/unverified), description, Urdu fields |
| `areas` | Master list of areas with coordinates |
| `area_coordinates` | Cached lat/lng for each area name (avoid repeated geocoding) |

### C) ALERT SYSTEM (8 tables)
| Table | Purpose |
|---|---|
| `alert_notifications` | Every alert sent to a user (success/failed, channels, score) |
| `alert_subscriptions` | Which alert types each user wants |
| `browser_push_subscriptions` | VAPID push endpoint + p256dh + auth key per user |
| `browser_notifications` | Stored browser notifications (so user sees them in dashboard) |
| `comprehensive_alerts` | Multi-channel alert tracking (email + sms + browser) |
| `notification_logs` | Detailed log of each notification attempt |
| `notifications` | System-wide notification queue |
| `user_alert_preferences` | Quiet hours, radius, type filters per user |

### D) SAFETY / LOCATION (4 tables)
| Table | Purpose |
|---|---|
| `user_location_history` | GPS points with risk level, accuracy, source (gps/ip/manual) |
| `user_locations` | Saved favorite locations |
| `system_alerts` | Admin-broadcast warnings to all citizens |
| `user_alerts` | Per-user alert inbox |

### E) COMMUNITY (5 tables)
| Table | Purpose |
|---|---|
| `community_alerts` | Alerts created by users (warning, info, emergency) |
| `community_incident_reports` | Citizen-reported incidents |
| `community_activity_log` | Every community action (joined group, reported, etc.) |
| `neighborhood_watch_groups` | Local watch groups with radius and members |
| `group_members` | Join table (group ↔ user, with role) |

### F) EMERGENCY (2 tables)
| Table | Purpose |
|---|---|
| `emergency_calls` | Each SOS call: contact name, number, GPS, address, type |
| `patrol_requests` | Citizen request for police patrol with urgency |

### G) LAW DATABASE (2 tables)
| Table | Purpose |
|---|---|
| `law_sections` | 18,000+ PPC/ATA/PECA sections with English title, AI verification status |
| `law_sections_audit` | Audit trail of who edited which section |

### H) REPORTS (3 tables)
| Table | Purpose |
|---|---|
| `report_history` | Generated reports (filename, format, size, status) |
| `reports` | Newer report records with parameters JSON |
| `scheduled_reports` | Recurring reports (daily/weekly/monthly) |

### I) GOVERNANCE / AUDIT (4 tables)
| Table | Purpose |
|---|---|
| `audit_logs` | Every admin action with IP, user agent, JSON details |
| `approval_requests` | Sensitive actions await super-admin approval |
| `system_logs` | App-level logs |
| `system_settings` | Global key-value settings (email config, thresholds, etc.) |

### J) SAFETY RESOURCES (3 tables)
| Table | Purpose |
|---|---|
| `safety_resources` | PDFs / guides uploaded for download |
| `resource_downloads` | Track who downloaded what |
| `safety_network_connections` | Friend / neighbor connections |

**Tip for the slide:** Use a single ER diagram showing only the 5 most important tables: `users_info`, `crimes`, `areas`, `alert_notifications`, `user_location_history`. Audience won't grasp 42 tables in one diagram.

---

## 9. BACKEND MODULES — FOLDER BY FOLDER

```
backend/
├── main.py                       ← FastAPI app entry point
├── schema.sql                    ← Full database schema dump
├── requirements.txt              ← All Python dependencies
└── app/
    ├── core/
    │   ├── config.py             ← env vars, paths, logger
    │   └── database.py           ← MySQL connection pool, schema migrations
    ├── routes/                   ← All API endpoints (13 files)
    │   ├── auth.py               ← register, login, 2FA, OAuth, password reset
    │   ├── admin.py              ← user management, system settings, audit
    │   ├── alerts.py             ← VAPID push, subscribe, weekly reports
    │   ├── crimes.py             ← list/add crimes, predict-risk, route-safety
    │   ├── emergency.py          ← SOS calls, patrol requests
    │   ├── community.py          ← community stats and alerts
    │   ├── location.py           ← live location update + history
    │   ├── reports.py            ← crime summary, system health reports
    │   ├── admin_reports.py      ← scheduled reports, export filtered
    │   ├── analytics.py          ← crime trends, predictive, area analysis
    │   ├── law_sections.py       ← PPC sections + AI verify
    │   ├── user_profile.py       ← profile alerts, mark read
    │   └── test_alerts.py        ← admin-only alert system testing
    ├── services/                 ← Business logic
    │   ├── route_safety_analyzer.py     ← rule-based scorer
    │   ├── route_safety_analyzer_ai.py  ← Poisson + RF scorer
    │   ├── multi_route_calculator.py    ← OSRM 3-route generator
    │   └── gemini_law_verifier.py       ← AI provider chain (Groq → OpenRouter)
    ├── crime_risk_model/         ← The ML pipeline
    │   ├── train_model.py        ← Train Random Forest
    │   ├── predict_risk.py       ← Use saved model on new data
    │   ├── config/severity_map.json  ← crime → severity score (1-10)
    │   ├── models/               ← rf_model.pkl, scaler.pkl, artifacts
    │   └── utils/
    │       ├── helpers.py        ← Feature engineering + DB I/O
    │       ├── poisson_predictor.py  ← Statistical probability model
    │       ├── severity_sync.py  ← Sync from law_sections to severity map
    │       ├── auto_retrain.py   ← Auto retrain when new data added
    │       └── model_watcher.py  ← Watches for OOV (out-of-vocab) crime types
    ├── ocr/
    │   ├── fir_specialized_ocr.py   ← Main FIR OCR engine (multi-region)
    │   ├── urdu_location_dictionary.py ← Urdu place-name dictionary
    │   ├── ppc_sections.py       ← PPC section name lookups
    │   └── image_hash_lookup.py  ← Image hash → known FIR cache
    ├── utils/
    │   ├── geo.py                ← haversine distance, bearings
    │   ├── risk.py               ← safety_score formula + risk labels
    │   ├── area_normalization.py ← match "Johar Town" ≈ "JOHAR TOWN"
    │   ├── validation.py         ← input validation helpers
    │   └── report_generator.py   ← PDF / Excel / CSV builders
    ├── reports/                  ← Crime / activity / health report generators
    ├── auth_updated.py           ← JWT issue / verify, password hashing
    ├── auth_routes.py            ← Original (legacy) auth endpoints
    ├── alert_notifications.py    ← Email + Push + SMS notification system
    ├── alert_routes.py           ← Older alert routes
    ├── alert_tester.py           ← Internal test harness
    ├── audit_logging.py          ← Helper to write to audit_logs table
    ├── approval_workflow.py      ← Approval-required actions
    ├── two_factor.py             ← 2FA enable/disable/verify
    ├── email_otp.py              ← One-time codes for login
    ├── email_verification.py     ← Email confirmation flow
    ├── email_templates.py        ← All HTML email templates (1000+ lines)
    ├── sms_templates.py          ← SMS body templates
    ├── password_reset_fixed.py   ← Forgot/reset password flow
    ├── cleanup_unverified_accounts.py  ← Background job
    ├── rate_limiting.py          ← Per-IP / per-user rate limits
    ├── dependencies.py           ← FastAPI dependencies (token, current_user)
    ├── models/
    │   ├── schemas.py            ← Pydantic request/response models
    │   └── types.py              ← TypedDict for DB rows
    └── tasks/                    ← Background scheduled tasks
```

---

## 10. AUTHENTICATION & SECURITY — HOW LOGIN WORKS

Walk the audience through the login flow (very visual):

### 10.1 Registration
1. User fills form (name, email, password, phone)
2. Frontend POSTs to `/auth/register`
3. Backend hashes password with **bcrypt** (one-way) and stores in `users_info`
4. Generates a random verification token, stores `email_verification_token` + `token_expires_at`
5. Sends verification email with a magic link
6. User clicks link → backend marks `is_verified = 1`

### 10.2 Login
1. User submits email + password to `/auth/login`
2. Backend fetches hash from DB, runs `verify_password()` (bcrypt compare)
3. If account has 2FA enabled → step-up to OTP screen (`/auth/verify-login-otp`)
4. Otherwise → issue **JWT access token** (15 min) + **refresh token** (7 days)
5. Frontend saves tokens in `localStorage`; axios attaches `Authorization: Bearer <token>` to every call

### 10.3 Security Features Implemented
- **Bcrypt password hashing** with salt (cost factor configurable)
- **JWT tokens** signed with `SECRET_KEY` from `.env`
- **Refresh tokens** to renew without forcing re-login
- **Two-Factor Authentication (TOTP)** via `pyotp` (Google Authenticator compatible)
- **Email OTP login** option for users who lose their authenticator
- **Email verification** required before login
- **Failed-attempt tracking** (`failed_attempts` column) → temporary lockout
- **Login attempts table** records IP + email for forensics
- **Rate limiting** (`rate_limiting.py`)
- **Approval workflow** — destructive admin actions queue for super-admin review
- **Audit logs** — every admin write goes to `audit_logs` with JSON details
- **Google OAuth** sign-in via `google-auth` library
- **Password reset** — token-based, expires after 1 hour
- **CORS whitelist** — only trusted frontend origins are allowed
- **Token cleanup** — invalid tokens are stripped from localStorage on app load

---

## 11. ML MODEL #1 — CRIME RISK PREDICTION (RANDOM FOREST)

This is the **flagship ML model** of the project. Explain it slowly.

### 11.1 What It Predicts
Given a future crime context (area, crime type, date/time, lat/lng) → predict **High / Medium / Low** risk.

### 11.2 Why Random Forest?
Read this almost verbatim — it's what we wrote in the code:

- Handles mixed numeric & categorical features without one-hot explosion
- Naturally robust to outliers (it's an ensemble of decision trees)
- Works well even on unseen areas (we use median fallback)
- Gives **feature importances** so we can explain predictions to a judge
- Doesn't need re-interpretation when scoring new data — just call `.predict()`

### 11.3 Training Pipeline (7 steps)

1. **Sync severity map** — read latest PPC sections from `law_sections` table → update `severity_map.json`. (So new crime types get severity automatically.)
2. **Load data** — `SELECT * FROM crimes` (~25,000 records) into a pandas DataFrame.
3. **Build severity map** — combine manual map + auto-derived map.
4. **Engineer features** (11 features per crime):
   - `crime_severity` (1–10)
   - `hour` (0–23, parsed from `crime_time`)
   - `day_of_week` (0=Mon)
   - `month` (1–12)
   - `is_weekend` (0/1)
   - `is_nighttime` (1 if hour ∈ [22,23,0,1,2,3,4])
   - `time_risk` (cosine peak at midnight)
   - `area_crime_frequency` (how many crimes happen in this area / total)
   - `area_freq_percentile` (0–100 hotspot rank)
   - `latitude`
   - `longitude`
5. **Generate rule-based labels** (because we had no ground-truth labels):
   - Score = 0.40·severity + 0.25·time + 0.25·area_hotspot + 0.10·weekend
   - Top 30% → High, bottom 25% → Low, rest → Medium
6. **Scale features** with `StandardScaler`
7. **Train model**:
   ```
   RandomForestClassifier(
       n_estimators=200,
       max_depth=15,
       min_samples_leaf=10,
       class_weight='balanced',
       random_state=42,
       n_jobs=-1
   )
   ```
8. **Cross-validate** with 5-fold stratified split → typical accuracy **~95%**
9. **Save** model + scaler + artifacts (severity map, area freq map, label classes) using `joblib`
10. **Backfill DB** — update every crime's `risk_level` column with the new prediction

### 11.4 Smart Trick — Severity Resolution Order
For every new crime type the system tries (in order):
1. **Manual severity map** — human-curated values (highest priority)
2. **Keyword-based inference** — e.g. text contains "murder" → 10, "bomb" → 10, "theft" → 5 (8 keyword tiers)
3. **Frequency-derived value** — rare = high severity (rarity is treated as danger proxy)
4. **Statistical median** — final fallback

This makes the model **never crash on new crime types** that didn't exist in training data.

### 11.5 Auto-save New Severity
When the system sees a new crime type it auto-saves the inferred severity to `severity_map.json` — so next training run learns it.

### 11.6 Output Example
```json
{
  "predicted_risk": "High",
  "risk_probability": {"High": 0.82, "Medium": 0.15, "Low": 0.03},
  "risk_score": 0.78
}
```

---

## 12. ML MODEL #2 — POISSON PROBABILITY PREDICTOR

This is the **time-aware companion** to the Random Forest.

### 12.1 The Problem RF Couldn't Solve
- RF only outputs a class (High/Med/Low). It can't say "what's the probability of a robbery in Gulberg on **next Tuesday at 9 PM**?"
- For route safety we needed a **continuous probability** that varies by **date and hour**.

### 12.2 The Math (explain in plain words)
Crime occurrences follow a **Poisson process**:
```
P(at least 1 crime today) = 1 - e^(-λ)
```
Where **λ (lambda)** = expected number of that crime per day in that area, then multiplied by:
- Day-of-week multiplier (e.g. Saturday is 1.4× higher)
- Month multiplier (e.g. December 1.2× higher)
- Hour multiplier (e.g. 11 PM is 2.5× higher than noon)

### 12.3 What Gets Saved (`poisson_artifacts.json`)
- `pair_lambdas` — (area, crime_type) → crimes/day
- `area_lambdas` — area → total crimes/day
- `crime_type_fractions` — crime_type → share of total
- `dow_multipliers` — per (area, crime, day-of-week)
- `month_multipliers` — per (area, crime, month)
- `area_dow_multipliers` — fallback when pair has no data
- `area_month_multipliers` — fallback when pair has no data
- `total_observation_days` — how many calendar days our data spans

### 12.4 Smart Tricks
- **Laplace smoothing** — add +1 pseudo-count so we never get probability = 0
- **Hour amplification exponent (2.2)** — raw multipliers cluster near 1.0; raising them spreads them so changing the visit time visibly changes the answer
- **Fallback hierarchy** — if (area, crime) pair has no data → use area-only data → use global average

### 12.5 What This Enables
- Route-safety analyzer uses Poisson **as primary**, RF only as fallback
- "What's the safest day to visit Anarkali this week?" → call `area_safety_profile()`
- Risk percentage that **smoothly varies** between 0–100 instead of jumping classes

---

## 13. ML MODEL #3 — ROUTE SAFETY ANALYZER

Two implementations live in `app/services/`:

### 13.1 Rule-Based Analyzer (`route_safety_analyzer.py`)

Starts with **base score of 100** then deducts/adds points:

**Crime deductions:**
- Each High-risk crime near route: −15
- Each Medium-risk crime: −8
- Each Low-risk crime: −3

**Infrastructure deductions:**
- Isolated road: −10
- Poor lighting: −12
- Far from police: −8
- Far from hospital: −5

**Infrastructure bonuses:**
- Police within 500m: +10
- Hospital within 1km: +8
- Main road: +5
- Heavy traffic: +5
- Good lighting: +8

**Time multipliers:**
- Late night (11 PM – 5 AM): worse score
- Daytime: bonus

**Final clamp:** score is forced into [10, 100]

**Safety levels:**
- 80+ → Safe
- 60–79 → Moderate
- 40–59 → Risky
- <40 → Dangerous

### 13.2 AI Analyzer (`route_safety_analyzer_ai.py`)
1. Take 10–20 sample points along the route
2. For each point: query Poisson model → get risk%, then RF as fallback
3. Aggregate: `route_score = average(point_scores) - penalty_for_high_risk_count`
4. Returns alerts (e.g. "Pass through 3 high-risk areas — consider alternative")

### 13.3 Multi-Route Generator (`multi_route_calculator.py`)
- Calls **OSRM** (Open Source Routing Machine) public API
- Asks for `alternatives=true` to get multiple paths
- If OSRM only returns 1–2, **forces variety** by inserting via-points perpendicular to start-end vector (1.5km left, 1.5km right, 3km offsets)
- Returns up to **4 routes** so the user can pick the safest

---

## 14. OCR PIPELINE — READING URDU FIR DOCUMENTS

This is one of the **most impressive** parts of the project — explain it slowly.

### 14.1 The Goal
A Pakistani FIR (First Information Report) is a paper document, often handwritten or photocopied, with **mixed Urdu and English** text. We extract:
- **Crime date** (DD-MM-YYYY)
- **Crime time** (HH:MM AM/PM)
- **Thana / Area** (police station)
- **PPC sections** (e.g. "302/324")
- **Crime description**

### 14.2 Multi-Engine Strategy
The OCR uses **4 engines in parallel** and picks the best result:

1. **EasyOCR** — best for Urdu (`['ur','en']` languages)
2. **PaddleOCR** — fast, good for printed text
3. **Tesseract** — fallback for English
4. **Google Gemini API** (via google-genai) — uses LLM vision when text is too blurry; cascades through Gemini 1.5 Flash → 1.5 Pro

If all engines fail → **OpenRouter Mistral** vision model is tried last.

### 14.3 Image Preprocessing (`FIRImagePreprocessor`)
Before OCR:
- Convert to grayscale
- Apply **CLAHE** (contrast-limited adaptive histogram equalization)
- Deskew using moments
- Sharpen with Laplacian kernel
- Crop to 7 known regions of the FIR template (header, table rows, etc.)

### 14.4 Region-Based Extraction (`FIRRegions`)
The standard FIR template has fixed positions, so we use **percentage-based coordinates**:
- Header: top 8–16% of image
- Date row: row 3 of table
- Thana: scanned in 3 places (Row 4, Row 2, header)
- Sections: Row 5

### 14.5 Smart Validation Rules
- **Reject Urdu diacritics (tashkeel)** — never appear in printed location names
- **Reject ≥2 consecutive repeated chars** — sign of garbled OCR
- **Reject Urdu/Arabic digits in location text**
- **Whitelist 50+ known Lahore thanas** — Shalimar, Gulshan Ravi, Iqbal Town, Model Town, Gulberg, Johar Town, Gulberg, etc. with all spelling variants

### 14.6 Image Hash Lookup
For frequently-uploaded FIRs we compute a perceptual hash and cache the result. Next time the same image is uploaded → instant return without running OCR.

### 14.7 Geocoding
After extracting "Iqbal Town" → call `geocode_crime_area()` → tries:
1. Local DB lookup (`area_coordinates` table)
2. Nominatim free OpenStreetMap geocoding
3. Fuzzy match against the crimes table

### 14.8 Pipeline End-to-End
```
[ Police uploads FIR.jpg ]
          ↓
   Image preprocessing
          ↓
   Image hash check ──→ HIT → return cached
          ↓ MISS
   Multi-engine OCR (parallel)
          ↓
   Voting + best result
          ↓
   Field extractors (date / thana / sections)
          ↓
   Validation + Urdu dictionary correction
          ↓
   Geocoding (lat / lng)
          ↓
   Insert into `crimes` table (status='unverified')
          ↓
   Run RF predict → set risk_level
          ↓
   Admin dashboard updates instantly
```

---

## 15. ALERT SYSTEM — REAL-TIME MULTI-CHANNEL

The system has a **comprehensive alert engine** in `alert_notifications.py`.

### 15.1 Three Channels
1. **Email** — full HTML templates from `email_templates.py` (1000+ lines)
2. **Browser Push** — Web Push protocol with VAPID keys
3. **SMS** — via SMS gateways (templates in `sms_templates.py`)

### 15.2 Alert Types
- **Live Risk Alert** — user enters a high-risk zone
- **Incident Alert** — new crime within user's saved areas
- **Weekly Safety Report** — every Monday morning, statistical summary
- **Community Alert** — neighborhood-wide warning
- **System Alert** — admin broadcast to all users
- **Emergency Notification** — SOS confirmation

### 15.3 VAPID Browser Push (Hardest Part)
- We generate a public/private key pair (P-256 ECDH)
- Frontend subscribes to the push service with the **public key** → gets an `endpoint`, `p256dh`, `auth` token → stored in `browser_push_subscriptions`
- When backend wants to push: uses **pywebpush** with the **private key** to sign and send to the endpoint
- Browser's service worker (`sw.js`) wakes up and shows the notification
- We had to **normalize private key formats** (DER ↔ PEM) because pywebpush is picky
- We persist key as a temporary `.pem` file because in-memory strings sometimes fail

### 15.4 Cooldown Logic
Each user has a per-zone cooldown cache (`alert_cooldown_cache`) so we don't spam them when they walk back and forth across a boundary.

### 15.5 Quiet Hours
`user_alert_preferences.quiet_hours_start/end` — alerts are suppressed during user's chosen "do not disturb" window.

### 15.6 Background Job
APScheduler runs `monitor_saved_locations()` every **5 minutes** — checks each user's saved home/work areas for new high-risk incidents and pushes alerts.

### 15.7 Weekly Reports
APScheduler runs `dispatch_weekly_safety_reports()` every **Monday 09:00** — generates a personalized HTML email with last week's crime stats around home/work area.

---

## 16. REAL-TIME LOCATION TRACKING

`routes/location.py` and `users_info.location_tracking_enabled` flag.

### 16.1 How It Works
1. Frontend asks browser for `navigator.geolocation` (with permission)
2. Sends GPS update to `POST /api/location/update` every 30 sec (interval configurable)
3. Backend stores in `user_location_history` with risk_level + safety_score + accuracy
4. If risk_level == 'High' and `alert_triggered = 0` → trigger alert + flip flag

### 16.2 Three Location Sources
- `gps` — high accuracy, browser geolocation
- `ip` — IP geolocation fallback (via free service)
- `manual` — user picks a pin on map

### 16.3 Privacy Controls
- Toggle: `location_tracking_enabled` (off by default)
- Toggle: `background_location_tracking`
- Toggle: `monitor_live_location`
- Toggle: `high_risk_alerts_only`

### 16.4 Address Resolution
- Reverse geocoding via OpenStreetMap Nominatim — converts lat/lng → readable address
- Cached to avoid hitting free tier rate limits

---

## 17. CRIME HEATMAP & MAP INTERFACE

`frontend/src/components/CrimeMapInterface/`

### 17.1 Stack
- **Leaflet** for the map
- **leaflet.heat** plugin for heat layer
- **OpenStreetMap** tiles (free)

### 17.2 Features
- Toggle layers: **All crimes**, **Last 7 days**, **Last 30 days**, **Last year**
- Filter by **crime type** dropdown
- Filter by **risk level** (High / Medium / Low)
- Click a point → popup with crime details
- Heatmap intensity = crime density per pixel
- Markers grouped by area → clicking shows top crimes for that area
- Search box → recenter map on area name

### 17.3 Real-Insights Mode
A second variant (`CrimeMapInterface_real_insights.jsx`) overlays:
- AI-predicted next-week risk for each area
- Police station icons (from `area_coordinates`)
- Hospital icons
- Safe-zone polygons

---

## 18. EMERGENCY SOS & PATROL REQUESTS

`routes/emergency.py` — **5 endpoints**

### 18.1 Quick SOS Button
- One-tap on UserDashboard
- Captures current GPS
- Inserts into `emergency_calls` with `emergency_type` (police, ambulance, fire)
- Sends email + SMS to **emergency contacts** (saved in profile)
- Optionally calls `tel:15` (Pakistan police number) directly

### 18.2 Public Emergency Call
`/emergency-call/public` — works even without login (for guest users on the public site)

### 18.3 Patrol Request
- Citizen marks a location and requests patrol
- Stored in `patrol_requests` with `urgency` (low/medium/high)
- Admin sees it in dashboard, can `assign` it to an officer
- Status flow: pending → assigned → completed / cancelled

### 18.4 Emergency Contacts
- Master list (city helplines, hospitals, women shelter, etc.)
- Stored in `system_settings` table for easy update
- `/emergency-contacts` returns the list

### 18.5 Emergency Stats
- Counts of last 24h calls
- Most common emergency types
- Average response time

---

## 19. COMMUNITY WATCH & SAFETY NETWORK

`routes/community.py`

### 19.1 Neighborhood Watch Groups
- Users can create a group: name, area, radius (default 2 km), max 50 members
- Other users in radius can request to join
- Group has roles: member / moderator / admin
- Group can post community alerts

### 19.2 Community Alerts
- Posted by group admin or any verified user
- Types: emergency, warning, info, safety
- Severity: low → critical
- Has expiry date and view count
- Pushed to all users within radius via the alert system

### 19.3 Incident Reports
- Anonymous or named
- Status flow: reported → investigating → resolved → closed
- Optionally assigned to a watch group
- Police admin can convert it into a verified `crimes` record

### 19.4 Safety Network Connections
- Friend requests between users (`safety_network_connections`)
- Connection types: neighbor / authority / emergency_contact
- Used for "alert my contacts" feature in SOS

### 19.5 Resource Library
- PDFs / guides uploaded by admins
- Download tracked in `resource_downloads` table

---

## 20. REPORTS GENERATION

`backend/app/reports/` and `routes/admin_reports.py`

### 20.1 Three Report Categories
| Type | What it Contains |
|---|---|
| **Crime Summary Report** | Date range, area, crime breakdown, charts, top hotspots |
| **User Activity Report** | Login stats, active users, engagement metrics |
| **System Health Report** | Uptime, DB size, error count, alert success rate |

### 20.2 Three Output Formats
- **PDF** — built with `reportlab`, branded header, charts as images
- **Excel** — built with `openpyxl`, multi-sheet, conditional formatting
- **CSV** — raw data for further analysis

### 20.3 Scheduled Reports
- Saved in `scheduled_reports` table with cron-style `schedule` column
- APScheduler picks them up at `next_run`
- Sends email with PDF attached to recipients list

### 20.4 Filtered Export
`/api/admin-reports/export-filtered` — admin selects filters (date, area, crime type) → instant export

---

## 21. LAW SECTIONS MODULE — PPC + AI VERIFICATION

`routes/law_sections.py` + `services/gemini_law_verifier.py`

### 21.1 What's In It
- 18,000+ rows in `law_sections` table covering:
  - **PPC** — Pakistan Penal Code 1860
  - **ATA** — Anti-Terrorism Act 1997
  - **CNSA** — Control of Narcotic Substances Act 1997
  - **PECA** — Prevention of Electronic Crimes Act 2016
  - **ARMS** — Arms Ordinance 1965
  - **HUDOOD** — Hudood Ordinances 1979
  - **EXPLOSIVE** — Explosive Substances Act 1908
  - **WOMEN_PROTECTION** — Women Protection Act 2006

### 21.2 AI Verification Chain (clever cost-saving design)
We don't pay for AI — we use **3 free providers in fallback order**:

1. **Groq** (`llama-3.3-70b-versatile`) — fastest, 14,400 free requests/day
2. **OpenRouter** (`meta-llama/llama-3.1-8b-instruct:free`) — different infra
3. **Google Gemini** (gemini-1.5-flash) — for OCR-related verification

Each section can be sent for AI verification → AI returns the official legal title and a confidence note → stored in `ai_response`, `ai_model`, `last_ai_check`. Super-admin can approve to set `is_verified = 1`.

### 21.3 Audit Trail
Every edit goes to `law_sections_audit` with `old_title`, `new_title`, `changed_by`, `change_reason`.

### 21.4 Severity Sync
After every AI verification, we re-derive severity scores → updates `severity_map.json` → next training run learns the new severity. (This is the **closed loop** that connects PPC to ML.)

---

## 22. BACKGROUND JOBS & SCHEDULERS

APScheduler runs **at least 3 critical jobs**:

| Job | Frequency | What It Does |
|---|---|---|
| `monitor_saved_locations` | every 5 min | Check each user's saved areas for new high-risk crimes; push alerts |
| `dispatch_weekly_safety_reports` | every Monday 09:00 | Generate + email weekly report to each user |
| `poll_new_incidents_for_alerts` | every 1 min | Detect new `crimes` rows and notify users in radius |
| `cleanup_unverified_accounts` | daily | Delete users who didn't verify email within 7 days |
| `auto_retrain` | weekly (when 500+ new rows) | Retrain RF and Poisson models |
| `model_watcher` | continuous | Watches new crime types; flags OOV (out-of-vocabulary) for review |

---

## 23. FRONTEND — ALL THREE DASHBOARDS

### 23.1 Public Site (`MainWebsite.jsx`)
- Hero / introduction
- Feature highlights
- Live statistics
- Risk-prediction tool (no login)
- Crime map (no login)
- Emergency contacts
- About / project video page

### 23.2 User Dashboard (`UserDashboard/UserDashboard.jsx`)
**Cards & Sections:**
- **Safety Score Card** — personalized score for home location
- **Risk Factors Card** — top crime categories with percentages
- **Weekly Alerts Card** — count + change vs previous week
- **Safe Routes Card** — count of safe routes recently planned
- **Nearest Safe Zone** — name + distance
- **AI Route Analysis** — full route planner (start, end, mode → 3 routes ranked by safety)
- **Prediction Section** — predict risk for any area + date + time
- **Crime Map** — embedded heatmap
- **Browser Push Setup** — VAPID subscribe
- **Quick Actions** — SOS, report incident, find help
- **Profile Modal** — edit info, 2FA, change password, alert preferences
- **Safety Radar Chart** — multi-axis chart (lighting, police proximity, traffic, etc.)
- **Score Explainer** — modal that explains how safety score is computed

### 23.3 Admin Dashboard (`AdminDashboard/AdminDashboard.jsx`)
**Panels:**
- User Management Summary (counts, recent users)
- Approval Requests (pending sensitive actions)
- Crime Heatmap (full city)
- **OCR Panel** — upload FIR image → see extracted fields → confirm + save
- Admin Prediction Panel — predict risk for any area
- Reports Panel — generate / schedule / download
- Notifications Panel — view system + community alerts
- Recent Activity feed
- Analytics Panel — charts of trends, hotspots, top crime types
- Quick Actions

### 23.4 Super-Admin Dashboard (`SuperAdminDashboard/SuperAdminDashboard_updated.jsx`)
**Sections:**
- Admin Management — create/edit/disable admins
- Permission Matrix — fine-grained per-admin permissions
- User Management — full user CRUD
- System Settings — global toggles (email, alerts, model versions)
- **PPC Management** — browse 18,000 law sections, send to AI for verification, approve
- Audit Logs — every admin write with full JSON details
- System Logs — app-level errors and info
- Analytics Dashboard — full company-wide analytics with risk-map modal
- Reports Panel — system reports
- Mini Heatmap — quick overview
- Pending Approvals

### 23.5 Other Pages
- `/login` — login + register modal
- `/verify-email` — email verification landing
- `/reset-password` — token-based password reset
- `/autologin` — magic-link login
- `/risk-prediction` — public prediction tool
- `/crime-map` — public crime map
- `/emergency` — public emergency contacts page
- `/about-project` — project video page

---

## 24. API ENDPOINTS — COMPLETE LIST (60+)

Group them by router for the slide:

### Auth (24 endpoints — `/auth`)
register, resend-verification, verify-email (POST + GET), login, verify-login-otp, resend-login-otp, force-change-password, google-login, google-register, google-client-id, logout, me, refresh-token, update-location, update-profile, upload-profile-photo, check-2fa-status, generate-2fa, enable-2fa, disable-2fa, forgot-password, reset-password, generate-email-token, email-link

### Crimes (17 endpoints — `/api/crimes`)
list crimes (GET), nearest-area, area-safety-profile, areas (list all), areas/{area}/details, crime-types, areas/{area}/safety-advice, predict-risk (POST), add crime (POST), analyze-route-safety-ai (POST), compare-routes (POST), intelligence-dashboard, model/oov-status, model/trigger-retrain, areas/{area}/heatmap, model-watcher-status, reload-model

### Alerts (16 endpoints — `/api/alerts`)
get-safety-stats-by-coords, vapid-public-key, community/subscribe, check-location, status, unsubscribe, browser-notifications/subscribe, browser-notifications (list), browser-notifications/{id}/read, browser-notifications/read-all, heartbeat, logout, test/fix-alerts, test/alert-system, test/trigger-immediate, check-risk

### Admin (24 endpoints — `/admin`)
register, list, public-settings, system-settings (GET/POST), system-settings/apply-runtime, users/{id} (PUT), {admin_id} (PUT), stats, notifications, recent-events, notifications/stream, users (list), user-bulk, admin-bulk, user-roles, audit-logs, alerts/system, approval-request, my-approval-requests, pending-approvals, approval-request/{id}, review-approval/{id}

### Emergency (5 endpoints — `/api/emergency`)
emergency-contacts, emergency-call (POST), emergency-call/public (POST), patrol-request (POST), emergency-stats

### Community (2 endpoints — `/community`)
stats, alerts

### Location (10 endpoints — `/api/location`)
update (POST), preferences (GET/PUT), history, status, debug-schema, debug, history (DELETE), ip-geolocation, reverse-geocode

### Reports (4 endpoints — `/api/reports`)
crime-summary, user-activity, system-health, export-crime-data

### Admin Reports (8 endpoints — `/api/admin-reports`)
schedule, history (GET/DELETE), scheduled, generate, schedule (POST), export-filtered, download/{report_id}

### Analytics (3 endpoints — `/api/analytics`)
crime-trends, predictive, area-analysis

### User Profile (4 endpoints — `/api/profile`)
activity, alerts, alerts/{id}/read, alerts/read-all

### Law Sections (11 endpoints — `/api/law-sections`)
list, stats, lookup/{section_number}, verify-ai (POST), {id} (PUT), approve-ai/{id}, seed, audit/{id}, ppc/scan-missing, insert, law-types

**Tip:** On the slide, just show the **count per router** (a bar chart) and keep details in a backup slide.

---

## 25. TRICKS, TECHNIQUES & SMART DECISIONS

These are the points that **impress the examiner**. Mention each one briefly:

1. **Multi-engine OCR voting** — never trust one engine; we use 4 + an LLM fallback, then pick the best.

2. **Image hash cache** — same image uploaded again? Skip OCR completely.

3. **Severity keyword inference** — model never crashes on unseen crime types because we have 8 keyword tiers (murder, kidnap, assault, robbery, burglary, theft, vandalism, traffic).

4. **Auto-saved severity** — if a new crime type is encountered, we save its inferred severity to JSON so next training run learns it.

5. **Median fallback for unknown areas** — area_freq_median used when prediction sees a brand-new area.

6. **Dynamic risk thresholds** — top 30% / bottom 25% percentile thresholds re-computed each training run, so labels self-calibrate as data grows.

7. **Laplace smoothing in Poisson** — never gives 0 probability even for area-crime pairs we've never seen.

8. **Hour-multiplier amplification (^2.2)** — spreads multipliers from clustering near 1.0 so picking different times visibly changes risk.

9. **Three free AI providers in cascade** — Groq → OpenRouter → Gemini. Zero cost.

10. **Force-route variety with via-points** — when OSRM only returns 1 alternative we mathematically inject perpendicular waypoints to **guarantee 3 different routes**.

11. **VAPID PEM normalization** — pywebpush is fussy about key formats; we save to a temp file because in-memory strings sometimes fail.

12. **Cooldown cache for alerts** — prevents spamming users when they cross zone boundaries repeatedly.

13. **Quiet hours** — alerts respect each user's "do not disturb" window.

14. **Refresh tokens** — users stay logged in 7 days without re-entering password.

15. **JWT + bcrypt + 2FA + email OTP + Google OAuth** — 5 layers of authentication choices.

16. **Audit logs for every admin write** — full IP, user-agent, JSON details (forensics-ready).

17. **Approval workflow** — destructive actions require super-admin sign-off.

18. **Service worker for offline + push** — frontend works offline and receives push even when tab is closed.

19. **Token cleanup on app load** — invalid/expired tokens are stripped from localStorage to prevent stale-auth bugs.

20. **CORS dual layer** — middleware AND framework-level allow-list to defeat tricky browser behaviors.

21. **Auto-retrain trigger** — when 500+ new rows are added, the system automatically retrains in the background.

22. **Model watcher** — continuously watches for OOV crime types and flags them.

23. **Connection pool reuse** — `get_db_connection()` returns from a pool; massive speedup.

24. **Pydantic schemas for every endpoint** — auto-generated OpenAPI docs at `/docs` (Swagger).

25. **Response models for every API** — guarantees consistent JSON shape to frontend.

26. **CrimeVision branded emails** — 1000+ lines of HTML templates with placeholders for safety score, alerts, top crimes, etc.

27. **PWA-style service worker** — `sw.js` registered at app root, scope `/`, handles updates automatically.

28. **TiDB Cloud compatibility** — `get_db_ssl_kwargs()` lets the same code run on local MySQL or TiDB Cloud.

29. **Render.com deployment** — backend on Python web service; CORS env-driven.

30. **Vercel deployment** — frontend prerendered, env-driven API URL detection.

---

## 26. CHALLENGES FACED & SOLUTIONS

Be honest — examiners love hearing about real problems:

| Challenge | How We Solved It |
|---|---|
| **No ground-truth risk labels** | Generated rule-based labels with weighted scoring + dynamic percentile thresholds |
| **Unseen crime types in production** | 8-tier keyword inference + auto-save to severity_map.json |
| **Urdu OCR accuracy** | Multi-engine voting (EasyOCR + PaddleOCR + Tesseract + Gemini) + Urdu dictionary correction + 50+ thana whitelist |
| **VAPID key format errors** | Normalize to PEM + save as temp file before passing to pywebpush |
| **Free AI quota limits** | Cascade through Groq → OpenRouter → Gemini (each has different free tier) |
| **OSRM only returns 1 route** | Mathematically force via-points (perpendicular offset) to guarantee 3 routes |
| **Safety score zero-sparsity** | Laplace smoothing + minimum-volume stabilizer |
| **Heatmap performance** | Pre-aggregate counts in DB; client only renders 1000 highest-density points |
| **Browser push not firing** | Registered service worker at root scope; saved subscription with explicit `userVisibleOnly:true` |
| **Token expiry mid-request** | Refresh-token endpoint + axios interceptor to retry once |
| **CORS for production** | `ALLOWED_ORIGINS` env var read at boot + middleware + force-headers middleware |
| **Geocoding rate limits** | Local cache table `area_coordinates` + on-disk fuzzy matcher |
| **Time-zone inconsistencies** | All DB timestamps stored as UTC; frontend converts to user's TZ |
| **Severe Pillow 10 ANTIALIAS removal** | Set `Image.ANTIALIAS = Image.LANCZOS` shim at OCR module top |
| **Model file growing too large** | Use joblib with compression; load once at startup |

---

## 27. FUTURE SCOPE

Mention 4–5 ideas to show you've thought beyond the FYP:

1. **Mobile app** (React Native) with same API
2. **Multi-city expansion** — Karachi, Islamabad, Faisalabad (just need their crime data)
3. **Real-time CCTV integration** — face recognition for missing-person alerts
4. **Voice SOS** — keyword detection ("help me") triggers SOS
5. **Predict crime-time-of-day** — currently we predict risk-class; next step is exact time prediction
6. **Citizen reputation system** — verified citizen reports get higher trust score
7. **Police body-cam integration** — auto-OCR FIR while officer is filling it
8. **Multilingual support** — full Urdu UI in addition to English
9. **Offline mode** — cache last-seen heatmap so app works without internet
10. **Federated learning** — train models city-wide without centralizing private data

---

## 28. CONCLUSION & DEMO TIPS

### 28.1 Closing Pitch
*"CrimeVision is more than a dashboard — it's a complete safety ecosystem combining 3 ML models, multi-engine OCR, real-time geolocation, multi-channel alerts, a community network, an emergency SOS, and a complete admin / super-admin governance layer. We built it to be free, scalable, and immediately usable in any Pakistani city."*

### 28.2 Live Demo Order (12 minutes)
1. **Open public site** → click Crime Map → show heatmap
2. **Login as user** → show dashboard cards (safety score, risk factors)
3. **Plan a route** in AI Route Analysis (Johar Town → Anarkali at 9 PM) → show 3 routes ranked
4. **Enable browser notifications** → show subscribe flow
5. **Trigger an alert** (admin presses "Test Alert") → show real-time browser push
6. **Login as admin** → upload a sample FIR image → show OCR extraction in real-time
7. **Generate a PDF report** → download
8. **Login as super-admin** → show audit logs + PPC management → run AI verification on one section

### 28.3 Q&A Preparation
Be ready for these questions:

- **"Why Random Forest?"** → handles mixed features, robust to outliers, gives feature importances, no preprocessing needed
- **"What's your model accuracy?"** → ~95% cross-validated (mention this is on rule-generated labels though)
- **"What if an area is brand new?"** → median fallback for area_freq + keyword severity
- **"How do you handle Urdu OCR?"** → 4-engine voting + Urdu dictionary correction
- **"Is this real-time?"** → APScheduler runs every 1–5 min; web push delivers in <1 sec
- **"Privacy?"** → Location tracking is opt-in; all toggles live in profile
- **"How do you scale?"** → MySQL with indexes, models loaded once at startup, stateless backend, deployable on any Python host
- **"Did you do user testing?"** → Mention any beta users / feedback you collected
- **"Why not use Google Maps Directions API?"** → Costs money; OSRM is free + open
- **"What's the difference between RF and Poisson models?"** → RF gives a class label, Poisson gives a probability that varies by exact day/hour

### 28.4 Things to Carry to the Demo
- Local copy of the working site (in case Wi-Fi is bad)
- A sample FIR image for the OCR demo
- Two test accounts (user + admin + super-admin)
- A mobile phone to demonstrate browser push notifications
- Backup slides with API endpoint counts and DB diagram

---

# QUICK CHEAT SHEET (Print This Page)

| Question Asked | One-Line Answer |
|---|---|
| What is the project? | AI-powered city safety platform with prediction, routing, alerts, OCR, and admin tools. |
| How many tables? | 42 tables in MySQL |
| How many endpoints? | 60+ FastAPI endpoints across 13 routers |
| ML models? | 3 — Random Forest classifier, Poisson probability, Rule-based route safety |
| Frontend? | React 18 + Vite + Leaflet + Chart.js |
| Backend? | Python + FastAPI + MySQL + APScheduler |
| OCR? | 4 engines (EasyOCR, PaddleOCR, Tesseract, Gemini) with voting + Urdu dictionary |
| Alerts? | Email + Browser Push (VAPID) + SMS, with cooldown + quiet hours |
| Auth? | JWT + bcrypt + 2FA + Google OAuth + email verification |
| Roles? | User / Admin / Super-Admin |
| Deployment? | Backend on Render, Frontend on Vercel |
| Background jobs? | 6+ scheduled jobs via APScheduler |
| AI providers? | Groq → OpenRouter → Gemini (free cascade) |
| Routing? | OSRM API + forced via-points for variety |
| Crime records? | ~25,000 in `crimes` table |
| Law sections? | ~18,000 in `law_sections` table |

---

**End of Presentation Guide**

Good luck with your defense! 🎯
