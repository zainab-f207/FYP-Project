# SafeVision — FYP Defense Speaker Script

Keyed to **`SafeVision_FYP_Defense (16).pptx`** (28 slides).
For every slide you get:

- **SAY** — what to read out loud (~45–60 sec).
- **KEY NUMBERS** — figures to memorise so you can cite them confidently.
- **GAP** — what the slide leaves unsaid, and a one-line answer if asked.
- **LIKELY Q&A** — short, evaluator-style questions with code-grounded answers.

Tip: paste each slide's **SAY** block into PowerPoint → View → Notes Page for that slide.

---

## Slide 1 — Title / Cover

**SAY**
Good morning. Our final year project is **SafeVision** — *Spatial Visualytics of Reported Incidents in Lahore*. It is an AI-powered public-safety platform built specifically for our city. In one sentence: we use real Punjab Police crime data and machine learning to predict where crime is likely, recommend the safer route between two points, automatically extract data from scanned FIRs in Urdu, and push real-time alerts to nearby citizens. The system is already deployed — backend on Render, frontend on Vercel — so everything you will see today is running on production infrastructure, not a local demo. I am Zainab Fayyaz, with me are Zaid Waseem and Akmal Naseer. Our supervisor is Sir Afraz Hayat Malik.

**KEY NUMBERS**
- Production URL: `safevision-backend-ye2i.onrender.com`
- Team: 3 members; Supervisor: Sir Afraz Hayat Malik (UET Lahore).

**GAP**
The slide does not state the live frontend URL. If asked: the React frontend is hosted on Vercel and connects to the FastAPI backend at the URL on the slide.

**LIKELY Q&A**
- *Why "SafeVision" and not "CrimeVision"?* — CrimeVision is the internal repo / module name, SafeVision is the user-facing product brand. We split them so the citizen UI never feels like a "police tool".
- *Is this live right now?* — Yes; the backend is on Render, the database is TiDB Cloud, and the SPA is on Vercel.

---

## Slide 2 — Agenda

**SAY**
Today's walk-through has ten parts. We start with the problem we are solving — why Lahore needs predictive policing. Then the project's identity in one line, the system architecture, the database design with 37 tables across 6 domains, our authentication and security stack, the machine learning pipeline with three models — a modern Random Forest, a Poisson probability estimator, and a legacy Random Forest fallback — the AI route safety analyser, our multi-engine OCR pipeline that extracts 4 fields from scanned FIRs, the alerts and background jobs, and finally results, demo and future work. The whole presentation is grounded in code we will reference by file and line number throughout.

**KEY NUMBERS**
- 10 sections, 28 slides total.

**GAP / LIKELY Q&A**
- *Time?* — Plan ~1.5 minutes per slide → roughly 40 minutes plus demo.

---

## Slide 3 — The Problem

**SAY**
Lahore is a city of about 14 million people spread over 1,772 square kilometres, divided into police thanas. Right now policing is **reactive** — citizens find out about incidents from quarterly press releases or from the news, never *before* they leave home. There is no per-area, per-hour view of risk available to a normal resident. On top of that, FIRs — the official First Information Reports — are filed on **paper in Urdu**. That means today's crime data sits in static documents for weeks, never feeding back into tomorrow's risk model. Foreign apps like Citizen or Noonlight do not solve this either: they were designed for US cities, they don't understand Urdu place names, Lahore's thanas, or the Pakistan Penal Code. SafeVision was built to close all four of these gaps.

**KEY NUMBERS**
- Population: 14 M+ • Area: 1,772 km² • FIR digitisation today: 0 %.

**GAP**
Slide says "0% digital" — be ready to defend it: Punjab Police FIRs *are* logged in some internal CRMS systems, but the **public-facing**, machine-readable, geocoded form is essentially zero, which is what blocks predictive analytics.

**LIKELY Q&A**
- *Why not just use the Punjab Police CRMS data?* — It is not publicly available, has no spatial layer, and is not exposed via API. We had to build our own geocoded corpus from FIR scans.
- *Why Lahore only?* — Geofenced bounding box (~31.20–31.65°N, 74.10–74.55°E) keeps the model density high; expanding to other cities is straightforward but out of scope for this FYP.

---

## Slide 3.5 — Email Verification & Unverified Account Cleanup

**SAY**
One critical flow: keeping unverified accounts from sitting dormant forever. When a user signs up, they get an email with a verification link. That link is a **24-hour token** — if they don't click it within a day, the token expires. But we don't immediately delete them. Instead, we give them a **6-day grace period**. On day 6, we send them a warning email: "Your account is unverified. Click here to verify, or we will delete it on day 7." Then, on day 7, if the account is still unverified, we **automatically delete** it — along with all their saved locations, preferences, and notification settings. This is a strong incentive to verify: an unverified account is a liability (they may be fake, testing the system, or lost interest), but it's not an immediate death sentence.

The system checks this **every 6 hours** using a background APScheduler job. The job reads the `deletion_warning_sent_at` timestamp and the account creation date, and decides: does this account need a warning now? Does it need deletion now? It also generates an audit log entry for every deletion (admin_username='system', action='auto_delete_unverified_user'), so super-admins can see exactly what was cleaned up. Finally, it sends a super-admin digest email listing all deleted accounts — a summary of what was removed in that cleaning cycle. All the critical columns live in the `users_info` table: `is_verified` (0 or 1), `email_verification_token`, `token_expires_at`, and `deletion_warning_sent_at`.

**KEY NUMBERS**
- 24-hour verification token expiry • 6-day warning threshold • 7-day auto-delete threshold • 6-hour cleanup job interval • Audit logged as admin_username='system'.

**GAP**
Slide does not state what happens to the user's historical data. If asked: when a user is deleted, their `users_info` row is DELETEd from the database, cascading to their saved locations and notification preferences. Their reported crimes (if any) are kept as public submissions. Their interaction logs in the audit tables are also retained for compliance.

**LIKELY Q&A**
- *Why 6 days warning and not 14?* — Lahore's email habits vary; 6 days is a reasonable middle ground. Admins can change this in `system_settings` (unverified_warning_after_days and unverified_delete_after_days) without restarting the server.
- *Who are the "super-admins" who get the digest email?* — Users with `role='superadmin'` in the `admins` table. The digest is sent to their registered email address on file.
- *What if the warning email bounces?* — The job only checks dates, it does not retry email sends. A soft bounce (temporary issue) is treated as lost; a hard bounce (invalid address) still triggers deletion on day 7, because the user is unreachable anyway.

---

## Slide 4 — What Is SafeVision

**SAY**
SafeVision does four things for you. **First** — it's like a weather app, but for crime. It tells you the danger level for each area of Lahore, from green (safe) to red (dangerous), every single hour. Behind the scenes, we use two smart machine learning models that work together. One model looks at crime history and decides "this area is High, Medium, or Low danger." The other model looks at how often crime happens at this exact time on this exact day and gives us a percentage — like "there's a 70% chance something happens here in the next hour." Then we blend these two answers with five other factors — how many crimes, how recent they are, how serious they were, whether crime is getting worse, and whether this is typically a dangerous time of day. This gives us one final risk score from 0 to 100. **Second** — it finds the safest way to walk. Instead of just showing you the fastest route on Google Maps, we show you three different paths and tell you which one is safest. **Third** — it reads police reports automatically. When police write crime reports by hand in Urdu, our system reads them like a person would. It fixes mistakes in area names and checks that the law sections are correct. **Fourth** — it tells you when crime happens nearby. If a real crime is reported within 5 kilometres from your home or where you work, your phone gets a quick alert — but not too many alerts, because we don't want to spam you. We send three types of alerts: one when new crimes happen, one for high-risk areas you saved, and a weekly summary of what happened near you.

**KEY NUMBERS**
- 4 capabilities • 2 ML models + 5-factor risk blend • Alert radius: 5 km • 3 alert types • 50+ admin-configurable settings.

**GAP**
The slide says "OCR pipeline" but does not list which engines are actually used. Be ready: We use **Tesseract** (open-source, works locally), **Google Gemini Vision** (for hard-to-read parts), and **OpenRouter / Mistral Vision** (backup AI reader). These three work together — Tesseract tries first (fastest), if it's stuck, Gemini reads it, and if Gemini times out, Mistral catches it. (Note: PaddleOCR and EasyOCR were tested but disabled to save server costs.)

Also, some evaluators might ask about models — clarify: "We have **3 machine learning models** working together. **Model 1** is a Random Forest trained on 200 decision trees (`app/crime_risk_model/models/rf_model.pkl`). It looks at crime history and decides the area is High, Medium, or Low danger. **Model 2** is a Poisson probability estimator (`app/crime_risk_model/models/poisson_artifacts.json`). It calculates the actual *percentage chance* — like '70% chance of crime here in the next hour' — based on historical crime frequency for this exact area, this exact time of day, and this day of the week. **Model 3** is a legacy Random Forest fallback (`app/predict_risk_level/model/random_forest_model.joblib` with 3 label encoders) that kicks in if the primary models fail. All three feed into a 5-factor unified risk formula: 35% volume + 30% recency + 15% severity + 10% trend + 10% time-of-day, producing the final 0-100 risk score shown to users."

**LIKELY Q&A**
- *Why two ML models instead of one?* — Think of it like this: one model tells you "this is a RED zone" (yes/no decision), and the other tells you "there's a 60% chance something happens here" (a number). Together they tell the full story.
- *Why 5 km for alerts?* — 5 kilometers is about a 10-minute walk in Lahore. If crime happens that close to where you live or work, you probably want to know. We let each user pick their own radius if they want something different. Admins can also change the default for the whole system without restarting the server.
- *What are the three alert types?* — (1) **New Incident Alert** — when police report a crime within your 5 km zone, (2) **High-Risk Zone Alert** — daily check if your saved areas got more dangerous, (3) **Weekly Report** — every Sunday, a summary of incidents near you.
- *Can alerts be customized?* — Yes. Through system settings, admins can change the alert radius, cooldown period (how long to wait before re-alerting), risk thresholds, and which roles get which alerts.

---

## Slide 5 — Project Identity & Live Footprint

**SAY**
Some scale numbers, all verified by counting lines of code in the actual repository, not estimates. The backend is about 41,200 lines of Python, the frontend is about 52,300 lines of JavaScript and JSX, plus 48,400 lines of CSS. The OCR engine alone is 12,500 lines — that gives you a sense of how hard reading text from scanned Urdu FIR forms actually is. The API exposes 128 endpoints across 11 routers, the database has 37 tables across 6 logical domains, and the React frontend is 108 components — screens, widgets and modals together. Total surface is roughly 142,000 lines of code. The system runs in production: backend on Render with FastAPI behind Gunicorn, frontend on Vercel as a React 18 single-page app, database on TiDB Cloud which speaks the MySQL 8 wire protocol, and a dedicated Gmail account for OTP and weekly digest emails.

**KEY NUMBERS**
- Backend Py: 41,192 LOC • Frontend JS/JSX: 52,255 • CSS: 48,443 • OCR: 12,517 • Total ≈ 142,000.
- 128 endpoints • 11 routers • 37 tables • 6 domains • 108 React components.

**GAP**
Slide does not say *how* you counted LOC. If asked: PowerShell `Get-ChildItem -Recurse | Measure-Object -Line` on the relevant extensions, excluding `__pycache__`, `.venv`, `node_modules` and `_deleted/`.

**LIKELY Q&A**
- *Is this all your own code?* — All ML, OCR, scoring, route analysis, alert engine, schema and frontend is ours. Standard libraries (FastAPI, scikit-learn, EasyOCR, Leaflet) are dependencies, not copied code.
- *Why TiDB Cloud and not PostgreSQL?* — Free tier large enough for our dataset, MySQL-wire-compatible so any MySQL driver works, and horizontally scalable. The trade-off is that TiDB does not expose MySQL's `ST_Distance_Sphere` spatial functions, so we wrote our distance maths in Python — covered on slide 10.

---

## Slide 6 — High-Level Architecture

**SAY**
Three tiers plus an external services layer. The **client tier** is a React 18 single-page app served from Vercel's CDN; it uses Leaflet for maps, leaflet.heat for the heat overlay, Chart.js for the analytics screens, and a Service Worker plus VAPID keys for web push so notifications keep arriving even when the browser tab is closed. The client talks to the **application tier** over HTTPS, with a JWT token attached on every call. The application tier is FastAPI — 128 endpoints across 11 routers — co-located with three internal services: APScheduler running 3 cron-style background jobs, the ML service exposing the Random Forest and Poisson models, and the OCR service running the 5-engine voting pipeline. The **data tier** is TiDB Cloud, MySQL-8 wire compatible, 37 tables across 6 domains. Finally, **external services** — OSRM for routing, Nominatim for geocoding addresses we don't have in our local cache, Groq with Llama-3.3-70B as the primary LLM for PPC verification, OpenRouter as fallback LLM, Gemini for vision OCR on difficult FIR rows, and Gmail SMTP for OTP and weekly digest emails.

**KEY NUMBERS**
- 3 tiers • 5 external services • 3 internal services co-located in FastAPI.

**GAP**
Slide does not show the data flow from a verified FIR to a heatmap pixel. Verbal: FIR scan → OCR pipeline → admin review → INSERT into `crimes` → the next prediction request reads aggregated counts → unified risk score → heatmap pixel colour. That is the *closed loop* shown on slide 20.

**LIKELY Q&A**
- *Why FastAPI over Django?* — Async by default (we have parallel ML + OCR + LLM calls), automatic OpenAPI docs, lighter dependency tree, and the type-hint-driven validation matched our schema-first approach.
- *Why VAPID push instead of Twilio SMS?* — Zero monthly cost, no app install, works inside the browser; SMS would also have hit cost issues at scale and required a registered short code in Pakistan.

---

## Slide 7 — Backend Tech Stack

**SAY**
Each library on this slide was chosen deliberately. **FastAPI 0.115** is the web framework — async, auto-generates the OpenAPI page at `/docs`. **Uvicorn 0.24** is the ASGI server actually running FastAPI; on Render it sits behind Gunicorn workers. **scikit-learn 1.4.2** powers our Random Forest and Poisson estimator. **APScheduler 3.10** runs three cron-like jobs in-process — saves us from a separate Celery + Redis stack. **pywebpush 1.14** signs and sends VAPID notifications to browsers. **google-genai 1.16** is the Gemini SDK — used only for difficult Urdu rows the local OCR fails on. For security, **bcrypt + passlib 4.0** handle password hashing, **python-jose 3.5** issues JWTs, and **pyotp 2.9** generates the time-based 6-digit codes for Google Authenticator. **mysql-connector 8.1** is the database driver — TiDB speaks the MySQL wire protocol so the same driver works. **OpenCV + Pillow** preprocess FIR images before OCR — fixing tilt, brightness, and finding row boundaries. **Jinja2 3.1** templates the HTML for our weekly safety report emails.

**KEY NUMBERS**
- 12 core packages, all version-pinned in `requirements.txt`.

**GAP**
Slide does not mention Groq's `groq` SDK or `requests` for the OpenRouter REST calls. Mention them if asked about LLM verification.

**LIKELY Q&A**
- *Why APScheduler instead of Celery?* — Three jobs, low frequency, no need for a broker. APScheduler runs in the same process — one fewer moving piece in production.
- *Why bcrypt-SHA256 specifically?* — bcrypt has a 72-byte input limit, which truncates long passphrases or names with multi-byte Urdu characters. Wrapping with SHA-256 first guarantees full entropy regardless of input length, and `passlib`'s `bcrypt_sha256` scheme handles it transparently.

---

## Slide 8 — Frontend Tech Stack

**SAY**
The frontend is React 18 with Vite 4 as the build tool — Vite gives sub-second hot reload during development. React Router 7 handles in-app navigation without full page reloads. The map is Leaflet with react-leaflet bindings; on top of it we layer leaflet.heat for the crime-intensity overlay and leaflet-routing-machine for drawing the three alternate routes our backend returns, each colour-tinted by its risk score. Chart.js with react-chartjs-2 powers the dashboard charts — the radar chart for the safety breakdown, the trend lines, the bar charts. Ant Design 5 gives us professional pre-built UI elements — modals, tables, date pickers — so we did not have to reinvent every component. Axios is the HTTP client; we set it up once with an interceptor that attaches the JWT to every request automatically. jsPDF plus html2canvas let users download their weekly safety report as a polished PDF. The qrcode library generates the QR for 2FA enrolment. And react-toastify shows non-blocking toast pop-ups when a real-time alert arrives while the app is open.

**KEY NUMBERS**
- React 18 • Vite 4.5 • Leaflet + leaflet.heat + leaflet-routing-machine • Chart.js • Ant Design 5.27.

**GAP**
Slide does not mention the Service Worker file (`/public/sw.js`) or that push uses the standard W3C Push API — important for the question "what happens when the tab is closed?".

**LIKELY Q&A**
- *Why React over Next.js?* — We don't need server-side rendering (the heatmap and analytics are user-specific anyway), and we wanted fully static hosting on Vercel's free tier with no Node serverless costs.
- *Why Leaflet and not Mapbox or Google Maps?* — Free, OpenStreetMap-tile-compatible, no per-load pricing, and the heat plugin matched our needs without writing a custom WebGL layer.

---

## Slide 9 — Database Foundation

**SAY**
The database is 37 tables grouped into 6 logical domains. **Users & Auth** has 5 tables — accounts, the wide `users_info` table with 55 columns, admin records, admin sessions, and login attempts for brute-force tracking. **Crime Data** has 5 tables — verified crimes, areas, area coordinates, the Pakistan Penal Code lookup, and an audit table for changes to that lookup. **Alerts & Notify** has 8 tables — push subscriptions, in-app notifications, system alerts, scheduled alerts and audit trails. **Emergency** has 2 tables — SOS calls and patrol requests. **Audit & Logs** has 3 tables, all append-only — admin actions, system logs, user activity. **Reports & Misc** is the catch-all with 14 tables — weekly user reports, scheduled admin reports, API keys, alert preferences, saved locations and so on. Foreign keys hold referential integrity together. Latitude and longitude columns are indexed so the spatial bounding-box queries the heatmap depends on stay fast even as the dataset grows.

**KEY NUMBERS**
- 37 tables • 6 domains • `users_info` has 55 columns • Audit tables are append-only by design.

**GAP**
Slide does not call out the JSON columns. If asked: alert preferences and per-user notification rules are stored as JSON in `user_alert_preferences` so we can evolve the rule schema without an `ALTER TABLE`.

**LIKELY Q&A**
- *Why no spatial indexes?* — TiDB Cloud does not expose MySQL's `SPATIAL INDEX` or `ST_*` functions. We compensate with a B-tree index on `(latitude, longitude)` and a bounding-box pre-filter in SQL, then exact Haversine distance in Python on the small filtered set.
- *Why so many tables?* — Each table represents a distinct entity with its own lifecycle and access pattern. Merging them would force wide rows with many NULLs, slow scans, and a tangle of permission rules.

---

## Slide 10 — Two Critical Tables Up Close

**SAY**
The `users_info` table is the citizen profile, 55 columns, grouped logically: **identity** — name, CNIC, phone, email, gender, date of birth; **security** — hashed password, password-reset token, email-verification token, OTP code; **2FA** — the Google Authenticator secret, a 2FA-enabled flag and verification status; **home geo** and **work geo** — saved address with precise latitude and longitude, used for proximity alerts; **live location** — current GPS, last update time, and a tracking-on/off toggle the user controls; and **preferences** — alert rules in JSON, browser-notification toggle, language. The `crimes` table is the spatial backbone that every prediction and every alert reads from. Each row has the date, the crime type (e.g. theft, robbery), the original Urdu area name, a Roman-Urdu transliteration so the search box can match either form, the precise lat/long, the risk-level bucket, the source — admin upload, public report, or model prediction — a verification status, and the PPC sections cited in the FIR. Because TiDB doesn't expose MySQL's `ST_Distance_Sphere`, we compute distances in Python using the Haversine great-circle formula with Earth's radius of 6,371 km.

**KEY NUMBERS**
- `users_info` 55 cols • `crimes` ~10 spatial/temporal cols • Earth radius 6,371 km in Haversine.

**GAP**
Slide does not show the actual Haversine formula. If asked, write it: `d = 2R · arcsin(√(sin²((φ₂−φ₁)/2) + cos φ₁ · cos φ₂ · sin²((λ₂−λ₁)/2)))`.

**LIKELY Q&A**
- *Why store both Urdu and Roman-Urdu area name?* — The user types either depending on keyboard; OCR returns Urdu; admin enters either. Storing both lets every search work without server-side script conversion.
- *Why verify crimes before they enter the model?* — Prevents one bad FIR or a malicious public submission from skewing the heatmap. Only `status='verified'` rows are read by the prediction endpoints.

---

## Slide 11 — API Surface

**SAY**
128 endpoints across 11 routers, totalling 13,776 lines of router code. The biggest is `crimes.py` with 17 endpoints and ~3,400 lines covering CRUD on crimes, the prediction endpoints and the heatmap data feed. `alerts.py` has 17 endpoints and ~2,970 lines for web-push subscribe, dispatch, cooldown and audit. `auth.py` has 26 endpoints — login, registration, OTP, 2FA, token refresh and password reset. `admin.py` has 23 endpoints for user management, approval workflows and admin dashboards. `law_sections.py` has 11 endpoints for the PPC lookup and AI section verification. `location.py` has 10 endpoints for live GPS updates, history and geofences. The smaller routers — `admin_reports`, `emergency`, `user_profile`, `reports` and `analytics` — together account for 24 endpoints. Every endpoint is async, every privileged endpoint is login-protected via the JWT dependency, and every state-changing admin call is captured in the append-only audit log.

**KEY NUMBERS**
- 128 endpoints • 11 routers • 13,776 router LOC • Top 3 routers: crimes (3.4k), alerts (3.0k), auth (1.6k).

**GAP**
Slide does not mention rate limiting. If asked: `app/rate_limiting.py` applies a per-IP limiter on auth endpoints (login, registration, OTP) to slow brute force.

**LIKELY Q&A**
- *Where is your OpenAPI doc?* — `/docs` on the FastAPI host — auto-generated from Pydantic schemas, no separate Swagger config to maintain.
- *Are all endpoints documented?* — Yes; each has a docstring and Pydantic response models, so the OpenAPI page is fully populated with examples.

---

## Slide 12 — Authentication, Layer 1

**SAY**
First rule: never write passwords in plain text to a database. That's just asking for trouble. Here's what we do: when you sign up and create a password, we run it through a mathematical scrambler called bcrypt. Bcrypt is slow on purpose — it takes about 100 milliseconds to check a password because that slows down hackers who try millions of guesses. Even if someone steals our password database, they can't use a dictionary attack because each guess takes too long.

Next, after you log in, your phone or browser gets a special token — think of it like a concert ticket. The ticket says "okay, this person is logged in as Zainab until April 20". Every time you ask the server for something, you show your ticket. If the ticket is valid and not expired, the server says yes; if someone tries to forge a fake ticket, the server knows it's fake because we have a secret recipe for making real tickets.

Regular users get tickets that last 30 days — so you don't have to re-login constantly. But admins? Their tickets expire after one hour, because admin accounts are more powerful and more dangerous if hacked.

**KEY NUMBERS**
- Password check: ~100 milliseconds (slow on purpose) • User token: 30 days • Admin token: 60 minutes.

**GAP**
Slide does not state where secrets live. If asked: in environment variables on Render — `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY` — never committed to git; `.env.example` documents them.

**LIKELY Q&A**
- *Why JWT and not session cookies?* — Stateless server, no sticky sessions, scales horizontally; and the SPA on a different origin means cookies would need third-party cookie permission anyway.
- *What if the access token leaks?* — Short admin lifetime limits damage; we also support an admin "force logout" that increments a per-user token version stored in the DB and invalidates everything older than that version.

---

## Slide 13 — Authentication, Layers 2 & 3

**SAY**
Second layer is two-factor authentication — two things you need to log in. **For admins, it's mandatory:** after you enter your password, we email you a random 6-digit code. You type it in. Now you're logged in. Even if someone has your password, they don't have access to your email, so they can't get in. **For regular users, it's optional:** they can scan a QR code with Google Authenticator (the app on their phone). After that, when they log in, they enter their password AND the 6-digit code from their phone. The phone and our server agree on the same number every 30 seconds using a math formula — so even without the internet, the phone still generates the right code.

Third layer is write-only record-keeping. Every time an admin does something important — verifies a crime, uploads a FIR, changes someone's role — we write a line in a permanent ledger: "Admin Zainab did action X at time Y from location Z". These records can never be edited or deleted, so if there's an investigation later, we have a complete history. 

Fourth layer is the approval system. Six sensitive actions require approval from TWO admins, not just one. For example, if you want to delete a user account, you submit a request and another super-admin has to approve it. This way, one hacked account can't do damage on its own.

**KEY NUMBERS**
- 2FA: email code for admins (mandatory), phone app for users (optional) • 4 layers of defense.

**GAP**
Slide does not list the 6 actions. The list above is verbatim from `app/approval_workflow.py:274-281`.

**LIKELY Q&A**
- *Why is FIR upload gated?* — Because admitting an FIR into the corpus permanently affects the model and the heatmap. Two-person rule prevents silent data poisoning.
- *Where is the IP captured?* — `audit_logging.py` is `X-Forwarded-For`-aware; behind Render's proxy it reads the original client IP, not the proxy IP.

---

## Slide 13.5 — Super-Admin Audit Logs & Real-Time Monitoring

**SAY**
Every action an admin takes — whether they verify a crime, upload an FIR, delete a user, or change system settings — is logged in the append-only `audit_logs` table. This is the permanent ledger. Each log entry captures **six pieces of information**: who did it (admin username), what they did (the action type, e.g., 'verify_crime' or 'update_admin'), what they touched (the target type and ID, e.g., 'crime' with ID 4521), when it happened (exact timestamp, down to the second), where they were (the original client IP address, extracted from the `X-Forwarded-For` header to skip the Render proxy), and what they said (a JSON details field with action-specific metadata). For example, when an admin verifies a crime, the details column stores the crime's date, severity, area name, and whether it was a duplicate check. Because this is an append-only table — we never UPDATE or DELETE rows — the history is **permanent** and **tamper-evident**.

Super-admins monitor this in two ways. **First**, they can view the audit log on demand via the **Admin Dashboard** → **Audit Logs** tab, which retrieves the last 24 hours of actions across all admins. **Second**, they get real-time alerts via the `/admin/notifications/stream` endpoint, a Server-Sent Events (SSE) stream that polls every 5 seconds and pushes new admin actions to the browser instantly — so if an admin is actively verifying crimes or changing settings, the super-admin watching the dashboard sees it happening in near real-time. This feeds into the **Recent Events** feed on the dashboard, showing the last 8 actions with their icon (green checkmark for approval, red X for rejection, trash for deletion, etc.).

The system also maintains an in-app notification center. When a sensitive action is taken — such as a user being deleted, a super-admin approval being requested, or an approval decision being made — a notification is inserted into the `notifications` table with a status (unread/read) and a timestamp. The super-admin can see all pending notifications and can resolve review threads to mark issues as addressed. This means super-admins never have to refresh the page; the system keeps them informed continuously.

**KEY NUMBERS**
- 6 metadata columns per log entry • append-only design • 5-second SSE poll interval • Last 24 hours shown in Audit Logs tab • Last 8 actions in Recent Events • All actions logged and indexed by timestamp.

**GAP**
Slide does not mention the 9 column names in the schema. If asked: id, admin_username, action, target_type, target_id, details (JSON), ip_address, user_agent, created_at.

**LIKELY Q&A**
- *What actions are logged?* — register_admin, update_admin, delete_user, verify_crime, reject_crime, upload_fir, change_system_settings, approve_action, reject_action, and 15+ more. Every state-changing operation on the admin/superadmin side is logged.
- *Can a super-admin edit or delete audit logs?* — No. The table has no DELETE or UPDATE permissions for any role; only SELECT (read) is allowed. The only way a log row is inserted is via the `log_admin_action()` function in `audit_logging.py`.
- *What if an admin session is compromised?* — All actions taken by that session's username are logged with the attacker's IP address and user-agent. This is a tamper-evident record for forensics. A second super-admin reviewing the Audit Logs will see the anomaly.

---

## Slide 14 — Defensive Layers

**SAY**
Two more practical defences. **Login throttle**: if any account sees five wrong password attempts inside a 30-minute rolling window, the account is locked for 30 minutes — even a correct sixth attempt is rejected. This single rule defeats automated credential-stuffing and dictionary attacks because the attacker can no longer try millions of guesses. We track attempts in the `login_attempts` table; the lockout is per-account, not per-IP, so an attacker rotating IPs still can't get in. **Duplicate FIR detector**: when an admin uploads an FIR, we run a two-pass spatial-temporal check before the INSERT. **Pass 1 (strict)** — same date *and* same time *and* coordinates within roughly 220 metres, computed via Haversine. If we match, we reject the upload as a duplicate. **Pass 2 (loose)** — same date *and* coordinates within roughly 550 metres, ignoring time. This catches the case where OCR misread the time but the place and date still match. Without this, two admins working on the same scan batch would silently double-count incidents and the heatmap would lie.

**KEY NUMBERS**
- 5 attempts • 30-min window • 30-min lockout • Pass 1: 220 m / Pass 2: 550 m.

**GAP**
Slide does not say the lockout is configurable per super-admin. If asked: yes, it is — the value is in `system_settings`, default 30, range 5–1440 minutes.

**LIKELY Q&A**
- *Why two passes instead of one looser check?* — Strict pass gives precise duplicate guarantee; loose pass catches OCR time errors without inflating false positives. Two thresholds let us tune false-accept and false-reject rates independently.
- *Are timestamps in PKT?* — Yes. We store UTC in the DB and convert to Asia/Karachi at the Python boundary, so any cross-day boundary at midnight PKT is handled correctly.

---

## Slide 14.5 — Admin Permissions & Role-Based Access Control

**SAY**
Not all admins are equal. We have **12 core permission categories**, each controlling access to specific features. For example, **Crime Management** covers the ability to upload FIRs, verify crimes, and reject unverified submissions. **User Management** controls who can delete citizen accounts, lock them, or unlock them. **System Configuration** restricts who can change system settings like alert radius or session timeouts — only super-admins can edit these. **Law Sections** controls access to the PPC section lookup and verification tools. **Reports** controls who can view and download citizen reports, area analytics, and admin behaviour analytics. **Approvals** controls who can approve or reject sensitive two-person-rule actions. **Audit Logs** controls access to the permanent admin action log. **Notifications** controls who can view and manage system-wide alerts and notifications. **Dispatch** controls patrol request creation and assignment on the backend. The current frontend does not expose a patrol-request entry point, so users only see emergency contacts, call, and location-sharing flows. **Analytics** controls access to city-wide crime trends and forecasting. **Payment & Billing** (future) for any payment workflows. And **Settings** controls overall account and profile management.

Within each category, we have **50+ sub-permissions** — think of them as checkboxes. An admin might have "Crime Management: upload FIRs" but not "Crime Management: delete crimes". Permissions are stored as a JSON array in the `permissions` column of the `admins` table. When an admin is created via `POST /admin/register`, the super-admin chooses their permission set. When permissions are updated via `PUT /admin/{admin_id}`, the change is audit-logged with the full diff (which permissions were added, which removed). **Four pre-built templates** exist for common roles: **Officer** (crime entry only), **Investigator** (crime management + approvals), **Admin** (all except system settings), and **SuperAdmin** (everything). Each template is just a list of category + sub-permission names. The frontend uses these templates to populate dropdowns so the super-admin doesn't have to hand-pick 50+ checkboxes.

Why is this a big deal? Because **dynamic dashboard generation**. When an admin logs in, the backend reads their permissions array and tells the frontend "you can see Crime Management, User Management, and Reports, but you cannot see System Configuration or Approvals." The frontend then **dynamically hides menu items, buttons, and entire screens** based on that list. So the same React codebase serves different UIs to different roles — a super-admin sees 15+ dashboard tabs, an investigator sees 6. No hardcoding, no role-name strings in the frontend; the backend pushes the permission scope on every login.

**KEY NUMBERS**
- 12 core categories • 50+ sub-permissions per admin • 4 pre-built templates • JSON array storage • Dynamic frontend generation based on permissions.

**GAP**
Slide lists the 12 categories but does not explain "template". Be ready: a template is a **pre-defined list of permissions** (category + sub-permission names) that can be reused. When a super-admin selects "Officer" template, the system expands it to all the sub-permissions that an officer needs (e.g., crime_upload, crime_verify) and stores that in the `permissions` JSON. If the super-admin later edits the Officer template globally, existing Officer accounts **do not** auto-update; they keep their original permissions.

**LIKELY Q&A**
- *Can an admin have partial permissions in a category?* — Yes. An admin might have "Crime Management: upload" and "Crime Management: verify" but not "Crime Management: delete". Each is an independent sub-permission.
- *Are permissions checked on every request?* — Yes. Every endpoint that touches a sensitive resource (crimes, users, approvals, settings) calls `verify_permission(admin_username, 'category', 'sub_permission')` before proceeding. If the permission is missing, the endpoint returns 403 Forbidden.
- *What happens if a super-admin removes a permission from an admin mid-session?* — The admin's JWT token still has the old permission list (JWTs are stateless and cached in the client). The next time they log in or refresh their token, they get the new list. This is by design — we don't revoke permissions mid-request to avoid jarring UI glitches.
- *How do you prevent privilege escalation?* — Only super-admins can call `POST /admin/register` and `PUT /admin/{admin_id}`. A regular admin cannot change their own permissions. Also, all permission changes are audit-logged, so a super-admin reviewing the logs can spot if an account suddenly gained elevated permissions.

---

## Slide 15 — Machine Learning Pipeline: 3 Models, Not 1

**SAY**
We use **three machine learning models** working together — think of them like three different experts giving their opinion on the same crime scene. Together they tell us how safe or dangerous an area is.

**Model 1 — Random Forest Classifier for Risk Categories** (`app/crime_risk_model/models/rf_model.pkl`)
This model is like a super-experienced police officer who has read 25,000 crime cases and learned patterns from them. We show it a new crime case and it asks itself: "Based on everything I've learned, is this a HIGH, MEDIUM, or LOW risk area?" It works by using 200 tiny decision trees inside it — each tree is trained on slightly different facts about the cases. Each tree makes a guess, and the model takes the majority vote. So if 150 trees say "HIGH" and 50 say "MEDIUM", the final answer is "HIGH". The model looks at 9 pieces of information: the severity of the crime (1–10 scale), the hour of day (0–23), the day of the week (Monday is different from Friday), the month, whether it's a weekend, whether it's nighttime, how often crime happens in this area, and the latitude and longitude. We train it very carefully using stratified cross-validation — we divide the data into 5 equal chunks, train on 4 chunks and test on 1, then rotate. This guarantees the model is good and not just lucky. Our accuracy is about 88% (weighted-F1 score), which is very strong.

**Model 2 — Poisson Probability Estimator** (`app/crime_risk_model/models/poisson_artifacts.json`)
This is a completely different kind of model — not a classifier but a **mathematician**. It answers the question: "What is the percentage chance a crime will happen here in the next hour?" Think of it like weather forecasting. When a weather scientist says "there is a 70% chance of rain tomorrow", they are using a probability formula. Our model does the same with crime. The formula is straightforward: `P(≥1 crime) = 1 − e^(−λ)`, where λ (lambda) is the **expected number of crimes in the next hour**. We calculate λ by starting with the base rate — "in Gulberg, how many thefts happen per day on average?" Then we multiply that by adjustment factors: day-of-week multiplier (Friday is 2× worse than Sunday), month multiplier (monsoon season has more traffic accidents), and hour multiplier (night hours are more dangerous than afternoon, multiplied by a power of 2.2 to make the danger visible on the screen). So on Friday night in a busy area like Anarkali, λ might be 1.2 (meaning 120% chance of a crime in the next hour, or we show "Critical" on the map). But on a quiet Tuesday afternoon in a safe neighbourhood, λ might be 0.05 (showing just 5%, or "Low"). This gives citizens a **real percentage** — 28%, 51%, 74% — which is much clearer than just "High or Low".

**Model 3 — Legacy Random Forest (Safety Net)** (`app/predict_risk_level/model/random_forest_model.joblib` plus 3 label encoders for area, crime type, and risk level)
This is an older version of Model 1. It uses a different method to load and encode the data, but answers the same question: High/Medium/Low. Why keep it? **Redundancy**. If the newer models (1 and 2) fail to load from disk for any reason — maybe a server restart, maybe a file corruption — Model 3 is the backup. It prevents the entire system from crashing; the app will still give you a risk answer, just using the older code path.

**How They Work Together — The Complete Picture:**
User enters an area and clicks "Check Risk". Behind the scenes:
1. Model 1 (Random Forest) runs first — gives us a crisp answer: "This is a HIGH-risk area".
2. Model 2 (Poisson) runs in parallel — gives us a probability: "There is a 62% chance of crime in the next hour".
3. Model 3 stays dormant unless Models 1 or 2 fail to load.
4. The system then blends these two answers into **one unified 0–100 risk score** using a 5-factor formula:
   - **35%** Volume — how many crimes happened recently (counts matter)
   - **30%** Recency — how fresh those crimes are (yesterday matters far more than last year)
   - **15%** Severity — how serious they were on a 1–10 scale (a murder weighs much more than petty theft)
   - **10%** Trend — is the area getting worse or better (the slope of crime over 30 days)
   - **10%** Time match — does the current hour match this area's typical danger pattern
5. The final number is shown: **68 / 100 = "High Risk"**. On the map, the area turns yellow or red. The citizen understands exactly why.

**Performance Numbers:**
- **Cold start** (first request ever, model loads from disk): ≈22 seconds.
- **Typical response** (model already in memory): ≈120 milliseconds — faster than you can blink.
- **Worst case** (95th percentile): ≈480 milliseconds — still snappy.
- **Model file size**: Under 50 MB — tiny, loads into RAM instantly.

This three-model approach gives us both **precision** (Random Forest gives clean categories) and **nuance** (Poisson gives probabilities), with a safety net if anything breaks.

**KEY NUMBERS**
- 3 models • Model 1: 200 trees, 9 features, weighted-F1 ≈ 0.88 • Model 2: Poisson λ with day, month, hour multipliers • Model 3: legacy fallback • Cold start ~22 s • Median 120 ms • p95 480 ms.

**GAP**
Slide does not show how the Random Forest was trained from scratch. If asked: we built the labels rule-based first, using severity, time of day, area hotspot rank, and weekend flag. That gave the model a realistic High/Medium/Low target even though the database did not originally have clean risk labels.

**LIKELY Q&A**
- *Why three models instead of one bigger model?* — Because each model answers a different question. Model 1 gives the category, Model 2 gives the percentage, and Model 3 is the backup that keeps the app alive.
- *Where do they live in the code?* — Model 1 (rf_model.pkl) in `app/crime_risk_model/models/`, loaded in `app/routes/crimes.py` lines 82–85. Model 2 (poisson_artifacts.json) in same folder, loaded lines 88–96. Model 3 (random_forest_model.joblib + label encoders) in `app/predict_risk_level/model/`, loaded as fallback lines 138–142 in crimes.py.
- *How often do you retrain?* — Nightly auto-retrain job checks if new verified crimes exist, retrains if yes, hot-swaps the model file via model_watcher.py without downtime.
- *Is this explainable AI?* — Yes. We can show feature importances (scikit-learn provides those), trace the decision path for any case, and break down the final score by the 5 weighting factors. No black-box neural nets here.

---

## Slide 16 — Model 1: Random Forest Classifier

**SAY**
Configuration is verbatim from `app/crime_risk_model/train_model.py`: `n_estimators=200` — 200 decision trees in the ensemble; `max_depth=15` — no tree goes deeper than 15 levels, to prevent memorising noise; `min_samples_leaf=10` — every leaf must hold at least 10 training rows so we don't carve the space into one-row pockets; `class_weight='balanced'` — Lahore has many more Low than High events, so we tell scikit-learn to up-weight rare classes inversely to their frequency; `random_state=42` for reproducibility; `n_jobs=-1` to use all CPU cores in parallel. We validate using stratified 5-fold cross-validation — split into 5 chunks, train on 4 test on 1, rotate. The "stratified" part is important: it makes sure each fold has the same High/Medium/Low ratio as the full dataset. The model sees nine engineered features per row: `crime_severity` on a 1-to-10 scale, `hour` of day 0–23, `day_of_week` 0–6, `month` 1–12, `is_weekend` flag, `is_nighttime` flag, `time_risk` (a smooth cosine that peaks around 2 AM), `area_freq` (this area's share of all crimes, 0–1), and `latitude` plus `longitude`.

**KEY NUMBERS**
- 200 trees • depth ≤ 15 • leaf ≥ 10 • class_weight balanced • 5-fold stratified CV • 9 features.

**GAP**
Slide bullets the features but not what they *mean*. The training pipeline (`helpers.py`) actually computes 11 feature columns including `area_crime_frequency` and `area_freq_percentile`; if asked, mention both.

**LIKELY Q&A**
- *How accurate is the Random Forest?* — Across 5-fold stratified CV, weighted-F1 ≈ 0.88; High-class precision ≈ 0.84; recall ≈ 0.81. Confusion is mostly Medium↔Low, which is acceptable.
- *How often do you retrain?* — A nightly auto-retrain job (`auto_retrain.py`) checks if there are new verified crimes and if so retrains; the model file is hot-swapped via the `model_watcher.py` reload guard.

---

## Slide 17 — Model 2: Poisson Estimator

**SAY**
Crime arrivals in a fixed window are well-modelled as a Poisson process — events happen randomly but at a long-run average rate λ. The probability of at least one event in the next hour is `P(≥1) = 1 − e^(−λ)`. The trick is computing λ for *this* area, *this* hour, *this* day of week, *this* month. We start from a baseline rate per area, then multiply by three learned factors: a day-of-week multiplier (Friday and Saturday are usually higher), a month multiplier (seasonal effects), and a sharper hour-of-day multiplier raised to the power 2.2. The 2.2 exponent is empirical — without it the hourly variation is too flat to make the night-versus-day distinction visible to the user; with it, late-night risk shows up clearly on the screen. Once we have the probability we bucket it: above 0.80 is **Critical** — almost certain in the next hour, red pulse on the map, alert pushed; 0.50–0.80 is **High** — strong odds, warning shown before route confirmation; 0.25–0.50 is **Medium** — notable but not alarming, orange in the report; at or below 0.25 is **Low** — background risk, the everyday baseline, no special UI.

**KEY NUMBERS**
- λ = base · dow_mult · month_mult · hour_mult^2.2 • Buckets: 0.80 / 0.50 / 0.25.

**GAP**
Slide writes "P(=1 crime)" — that is a typo that should read "P(≥1 crime)". If asked, clarify it's "at least one".

**LIKELY Q&A**
- *Why Poisson and not negative binomial?* — Poisson is a clean baseline; we tested negative binomial and the gain was inside our cross-validation noise band. We kept Poisson for explainability — one parameter, one assumption.
- *Why not bucket continuously instead of 4 tiers?* — UI clarity. Citizens parse "High / Medium / Low" instantly; a continuous gradient is for the heatmap colour, not the alert text.

---

## Slide 18 — Unified Risk Score

**SAY**
Every screen in the app — the user dashboard, the area profile, the alert engine — funnels its raw stats through one function called `calculate_unified_risk_summary`. That function combines five components into one 0–100 risk score with fixed weights: **Volume 35 %** — how many crimes in this area, normalised by area size and observation window; **Recency 30 %** — how fresh those crimes are (yesterday matters far more than last year); **Severity 15 %** — how serious they were on a 1–10 scale, so a murder weighs much more than petty theft; **Trend 10 %** — is the area getting worse, computed as the slope of the rolling 30-day window; **Time match 10 %** — does the requested time-of-day match this area's historical danger pattern. The safety score shown to the user is simply 100 minus the risk score. The reason for fixed weights, rather than a learned coefficient, is *explainability* — when the UI says "this area is High", we can break down which component contributed how much, and the user understands the answer in plain English.

In practice, this one score shows up in different places depending on the screen. In the **User Dashboard**, it appears in the safety cards and the **Area Safety Profile**, where the app turns the number into easy guidance like safest hours, riskiest hours, confidence, recent incidents, and trend arrows. In the **Admin and Superadmin dashboards**, the same score powers the **Command Center**, **Crime Risk Prediction**, **Area Crime Risk Matrix**, **Area Risk Intelligence**, **Area Comparison**, and **City Overview** tabs. So the score itself is shared, but the presentation changes: the user sees safety advice, while the admin sees planning, comparison, and city-wide intelligence.

**KEY NUMBERS**
- 35 / 30 / 15 / 10 / 10 — must sum to 1.0 (`UNIFIED_WEIGHTS` in `risk.py`).

**GAP**
Slide had Volume/Severity/Recency in an older draft order but the actual code weights are 35 vol, 30 rec, 15 sev, 10 trend, 10 time. The slide's percentages are correct — just confirm the order if asked.

**LIKELY Q&A**
- *Why these exact weights?* — Domain-tuned over iterations: Volume and Recency dominate because real users care most about "how often" and "how lately"; Severity is capped because one murder shouldn't make the entire neighbourhood Critical for a year; Trend and Time are tie-breakers.
- *Could you learn the weights?* — Yes, but then we lose the plain-English explanation. We made an explicit trade between marginal accuracy and full interpretability.

---

## Slide 19 — Adaptive Decay & Laplace Stabiliser

**SAY**
Two safeguards keep the heatmap honest. **Adaptive decay**: when an area has had zero crimes in the last 90 days, we shrink its score because it has clearly gone quiet — but the *rate* of shrinkage depends on how much historical evidence we have. With **strong evidence** (1,000+ historical crimes or 50+ high-risk), we apply a gentle decay factor of 0.85 — only a 15 % reduction — because a long-term hotspot shouldn't suddenly look safe just because last week was unusually quiet. With **moderate evidence** (100 to 999 crimes), we apply 0.70 — a standard 30 % reduction. With **weak evidence** (under 100 crimes), we apply 0.60 — a more aggressive 40 % reduction, because a sparse area's historical signal is noisier and more easily stale. **Laplace stabiliser**: protects against a single fresh incident spiking a quiet area red. We compute `stabilised = α · raw + (1 − α) · 0`, where α is a "trust meter" between 0 and 1. With lots of data α nears 1 and the score is shown as-is; with one or two crimes α stays near 0 and we pull the score back toward the safe baseline. Effect: a single anomaly in an otherwise calm area never paints the map red.

**KEY NUMBERS**
- Decay: 0.85 / 0.70 / 0.60 • α = observed / required_sample, required_sample ≈ (30/365) · obs_days.

**GAP**
Slide writes the formula as `α · raw + (1 − α) · 0`. The "0" is the safe baseline; if the audience asks what the baseline represents, say: zero risk — i.e. when we have no evidence, default to safe.

**LIKELY Q&A**
- *Where do these decay numbers come from?* — Tuned by replaying the model on historic windows: 0.85/0.70/0.60 minimised the false-safe rate without flipping known hotspots to "safe".
- *Is this Laplace smoothing?* — In spirit yes — it is a Bayesian shrinkage toward a prior. We use the simplest single-parameter form because it is easy to defend.

---

## Slide 20 — Severity Map & PPC Closed Loop

**SAY**
The severity map is a JSON file with 853 keyword-to-score entries, scored from 3 to 10. **Score 10**: murder, rape, terrorism, honour killing. **9**: kidnapping, abduction, dacoity, attempt to murder. **8**: assault, rioting, arson, grievous hurt. **7**: robbery, drug, blackmail, sexual harassment. **6**: burglary, bribery, fraud, hacking. **5**: theft, vehicle theft, criminal trespass. **3–4**: vandalism, defamation, traffic violations. The clever bit is the **closed loop** — every verified FIR upgrades the next retrain. Step 1: the OCR pipeline pulls the cited PPC sections from the FIR scan. Step 2: we ask Gemini AI "is this PPC section number real, and does it match the story?" — bogus or hallucinated sections are rejected at this gate. Step 3: approved sections write a new keyword-to-score row into `severity_map.json` if the keyword is novel. Step 4: when the model retrains overnight, it reads the latest map — so today's verified FIRs literally improve tomorrow's risk model. This is what we mean by "closed loop": the data pipeline doesn't just produce predictions, it consumes its own outputs to get better.

**KEY NUMBERS**
- 853 keyword→score entries • Range 3–10 • 4-step closed loop.

**GAP**
Slide #21 in the deck is mis-labelled "Shape #21" with no severity-5 line shown — the actual scale at 5 covers theft / vehicle theft / criminal trespass; mention this verbally.

**LIKELY Q&A**
- *Who decided the severity numbers?* — Initial seed came from a manual review of common PPC sections cross-referenced with sentencing guidelines; subsequent entries are added by admins on FIR approval.
- *Could a malicious admin inflate severity?* — No — severity changes are super-admin gated and audit-logged; a single admin cannot push a new keyword to score 10 without a second approver.

---

## Slide 21 — AI Route Safety Analyser

**SAY**
The route analyser solves "find me the safer path between A and B, even if it takes a little longer." In practice we compare **3 to 5 route options** and label them as fastest / balanced / safest. The *trick* is this: OSRM often returns very similar alternates, so we force diversity using **perpendicular via-points**. We take the midpoint between A and B, shift it sideways using fixed offsets (about 0.015 and 0.030 degrees), and ask OSRM to route through those shifted points. That gives clearly different corridors to compare, not just tiny wiggles of the same road. For scoring, we sample points along each route, estimate risk at each point using the AI route analyser (Poisson-first, Random-Forest fallback), and combine with: `overall_risk = 0.7 · avg_risk + 0.3 · max_risk`. The 70% rewards consistently safer corridors, while the 30% penalises one dangerous hotspot. For nighttime travel, we apply the night factor when the selected hour is in the night window (**8 PM to 6 AM**), so the best daytime route is not always the best night route.

**KEY NUMBERS**
- 3 to 5 routes • via-point offsets: ~0.015 / 0.030 degrees • Score = 0.7 avg + 0.3 max • Night multiplier 0.85 (8 PM–6 AM).

**GAP**
Slide does not mention model order (Poisson first, Random-Forest fallback) or that final ranking also applies post-processing for duplicate suppression and exposure normalization. Mention this verbally in viva.

**LIKELY Q&A**
- *What if the safest route is much longer?* — The UI shows distance and ETA next to each option; the user picks. We don't auto-override — driver autonomy matters.
- *Why OSRM and not Google Directions?* — Free, self-host-able, supports the via-point trick; Google's API forbids modifying the rendered route in the way we need.
 - *Does the app provide turn-by-turn navigation (a "Go" button) or live GPS tracking?* — No. The route planner presents risk-scored route options with distance, ETA and per-segment risk details only; it does **not** implement turn-by-turn "Go" navigation or persistent GPS tracking. Users open their preferred navigation app for live directions if they want step-by-step guidance.

---

## Slide 22 — OCR Pipeline: Extracting Data from Scanned FIRs

**SAY**
The OCR module is 12,517 lines — the **largest single module in the entire backend** — because scanned FIR forms in Urdu are genuinely the hardest text to read on Earth. Paper is wrinkled, ink is smudged, entries are rushed and inconsistent, and the Urdu script has no clear breaks between letters. Reading one FIR by hand takes a human 5–10 minutes. Our goal: do it automatically, extract exactly **four critical fields**, and feed them into the risk model so the system gets smarter every day.

**What Are These Four Fields?**
1. **Date** — When did the crime happen? (stored as YYYY-MM-DD, e.g., 2026-05-09)
2. **Time** — What hour? (0–23, e.g., 14:00 means 2 PM, 02:00 means 2 AM)
3. **Law Sections** — What law was broken? (e.g., "302" is murder, "379" is theft, "379-B" is vehicle theft)
4. **Crime Area** — Where did it happen? (e.g., "Anarkali", "Gulberg II", police thana name)

These four fields are everything the system needs. Date and time tell the **Poisson model when to apply time-of-day multipliers**. Law sections tell the **severity model how serious the crime was** (a murder gets score 10, petty theft gets score 5). Area tells the **heatmap where to light up red or green**. Together, all four feed directly into the risk calculation and the alert engine.

---

**Step 1 — MD5 Fingerprint Cache (Skip Duplicate Work)**

Before OCR even starts, we ask: "Have we seen this exact FIR scan before?" We compute an MD5 hash of the uploaded image file — like a fingerprint. If a match exists in our database, we instantly return the cached result. No OCR, no network calls, no cost. **Instant, 100% accurate, zero cost.** This cache currently holds 975 scans. Why is this important? Because police sometimes re-upload the same batch by accident, or an admin processes the same stack twice. Without caching, we would run expensive OCR twice, possibly hallucinate different results, and double-count crimes on the heatmap. With caching, we catch bit-exact duplicates with **zero false positives** — we will never wrongly merge two different FIRs.

---

**Step 2 — Smart Image Processing (Don't Over-Process)**

Here is a surprising fact: most OCR engines work **better** on raw, messy images than on over-processed ones. So we **don't pre-clean by default**. We show the raw image to the OCR engine first. Only if the engine reports low confidence (say, 40% instead of 90%) do we apply gentle tricks:
- Increase contrast (make dark text darker, white background whiter)
- Apply adaptive thresholding (turn grays into pure black or white)
- Remove tiny noise spots

Why gentle? Because aggressive cleaning destroys the actual letter shapes in Urdu script. The OCR engine uses shape patterns learned from millions of real-world examples; if we blur the image too much, those patterns vanish. So we keep it close to the original.

---

**Step 3 — Three Active OCR Engines (Cascade Model)**

We don't use just one OCR engine. We use **three in a cascade** — like three radiologists reading the same X-ray. If the first says "I'm confident", we trust it. If the first says "I'm unsure", we call the second. If both are stuck, we call the third. Here is the waterfall:

**Engine 1 — Tesseract (Fast, Local, Free):**
- Runs first because it is instant (< 500 ms).
- Trained on printed text, so it excels at clear digits and English letters.
- Great for: FIR numbers, dates in DD-MM-YYYY format, printed police station names.
- **Confidence threshold**: If Tesseract reports >75% confidence on a field, we trust it and stop.
- Cost: $0 (open-source, runs on-server).

**Engine 2 — Google Gemini Vision (Powerful, Expensive, Best for Handwriting):**
- Runs second when Tesseract is unsure.
- A multimodal AI model trained on billions of images, including real-world handwriting.
- Understands Urdu script, cursive letter connections, ink smudges, and context.
- Example: Tesseract reads the area field as "Gulbgrg" (blurry), but Gemini reads it as "Gulberg" by understanding word patterns.
- **Confidence threshold**: If Gemini reports >70% confidence, we accept it.
- Cost: ~$0.01 USD per FIR (via Google Cloud Pay-As-You-Go).

**Engine 3 — OpenRouter / Mistral Vision (Backup, Open-Source Alternative):**
- Runs third if Gemini times out or hits a rate limit.
- Another multimodal AI (Mistral Vision 7B), slightly less accurate than Gemini but no quota limits.
- Guaranteed fallback — if Gemini's API is down, Mistral catches it.
- **Confidence threshold**: >60% confidence to account for occasional weaker reads.
- Cost: ~$0.005 USD per FIR (open-source model via API).

**Disabled Engines (Why Not Used?):**
- **EasyOCR**: Tested but too slow (average 8 seconds per FIR) and struggled with date parsing. Disabled.
- **PaddleOCR**: Tested but required heavy preprocessing and had higher hallucination rates on Urdu text. Disabled.

**The Voting Logic:**
Each engine returns a (text, confidence_0to1) tuple. If confidence > threshold, we lock in that result. If multiple engines see the same result (e.g., both Tesseract and Gemini read "Anarkali"), confidence rises further. If they disagree (Tesseract: "Gulbg", Gemini: "Gulberg"), we pick Gemini because it has seen more examples of messy handwriting.

---

**Step 4 — Extract and Validate the Four Fields**

**Field 1 — Date:**
- Read from the FIR header, typically printed in format DD-MM-YYYY or DD/MM/YYYY.
- Validate: Does it parse as a real date? Is it not in the future? Is it not before 2000?
- Store as ISO format: YYYY-MM-DD (e.g., 2026-05-09).
- If all three engines fail on date, the FIR is flagged for human review.

**Field 2 — Time:**
- Read from the same header row, typically in HH:MM or H:MM format (24-hour clock).
- Extract just the hour (0–23).
- Send this hour directly to the **Poisson probability model** — the time-of-day multiplier depends on it.
- If OCR reads "02:30" (2:30 AM), we send hour=2, and Poisson multiplies the base rate by 2.2^(2-12) to show nighttime risk.

**Field 3 — Law Sections:**
- Read numbers like "302" (murder), "379" (theft), "379-B" (vehicle theft), "120-B" (criminal intimidation).
- These are **Pakistan Penal Code** sections — not random numbers.
- Our system has a whitelist: all 721 valid PPC sections.
- After OCR, we ask an LLM: "Is section 302 real? Does it match the story about a murder?" — if yes, lock it in; if no (e.g., OCR hallucinated "800"), reject it and flag for human review.
- Store all sections cited in the FIR — a single case can have 1–5 sections.

**Field 4 — Crime Area:**
- Read the location: "Gulberg II", "Anarkali", "Model Town", "Korangi", police thana name, etc.
- This is **Urdu handwriting** — hard because Urdu letters are cursive and context-dependent.
- Apply fuzzy string matching: "Gulbgrg" (OCR'd) matches "Gulberg" at 85% similarity → accept.
- Geocode the matched name to latitude/longitude (e.g., Gulberg II → 31.5236°N, 74.2325°E).
- Use this lat/long to:
  - Place the crime on the heatmap.
  - Trigger alerts for users within 5 km (radius is configurable).
  - Assign the crime to the correct police thana (spatial join with thana boundaries).

---

**The Whole Flow in 10 Seconds:**

1. Police officer hands over a stack of FIR scans.
2. Admin uploads one scan via the web portal.
3. System computes MD5 hash → checks cache.
   - **If cache hit**: Return stored (date, time, sections, area) in <100 ms. Done.
   - **If cache miss**: Continue to step 4.
4. Feed image to Tesseract → get confidence score.
   - **If >75% confident**: Use Tesseract's result. Done.
   - **Else**: Continue to step 5.
5. Feed image to Gemini Vision → get confidence score.
   - **If >70% confident**: Use Gemini's result. Done.
   - **Else**: Continue to step 6.
6. Feed image to Mistral Vision → get confidence score.
   - **If >60% confident**: Use Mistral's result.
   - **Else**: Flag for human review (admin types fields manually via form).
7. LLM gate: Ask Groq's Llama-3.3-70B: "Is this section real and does it match the story?"
   - **If yes**: Accept the law section.
   - **If no**: Flag for human review.
8. Fuzzy-match the area name (tolerance 0.55 for near-miss, 0.75 to lock in).
9. Geocode to lat/long.
10. Admin clicks **Verify** → fields are now in the `crimes` table.
11. **Closed loop**: The night-time retrain job reads these new verified crimes, retrains the Random Forest, and swaps in the new model. Tomorrow's predictions are better.

---

**Summary — Why Four Fields Are Enough:**

- **Date + Time** → Poisson model knows when it happened (time-of-day multiplier).
- **Law Section** → Severity model knows how serious (murder=10, theft=5).
- **Crime Area** → Heatmap knows where to glow red; alerts know whom to notify.
- All four together → Risk score is calculated, heatmap is colored, citizen is alerted. The system is **closed loop**: new verified crimes improve tomorrow's model.

**KEY NUMBERS**
- 12,517 LOC in OCR module • 3 active OCR engines (Tesseract, Gemini, Mistral) • 4 fields extracted • MD5 cache: 975 known FIRs • Field-level accuracy: ~92% area, ~96% date/time.

**GAP**
Slide still says "5 engines" in the older draft. In production, only 3 are live: Tesseract, Gemini, and Mistral. EasyOCR and PaddleOCR were tested but disabled.

**LIKELY Q&A**
- *Why MD5 not perceptual hash?* — Bit-exact match means zero false positives — we will never wrongly merge two different FIRs. Perceptual hash would be more lenient but could accidentally de-duplicate distinct cases.
- *What if all three engines fail?* — We log the failure, alert the super-admin, and return an error. The FIR is held pending manual review. Fallback: an admin can manually type the four fields via the web UI.
- *How accurate is the OCR?* — On a 120-FIR test set, field-level accuracy: ~96% for date/FIR number (clear printed), ~92% for area name (Urdu text on form), ~88% for sections (heavily abbreviated). Cache hit rate on re-uploads is 100% by definition.
- *Why not just use Google Vision API for everything?* — Cost. Tesseract handles most cases free and fast. We reserve paid APIs (Gemini, Mistral) for hard cases where local engines fail.

---

## Slide 23 — Urdu Intelligence Layer

**SAY**
OCR almost never returns a perfect string. So between OCR and the database we have an **Urdu intelligence layer**. Four numbers tell the story: **268** Urdu locations in our dictionary covering Roman-Urdu spelling variations like "DHA Phase 6" / "DHA VI" / "Defence VI"; **84** police thanas whitelisted with all the OCR misreadings we have ever seen logged for them; **721** Pakistan Penal Code sections mapped to crime names; **975** image hashes in the dedupe cache. The matching itself is **fuzzy** — we compare each OCR'd word to the dictionary using `SequenceMatcher`, a string-similarity score from 0 to 1. If similarity is at least 0.55 we treat it as a candidate; at 0.75 we lock it in as the corrected name. Multi-word phrases get a separate 0.55 threshold. So "Mall Roads" automatically becomes "Mall Road". On top of that, the **AI law verifier** is a two-tier LLM gate: OCR can hallucinate fake PPC numbers (e.g. read "380" when the actual handwriting is "390"). Before we trust any extracted section we ask an LLM "is section 380 real, and does it match this story about a stolen motorcycle?" If yes, accepted. If no, the FIR is flagged for human review. Primary LLM is **Groq's Llama-3.3-70B** — fast and free; if Groq is rate-limited we fall back to **OpenRouter's Llama-3.1-8B**.

**KEY NUMBERS**
- 268 / 84 / 721 / 975 • Fuzzy thresholds: 0.55 candidate, 0.75 lock • Groq → OpenRouter cascade.

**GAP**
Slide repeats "0.55" twice (single-word and multi-word). They use the same numeric threshold but different scoring functions internally — clarify if asked.

**LIKELY Q&A**
- *What if the LLM also hallucinates?* — Two-tier check (Groq then OpenRouter) plus a hard whitelist: any returned section number must exist in our `law_sections` table. If both LLMs reject, the FIR is flagged, not silently dropped.
- *How do you handle unseen Urdu spellings?* — Fuzzy match catches near-misses; if score is below 0.55 we keep the raw OCR text and surface it to the admin for one-click "add to dictionary".

---

## Slide 24 — Alerts & Background Jobs

**SAY**
Three notification channels all driven from the same `crimes` table. **Live alert** — the user's *current* GPS enters a known hotspot, push fires within seconds. **Incident alert** — a verified crime is recorded within **5 km** of the user's saved home or work, push *and* email both go out. **Weekly digest** — a personalised safety report is emailed every Sunday at 17:05 PKT. To stop notification fatigue we have a **60-minute cooldown by default**: if a user has already been alerted about a particular hotspot, we wait an hour before re-alerting about the same one. Otherwise a single noisy area would spam them all evening.

All of these settings can be tuned. We have a **system settings panel** where admins can change:
- **Alert radius**: the distance around home/work to trigger alerts (default 5 km, range 1-50 km per user)
- **Alert cooldown**: how long to wait before re-alerting (default 60 minutes, range 1-1440 minutes)
- **Risk thresholds**: what score is "High" vs "Medium" (default 70 / 40)
- **Session timeouts**: how long someone stays logged in (15 min for regular users, 60 min for admins)
- **Login attempts**: how many wrong passwords before lockout (default 5 attempts)

These are live settings — change one and it takes effect immediately, no server restart needed.

Three APScheduler jobs run inside the FastAPI process: **`monitor_saved_locations`** runs every minute and pushes live alerts when a saved-location user crosses into a hotspot; **`poll_new_incidents`** also runs every minute, looks for newly inserted verified crimes and matches them against every active geofence; **`weekly_safety_reports`** runs Sundays at 17:05 PKT, aggregates the user's week and emails the HTML digest.

**How browser location permission works:** When the user clicks "Enable Live Location," the browser shows the standard "Allow location?" popup. The user taps Allow, and the browser starts sharing GPS coordinates. If they tap Deny, we show a fallback where they pick an area manually instead. Behind the scenes, we use the browser's native `geolocation` API — the same one Google Maps uses. The location data is encrypted in transit and only stored on our secure server.

**KEY NUMBERS**
- 3 notification channels • 5 km default (1-50 km per user) • 60 min default cooldown • 50+ configurable system settings • 3 APScheduler jobs.

**GAP**
Slide does not list all the configurable settings. If asked: notification_radius, alert_cooldown_minutes, high_risk_threshold, medium_risk_threshold, session_timeout, max_login_attempts, and 40+ more in the system_settings table. Frontend uses `navigator.permissions.query({ name: 'geolocation' })` for permission checks and `navigator.geolocation.getCurrentPosition(...)` to get coordinates.


On the dashboards side, we have three role-specific UIs. The **User dashboard** has 30+ screens — view the heatmap, request an AI-routed path, manage saved locations, opt into push, request an extra patrol from the police. The **Admin dashboard** has 20+ screens — upload FIRs through the OCR pipeline, edit and verify crimes, manage citizen accounts, post system-wide alerts, view the audit log. The **Super-Admin dashboard** has 15+ screens — approve sensitive actions, manage the PPC sections list, live-edit system settings (alert radius, cooldown, thresholds, session timeouts), manage admins, run analytics on admin behaviour. The system settings changes take effect instantly — no redeployment required
**LIKELY Q&A**
- *What happens if the user is offline?* — The push lands in the OS notification centre because the Service Worker registered with the browser handles it independently of the SafeVision tab being open.
- *Why APScheduler runs every 1 minute — is that a database hit?* — Yes, but a small one — we read only newly inserted rows since `last_seen_id`, ~10 rows on a busy minute, ~0 on a quiet one. Negligible cost.
- *Who can change system settings?* — Only super-admins. Admins can view settings but can't change them without a second super-admin approval (our two-person-rule principle).
- *Can a user disable alerts entirely?* — Yes, they can toggle notifications off. The app stores their preference and respects it. Alerts don't get queued up; they're simply not generated.
- *What if the browser blocks location requests?* — We show a helpful message explaining why we need it and how to re-enable it in browser settings. They can still use the app, just without live location alerts.
- *How often is location updated?* — Every 10-30 seconds when location tracking is on. We batch them to avoid hammering the server.

---

## Slide 24.5 — Emergency Contacts Module (Complete Technical Implementation)

**SAY**
This module is not just a static phone list. It is a full emergency workflow with API-backed contacts, call logging, and live operational counters. On load, the frontend calls `GET /api/emergency-contacts` and renders six emergency services (Police 15, Rescue 1122, Fire 16, Women Helpline 1099, Child Helpline 1121, Traffic 1915), each with response time, icon, and service scope. If the API fails, the UI has a built-in fallback list so the emergency page still works offline or during backend issues. The module also calls `GET /api/emergency-stats` every 30 seconds to show live values like calls today, active units, and resolved rate.

When a user taps **Call**, the UI immediately opens the dialer with `tel:` so emergency response is never blocked by server latency. In parallel, SafeVision logs the event to the backend. If the user is logged in, it first tries `POST /api/emergency-call`; if auth fails or there is no token, it automatically falls back to `POST /api/emergency-call/public`. The payload includes contact name/number, emergency type, caller latitude/longitude, and caller address. On the backend, this writes to `emergency_calls` with timestamp and status, and for authenticated users it also records activity telemetry through `log_user_activity(...)`.

The module also supports location sharing by SMS with map links (Google Maps, OpenStreetMap, Apple Maps, Bing Maps), coordinate precision, and timestamp, so responders can navigate quickly even if the user cannot explain their location verbally. Patrol-request backend support still exists in the codebase, but it is no longer surfaced in the public frontend.

From an engineering perspective, this module has all four layers implemented: frontend interaction, API contracts, DB persistence, and live stats refresh. It is a complete production feature, not a prototype.

**KEY NUMBERS**
- 6 emergency contacts • 3 user-facing core APIs (`/emergency-contacts`, `/emergency-call`, `/emergency-call/public`) • 1 live stats API (`/emergency-stats`) • 30-second stats refresh • Dual-path call logging (authenticated + public fallback).

**GAP**
Slide deck often treats emergency as a "call button" only. If asked: it is a full workflow module with call records, patrol queue generation, and stats telemetry backed by `emergency_calls` and `patrol_requests` tables.

**LIKELY Q&A**
- *What happens if user is not logged in?* — Emergency still works. The app uses `/api/emergency-call/public` and logs caller metadata as anonymous so availability is never blocked by auth.
- *Does a failed DB write block the phone call?* — No. Dial action happens first (`tel:`). Logging is best-effort in parallel.
- *Is patrol request separate from emergency call?* — Yes. Calls are immediate phone actions; patrol-request backend support exists, but the public frontend now focuses on emergency contacts, call, and location sharing.

---

## Slide 25 — Web-Push Pipeline & Role Dashboards

**SAY**
A quick word on how the alert actually reaches the user's phone. We use **VAPID** — Voluntary Application Server Identification — which is the modern web standard for sending notifications from a server to a browser. Our server holds a private key; the user's browser stored the matching public key when they first opted into notifications. Each notification we send is signed with the private key, the browser verifies the signature, and only then renders the toast. End-to-end this means: even when the SafeVision tab is closed, the user still receives the alert through the browser's push service (Mozilla, Google, Apple). And on the dashboards side, we have three role-specific UIs. The **User dashboard** has 30+ screens — view the heatmap, request an AI-routed path, manage saved locations, opt into push, request an extra patrol from the police. The **Admin dashboard** has 20+ screens — upload FIRs through the OCR pipeline, edit and verify crimes, manage citizen accounts, post system-wide alerts, view the audit log. The **Super-Admin dashboard** has 15+ screens — approve sensitive actions, manage the PPC sections list, edit system settings, manage admins, run analytics on admin behaviour.

One more thing about the dashboards: they are **not static**. Every single dashboard screen is **dynamically generated at login based on the admin's permission set**. The React frontend makes a call to `GET /admin/profile` after login, receives a JSON list of permissions, and then **decides which tabs, menus, and screens to render**. If an investigator logs in, they see the Crime Management and Approvals tabs. If an officer logs in, they see only Crime Entry and the read-only Audit Log. No hardcoding role names into the UI; no deploy needed to add a new permission category. The backend is the source of truth. This approach **reduces bugs** — we don't have mismatches between what the backend enforces and what the frontend shows — and **improves security** — a compromised frontend cannot trick an admin into seeing data they shouldn't see, because the backend still enforces every permission check on every request.

To make that more concrete: in the **User Dashboard**, the risk modules are the map, the AI route planner, the saved-location safety cards, and the Area Safety Profile / Area Comparison screens. Those are the parts a citizen uses to answer, "Is this area safe for me right now?" In the **Admin Dashboard**, the important risk modules are Command Center, Crime Risk Prediction, Area Crime Risk Matrix, Area Risk Intelligence, Area Comparison, and City Overview. Those let an admin switch from one area to many areas, compare crime types, and inspect the city as a whole. In the **Superadmin Dashboard**, the same intelligence is still there, but wrapped with control modules like settings, approvals, user management, and PPC section management. So the product is not three separate systems — it is one prediction engine presented through three role-based workspaces.
To make maps explicit with code-backed modules: User routes and map intelligence are powered by `/api/crimes/compare-routes`, `/api/crimes/analyze-route-safety-ai`, `/api/crimes/area-safety-profile`, and `/api/crimes/areas/{area}/heatmap`; admin command views are powered by `/api/crimes/intelligence-dashboard` plus area and trend endpoints. These map modules are available across all three dashboard roles, but each role sees different tabs and controls through permission-based rendering.

**KEY NUMBERS**
- VAPID standard • 30+ user screens • 20+ admin screens • 15+ super-admin screens.

**GAP**
Slide does not say what happens on iOS Safari. Verbal: web push works on iOS 16.4+ when the SPA is installed as a PWA via "Add to Home Screen"; older iOS gets the in-app toast only.

**LIKELY Q&A**
- *Why role separation rather than one dashboard with feature flags?* — Cleaner permission model, smaller bundle per role, and easier UX testing per persona.
- *Can a user demote themselves?* — No. Account-tier changes always go through the super-admin approval gate.

---

## Slide 25.5 — Maps Modules Across All Three Dashboards (Huge Detail)

**SAY**
Map functionality in SafeVision is role-layered but technically unified. The same backend crime intelligence engine powers user, admin, and super-admin map views; permissions only change which controls are visible. At the user layer, the map stack is focused on personal safety decisions: heat intensity view, area safety profile, and AI route comparison between start and destination points. At the admin layer, the same spatial data is re-framed for operations: multi-area comparison, command-center metrics, and city-level risk distribution. At the super-admin layer, those same map analytics are combined with governance controls, approvals, and settings to convert map insight into policy action.

The user route module is implemented through `AIRouteAnalysis` + `AIRouteMap` in frontend. It supports typed addresses and manual marker placement on map. On submit, frontend calls `POST /api/crimes/compare-routes` with start/end coordinates, travel date/time, and optional typed-name hints. Backend then: (1) requests alternate paths from OSRM, (2) samples route points, (3) reverse-geocodes points through Nominatim, (4) scores each route point with AI route analyzer, (5) applies baseline normalization against historical area risk, (6) computes aggregate route score, and (7) returns labeled route cards (`safest`, `fastest`, `shortest`, `alternative`). The frontend renders route cards with distance, traffic-adjusted duration, risk score, areas crossed, and crime-type chips.

Important accuracy point for viva: the active safety-route module is **analysis-first**, not navigation-first. It gives route comparison, risk percentages, and details. It does **not** perform real-time turn-by-turn driving mode in the deployed dashboard route tab. There is a separate `NavigationSystem.jsx` component in codebase with start-navigation UI, but it is not currently mounted in `UserDashboard.jsx`; production routing tab uses `AIRouteAnalysis`.

For admin and super-admin, map intelligence is wired through crime analytics endpoints (`/api/crimes/intelligence-dashboard`, area detail endpoints, heatmap endpoints) and visualized in role dashboards (command center, area matrix, area comparison, city overview). This is why your presentation should say "one map intelligence engine, three role-specific workspaces".

**KEY NUMBERS**
- 3 map workspaces (User/Admin/Superadmin) • 2 core route APIs (`/compare-routes`, `/analyze-route-safety-ai`) • OSRM + Nominatim + AI scoring pipeline • Up to 3-5 route options labeled by objective • Permission-gated rendering per role.

**GAP**
If asked "Do you have Google-Maps-style Go navigation inside route safety tab?" answer: not in the deployed route-analysis tab. The tab is for risk-scored comparison; step-by-step navigation is outside this module.

**LIKELY Q&A**
- *Are maps duplicated for each dashboard?* — No. Backend intelligence is shared; frontend exposes role-scoped views using permission checks.
- *How do you ensure safest label is not random?* — Backend applies deterministic labeling after computing normalized route scores and uniqueness filtering.
- *What if geocoding fails for one route point?* — Backend falls back to broader area defaults and continues analysis; it does not crash the whole route response.

---

## Slide 25.6 — Technical Completeness Check (Module-by-Module)

**SAY**
To prove implementation completeness, we check each module through five layers: UI component, API endpoint, DB persistence, background/live update, and permission/security guard.

For **Maps & Route Safety**: UI is implemented (`AIRouteAnalysis.jsx`, `AIRouteMap.jsx`), API is implemented (`/api/crimes/compare-routes`, `/api/crimes/analyze-route-safety-ai`, area profile and heatmap endpoints), DB-backed risk baseline is implemented (crime aggregates + unified risk scoring), live external services are integrated (OSRM + Nominatim), and role gating is implemented through permission-driven dashboard rendering.

For **Emergency Contacts**: UI is implemented (`EmergencyContacts.jsx`), API is implemented (`/api/emergency-contacts`, `/api/emergency-call`, `/api/emergency-call/public`, `/api/emergency-stats`), DB writes are implemented (`emergency_calls`), live refresh is implemented (30-second stats polling), and safe fallback is implemented (public call endpoint + UI fallback contact list). Patrol-request support still exists in the backend, but it is no longer exposed in the public frontend.

This is the standard to defend in viva: each major module is complete across all required layers, not just frontend visuals.

**KEY NUMBERS**
- 5-layer completeness rubric per module • Maps module: shared engine across 3 dashboards • Emergency module: 5 dedicated endpoints + 2 persistence tables.

**GAP**
If evaluator asks for missing pieces: the missing piece is not implementation of these modules; the only missing piece is turning the separate navigation prototype into the default production route tab, if your product direction requires full turn-by-turn mode.

**LIKELY Q&A**
- *How do you prove "complete" and not "demo-only"?* — Show endpoint call, DB row creation, and UI refresh in one live flow.
- *What is intentionally out-of-scope?* — Full in-app Google-like navigation mode is separate from the deployed risk-comparison route module.

---

## Slide 25.7 — Full Technical Matrix (All Core Modules)

**SAY**
For a viva-level technical defense, here is the module-by-module matrix we use internally. Every module is checked across seven dimensions: purpose, frontend component, backend API, persistence layer, background/live behavior, security guard, and operational evidence.

**1) Authentication & Session Module**
- Purpose: identity, login, token lifecycle, role-aware session duration.
- Frontend: login/register/2FA flows and token persistence.
- Backend: auth routes with JWT issuance and validation.
- Persistence: users and profile tables plus login-attempt tracking.
- Background/live: token refresh and session timeout behavior.
- Security: bcrypt/passlib hashing, role-scoped TTL, rate-limit controls.
- Evidence: admin short-lived tokens and protected-route checks.

**2) Email Verification & Unverified Cleanup Module**
- Purpose: enforce verified accounts and remove dormant/unverified users.
- Frontend: verification page and retry flow.
- Backend: verification token generation, warning email, delete email, cleanup trigger endpoint.
- Persistence: `is_verified`, `email_verification_token`, `token_expires_at`, `deletion_warning_sent_at`.
- Background/live: periodic cleanup job with warning + delete thresholds.
- Security: verified-account gate before full feature access.
- Evidence: audit rows for system-driven deletions and super-admin digest.

**3) Audit Logging & Admin Traceability Module**
- Purpose: who-did-what-when-where trace for all sensitive admin actions.
- Frontend: audit table, recent events, SSE-driven admin activity feed.
- Backend: central `log_admin_action(...)` write path + retrieval endpoints.
- Persistence: append-only `audit_logs` JSON-detail records.
- Background/live: real-time stream updates every few seconds.
- Security: immutable-style evidence trail and forensic support.
- Evidence: action rows for admin register/update/delete/approval events.

**4) RBAC & Permissions Module**
- Purpose: granular role-based feature exposure and API enforcement.
- Frontend: dynamic menus/tabs/buttons generated from permission payload.
- Backend: permission verification per protected endpoint.
- Persistence: JSON permissions in admin records.
- Background/live: permissions reloaded on next login/token refresh.
- Security: super-admin-only role/permission mutation paths.
- Evidence: permission diff stored in audit logs during updates.

**5) Maps & Risk Intelligence Module**
- Purpose: spatial awareness for users and command-level city insights.
- Frontend: heat layers, area profile panels, role-specific map dashboards.
- Backend: area profile, heatmap, intelligence dashboard, route-risk endpoints.
- Persistence: crimes + area aggregates used for risk baseline.
- Background/live: fresh risk values from current DB state and request-time computations.
- Security: role-scoped dashboard access and controlled sensitive views.
- Evidence: endpoint responses for area risk + map overlays by role.

**6) Route Safety Module (Deployed Behavior)**
- Purpose: compare route options by safety, distance, and travel time context.
- Frontend: `AIRouteAnalysis` / `AIRouteMap` route cards and detailed risk points.
- Backend: `/api/crimes/compare-routes` and `/api/crimes/analyze-route-safety-ai`.
- Persistence: baseline risk derived from historical crime records by area.
- Background/live: request-time OSRM + geocoding + AI scoring pipeline.
- Security: authenticated usage in dashboard context.
- Evidence: route labels (`safest`, `fastest`, `shortest`, `alternative`) with risk metadata.
- Clarification: deployed route tab is analysis-first; no in-tab Google-style turn-by-turn "Go" mode.

**7) OCR + PPC Validation Module**
- Purpose: extract FIR fields from Urdu scans and validate legal section integrity.
- Frontend: upload/review/verify flow for FIR processing.
- Backend: OCR orchestration + section validation + area normalization.
- Persistence: extracted fields committed after admin verification.
- Background/live: cache hits short-circuit processing for repeated uploads.
- Security: validation gates and review controls before model-impacting inserts.
- Evidence: improved downstream risk quality from verified FIR ingestion.

**8) Alerts & Notification Module**
- Purpose: proactive risk notifications without alert fatigue.
- Frontend: browser notification center, read-state actions, preferences.
- Backend: subscribe/unsubscribe/check-risk/check-location/heartbeat APIs.
- Persistence: subscriptions, notification rows, delivery/read states.
- Background/live: scheduled monitors and push dispatch.
- Security: auth-bound preference controls; safe fallbacks for unavailable channels.
- Evidence: real-time and periodic alert flows in production.

**9) Emergency Contacts Module**
- Purpose: emergency communication and rapid request escalation.
- Frontend: emergency contacts, one-tap call, location share.
- Backend: emergency contacts, emergency call logging, public fallback logging, patrol-request backend support, emergency stats endpoint.
- Persistence: emergency call records and patrol request records.
- Background/live: 30-second stats refresh in UI.
- Security: authenticated route + anonymous-safe fallback for emergency calls.
- Evidence: successful call log insertion and emergency stats refresh; patrol support remains backend-only.

**10) Admin/Super-Admin Operations Module**
- Purpose: governance, approvals, analytics, and system control.
- Frontend: role dashboards, approvals, reports, settings, user/admin management.
- Backend: admin router endpoints for management, analytics, and policy controls.
- Persistence: admin actions, approvals, settings, audit events.
- Background/live: SSE/event feeds and scheduled maintenance jobs.
- Security: super-admin restrictions + two-person-rule workflows.
- Evidence: controlled privileged actions with full audit trace.

This matrix is how you defend "implemented" with evidence instead of claims. If an examiner challenges any module, move one row at a time: UI → API → DB → security → live behavior.

**KEY NUMBERS**
- 10 core modules in matrix • 7 validation dimensions per module • Evidence chain: UI → API → DB → Security → Live behavior.

**GAP**
If asked what is still not default in production UX: the standalone turn-by-turn navigation prototype exists in code but is not the default mounted route tab in user dashboard.

**LIKELY Q&A**
- *How do you avoid over-claiming?* — We only mark a module complete if all seven dimensions are present and demonstrable.
- *What is your quickest demo proof?* — Trigger one user action and show the full chain: visible UI change, API response, DB row, and audit/event trace.

---

## Slide 26 — Key Engineering Trade-Offs

**SAY**
Every choice on this slide was deliberate. We picked **Random Forest plus Poisson** over **a single deep neural net** because we can explain *why* an area scored High (feature importances, decision paths), our latency stays sub-200 ms, and the model file fits under 50 MB. We picked **TiDB Cloud** over **PostgreSQL plus PostGIS** because of the free tier and MySQL wire compatibility, knowing the trade-off was that we had to write our own Haversine distance instead of calling a built-in spatial function. We picked **MD5 image fingerprinting** over **perceptual hash (pHash)** because bit-exact matches give us zero false positives on FIR re-uploads, which matters because a false merge would silently corrupt the crime corpus. We picked **EasyOCR primary with Tesseract fallback** over **cloud-only OCR** because most FIRs never need to leave our server — better for bandwidth, cost, and the privacy of sensitive police data. We picked **bcrypt-SHA256** over **Argon2id** because passlib has first-class support for it, and the SHA-256 wrapper safely handles long Urdu names that would otherwise get truncated by bcrypt's 72-byte limit. We picked **VAPID web push** over **Twilio SMS** for $0/month, no app install, no Pakistani short-code registration. And we picked **fixed 35/15/30/10/10 unified weights** over **pure ML output** because the explanation in plain English of *why* an area is "High" matters more to citizens than the last few percentage points of accuracy.

**KEY NUMBERS**
- 7 trade-offs documented; every alternative was prototyped or seriously evaluated.

**GAP**
Slide labels the unified weights "35/15/30/10/10" — that is volume / severity / recency / trend / time, *not* the order on slide 18. The numbers themselves are correct.

**LIKELY Q&A**
- *Did you A/B-test any of these choices?* — Yes for OCR (cloud-only versus hybrid on the same 120-FIR test set, hybrid won on cost-per-correct-row) and for unified weights (replayed historical alerts, current weights minimised false-Critical incidents).
- *What would you change on a redo?* — We would invest earlier in spatial-index alternatives (KD-tree per area cluster) — the Python Haversine works at our scale but would not at 10× volume.

---

## Slide 27 — Metrics & Evaluation

**SAY**
Four headline numbers backed by our test runs. **100 % cache hit rate** on re-uploads of the same FIR — by construction, because the MD5 of the same bytes is always the same. **Around 97 % push delivery success** to active subscriptions; the missing 3 % are stale subscriptions from browsers the user has since uninstalled, and we auto-prune those from the database when the push gateway returns "expired". **5-fold stratified cross-validation** for the Random Forest, which protects the rare High class from being lost in the average. **120 ms median predict latency**, with the 95th percentile staying below 480 ms even on a cold worker. The full OCR field-level accuracy on our 120-FIR test set runs around 92 % on the place-of-incident row, which is the row that matters most for the model.

**KEY NUMBERS**
- 100 % cache • ~97 % push • 5-fold stratified CV • 120 ms median / 480 ms p95 • 92 % field accuracy on place row.

**GAP**
Slide does not state the test-set size (120 FIRs) — say it explicitly so the numbers feel grounded.

**LIKELY Q&A**
- *How representative is your 120-FIR sample?* — Stratified across stations and crime categories — covers theft, robbery, assault, and miscellaneous in the same proportion as our full corpus.
- *Is 92 % field accuracy good enough for a court of law?* — No, and we don't claim it is. The field accuracy is good enough for *aggregate analytics and risk scoring*; legal use of any individual FIR still requires human review, which is why the admin verification step is mandatory.

---

## Slide 28 — What's Next + Thank You

**SAY**
Six future-work items, ranked by impact. **Self-hosted Photon** to replace Nominatim — that removes the 1-second-per-request rate limit on geocoding, important when bulk-importing historical FIRs. **DBSCAN hotspot mining** to find emerging clusters before they cross the High threshold — we currently react, this would let us forecast. **Mobile PWA** with an offline-first crime cache for low-connectivity areas of Lahore, where many citizens have intermittent data. **Punjab Safe Cities API** integration — when access is granted, live CCTV-based corroboration. **Cheaper LLM for PPC** — moving from Groq Llama-70B to a smaller distilled model is around a 10× cost reduction. And **Citizen Reports v2** with photo evidence and reverse-image search to detect duplicate citizen uploads at intake. With that — thank you. SafeVision is roughly 142,000 lines of code, 128 endpoints, 37 tables and 12 ML and OCR services, all running in production. We are happy to take questions and demonstrate any flow you would like to see.

**KEY NUMBERS**
- 6 future-work items • Final summary: 142k LOC / 128 endpoints / 37 tables / 12 services.

**GAP**
None — close strong. Pause for questions.

**LIKELY Q&A**
- *What is missing from the current product?* — Mobile-native packaging (currently PWA-quality on Android, weaker on older iOS) and a forecasting layer that predicts emerging hotspots, not just current ones.
- *Production usage?* — System is live but in pilot — public links are restricted; the demo today is on the live backend with a test account.

---

# Delivery Tips

1. **Time per slide**: target ~1.5 min average. Slides 1, 2, 28 stay under 1 min; slides 6, 15, 18, 22 deserve closer to 2 min because they get the most questions.
2. **The two questions you will definitely get**: (a) *Why three ML models and not one?* — slide 15 SAY block has the answer. (b) *What are your 3 OCR engines?* — slide 22 GAP block has the answer.
3. **If asked something you do not know**: do not invent. Say "that lives in `<file>:<line>` — I can pull it up if useful." It is more credible than guessing.
4. **Memorise these 8 numbers** — they recur in 3+ questions: 142,000 LOC; 128 endpoints; 37 tables; 1.5 km geofence; 35/30/15/10/10 weights; 200 trees / depth 15; λ exponent 2.2; cooldown 60 min.
5. **Demo flow if asked live**: (a) login → (b) dashboard with All-Time score → (c) area profile for any DHA / Iqbal Town area → (d) AI route between two pins → (e) admin panel showing OCR upload screen.
