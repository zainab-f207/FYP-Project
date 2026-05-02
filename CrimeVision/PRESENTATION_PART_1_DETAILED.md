# CrimeVision — DETAILED PRESENTATION GUIDE (Part 1 of 2)

> This is **Part 1**: full project explanation in detail with simple words.
> **Part 2** (`PRESENTATION_PART_2_VIVA_QA.md`) contains 100+ viva questions and answers.
>
> **How to use:** Read each section out loud. Every paragraph is what you can actually say. Bold sentences are **definitions you should memorize verbatim** — examiners ask for these word-for-word.

---

# CHAPTER 1 — INTRODUCTION & PROBLEM CONTEXT

## 1.1 What is CrimeVision?

**Definition (memorize):** CrimeVision (also branded SafeVision) is a full-stack, AI-powered web platform that combines historical crime data, machine learning, real-time geolocation, multi-channel alerting, OCR-based FIR digitization, and a community safety network to help citizens, police officers, and city administrators make better safety decisions in real time.

In simple words: it is **one website** that does **eight big things at once**:

1. Shows a live map of crime hotspots in Lahore.
2. Predicts how dangerous any area will be on any future day and time.
3. Plans the **safest route** between two points, comparing 3 options by safety score.
4. Reads scanned Urdu/English FIR documents using OCR and saves them in the database.
5. Sends **real-time alerts** by email, browser push notifications, and SMS when a user enters a risky zone.
6. Provides **emergency SOS** with one-tap calling and patrol requests.
7. Lets neighbours form **community watch groups** and post local alerts.
8. Gives admins / super-admins a **complete control panel** with reports, audit logs, user management, and a verified PPC law database.

## 1.2 Why we built it (The Problem)

### Pain Point #1 — No public source of crime intelligence
In Pakistan, most crime data is locked inside paper FIRs at police stations. Citizens have no public tool to see "is my neighbourhood safe?" before they move there or before they go out at night.

### Pain Point #2 — Maps don't care about safety
Google Maps and Waze find the **fastest** route, not the **safest** one. A late-night route can pass through 4 different known-dangerous spots, and the maps will not warn you.

### Pain Point #3 — FIRs sit in cabinets
A paper FIR records date, time, area, and PPC sections — but because it is on paper, no one can search it, analyze it, or feed it to a model. We needed an **OCR pipeline** specifically designed for the Punjab Police FIR template, including Urdu text.

### Pain Point #4 — No early warning
When a crime happens, neighbours are not told. By the time the news reaches them through word-of-mouth, the criminal is already gone. We needed **push notifications** that arrive in seconds.

### Pain Point #5 — Police lack a single dashboard
Officers wanted one screen showing: where crimes cluster, which areas need patrol, recent FIRs, and statistics — all together.

## 1.3 Our Goal

**Memorize this sentence:** Our goal is to deliver a free, scalable, browser-based safety platform that turns historical crime records into actionable, real-time intelligence for everyone — not just law enforcement.

## 1.4 Project Scope (What We Did vs Did Not Do)

**In scope (what we built):**
- Web application (mobile-responsive React frontend + Python FastAPI backend)
- Three machine-learning models (Random Forest classifier, Poisson probability estimator, Rule-based route-safety scorer)
- Multi-engine OCR pipeline for FIRs
- Multi-channel alert system (email + browser push + SMS templates)
- Three role-based dashboards (User, Admin, Super-Admin)
- 42-table MySQL database
- 60+ REST API endpoints
- Background scheduler for automatic alerts and weekly reports
- Verified PPC law section database with AI cross-checking

**Out of scope (mention if asked):**
- Native mobile apps (web app is mobile-responsive instead)
- Live CCTV feed integration
- Voice / phone-call SOS (we use email + SMS instead)
- Multi-city deployment (designed for it, but trained on Lahore only)
- Encryption-at-rest beyond bcrypt password hashing

---

# CHAPTER 2 — TECHNOLOGY STACK (Why each tool was chosen)

## 2.1 Backend Technologies (the brain)

### 2.1.1 Python 3 + FastAPI 0.104
**Why Python?** It is the de-facto language for AI/ML. Every library we needed (scikit-learn, pandas, numpy, OpenCV, EasyOCR) is written in Python.

**Why FastAPI (and not Flask or Django)?**
- It is **async by default** — requests don't block each other.
- It uses **Pydantic schemas** for request/response → automatic validation and automatic Swagger documentation at `/docs`.
- It is benchmarked to be one of the fastest Python frameworks (close to Node.js / Go).
- Type hints in Python become real run-time validation.

### 2.1.2 Uvicorn
ASGI (Asynchronous Server Gateway Interface) server. **Memorize:** Uvicorn is what actually runs the FastAPI app — it accepts HTTP connections, hands them to FastAPI, and returns responses.

### 2.1.3 MySQL 8 + mysql-connector-python
- Relational, mature, free.
- Foreign keys + indexes give us fast joins across 42 tables.
- We also support **TiDB Cloud** (a MySQL-compatible cloud database) by adding SSL kwargs in `core/config.py`.

### 2.1.4 scikit-learn 1.4.2
The ML library. Used for: `RandomForestClassifier`, `StandardScaler`, `LabelEncoder`, `cross_val_score`, `StratifiedKFold`, `MinMaxScaler`, `classification_report`.

### 2.1.5 pandas + numpy
Data wrangling. Pandas is used for `DataFrame` operations during training; numpy for fast array maths in the Poisson predictor.

### 2.1.6 joblib
Serializes Python objects (our trained model and scaler) to `.pkl` files. Loaded once at server startup, reused for every prediction.

### 2.1.7 APScheduler (Advanced Python Scheduler)
A cron-like library that lives inside the FastAPI process. Runs background jobs every 1 minute, every 5 minutes, every Monday at 09:00, etc.

### 2.1.8 python-jose + passlib[bcrypt] + bcrypt
- python-jose creates and verifies JWT (JSON Web Tokens).
- passlib + bcrypt securely hashes passwords with a per-user salt and tunable cost factor.
- We use `bcrypt_sha256` scheme on top of `bcrypt` to safely accept passwords longer than 72 bytes (bcrypt's hard limit).

### 2.1.9 pyotp
Generates TOTP (Time-based One-Time Passwords) for 2FA. Compatible with Google Authenticator, Authy, Microsoft Authenticator.

### 2.1.10 pywebpush + cryptography
Handles VAPID-signed Web Push notifications. We use the `cryptography` library to convert between DER and PEM key formats because pywebpush expects PEM and our keys come in DER from the generator.

### 2.1.11 OCR Engines
- **EasyOCR** — neural-network OCR with built-in Urdu support (`['ur','en']`).
- **PaddleOCR** — Baidu's high-speed OCR.
- **pytesseract** — wrapper around Google's Tesseract.
- **google-genai (Gemini)** — vision LLM, used as the smart fallback for blurry images.
- **OpenRouter Mistral** — vision-LLM, last-resort.

We use 4 engines and **vote** on the result so no single engine's failure breaks the pipeline.

### 2.1.12 OpenCV (cv2) + Pillow (PIL)
Image preprocessing: grayscale conversion, CLAHE contrast enhancement, deskew, sharpen, region cropping.

### 2.1.13 reportlab + openpyxl
- reportlab: builds PDFs (with charts as images, branded headers, multi-page).
- openpyxl: builds Excel workbooks (multiple sheets, conditional formatting).

### 2.1.14 geopy
Wrapper around free geocoding services. We use Nominatim (OpenStreetMap) to convert area name → latitude/longitude.

### 2.1.15 OSRM (Open Source Routing Machine)
External service we call over HTTP. Returns possible routes between two GPS points. Free, public.

### 2.1.16 Free AI Providers (no billing)
- **Groq** (`llama-3.3-70b-versatile`) — fastest, 14,400 free requests/day.
- **OpenRouter** (`meta-llama/llama-3.1-8b-instruct:free`) — different infrastructure.
- **Google Gemini** (`gemini-1.5-flash`, `gemini-1.5-pro`) — for vision and text.

We chain them in fallback order so when one is rate-limited, the next provider takes over automatically.

## 2.2 Frontend Technologies (what users see)

### 2.2.1 React 18 + Vite 4
- React: component-based UI library; lets us build reusable `<Card />`, `<Modal />`, `<Map />` widgets.
- Vite: dev server with **hot module reload** (changes show in <100 ms) + production build that tree-shakes unused code.

### 2.2.2 react-router-dom 7
Client-side routing — `/dashboard`, `/login`, `/risk-prediction`, `/crime-map` are different "pages" without full reload.

### 2.2.3 Leaflet + react-leaflet
The map engine. Leaflet is the JavaScript library; react-leaflet wraps it as React components. We render OpenStreetMap tiles (free, no API key).

### 2.2.4 leaflet.heat
Plugin that turns a list of `[lat, lng, intensity]` points into a coloured heat layer. Used for the crime density heatmap.

### 2.2.5 leaflet-routing-machine + leaflet-polylinedecorator
Draws turn-by-turn route polylines with arrowheads. Powered by OSRM.

### 2.2.6 Chart.js 4 + react-chartjs-2
For bar / line / radar / doughnut charts in the dashboards.

### 2.2.7 Ant Design + Bootstrap 5
- Ant Design (`antd`): pre-styled tables, modals, forms, date pickers.
- Bootstrap 5: grid, buttons, utility classes.
We mix them because each has strengths the other lacks.

### 2.2.8 Axios
HTTP client. We add an interceptor that automatically attaches the JWT token from localStorage to every outgoing request, and another that catches `401 Unauthorized`, calls the refresh-token endpoint, retries once.

### 2.2.9 react-toastify
Toast popups (top-right corner) for success / error / info messages.

### 2.2.10 jspdf + html2canvas
Lets the user click "Save dashboard as PDF" — `html2canvas` screenshots the DOM, `jspdf` writes it into a PDF. Pure client-side, no server round-trip.

### 2.2.11 qrcode
Generates the QR code image shown when a user enables 2FA. They scan it with Google Authenticator.

## 2.3 Deployment

| Layer | Where | How |
|---|---|---|
| Backend | **Render.com** Python web service | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Frontend | **Vercel** static site | `vite build` → deployed to CDN |
| Database | Local MySQL during dev, TiDB Cloud in prod | SSL connection via env var |
| Env vars | `.env` file (local) and Render/Vercel dashboards (prod) | Loaded with `python-dotenv` |

---

# CHAPTER 3 — SYSTEM ARCHITECTURE

## 3.1 The Big Picture

```
┌──────────────────────────────────────────────────────────────────┐
│                  USER'S BROWSER (React + Service Worker)          │
│   • Dashboard UI    • Map        • Push receiver (sw.js)         │
└─────────────┬────────────────────────────────┬──────────────────┘
              │ HTTPS + JWT in headers          │ Push events
              ▼                                  ▲
┌──────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI on Render)                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Middleware: CORS, force-headers, JWT verification         │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  13 Routers (60+ endpoints)                                │  │
│  │  auth · crimes · alerts · admin · emergency · community    │  │
│  │  location · reports · admin_reports · analytics · law      │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Services Layer                                            │  │
│  │  • RouteSafetyAnalyzer (rule-based)                        │  │
│  │  • AIRouteSafetyAnalyzer (Poisson + RF)                    │  │
│  │  • MultiRouteCalculator (OSRM caller)                      │  │
│  │  • GeminiLawVerifier (Groq → OpenRouter → Gemini)          │  │
│  │  • AlertNotificationSystem (email + push + SMS)            │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  ML Layer                                                  │  │
│  │  • rf_model.pkl + scaler.pkl  (Random Forest)              │  │
│  │  • poisson_artifacts.json     (Poisson)                    │  │
│  │  • severity_map.json          (1-10 severity per crime)    │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  OCR Layer                                                 │  │
│  │  • FIRExtractor (EasyOCR + Paddle + Tesseract + Gemini)    │  │
│  │  • ImageHashLookup (cache for repeated FIRs)               │  │
│  │  • UrduLocationDictionary (50+ thanas + spell-fix)         │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Background Scheduler (APScheduler)                        │  │
│  │  • monitor_saved_locations  (every 5 min)                  │  │
│  │  • poll_new_incidents       (every 1 min)                  │  │
│  │  • dispatch_weekly_reports  (Monday 09:00)                 │  │
│  │  • cleanup_unverified_accounts (daily)                     │  │
│  │  • auto_retrain  (when 500+ new rows)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────┬──────────────┬───────────────────┬─────────────┬──────────┘
       │              │                    │             │
       ▼              ▼                    ▼             ▼
┌────────────┐  ┌────────────┐    ┌─────────────┐  ┌────────────┐
│   MySQL    │  │  External  │    │   SMTP      │  │ Web Push   │
│  42 tables │  │  • OSRM    │    │   Gmail     │  │  Service   │
│            │  │  • OSM     │    │             │  │ (browser)  │
│            │  │  • Groq    │    │             │  │            │
│            │  │  • Gemini  │    │             │  │            │
└────────────┘  └────────────┘    └─────────────┘  └────────────┘
```

## 3.2 Why this architecture is good

1. **Stateless backend:** every request carries its own JWT. The server stores zero session data. This means we can spin up 10 backend instances behind a load balancer and any of them can serve any request.
2. **Single source of truth:** all data lives in MySQL; no caching that can drift.
3. **Models loaded once:** at startup `joblib.load()` reads the .pkl files into memory. Every prediction is then ~5 ms (no disk I/O).
4. **Async I/O:** while one user is waiting for OSRM, the server can serve dozens of others.
5. **Service worker:** push notifications keep working even when the tab is closed.

## 3.3 Request flow (one example: "predict risk for Johar Town tomorrow at 9 PM")

1. User clicks "Predict" in the React dashboard.
2. React calls `axios.post("/api/predict-risk", {area, crime_type, date, time})`.
3. Axios attaches `Authorization: Bearer <jwt>` header.
4. CORS middleware accepts the cross-origin request.
5. FastAPI matches the route to `crimes.py → predict_risk()`.
6. Pydantic validates the body matches `PredictRiskRequest`.
7. JWT dependency verifies the token; returns the username.
8. The function calls `_poisson_predict(artifacts, area, crime_type, date_str, hour)`.
9. Poisson predictor looks up `pair_lambdas`, multiplies by day-of-week, month, hour multipliers.
10. Computes `P = 1 - e^(-λ)` → converts to risk percentage and risk level.
11. Builds JSON with: risk_level, risk_percentage, confidence, safest_hours, safest_days, safest_months, visit-time comparison.
12. FastAPI serializes the dict to JSON, adds CORS headers, returns 200.
13. Axios resolves the promise; React updates state; UI re-renders the card with new data.

Total time: typically **20-40 ms** server-side, dominated by the Poisson math (no DB call needed for prediction).

---

# CHAPTER 4 — THE DATABASE (42 Tables, Explained Plainly)

## 4.1 Database overview

**Memorize:** The database is MySQL 8.0, charset `utf8mb4` (so it stores Urdu and emojis), collation `utf8mb4_0900_ai_ci`. It contains 42 tables grouped into 10 logical domains: Auth, Crime, Alerts, Location, Community, Emergency, Law, Reports, Audit, Resources.

## 4.2 Core data flow

```
Police uploads FIR.jpg → OCR extracts (date, area, sections)
                                    ↓
                        crimes table (status='unverified')
                                    ↓
                       Random Forest predicts risk_level
                                    ↓
                Poisson predictor uses it for future queries
                                    ↓
        Background scheduler picks new rows → notifies users in radius
                                    ↓
                 alert_notifications + browser_notifications
```

## 4.3 Detailed table descriptions

### Domain A — User & Authentication (8 tables)

**`users_info` (master user table)** — every column explained:
- `id` (int PK) — surrogate key.
- `username` (varchar 50, unique) — display name in dashboard.
- `first_name`, `last_name` (varchar 50) — personal name.
- `email` (varchar 100, unique) — login + alert destination.
- `role` enum('user','admin','superadmin') — access level.
- `password_hash` (varchar 255) — bcrypt hash, never plain.
- `home_area`, `home_latitude`, `home_longitude` — saved home; alerts use this radius.
- `work_area`, `work_latitude`, `work_longitude` — same for work.
- `alert_radius` (int, default 5) — km radius for incident alerts.
- `profile_picture` (varchar 255) — relative path under `/profile_photos`.
- `permissions` (JSON) — fine-grained per-user permissions (admins).
- `last_login` (timestamp) + `failed_attempts` (int) — for brute-force protection.
- `two_factor_secret` (varchar 32) + `two_factor_enabled` (tinyint) — TOTP 2FA.
- `verification_status` enum + `verified_at` + `verified_by` — manual user verification (KYC-lite).
- `is_verified` (tinyint) — quick boolean for "email confirmed".
- `email_verification_token` + `token_expires_at` — magic-link verification.
- `password_reset_token` + `reset_token_expires_at` — password-reset flow.
- `alert_preferences` (JSON, default '{}') — channel preferences per category.
- `monitor_live_location` (tinyint) — whether the system tracks them.
- `notification_preferences` (JSON, default '{"email":true,"sms":false}').
- `sms_carrier`, `sms_enabled`, `phone_number` — SMS gateway config.
- `is_active` (tinyint) — soft-delete flag.
- `browser_notifications_enabled` (tinyint) — VAPID subscription state.
- `is_logged_in` (tinyint) — admin can see who is online.
- `last_activity_at` (datetime) — heartbeat updates this every minute.
- `location_tracking_enabled` (tinyint) — opt-in privacy switch.
- `location_update_interval` (int, default 30 sec).
- `background_location_tracking` (tinyint) — keep tracking when tab inactive.
- `high_risk_alerts_only` (tinyint) — filter out low/medium alerts.
- `last_location_update` (timestamp).
- `location_source` enum('gps','ip','manual').
- `google_id` (varchar 255, unique) — Google OAuth user.
- `email_verified` (tinyint) — confirmed via link click.
- `otp_code` (varchar 10) + `otp_expires_at` — email OTP login.
- `password_must_change` (tinyint) — forced rotation after admin reset.
- `email_alerts_enabled` (tinyint) — master email switch.
- `weekly_reports_enabled`, `incident_alerts_enabled`, `live_alerts_enabled` (tinyint each) — granular alert toggles.

**`users` (legacy)** — older simpler user table; kept for backward compatibility with two community tables that reference `users.id`.

**`admins`** — separate from `users_info` historically; stores police officer accounts. Columns include `username`, `email`, `password_hash`, `department`, `permissions` (JSON), `phone`, `address`, `created_by`, `status`, `role`. Foreign-keyed by `admin_sessions`.

**`admin_sessions`** — active admin login sessions with `session_token`, `ip_address`, `user_agent`, `last_activity`, `is_active`. Lets a super-admin force-logout an admin.

**`login_attempts`** — every login try (success or failure) with `email`, `ip_address`, `attempt_time`, `success`. Used for brute-force lockout (e.g., "5 failures in 10 min from same IP → block 30 min").

**`user_activity_logs`** — every important user action stored as JSON. Lets admins reconstruct what a user did.

**`admin_messages`** — internal messaging between admins.

**`api_keys`** — for external integrations: stores `name`, `key_hash`, `permissions` JSON, `rate_limit`, `last_used`.

### Domain B — Crime Data (3 tables)

**`crimes` (the most important table — 25,500+ rows)**:
- `id` (int PK)
- `crime_date` (date) — when it happened
- `crime_time` (varchar 20) — string like "09:30 PM" because OCR returns various formats
- `area` (varchar 100) — police station / locality, e.g. "Iqbal Town"
- `crime_type` (varchar 1000) — detailed legal description, can include PPC sections
- `latitude`, `longitude` (decimal 9,6) — geocoded position
- `risk_level` enum('Low','Medium','High') — set by Random Forest
- `source` enum('admin','public','predicted') — who entered it
- `status` enum('verified','unverified') — admin must approve OCR-extracted records before they count
- `description` (text) — free-form notes
- `created_at` (timestamp)
- `area_urdu` (varchar 255) — original Urdu name
- `area_translit` (varchar 500) — Roman-Urdu transliteration

**`areas`** — master list of areas with canonical English name and coordinates. Used for `area_like_pattern()` SQL matching when names have minor differences.

**`area_coordinates`** — cached lat/lng per area name (avoids repeated Nominatim calls). Created automatically by `geocode_crime_area()`.

### Domain C — Alert System (8 tables)

**`alert_notifications`** — every alert that was sent to a user, with channels (email_sent, sms_sent), success_status, safety_score at trigger time, risk_level, high_risk_count, error_details. Used for the "Alerts" tab in the dashboard.

**`alert_subscriptions`** — what alert types each user wants to receive: `alert_types` JSON list, `areas` JSON list, `radius` float, `notification_types` JSON, `is_active`.

**`browser_push_subscriptions`** — VAPID subscription per user: `endpoint` (long URL to push service), `p256dh` (encryption key), `auth` (auth token). Used by `pywebpush` to send.

**`browser_notifications`** — stored notification records so the user can see them in the dashboard's bell icon. Includes `is_read`, `notification_data` JSON.

**`comprehensive_alerts`** — multi-channel tracker: did email succeed? did SMS succeed? did browser push succeed?

**`notification_logs`** — granular log of each notification attempt with success boolean and error_message.

**`notifications`** — system-wide notification queue (admin → user broadcast).

**`user_alert_preferences`** — quiet hours start/end, alert radius, preferred areas JSON, crime type filters JSON, risk level filters JSON.

### Domain D — Location & Safety (4 tables)

**`user_location_history`** — GPS pings: lat, lng, accuracy, address, risk_level, safety_score, accuracy_score, device_type, client_ip, alert_triggered, location_source. Lets us replay where a user was on any day.

**`user_locations`** — saved favourite locations (e.g., friends' houses).

**`system_alerts`** — admin broadcast warnings to all citizens with `alert_type`, `area`, `severity`, `target_audience`, `expires_at`, `is_active`.

**`user_alerts`** — per-user alert inbox that the dashboard shows. `is_read` tracks unread count.

### Domain E — Community (5 tables)

**`community_alerts`** — alerts created by users (warning, info, emergency, safety) with severity, area, lat/lng, radius_km, expires_at, view_count.

**`community_incident_reports`** — citizen-submitted reports. Status flow: reported → investigating → resolved → closed. Can be assigned to a watch group.

**`community_activity_log`** — audit trail for community actions: joined_group, left_group, reported_incident, created_alert, downloaded_resource, made_connection, requested_patrol.

**`neighborhood_watch_groups`** — community-level watch units: name, area, radius_km (default 2km), max_members (default 50), created_by.

**`group_members`** — join-table linking users to groups with `role` (member/moderator/admin). UNIQUE constraint prevents double-joining.

### Domain F — Emergency (2 tables)

**`emergency_calls`** — every SOS call: contact_name, contact_number, caller_location_lat/lng, caller_address, call_timestamp, user_id, emergency_type (police/ambulance/fire/general), status.

**`patrol_requests`** — citizen patrol requests: latitude, longitude, urgency (low/medium/high), description, status (pending/assigned/completed/cancelled), assigned_to, responded_at, completed_at.

### Domain G — Law Database (2 tables)

**`law_sections`** (18,025 rows) — every PPC/ATA/CNSA/PECA/ARMS/HUDOOD/EXPLOSIVE section. Columns include `law_type`, `section_number`, `english_title`, `chapter`, `source`, `verified_by`, `verified_at`, `is_verified`, `ai_response` (TEXT), `ai_model`, `last_ai_check`. Unique constraint on (law_type, section_number) prevents duplicates.

**`law_sections_audit`** — change log: action, old_title, new_title, changed_by, change_reason, created_at. Forensics-ready.

### Domain H — Reports (3 tables)

**`report_history`** — old report records: report_type, report_name, format (pdf/excel/csv), generated_by, file_path, file_size, status, filters JSON.

**`reports`** — newer flat report registry: title, type, format, file_path, file_size, status, parameters JSON.

**`scheduled_reports`** — recurring reports: schedule (`daily`, `weekly`, `monthly`), recipients JSON, next_run, last_run, status.

### Domain I — Governance & Audit (4 tables)

**`audit_logs`** — admin-write audit: admin_username, action, target_type, target_id, details JSON, ip_address, user_agent. Append-only.

**`approval_requests`** — when an admin tries a sensitive action (delete user, change role, modify settings) it goes here as `pending`. A super-admin approves or rejects. Columns: action_type, target_type, target_id, request_data JSON, status, reviewed_by, review_notes.

**`system_logs`** — generic application logs (errors, warnings, info).

**`system_settings`** — global key-value config: setting_key (PK), setting_value (text), category. Examples: `alert_threshold`, `notification_radius`, `admin_session_timeout`, `alert_last_30_window_days`, `model_version`, `email_template_brand`.

### Domain J — Safety Resources (3 tables)

**`safety_resources`** — safety guides / PDFs uploaded by admins: title, description, resource_type (guide/protocol/training/toolkit/article), category, content, file_path, mime_type, download_count.

**`resource_downloads`** — tracking who downloaded what (UNIQUE on user_id+resource_id so each user is counted once).

**`safety_network_connections`** — friend / neighbour connections: requester_id, target_id, connection_type (neighbour/authority/emergency_contact), status (pending/accepted/declined/blocked).

## 4.4 Indexes (why queries are fast)

We added more than 100 indexes. Examples:
- `crimes.created_at` — for "list newest crimes"
- `crimes.area` (implicit via PK) + `area_translit` — fuzzy match
- `user_location_history.(user_id, created_at)` — composite for history queries
- `audit_logs.action`, `audit_logs.admin_username`, `audit_logs.created_at`
- `alert_notifications.user_id` (FK) — to find a user's alerts
- `users_info.email_verification_token`, `users_info.password_reset_token` — token lookups
- `law_sections.(law_type, section_number)` UNIQUE — prevents duplicates and gives O(log n) lookup

## 4.5 Foreign keys & cascade rules

Most child tables use `ON DELETE CASCADE` (e.g., when a user is deleted, their alerts and locations also delete) but some use `ON DELETE SET NULL` (e.g., `community_alerts.created_by` → NULL when the creator is deleted but the alert survives because it's still useful info for the community).

---

# CHAPTER 5 — AUTHENTICATION & SECURITY (How Login Really Works)

## 5.1 The Six Layers of Authentication

**Memorize:** CrimeVision has six layers of authentication and authorization: (1) bcrypt password hashing, (2) JWT access tokens, (3) JWT refresh tokens, (4) Two-factor authentication via TOTP, (5) Email-OTP fallback for 2FA recovery, (6) Google OAuth single sign-on. Plus role-based access control (user / admin / super-admin) and an approval workflow for destructive admin actions.

## 5.2 Registration flow (step by step)

1. User opens `/login` page → clicks **Register**.
2. Frontend opens the registration modal with fields: first name, last name, email, password, phone, agree-to-terms.
3. Submits to `POST /auth/register`.
4. Backend validates the email format, checks `users_info` for duplicates.
5. If new: hashes the password with bcrypt (`pwd_context.hash(password[:72])` — bcrypt hard-limits at 72 bytes; we truncate to avoid silent truncation bugs).
6. Generates a 32-byte random `email_verification_token` using `secrets.token_urlsafe(32)`.
7. Inserts into `users_info` with `is_verified=0`, `verification_status='pending'`, `token_expires_at=NOW()+24h`.
8. Sends a verification email with link `https://safevision.app/verify-email?token=<token>`.
9. Returns `200 OK` with message "Please check your email".

## 5.3 Email verification

1. User clicks the link.
2. Frontend route `/verify-email` reads the token from URL.
3. Calls `POST /auth/verify-email` with `{token}`.
4. Backend looks up the row WHERE `email_verification_token=%s AND token_expires_at > NOW()`.
5. If found: sets `is_verified=1`, `verification_status='verified'`, clears the token.
6. User can now log in.

## 5.4 Login flow (with 2FA)

1. User submits `email + password` to `POST /auth/login`.
2. Backend:
   - Inserts a row into `login_attempts` with `success=0` (we set 1 if successful below).
   - Looks up `users_info WHERE email=%s`.
   - Calls `pwd_context.verify(plain_password[:72], stored_hash)` → True/False.
   - If false: increment `failed_attempts`. If `failed_attempts >= 5` within 10 min → return `423 Locked` for 30 min.
3. If 2FA is enabled (`two_factor_enabled=1`):
   - Returns a partial response with `requires_2fa=true`, `temp_token=<short-lived JWT>`.
   - Frontend shows OTP screen.
   - User enters the 6-digit code from Google Authenticator.
   - Calls `POST /auth/verify-login-otp` with `{temp_token, otp_code}`.
   - Backend uses `pyotp.TOTP(user.two_factor_secret).verify(otp_code)`.
   - If valid: issues full access token + refresh token.
4. If 2FA is **not** enabled: issues access + refresh tokens directly.
5. Frontend saves both tokens in `localStorage`.

## 5.5 Token strategy (very important)

| Token | Lifetime | Stored In | Signed With |
|---|---|---|---|
| Access token | 30 days for users / 60 min for admins / 60 min for super-admins | `localStorage.access_token` | `SECRET_KEY` from `.env` |
| Refresh token | 90 days | `localStorage.refresh_token` | `REFRESH_SECRET_KEY` (different from access secret) |
| Email verification token | 24 hours | `users_info.email_verification_token` | random `secrets.token_urlsafe(32)` |
| Password reset token | 1 hour | `users_info.password_reset_token` | random `secrets.token_urlsafe(32)` |
| 2FA TOTP code | 30 seconds | n/a (computed by `pyotp` from secret) | shared secret in `users_info.two_factor_secret` |
| Email OTP login code | 10 minutes | `users_info.otp_code` | random 6-digit number |

**Key security decisions:**
- **Different secrets for access and refresh** — if access secret leaks, refresh tokens still work and we rotate the access secret.
- **Role-based token expiry from system_settings table** — super-admin can change `admin_session_timeout` without redeploying.
- **Short admin sessions (60 min)** — limits damage if an admin laptop is left unlocked.
- **Long user sessions (30 days)** — better UX for citizens.

## 5.6 2FA setup ceremony

1. User clicks "Enable 2FA" in profile.
2. Frontend calls `POST /auth/generate-2fa`.
3. Backend calls `pyotp.random_base32()` → 32-character secret.
4. Stores secret in DB but **does not enable** 2FA yet (`two_factor_enabled=0`).
5. Returns provisioning URI: `otpauth://totp/CrimeVision:zainwaseempgc1@gmail.com?secret=<S>&issuer=CrimeVision`.
6. Frontend uses `qrcode.toDataURL()` to render a QR code image.
7. User scans with Google Authenticator, gets a 6-digit code.
8. User types the code → `POST /auth/enable-2fa` with `{otp_code}`.
9. Backend verifies → if valid, sets `two_factor_enabled=1`.
10. Future logins now require the OTP step.

## 5.7 Password reset flow

1. User clicks "Forgot password" → enters email.
2. `POST /auth/forgot-password`.
3. Backend generates `password_reset_token`, stores it with 1-hour expiry, emails a link.
4. User clicks link → `/reset-password?token=...`.
5. Enters new password.
6. `POST /auth/reset-password` with `{token, new_password}`.
7. Backend verifies token + expiry, hashes new password, clears the token.

## 5.8 Google OAuth single sign-on

1. User clicks "Sign in with Google".
2. Google's library returns an `id_token` (a JWT signed by Google).
3. Frontend posts it to `POST /auth/google-login`.
4. Backend calls `id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)`.
5. If valid: extracts email, given_name, family_name, picture URL.
6. If user exists → log them in. If new → auto-register (downloads profile pic).
7. Returns the same access + refresh tokens as normal login.

## 5.9 Approval workflow (super-admin oversight)

Some admin actions are too dangerous to take alone:
- Deleting a user
- Bulk-changing user roles
- Modifying the system_settings table

These actions don't execute immediately. Instead the admin's request is inserted into `approval_requests` with `status='pending'`. The super-admin sees it in their "Pending Approvals" panel, can review the JSON `request_data`, then approves or rejects with a `review_notes` reason. Only after approval does the actual change happen.

## 5.10 Audit logs

Every admin write goes to `audit_logs` with:
- `admin_username` who did it
- `action` (e.g., "delete_user", "update_settings", "create_admin")
- `target_type` + `target_id` (which entity was affected)
- `details` JSON (full before/after state)
- `ip_address` + `user_agent`
- `created_at`

This is **append-only** — no UPDATE or DELETE allowed by application code. If you ever need forensic evidence, this table has it.

## 5.11 Other security tricks

- **Rate limiting** — `rate_limiting.py` puts caps on per-IP and per-user request counts.
- **CORS whitelist** — only the frontend origins listed in `ALLOWED_ORIGINS` env var are accepted.
- **Force-CORS middleware** — explicit headers added to every response (handles edge browsers).
- **Token cleanup** — `cleanupInvalidTokens()` runs at app load, strips malformed JWTs from localStorage.
- **CSRF protection** — JWT tokens in `Authorization` header (not cookies) inherently resist CSRF.
- **Password truncation safety** — we explicitly truncate passwords to 72 bytes before hashing because bcrypt silently truncates at 72; making it explicit prevents future bugs.
- **Login attempts table** — every failed attempt logged with IP for forensic analysis.

---

# CHAPTER 6 — MACHINE LEARNING MODEL #1: RANDOM FOREST

## 6.1 What problem it solves

**Memorize:** Given a crime context (area, crime type, date/time, location), the Random Forest classifier predicts whether the resulting risk class is **High**, **Medium**, or **Low**. It is used to label every row in the `crimes` table with a `risk_level` so that all downstream features (heatmap, dashboard cards, alerts) have consistent risk classification.

## 6.2 Why we picked Random Forest specifically

This question **always** comes up in viva. Here are 6 strong reasons:

1. **No preprocessing for mixed types.** Trees naturally handle numeric and (encoded) categorical features. We don't need one-hot encoding which would balloon our 11 features into hundreds.
2. **Robust to outliers.** A single decision tree might split badly on an outlier; the average of 200 trees smooths that out.
3. **Generalises to unseen data.** When we encounter a brand-new area, our `area_freq_median` fallback ensures the prediction still works.
4. **Feature importance for free.** `model.feature_importances_` tells us which features drive predictions — useful for explainability in a security app.
5. **Fast inference.** ~5 ms per prediction with 200 trees and depth 15.
6. **Handles class imbalance.** `class_weight='balanced'` automatically up-weights minority classes (we had skewed High/Medium/Low distribution).

## 6.3 The 11 input features (memorize these)

| # | Feature | Range | What it captures |
|---|---|---|---|
| 1 | `crime_severity` | 1–10 | How serious is the crime (murder=10, theft=5) |
| 2 | `hour` | 0–23 | Time of day (parsed from `crime_time`) |
| 3 | `day_of_week` | 0–6 | Mon=0 |
| 4 | `month` | 1–12 | Seasonal pattern |
| 5 | `is_weekend` | 0/1 | Friday & Saturday in our culture |
| 6 | `is_nighttime` | 0/1 | 1 if hour ∈ {22,23,0,1,2,3,4} |
| 7 | `time_risk` | 0–1 | Cosine peaking at 2 AM, smoothing daily cycle |
| 8 | `area_crime_frequency` | 0–1 | Share of all crimes that happen in this area |
| 9 | `area_freq_percentile` | 0–100 | Hotspot rank vs other areas |
| 10 | `latitude` | decimal | Geographic position |
| 11 | `longitude` | decimal | Geographic position |

## 6.4 The seven-step training pipeline

### Step 1 — Severity sync from law_sections
Before training, we **call `sync_severity_from_db()`** which:
- Queries `law_sections WHERE is_verified=1`
- For each verified section, derives a severity 1–10 from keywords in the title (murder→10, theft→5)
- Updates `severity_map.json`

This means every time a super-admin verifies a new PPC section through AI, the next training run learns the correct severity. **This is the closed loop between the law module and the ML module.**

### Step 2 — Load training data
```python
SELECT id, area, crime_type, crime_date, crime_time,
       latitude, longitude, risk_level
FROM crimes ORDER BY id
```
Returns ~25,500 rows into a pandas DataFrame.

### Step 3 — Build the combined severity map
- `manual_map` = the curated `severity_map.json` (human-reviewed values)
- `auto_map` = derived from rarity (rarer crime → higher severity, scaled 2–10 with `MinMaxScaler`)
- `combined = {**auto, **manual}` — manual values override auto

### Step 4 — Engineer features (call `engineer_features()`)
For each crime row:
1. Resolve severity using a 4-step priority chain:
   - Manual map → keyword inference → auto-derived → median fallback
2. Parse `crime_time` ("09:30 PM" / "21:30:00" / `datetime.time`) into integer hour
3. Compute `hour`, `day_of_week`, `month`, `is_weekend`, `is_nighttime`
4. Compute `time_risk = max(0, cos((hour - 2) × 2π / 24))`
5. Compute `area_crime_frequency = count(area) / total`
6. Compute `area_freq_percentile = (count of areas with freq ≤ this) / total × 100`
7. Output: 11 columns ready for the model

### Step 5 — Generate training labels (rule-based)
This is where we **invented** labels because the database had no ground-truth.

The composite risk score is:
```
score = 0.40 × normalized_severity
      + 0.25 × time_risk_norm
      + 0.25 × area_hotspot_rank
      + 0.10 × is_weekend
```
Where:
- `normalized_severity = clip((severity - 3) / 7, 0, 1)`
- `time_risk_norm`: 1.0 for late night, 0.65 for evening, 0.35 for commute, 0 for daytime
- `area_hotspot_rank = area_freq_percentile / 100`
- `is_weekend` contributes 0.10 if weekend else 0

Then **dynamic percentile thresholds**:
- Top 30% (score > 70th percentile) → **High**
- Bottom 25% (score ≤ 25th percentile) → **Low**
- Otherwise → **Medium**

**Why dynamic thresholds?** As new crime types and severities are added to the dataset, the absolute score distribution shifts. If we used fixed cutoffs (e.g. >0.7 → High), one training run might end up 90% Medium. Dynamic percentiles guarantee a balanced label distribution every run.

### Step 6 — Standard scaling
```python
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```
This shifts every feature to mean=0, std=1. Random Forest doesn't strictly need this, but consistency with future models is nice.

### Step 7 — Train the model
```python
model = RandomForestClassifier(
    n_estimators=200,        # 200 trees — stable predictions
    max_depth=15,            # prevent overfitting on 25k rows
    min_samples_leaf=10,     # require 10 rows per leaf — avoid memorizing
    class_weight='balanced', # auto-balance label distribution
    random_state=42,         # reproducible training
    n_jobs=-1                # use all CPU cores in parallel
)
model.fit(X_scaled, y)
```

### Step 8 — 5-fold stratified cross-validation
```python
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
```
**Stratified** means each fold has the same class proportions. We typically see **~95% accuracy** on the rule-based labels (this is high because the labels themselves came from a deterministic formula; the model is reverse-engineering the rule).

### Step 9 — Save artifacts
```
backend/app/crime_risk_model/models/
├── rf_model.pkl                 # the forest
├── scaler.pkl                   # the StandardScaler
├── model_artifacts.json         # severity map, area freq map, medians, classes, CV accuracy, training timestamp
├── kmeans_model.pkl             # legacy K-means (unused)
├── poisson_artifacts.json       # Poisson predictor
├── oov_counts.json              # out-of-vocabulary tracking
└── risk_mapping.json            # legacy mapping
```

### Step 10 — Backfill the database
```python
UPDATE crimes SET risk_level = %s WHERE id = %s
```
Runs `executemany()` to update every row's `risk_level` with the new prediction. Subsequent dashboard queries see the updated data immediately.

## 6.5 The 8-tier keyword severity system (a subtle but important trick)

When we encounter a crime type that is **not** in `severity_map.json`, we infer severity from keywords. This is essential because:
- New crime types appear via OCR every day
- We don't want to crash or default everything to "Medium"

The eight tiers, from most severe down:
- **Score 10** — life-threatening / extreme: murder, kill, qatl, massacre, acid, rape, terrorism, bomb, blast, beheading
- **Score 9** — serious violent / organised: kidnap, abduct, trafficking, ransom, dacoity, extortion, carjacking, honour killing, attempt to murder
- **Score 8** — violent assault / serious harm: assault, attack, grievous hurt, stab, shoot, gunshot, arson, fire, riot, weapon, explosive
- **Score 7** — causing hurt / robbery / drugs: robbery, snatch, drug, narcotic, smuggling, intimidate, blackmail, sexual harassment, stalking
- **Score 6** — burglary / corruption / fraud: burglary, house breaking, trespass, bribery, corruption, fraud, cyber, hacking, scam, domestic violence
- **Score 5** — property / financial: theft, stealing, pickpocket, shoplifting, cheating, forgery, counterfeit, embezzlement
- **Score 4** — minor / petty: vandalism, damage, mischief, defamation, slander, nuisance, loitering, gambling
- **Score 3** — trivial / regulatory: traffic, parking, signal, noise, littering, violation, minor

When a new crime type matches a keyword, we **auto-save** the inferred severity to `severity_map.json` so subsequent training runs treat it as known.

## 6.6 Inference path (production)

When a request comes in:
1. Load model + scaler + artifacts (cached in memory after first call).
2. Build a 1-row DataFrame from input.
3. Call `engineer_features()` — feeds severity_map and area_freq_map from artifacts (not recomputed).
4. `X_scaled = scaler.transform(X)`.
5. `prediction = model.predict(X_scaled)[0]` → "High" / "Medium" / "Low".
6. `probability = model.predict_proba(X_scaled)[0]` → e.g. `[0.82, 0.15, 0.03]`.
7. Return `{predicted_risk, risk_probability_per_class, raw_risk_score}`.

## 6.7 Auto-retrain trigger

`utils/auto_retrain.py` is called when:
- 500+ new crime rows have been added since last training, OR
- An admin manually clicks "Retrain Model" in the super-admin panel

Auto-retrain runs in a background thread (so the API stays responsive), then calls `reload_model()` to swap the in-memory model atomically.

## 6.8 Model watcher (OOV detection)

`utils/model_watcher.py` runs every minute:
- Counts crime types that appeared in `crimes` but NOT in `severity_map.json`
- Stores counts in `oov_counts.json`
- When count for a new type passes a threshold (e.g., 20 occurrences), flags it for super-admin review

This way, the system **never silently degrades** — it tells you when it's seeing things it wasn't trained on.

---

# CHAPTER 7 — MACHINE LEARNING MODEL #2: POISSON PROBABILITY ESTIMATOR

## 7.1 The fundamental problem RF couldn't solve

Random Forest gives a **class label** (High/Medium/Low). But citizens want to know:
- "What's the probability of a robbery in Gulberg next Tuesday at 9 PM specifically?"
- "Which day in the next 30 days is the safest to visit my aunt in Anarkali?"
- "Which **hour** is safer if I have to go to Iqbal Town tonight?"

A class label can't answer these. We need a **continuous probability** that varies with **date and hour**. Hence Poisson.

## 7.2 The math (explained simply)

**Memorize this paragraph for viva:** Crime occurrences follow a Poisson process. The probability of at least one event in a time window equals 1 minus e to the negative lambda, where lambda is the expected number of events per unit time. For our model, lambda is the historical average crimes per day for a specific area-and-crime-type combination, then multiplied by day-of-week, month, and hour multipliers learned from the data.

Formal:
```
P(≥1 crime today) = 1 - e^(-λ)

λ = base_λ × dow_mult × month_mult × hour_mult^2.2
```

**The hour-multiplier exponent (2.2)** is a trick we added because the raw smoothed multipliers cluster very close to 1.0 (because hour bucketing has 24 buckets and Laplace smoothing pulls everything toward 1/24). Raising them to the 2.2 power **amplifies** the differences so picking 9 PM vs 9 AM produces a visibly different risk percentage.

## 7.3 The artifact JSON (what gets saved)

When we train, we save **everything we need at inference** in `poisson_artifacts.json`:

| Key | Type | Description |
|---|---|---|
| `pair_lambdas` | dict[str → float] | Key `"area\|\|\|crime_type"` (lowercased), value = crimes/day |
| `area_lambdas` | dict[str → float] | Per-area total crimes/day |
| `crime_type_fractions` | dict[str → float] | Crime type's share of all crimes |
| `global_lambda` | float | Total crimes/day across all areas |
| `dow_multipliers` | dict[str → dict[str → float]] | Per pair, then per day-of-week (0..6) |
| `month_multipliers` | dict[str → dict[str → float]] | Per pair, then per month (1..12) |
| `area_dow_multipliers` | dict[str → dict[str → float]] | Per area only (fallback) |
| `area_month_multipliers` | dict[str → dict[str → float]] | Per area only (fallback) |
| `hour_multipliers` | dict[str → dict[str → float]] | Per pair, then per hour (0..23) |
| `area_hour_multipliers` | dict[str → dict[str → float]] | Per area only (fallback) |
| `known_areas` | list[str] | Areas seen in training |
| `known_crime_types` | list[str] | Crime types seen (lowercased) |
| `total_observation_days` | int | Distinct calendar dates in dataset |

## 7.4 Laplace smoothing (the trick for sparse data)

For day-of-week multipliers per (area, crime) we'd like to compute:
```
mult(d) = (count_on_day_d) / (total) / (1/7)
```
But many (area, crime, day) cells have **zero** observations. That would give multiplier = 0, which means probability=0, which is misleading.

So we add **+1 pseudo-count** to each bucket:
```
mult(d) = (count + 1) / (total + 7) / (1/7)
```
This guarantees no multiplier is ever 0, while preserving the relative ordering. Same for month (+1, /12) and hour (+1, /24).

## 7.5 Inference: the 5-tier confidence cascade

When a request comes in for `(area, crime_type, date)`:

1. **Tier 1 (confidence 0.90):** Both `area` AND `crime_type` AND the pair are in training data → use pair λ directly.
2. **Tier 2 (confidence 0.65):** Both individually known but never observed together → use `area_λ × crime_type_fraction`. Note added: "based on similar historical patterns".
3. **Tier 3 (confidence 0.45):** Known area, unknown crime type → use `area_λ × 0.05 × (severity/10)`. Note: "based on this area's overall patterns".
4. **Tier 4 (confidence 0.35):** Unknown area, known crime type → use `(global_λ / n_areas) × crime_type_fraction`. Note: "regional patterns".
5. **Tier 5 (confidence 0.25):** Both unknown → use `global_λ / n_areas × 0.05`. Note: "rare combination".

This means **the model never refuses to answer** — it always returns something with appropriate confidence.

## 7.6 Risk-level thresholds

After computing `P = 1 - e^(-λ_adjusted)`:
- `P > 0.80` → Critical
- `P > 0.50` → High
- `P > 0.25` → Medium
- otherwise → Low

## 7.7 Rich response (what /predict-risk returns)

Beyond a single risk percentage, the Poisson endpoint returns:
- `risk_level`, `risk_percentage`, `confidence`, `probability` (raw)
- `lambda` (raw rate, useful for debugging)
- `time_period` ("Morning"/"Afternoon"/"Evening"/"Night") — when hour given
- `safest_hours` — top 3 hours with lowest historical multiplier
- `riskiest_hours` — top 3 hours
- `hourly_risk_profile` — average risk per period (Morning/Afternoon/Evening/Night)
- `visit_time_comparison` — risk at 8AM, 2PM, 8PM, 11PM head-to-head
- `safest_days_of_week` — top 3 days
- `riskiest_day_of_week` — single most dangerous day
- `safest_months` — top 3 months
- `safest_upcoming_dates` — 3 lowest-risk dates in the next 30 days
- `is_estimated` — true if we used a fallback tier
- `note` / `message` — human-readable explanation

This gives the user **far more value** than a single number — they can plan their visit.

## 7.8 Area safety profile

`area_safety_profile(artifacts, area, date_str)` runs the prediction across all crime types for one area on one date and returns a sorted list. The dashboard shows "Top 5 risks for Gulberg today: theft 18%, snatching 12%, ...".

---

# CHAPTER 8 — MACHINE LEARNING MODEL #3: ROUTE SAFETY ANALYZER

## 8.1 Purpose

When a user enters "from Johar Town to Anarkali", the system fetches 3 candidate routes from OSRM, then **scores each one** for safety so the user can pick the safest, not just the fastest.

## 8.2 Two implementations exist

### 8.2.1 Rule-based analyzer (`route_safety_analyzer.py`)
A deterministic scoring function. **Predictable, explainable, fast.**

### 8.2.2 AI analyzer (`route_safety_analyzer_ai.py`)
Calls the Poisson model (primary) or Random Forest (fallback) for each sample point along the route. **Data-driven, more accurate when data exists.**

The endpoint `/api/crimes/analyze-route-safety-ai` uses the AI version; the rule-based one is a fallback for when models aren't loaded.

## 8.3 Rule-based scoring (every constant explained)

Start with **base score = 100**. Add bonuses, subtract deductions.

### Crime-related deductions (proportional to count near route):
- High-risk crime within 200m of route: −15 each
- Medium-risk crime: −8 each
- Low-risk crime: −3 each

### Crime threshold flags:
- ≥5 crimes nearby → `factors["crime_rate"] = "high"`
- ≥2 crimes → `factors["crime_rate"] = "medium"`
- otherwise → `"low"`

### Infrastructure deductions:
- Isolated road (residential, no main road nearby): −10
- Poor lighting (at night): −12
- Far from police station (>2 km): −8
- Far from hospital (>3 km): −5

### Infrastructure bonuses:
- Police within 500m: +10
- Hospital within 1 km: +8
- On a main / motorway road: +5
- Heavy traffic (criminals avoid crowds): +5
- Good lighting at night: +8

### Time multipliers (applied to crime deduction only):
- Late night (11 PM – 5 AM): crime deduction × 2.0
- Night (8 PM – 11 PM, 5 AM – 6 AM): crime deduction × 1.5
- Daytime: crime deduction × 1.0

### Final clamp & level:
- Score forced into `[10, 100]`.
- ≥80 → "Safe"
- 60–79 → "Moderate"
- 40–59 → "Risky"
- <40 → "Dangerous"

## 8.4 AI-based scoring (`route_safety_analyzer_ai.py`)

1. Take 10–20 sample points along the route polyline (every 250m).
2. For each point, find the nearest area name (geocoder).
3. Call `predict_point_risk(area, dominant_crime_type, today_date)`.
4. Combine point scores: `route_score = 100 - average(risk_percentages) - 5 × count_high_risk_points`.
5. Generate alerts for each high-risk point: "passes near 3 high-risk areas — consider alternative".

## 8.5 Multi-route generation (`multi_route_calculator.py`)

OSRM's free public API returns 1–3 alternatives. Sometimes only 1.

**Trick we invented:** to **guarantee 3 routes**, when OSRM returns fewer, we mathematically force variety:
1. Compute the start→end vector `(d_lat, d_lng)`.
2. Compute perpendicular vectors: `(-d_lng, d_lat)` and `(d_lng, -d_lat)`.
3. Apply offsets `[0.015, -0.015, 0.030]` (≈1.5km, 1.5km opposite, 3km).
4. For each offset, compute a via-point at `(midpoint + scale × perp_vector)`.
5. Re-call OSRM as `start → via → end`.
6. Now we have 3+ definitely-different routes.

This single trick massively improves the user experience because before this, half the time we showed only one option.

## 8.6 Route comparison response

```json
{
  "routes": [
    {
      "id": "osrm_alt_0",
      "distance_km": 8.4, "duration_min": 22,
      "safety_score": 84.5, "safety_level": "Safe",
      "alerts": [], "factors": {...},
      "geometry": [...lat/lng pairs...]
    },
    { "id": "via_left", "distance_km": 9.1, ... },
    { "id": "via_right", ... }
  ],
  "recommended_route_id": "osrm_alt_0",
  "fastest_route_id": "via_right",
  "comparison": {...}
}
```

The frontend draws all three on the map in different colours (green = safest, yellow = middle, red = fastest-but-risky).

---

# CHAPTER 9 — OCR PIPELINE FOR PUNJAB POLICE FIRS

## 9.1 Why this is hard

Pakistani FIRs are scanned paper documents with:
- **Mixed Urdu and English** text
- **Handwritten** annotations
- **Fixed table template** (each cell has a known purpose)
- **Often blurry** photocopies
- **Diacritics (tashkeel)** that confuse OCR engines

A naive single-engine OCR fails ~40% of the time. We need a robust, multi-stage pipeline.

## 9.2 Pipeline architecture (top-down)

```
[ Police uploads FIR.jpg via Admin Dashboard OCR Panel ]
          ↓
   1. Image hash check (image_hash_lookup.py)
          → if hit: return cached extraction (sub-millisecond)
          ↓ miss
   2. Image preprocessing (FIRImagePreprocessor)
      • Grayscale + CLAHE
      • Deskew
      • Sharpen
          ↓
   3. Region cropping (FIRRegions)
      • HEADER_TOP/BOTTOM/LEFT/RIGHT
      • DATE_TIME_ROW
      • THANA region
      • SECTIONS region
      • DESCRIPTION region
          ↓
   4. Multi-engine OCR (in parallel)
      • EasyOCR (Urdu+English)
      • PaddleOCR
      • Tesseract
      • Gemini Vision (LLM)
          ↓
   5. Result voting / scoring
          ↓
   6. Field-specific extractors:
      • extract_thana()      ← whitelist match against 50+ known thanas
      • extract_date()       ← regex DD/MM/YYYY
      • extract_time()       ← regex with AM/PM
      • extract_sections()   ← regex 302/324, etc.
          ↓
   7. Validation + Urdu dictionary correction
      • Reject diacritics
      • Reject repeated chars
      • Reject Urdu digits in location text
      • Fuzzy-match to known thanas
          ↓
   8. Geocode (geocode_crime_area)
      • Local DB lookup
      • Nominatim
      • Fuzzy match against crimes table
          ↓
   9. Insert into crimes table (status='unverified')
          ↓
  10. Run Random Forest → set risk_level
          ↓
  11. Admin reviews → approves → status='verified'
```

## 9.3 Image hashing for cache

`image_hash_lookup.py` computes a **perceptual hash** (pHash) of the uploaded image and looks it up in a JSON dictionary mapping hashes to known-good extractions. If the same FIR is uploaded again (very common during demos and testing), we skip OCR completely.

## 9.4 Preprocessing tricks

```python
img = cv2.imread(...)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# CLAHE = Contrast-Limited Adaptive Histogram Equalization
# Local contrast enhancement; better than global histogram equalization
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)

# Deskew using moments (compute angle from line of black pixels)
coords = np.column_stack(np.where(enhanced < 128))
angle = cv2.minAreaRect(coords)[-1]
if angle < -45: angle = -(90 + angle)
else: angle = -angle
M = cv2.getRotationMatrix2D(center, angle, 1.0)
deskewed = cv2.warpAffine(enhanced, M, ...)

# Sharpen
kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
sharpened = cv2.filter2D(deskewed, -1, kernel)
```

## 9.5 Region cropping (FIRRegions)

The Punjab Police FIR has a **fixed template**. We hardcoded the percentage coordinates of each cell:

| Field | Top % | Bottom % | Left % | Right % |
|---|---|---|---|---|
| HEADER (FIR number) | 8 | 16 | 10 | 90 |
| DATE_TIME_ROW | (varies) | | | |
| THANA (Row 4) | 36 | 48 | 2 | 98 |
| THANA (Row 2 backup) | 17 | 26 | 2 | 70 |
| HEADER_THANA_BACKUP | 2 | 12 | 30 | 80 |
| SECTIONS_ROW | (varies) | | | |
| DESCRIPTION_ROW | (varies) | | | |

For each field, we crop the region **and only run OCR on that crop** — much faster and more accurate than running OCR on the whole image.

## 9.6 Multi-engine voting (the key trick)

For each region we run **all four engines in parallel** and:
- If 3+ engines agree → use that result with high confidence.
- If 2 agree → use it with medium confidence.
- If all four disagree → call Gemini Vision LLM as the deciding judge.
- If still unclear → return empty string (don't fabricate).

## 9.7 Thana extraction (the crown jewel)

Most challenging field because thanas are written in **Urdu** with many spelling variants. We hardcoded a **whitelist of 50+ Lahore thanas** with all observed Urdu and English spellings, e.g.:

```python
KNOWN_THANAS_MAP = {
    'شالیمار': 'Shalimar', 'شالامار': 'Shalimar',
    'شالاارے': 'Shalimar', 'شالاار': 'Shalimar',
    ...
    'گلشن راوی': 'Gulshan Ravi',
    'اقبال ٹاؤن': 'Iqbal Town',
    'ماڈل ٹاؤن': 'Model Town',
    'گلبرگ': 'Gulberg',
    'جوہر ٹاؤن': 'Johar Town',
    ...
}
```

Then for each region, we scan the OCR output and check if any of the patterns (case-insensitive substring match) are present. This guarantees we **only return real thanas** and never fabricate one from garbled text.

## 9.8 Validation rules (anti-garbage)

Even valid OCR can return junk. We reject text that:
- Contains Arabic diacritics (tashkeel: ً–ْ) — printed thanas don't have these
- Has 2+ consecutive repeated characters (e.g., "اا", "سس") — sign of OCR misreading
- Contains Urdu/Arabic digits (۰-۹) — never appear in valid location names
- Has too many short words (≥55% words are ≤2 chars)
- Has any word longer than 10 characters
- Has space ratio > 35%
- Has fewer than 5 Urdu chars and no whitelist keyword

## 9.9 Urdu location dictionary

`urdu_location_dictionary.py` provides:
- `correct_location_text()` — fuzzy correction (e.g. "ٹاؤن شالیمار" → "شالیمار ٹاؤن")
- `_normalize_text()` — strips tashkeel, normalizes Yeh and Heh variants

## 9.10 Geocoding

After we have a clean English thana name (e.g. "Iqbal Town"):
1. Look up `area_coordinates` table for cached lat/lng → return if found.
2. Look up the `crimes` table for any prior crime in this area → take its mean lat/lng.
3. Call Nominatim: `https://nominatim.openstreetmap.org/search?q=Iqbal+Town,Lahore,Pakistan&format=json`.
4. Cache the result in `area_coordinates`.

## 9.11 Why Gemini is in the chain

Pure CV-based OCR struggles with very blurry photos. Gemini 1.5 Flash is a vision-language model — we send it the image with a prompt like "Extract the thana name from this Urdu FIR. Return only the English equivalent." and it returns plain text.

We added Gemini as a **last resort** rather than first because:
- It costs API quota
- It's slower (~2 s) than EasyOCR (~200 ms)
- For most clean images, EasyOCR is enough

This cascade keeps us free / fast in the common case and only spends LLM quota on the hard cases.

---

# CHAPTER 10 — ALERT NOTIFICATION SYSTEM

## 10.1 Three channels, three alert categories

### Alert categories
1. **Live Alert** — user is currently in a high-risk zone (triggered by location update).
2. **Incident Alert** — a new crime was added near user's saved area.
3. **Weekly Safety Report** — Monday morning digest of last week's stats.

### Channels
1. **Email** — fully-styled HTML templates from `email_templates.py` (1000+ lines).
2. **Browser Push** — via VAPID + service worker.
3. **SMS** — uses email-to-SMS gateway (e.g. `<phone>@txt.att.net`) since real SMS APIs cost money.

## 10.2 The `AlertNotificationSystem` class

A central class with methods:
- `send_email_alert(alert, user_data)` — builds HTML, calls smtplib.
- `send_browser_notification(alert, user_data)` — pywebpush call with VAPID auth.
- `send_sms_alert(alert, user_data)` — formats via `sms_templates`, sends via SMS gateway email.
- `get_real_safety_data(lat, lng, radius_km)` — queries `crimes` table, computes unified risk summary.
- `store_browser_notification(...)` — saves notification to DB so user sees it in dashboard bell.

## 10.3 Triggering an alert (full pipeline)

When `monitor_saved_locations()` (the 5-min background job) finds a new high-risk crime within a user's radius:

1. Build a `RiskZoneAlert` Pydantic object with: user_id, latitude, longitude, address, alert_type, severity, time_risk_label, etc.
2. Call `get_real_safety_data(lat, lng, 1.0)` — runs the heavy SQL query computing all scores.
3. Compute unified risk summary using the formula:
   ```
   risk = 0.35×volume + 0.15×severity + 0.30×recency + 0.10×trend + 0.10×time
   safety = 100 - risk
   ```
4. Determine severity: critical (≥81%), high (≥51%), medium (≥21%), low.
5. Look up user's `alert_preferences` JSON to see which channels they want.
6. Check **cooldown cache** — if user got an alert for this zone in last 60 min, skip.
7. Check **quiet hours** — if current time is in user's quiet hours, defer.
8. For each enabled channel:
   - Email → render HTML template, smtplib.sendmail
   - Browser → pywebpush.send with VAPID
   - SMS → format short text, send via SMS gateway email
9. Insert success/failure into `notification_logs`, `alert_notifications`, `comprehensive_alerts`.
10. Update `last_activity_at` on user row.

## 10.4 VAPID web push (the hardest engineering challenge)

### What VAPID is
**Voluntary Application Server Identification.** A scheme where each app generates a public/private key pair (P-256 ECDH curve). The public key is sent to the browser when subscribing; the private key signs every push. The browser's push service (FCM/Mozilla autopush) verifies the signature so that only **your** server can push to **your** subscribers.

### Subscription flow
1. Frontend asks `Notification.requestPermission()` → user clicks "Allow".
2. Frontend calls `navigator.serviceWorker.register('/sw.js')`.
3. Frontend calls `registration.pushManager.subscribe({applicationServerKey: <vapid_public_key_bytes>, userVisibleOnly: true})`.
4. Browser returns a `PushSubscription` with `endpoint` (a long URL), `keys.p256dh`, `keys.auth`.
5. Frontend posts these to `/api/alerts/browser-notifications/subscribe`.
6. Backend stores in `browser_push_subscriptions` table.

### Sending flow
1. Backend wants to send a push.
2. Builds a JSON payload (`{title, body, icon, tag, data:{...}}`).
3. Calls `pywebpush.webpush(subscription_info, data, vapid_private_key, vapid_claims)`.
4. pywebpush:
   - Encrypts payload with the user's `p256dh` + `auth`.
   - Signs the request with VAPID private key.
   - POSTs to the `endpoint` URL.
5. Browser's push service forwards to the device.
6. Service worker `sw.js` receives the push event, calls `self.registration.showNotification(title, options)`.
7. User sees the notification.

### Key format gotcha (the bug we hit)
pywebpush wants the VAPID private key in **PEM** format. Most generators produce **DER**. The fix in `alert_notifications.py`:

```python
def _normalize_vapid_private_key(self, key_str):
    if "BEGIN PRIVATE KEY" in key_str:
        return key_str  # already PEM
    # Otherwise: it's base64-DER
    der = base64.urlsafe_b64decode(key_str)
    pk = load_der_private_key(der, password=None)
    pem = pk.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode()
    return pem
```

And then we **save the PEM as a temp file** because pywebpush's `from_string` is buggy in some versions:
```python
fd, path = tempfile.mkstemp(prefix="safevision_vapid_", suffix=".pem")
with open(path, 'w') as f: f.write(pem)
# pywebpush reads from `path` reliably
```

## 10.5 Email templates

`email_templates.py` is over 1000 lines. Each alert type has its own HTML template with:
- Branded SafeVision header
- User name (personalised)
- Risk score visual bar (red/yellow/green)
- Top crime types list (with percentages)
- Map preview
- "View dashboard" CTA button
- Unsubscribe footer

Templates use Python f-strings to inject values; no template engine needed.

## 10.6 Smart deduplication rules

- **Cooldown:** `alert_cooldown_cache: Dict[str, datetime]` keyed by `f"{user_id}:{zone_hash}"`. If last alert for same key was <60 min ago, skip.
- **Quiet hours:** If user's `quiet_hours_start <= now < quiet_hours_end`, defer the alert (don't drop it).
- **High-risk-only filter:** If user has `high_risk_alerts_only=1`, skip Medium/Low alerts entirely.
- **Channel preferences:** If user has `email_alerts_enabled=0`, skip email channel.

## 10.7 Body-text generation (the trick that makes alerts useful)

Instead of generic text, we **vary the message** based on context:

If user just **moved** into the zone (location-trigger):
- "🚨 Entered High-Risk Zone — Recent high-risk incidents detected near your location in {area}. Stay alert — especially at {time_str}."

If alert is from a **new incident**:
- "🚨 {Crime Type} Near Your {Location_label} — A {severity}-severity {crime} was just reported in {area}. Risk is higher at {time_str}."

If user just **approached** a historically risky zone (no recent crime):
- "🚨 High-Risk Area Nearby — You are within {radius_km} km of a historically high-risk zone in {area}."

We also include **deep-link buttons**:
- `action_map_url` → opens dashboard map at the area
- `action_route_url` → opens route planner avoiding the area

## 10.8 The unified risk formula (used everywhere)

`calculate_unified_risk_summary(stats, observation_days)` produces a consistent risk score across the dashboard, alerts, predictions, and admin views. Formula:

```
risk = 0.35 × volume_score
     + 0.15 × severity_score
     + 0.30 × recency_score
     + 0.10 × trend_score
     + 0.10 × time_risk_score

safety = 100 - risk
```

Where:
- `volume_score = 0.6 × Poisson(crimes/day) + 0.4 × log_scaled_count`
- `severity_score = ((weighted_avg(severity) - 2) / 6) × 100`
- `recency_score`: 30-day vs 90-day concentration
- `trend_score`: recent half vs older half (declining = safer)
- `time_risk_score`: 85 at night (10 PM-4 AM), 70 evening, 45 morning, 35 daytime, +5 weekend

**Adaptive decay** — when there's no crime in last 90 days:
- 1000+ historical crimes or 50+ high-risk → 0.85× decay (preserves history)
- 100–999 crimes → 0.70× decay
- <100 crimes → 0.60× decay
This avoids "Iqbal Town suddenly looks safe" because there's been no crime this month.

**Sparse-data stabilizer** — for areas with very few crimes, blend toward neutral to avoid wild scores from one event:
```
required = max(3, 30/365 × observation_days)
α = n / required (clipped to [0,1])
stabilized = α × raw_score + (1-α) × 0
```

## 10.9 Quiet hours enforcement

When a user sets quiet hours (e.g., 22:00–07:00), the alert system:
1. Checks current time vs quiet hours.
2. If inside quiet hours → push the alert into a **deferred queue**.
3. At the next "outside quiet hours" tick, the scheduler re-evaluates and sends.
4. Alerts older than 4 hours are dropped (no point sending stale alerts).

---

That's Part 1 done. Continue to **PRESENTATION_PART_2_VIVA_QA.md** for:
- Chapter 11–18 (Frontend dashboards, Reports, Community, Emergency, Background jobs)
- 100+ viva questions and answers
- Demo script
- Cheat sheets

