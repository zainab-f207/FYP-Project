# CrimeVision — DETAILED PRESENTATION GUIDE (Part 2 of 2)

> This is **Part 2**: Frontend deep-dive (Chapter 11), reports/community/emergency (12-15), background jobs (16), tricks & techniques (17), challenges (18), 100+ viva questions and answers (19), demo script (20), printable cheat sheets (21).

---

# CHAPTER 11 — FRONTEND DEEP DIVE

## 11.1 Application bootstrap (`App.jsx`)

When the app loads:
1. **`cleanupInvalidTokens()`** runs — removes any malformed JWTs from localStorage.
2. **Service worker registers** — `navigator.serviceWorker.register('/sw.js', {scope: '/'})`. This enables offline support and push notifications.
3. **ErrorBoundary** wraps everything — if any React component throws, we show a friendly error screen instead of a blank page.
4. **Provider chain mounts**: `Router → SystemSettingsProvider → NotificationProvider → AuthProvider → AppRouter`.

## 11.2 Auth context (`AuthContext_updated.jsx`)

A React context that exposes:
- `isAuthenticated`, `user`, `loading`, `initialized`
- `login()`, `logout()`, `register()`
- `updateUser()`, `refreshToken()`

It runs once at mount: reads `access_token` from localStorage, calls `/auth/me` to get user data, sets `initialized=true`. Until then, the `AppRouter` shows a spinner.

## 11.3 Token validator (`TokenValidator.jsx`)

Continuously validates the JWT in the background:
- On window focus: re-checks token validity.
- On 401 response: calls `/auth/refresh-token`, retries the failed request.
- If refresh fails: logs out and redirects to `/login`.

## 11.4 Protected vs public routes

```jsx
<Route path="/dashboard/*" element={
  <ProtectedRoute>
    {user?.role === 'admin'      ? <AdminDashboard /> :
     user?.role === 'superadmin' ? <SuperAdminDashboard /> :
                                    <UserDashboard />}
  </ProtectedRoute>
} />
```

`ProtectedRoute` checks `isAuthenticated`. If false, redirects to `/login` and remembers where the user wanted to go (`location.state.from`). After login, they land back where they were trying to go.

`PublicRoute` is the reverse — wraps `/login`, redirects to `/dashboard` if already authenticated.

## 11.5 User Dashboard — every card explained

The user dashboard (`UserDashboard.jsx`, 2000+ lines) renders the following cards in a responsive grid:

### Card 1 — Safety Score Card
- Big circular gauge (0–100)
- Letter grade (A/B/C/D/F)
- Coloured ring (green ≥80, yellow 60–79, orange 40–59, red <40)
- Subtitle: "Your home area: Iqbal Town"
- Click → opens `SafetyScoreExplainer` modal that breaks down the score into its 5 components (volume, severity, recency, trend, time)

### Card 2 — Risk Factors Card
- List of top 5 crime categories near user's home
- Each shown with percentage of total: "Theft & Robbery — 29%"
- Sourced from `/api/auth/me/stats?lat=...&lng=...&time_filter=12m`
- Clickable: opens detailed view

### Card 3 — Weekly Alerts Card
- Number of alerts received this week
- Comparison arrow vs previous week (↑ +3, ↓ -2)
- Click → opens alerts inbox

### Card 4 — Safe Routes Card
- Count of routes successfully planned this week
- Encourages engagement

### Card 5 — Nearest Safe Zone
- Name (e.g., "Park Avenue Mall")
- Distance in km
- Quick link to route there

### Section 6 — AI Route Analysis (`AIRouteAnalysis.jsx`)
The crown jewel:
1. Two location inputs (with autocomplete)
2. Mode selector (driving / walking / bicycle)
3. Time-of-day selector (now / specific hour)
4. **Calculate** button → POST to `/api/crimes/compare-routes`
5. Map (`AIRouteMap.jsx`) draws all 3 routes in different colours
6. Right panel: route cards with safety score, distance, duration, alerts
7. **Recommended** badge on the safest route
8. Click a route → it becomes the active one (others fade)

### Section 7 — Prediction Section (`PredictionSection.jsx`)
1. Area autocomplete (loads from `/api/areas`)
2. Crime type autocomplete (loads from `/api/crime-types`)
3. Date picker (default = tomorrow)
4. Time picker (optional)
5. **Predict** button → POST to `/api/predict-risk`
6. Result card shows:
   - Big risk percentage
   - Risk level badge
   - Confidence indicator
   - "Best 3 days to visit" list
   - "Best 3 hours" list (when time provided)
   - Visit-time comparison bar chart (8AM/2PM/8PM/11PM)

### Section 8 — Crime Heatmap (`HeatMapLayer.jsx`)
- Embedded Leaflet map
- `leaflet.heat` plugin shows crime density
- Filter dropdown: All / 7d / 30d / 12m / All time
- Filter by crime type
- Click a hot spot → popup with recent crimes

### Section 9 — Browser Notifications (`BrowserPushSetup.jsx`)
1. Detects browser support (`'PushManager' in window`)
2. If unsupported → shows a friendly message
3. Otherwise: button "Enable Notifications"
4. On click:
   - `Notification.requestPermission()`
   - Wait for service worker ready
   - `pushManager.subscribe({applicationServerKey, userVisibleOnly: true})`
   - POST subscription to `/api/alerts/browser-notifications/subscribe`
5. Once subscribed: shows green check + "Test Notification" button

### Section 10 — Profile Modal (`ProfileModal.jsx`)
A multi-tab modal:
- **Personal Info**: name, email, phone, avatar upload
- **Locations**: home + work (with map picker)
- **Security**: change password, enable 2FA (QR code), connect Google
- **Alert Preferences**: per-category toggles, radius slider, quiet hours, crime-type filters
- **Privacy**: location tracking toggles
- **Sessions**: logout from other devices

### Section 11 — Quick Actions
4 big buttons:
- **🚨 SOS** → posts to `/api/emergency-call/public` with current GPS
- **🚓 Patrol Request** → opens form
- **📋 Report Incident** → opens community report form
- **📞 Emergency Contacts** → opens contact list modal

### Section 12 — Safety Radar Chart (`SafetyRadarChart.jsx`)
A radar (spider) chart with 5 axes:
- Violent crime safety
- Property crime safety
- Personal safety
- Daytime safety
- Nighttime safety

Computed from `calculate_breakdown()` in `utils/risk.py`. Lets users see at a glance which dimension is weakest in their area.

## 11.6 Admin Dashboard

The admin dashboard (`AdminDashboard.jsx`) has a left sidebar with these panels:

### Panel 1 — User Management Summary
Cards showing:
- Total users / active users / new this week
- Recent registrations (table)
- Quick "Verify" / "Suspend" actions

### Panel 2 — Crime Heatmap (full city)
Same heatmap as the user dashboard but with:
- Larger viewport
- Click-to-add-crime mode
- Bulk selection for verification

### Panel 3 — OCR Panel (`OCRPanel.jsx`)
The admin's main tool:
1. Drag-and-drop FIR image
2. Live preview with crop overlay
3. **Extract** button → POST to backend
4. Returns:
   - Extracted thana name (with confidence)
   - Extracted date
   - Extracted time
   - Extracted PPC sections
   - Geocoded lat/lng
5. Admin can edit any field before saving
6. **Save** button → inserts into `crimes` with `status='unverified'`
7. After save, RF predicts `risk_level` automatically

### Panel 4 — Admin Prediction Panel
Same prediction tool as user dashboard but with admin extras:
- Bulk prediction (paste a CSV of areas → predict all)
- Compare two areas side by side
- Export predictions as CSV

### Panel 5 — Reports Panel (`ReportsPanel.jsx`)
- Generate report: pick type (crime / activity / health), date range, format (PDF/Excel/CSV), filters
- Schedule report: same fields + cron-style schedule + recipients email list
- History: download / delete past reports

### Panel 6 — Notifications Panel
- View all system alerts
- Send a custom alert to all users in an area (radius selector)
- View browser-push subscription count

### Panel 7 — Recent Activity
A live-updating feed (uses Server-Sent Events from `/admin/notifications/stream`) showing:
- Login events
- New crime added
- New user registered
- OCR extraction completed

### Panel 8 — Approval Requests
For sensitive admin actions, a list of pending approvals waiting for super-admin review.

### Panel 9 — Analytics Panel (`AnalyticsPanel.jsx`)
Charts:
- Crime trend (last 12 months) — line chart
- Top 10 hotspot areas — horizontal bar
- Crime type distribution — doughnut
- Heatmap of (day-of-week × hour-of-day) — to spot peak times

## 11.7 Super-Admin Dashboard

`SuperAdminDashboard_updated.jsx` extends the admin one with:

### Panel A — Admin Management
- List of all admins
- Create new admin (`AdminRegistrationForm.jsx`)
- Edit permissions JSON
- Disable/enable account
- Force logout

### Panel B — Permission Matrix (`PermissionMatrix.jsx`)
A grid: rows = admins, columns = permission keys (manage_users, view_reports, edit_settings, ...). Toggle checkboxes to grant/revoke.

### Panel C — Audit Logs (`AuditLogs.jsx`)
Searchable, filterable, paginated table:
- Filter by admin, action, date range
- Click a row → see full JSON details
- Export to CSV

### Panel D — System Logs (`SystemLogs.jsx`)
Application-level logs (errors, warnings, info). Filter by log_type.

### Panel E — System Settings (`SystemSettings.jsx`)
Edit `system_settings` table values:
- `notification_radius` (km)
- `alert_threshold` (low/medium/high)
- `admin_session_timeout` (minutes)
- `email_template_brand`
- `model_version` (forces use of a specific model file)

### Panel F — PPC Management (`PPCManagement.jsx`)
- Browse 18,025 law sections (paginated)
- Filter by law_type (PPC, ATA, PECA, ...)
- Click a section → "Verify with AI" button → calls `/api/law-sections/verify-ai/{id}`
- AI returns suggested title + confidence + citations
- Super-admin can **Approve** (sets `is_verified=1`) or **Edit** then save

### Panel G — Risk Map Modal (`RiskMapModal.jsx`)
Full-screen heatmap with admin controls:
- Show predicted risk for tomorrow
- Toggle police station overlay
- Toggle hospital overlay
- Click area → see all crimes in that area

### Panel H — Analytics Dashboard
Higher-level than admin's: city-wide trends, year-over-year comparisons, ML model performance metrics (accuracy, OOV rate, retraining history).

## 11.8 Public pages (no login required)

- **`/`** (`MainWebsite.jsx`) — landing page with hero, features, statistics, testimonials
- **`/risk-prediction`** (`RiskPredictionPage.jsx`) — try the prediction tool without login
- **`/crime-map`** (`CrimeMapPage.jsx`) — public crime heatmap
- **`/emergency`** (`EmergencyPage.jsx`) — emergency contacts directory
- **`/about-project`** (`ProjectVideoPage.jsx`) — project introduction video
- **`/login`**, **`/verify-email`**, **`/reset-password`**, **`/logout`**, **`/autologin`**

## 11.9 Shared utilities

### `services/apiService_updated.js`
Axios instance with:
- Base URL auto-detection (`localhost:8000` in dev, `https://crimevision-api.onrender.com` in prod)
- Request interceptor: attaches `Authorization: Bearer <jwt>`
- Response interceptor: catches 401, calls refresh-token, retries

### `contexts/SystemSettingsContext.jsx`
Loads global settings from `/admin/public-settings` once at app load, exposes them to every component (e.g., the current notification radius, brand name, version).

### `contexts/NotificationContext.jsx`
Manages toast notifications and the in-app notification bell.

### `utils/tokenCleanup.js`
On app load, scans localStorage for malformed JWTs and removes them.

---

# CHAPTER 12 — REPORTS GENERATION

## 12.1 Three report types

| Type | Audience | Contents |
|---|---|---|
| **Crime Summary** | Police, citizens | Total crimes, breakdown by type/risk/area, hotspot ranking, time-of-day distribution, trend chart |
| **User Activity** | Super-admin | Active users, new registrations, login frequency, dashboard engagement |
| **System Health** | Super-admin | Uptime, DB size, alert success rate, OCR accuracy, model performance |

## 12.2 Three formats

### PDF (reportlab)
- A4 page with branded header (CrimeVision logo)
- Title + date range + filters used
- Charts embedded as PNG images (rendered with matplotlib then included)
- Tables with alternating row colours
- Footer with page number and generation timestamp

### Excel (openpyxl)
- Multiple sheets: Summary, Detail, Charts, Filters Used
- Conditional formatting (red cells for High risk)
- Auto-fit column widths
- Frozen header row
- Hyperlinks back to dashboard

### CSV
- Raw data only, UTF-8 BOM for Excel compatibility
- Pipe-separated for fields that might contain commas

## 12.3 Generation pipeline

```python
# 1. Get filtered data
data = get_crime_summary_data(date_from, date_to, area, crime_type)

# 2. Build the file
file_path = generate_crime_summary_pdf(data, options)

# 3. Save metadata
report_id = save_report_to_db(
    report_type='crime_summary',
    file_path=file_path,
    file_size=os.path.getsize(file_path),
    parameters={'from': date_from, 'to': date_to, 'area': area},
    created_by=admin_username,
)

# 4. Return download URL
return {'download_url': f'/api/admin-reports/download/{report_id}'}
```

## 12.4 Scheduled reports

Stored in `scheduled_reports`:
- `schedule` column: `daily`, `weekly`, `monthly`, or cron string
- `next_run`: when to fire next
- APScheduler job ticks every 5 minutes, checks `next_run <= NOW()`, fires the report
- After firing: emails to `recipients` JSON list, updates `last_run`, computes new `next_run`

## 12.5 Filtered export

`/api/admin-reports/export-filtered?date_from=&date_to=&area=&crime_type=&format=csv` → instant CSV download. Used when admin wants raw data quickly.

---

# CHAPTER 13 — COMMUNITY MODULE

## 13.1 Purpose

Crime prevention is a community sport. We let users:
- Post local warnings to neighbours
- Form watch groups around their address
- Report incidents (anonymously if wished)
- Connect with neighbours / authorities
- Download safety guides

## 13.2 Watch groups

- Anyone can create a group: `name`, `area`, `radius_km` (default 2 km), `max_members` (50)
- Visible to users within radius
- Members can post community alerts that other members receive immediately
- Roles: member / moderator / admin

## 13.3 Community alerts

When a user posts a community alert:
1. Validates: severity, area, expiry
2. Inserts into `community_alerts`
3. Triggers the alert pipeline → all users within radius get push + email

## 13.4 Incident reports

Two-step flow:
1. Citizen reports → `community_incident_reports` with status=`reported`, `is_anonymous` flag
2. Admin reviews → can:
   - Mark as investigating
   - Convert to verified `crimes` record (which then enters the ML pipeline)
   - Resolve / close

This is how citizen-sourced data **enters our trained model** without polluting it.

## 13.5 Safety network

Users can send "connection requests" to other users (like LinkedIn) with `connection_type`:
- **neighbour** — same area
- **authority** — police officer / officer
- **emergency_contact** — someone to alert during SOS

## 13.6 Resource library

Admins upload PDFs (e.g., "What to do during a robbery", "Women's safety guide"). Citizens download them. Each download is logged, used for engagement metrics.

---

# CHAPTER 14 — EMERGENCY MODULE

## 14.1 SOS Button

Big red button on the user dashboard. On tap:
1. Capture GPS via `navigator.geolocation.getCurrentPosition()`
2. Reverse-geocode to get address (Nominatim)
3. POST to `/api/emergency-call` with: `{contact_name, contact_number, lat, lng, address, type}`
4. Backend:
   - Inserts into `emergency_calls`
   - Sends email + SMS to user's emergency contacts
   - Notifies the nearest admin/police via push
5. Returns confirmation; UI shows "Help is on the way" with audio alarm

## 14.2 Public SOS endpoint

`/api/emergency-call/public` — works **without authentication**. So any visitor on the public site can call for help.

## 14.3 Patrol requests

Citizens can request police patrol for an area:
1. Mark a location on map
2. Set urgency (low/medium/high)
3. Add description
4. POST to `/api/patrol-request`
5. Stored with `status='pending'`
6. Admin sees it in dashboard, assigns to officer (status=`assigned`), officer marks complete

## 14.4 Emergency contacts directory

System-wide list (stored in `system_settings` with key `emergency_contacts_json`):
- 15 (Police)
- 1122 (Rescue)
- 130 (Fire Brigade)
- 1099 (Ambulance)
- Local hospital numbers
- Women's helpline
- Suicide prevention

Returned via `/emergency-contacts`. Editable by super-admin.

## 14.5 Emergency stats

`/emergency-stats` returns:
- Calls in last 24h
- Most common emergency types (police 60%, ambulance 25%, fire 10%, general 5%)
- Average response time (from call to "completed" status)

---

# CHAPTER 15 — REAL-TIME LOCATION TRACKING

## 15.1 The opt-in story

Privacy-first. Tracking is **off by default**. User must:
1. Toggle `location_tracking_enabled` in profile
2. Grant browser geolocation permission when prompted

Users can disable any time. We never sell or share location data.

## 15.2 Update flow

Frontend hook:
```javascript
useEffect(() => {
  if (!locationTrackingEnabled) return;
  const watchId = navigator.geolocation.watchPosition(
    (pos) => {
      api.post('/api/location/update', {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        device_type: getDeviceType(),
      });
    },
    (err) => console.warn('GPS error:', err),
    { enableHighAccuracy: true, maximumAge: 30000, timeout: 30000 }
  );
  return () => navigator.geolocation.clearWatch(watchId);
}, [locationTrackingEnabled]);
```

Backend:
```python
@router.post("/update")
async def update_location(payload, current_user):
    # Reverse-geocode
    address = await reverse_geocode(lat, lng)

    # Compute risk for this exact spot
    safety_data = await get_real_safety_data(lat, lng, 1.0)

    # Save
    INSERT INTO user_location_history (...) VALUES (...)
    UPDATE users_info SET last_location_update = NOW()

    # If high risk and not yet alerted in this zone
    if safety_data['risk_level'] == 'High' and not_recently_alerted(user_id, lat, lng):
        trigger_live_risk_alert(user_id, lat, lng, address, safety_data)
```

## 15.3 Three location sources

| Source | When used | Accuracy |
|---|---|---|
| **gps** | User's browser sent valid coordinates | ~10-100m |
| **ip** | Browser denied GPS, fall back to IP geolocation API | ~50km |
| **manual** | User clicked a pin on the map | exact |

Saved in the `location_source` column for audit.

## 15.4 IP geolocation fallback

`/api/location/ip-geolocation` calls a free IP API (we use `ipapi.co`'s free tier). Returns coarse city-level lat/lng. Lets us still provide some safety context when GPS is unavailable.

## 15.5 Reverse geocoding

`/api/location/reverse-geocode?lat=...&lng=...` calls Nominatim, returns:
```json
{"display_name": "Iqbal Town, Lahore, Punjab, Pakistan", "area": "Iqbal Town"}
```
We cache results in memory to avoid hitting Nominatim's rate limit (1 req/sec).

## 15.6 Privacy controls (granular)

- `location_tracking_enabled` — master switch
- `background_location_tracking` — keep tracking when tab inactive
- `monitor_live_location` — let admins see your live location (off by default for users; on for admins)
- `high_risk_alerts_only` — suppress Medium/Low alerts
- `location_update_interval` — seconds between updates (default 30)

## 15.7 History view

Users can see their own location history (last 30 days) on `/api/location/history`. Each entry shows: timestamp, lat/lng, accuracy, address, risk_level, safety_score, whether an alert was triggered. Users can delete entries via DELETE endpoint.

---

# CHAPTER 16 — BACKGROUND JOBS (APScheduler)

## 16.1 The scheduler setup

In `main.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(monitor_saved_locations, IntervalTrigger(minutes=5))
scheduler.add_job(poll_new_incidents_for_alerts, IntervalTrigger(minutes=1))
scheduler.add_job(dispatch_weekly_safety_reports, CronTrigger(day_of_week='mon', hour=9))
scheduler.add_job(cleanup_unverified_accounts, CronTrigger(hour=3))
scheduler.add_job(check_and_retrain, IntervalTrigger(hours=12))
scheduler.start()
```

## 16.2 Job 1 — `monitor_saved_locations` (every 5 min)

For each user with `live_alerts_enabled=1`:
1. Get their `home_lat/lng` and `work_lat/lng`
2. Query `crimes` for new crimes (created in last 5 min) within `alert_radius`
3. If found and severity ≥ user's threshold:
   - Build `RiskZoneAlert`
   - Send via enabled channels
   - Log to `alert_notifications`

## 16.3 Job 2 — `poll_new_incidents_for_alerts` (every 1 min)

Tighter cycle for new incidents:
1. SELECT crimes WHERE created_at > last_run AND status='verified'
2. For each new crime, find users in radius (using haversine in SQL)
3. Send incident alerts in parallel (asyncio.gather)
4. Update `last_run` timestamp

## 16.4 Job 3 — `dispatch_weekly_safety_reports` (Mondays 9 AM)

For each user with `weekly_reports_enabled=1`:
1. Aggregate stats for last 7 days around `home_lat/lng`
2. Render the weekly HTML email template
3. Send via SMTP
4. Log success/failure

## 16.5 Job 4 — `cleanup_unverified_accounts` (daily 3 AM)

`DELETE FROM users_info WHERE is_verified=0 AND created_at < NOW() - INTERVAL 7 DAY`. Frees up usernames and emails for retry.

## 16.6 Job 5 — `auto_retrain` (every 12 hours)

1. Count rows in `crimes` since last training (`last_training_at` from `system_settings`)
2. If ≥500 new rows, kick off `train_crime_risk_model()` in a background thread
3. After training: `reload_model()` swaps in the new model atomically
4. Log to `system_logs` with new accuracy

## 16.7 Job 6 — `model_watcher` (continuous)

A separate thread that monitors:
- New crime types not in `severity_map.json`
- Counts how often each unknown type appears
- When count crosses threshold (default 20), flags it in `oov_counts.json`
- Super-admin sees the OOV list in `/api/crimes/model/oov-status`

## 16.8 Server-Sent Events for real-time admin dashboard

`/admin/notifications/stream` is a special endpoint that holds the connection open and pushes events as they happen (login, new crime, OCR done). Implemented with FastAPI's `StreamingResponse`.

---

# CHAPTER 17 — SMART TRICKS, TECHNIQUES & DESIGN DECISIONS (40 items)

These are the "wow" points to mention in the panel. Be ready to explain any of them in 2 sentences.

1. **Multi-engine OCR voting** — never trust one engine; we run 4 in parallel and choose the consensus.
2. **Image hash perceptual cache** — same FIR uploaded twice? Skip OCR, return cached extraction.
3. **Severity keyword inference (8 tiers)** — model never crashes on unseen crime types.
4. **Auto-saved severity** — new crime types automatically saved to severity_map.json so future training learns them.
5. **Median fallback for unknown areas** — area_freq_median ensures predictions work for new areas.
6. **Dynamic risk thresholds (percentile-based)** — labels self-balance every training run.
7. **Laplace smoothing in Poisson** — never gives 0 probability for rare combinations.
8. **Hour-multiplier amplification (^2.2)** — spreads multipliers from clustering near 1.0 so time selection visibly affects risk.
9. **5-tier confidence cascade in Poisson** — model always returns an answer with appropriate confidence.
10. **Three free AI providers in cascade** — Groq → OpenRouter → Gemini, zero cost.
11. **Force-route variety with via-points** — guarantees 3 routes even when OSRM returns 1.
12. **VAPID PEM normalization** — pywebpush is fussy; we save key as temp file.
13. **Cooldown cache for alerts** — prevents spamming users at zone boundaries.
14. **Quiet hours** — alerts respect each user's "do not disturb" window.
15. **Different secrets for access vs refresh tokens** — limits blast radius.
16. **Role-based session timeouts** — 60 min for admins, 30 days for users.
17. **JWT + bcrypt + 2FA + email OTP + Google OAuth** — five authentication paths.
18. **Audit logs (append-only)** — full forensics on every admin write.
19. **Approval workflow** — destructive admin actions require super-admin sign-off.
20. **Service worker (`sw.js`)** at root scope — offline + push notifications.
21. **Token cleanup on app load** — strips invalid JWTs from localStorage.
22. **Force-CORS middleware** — explicit headers on every response.
23. **Auto-retrain when 500+ rows added** — model stays fresh.
24. **Model watcher** — detects out-of-vocabulary crime types continuously.
25. **Connection pool reuse** — `get_db_connection()` from a pool.
26. **Pydantic schemas everywhere** — auto Swagger at `/docs`.
27. **Pre-aggregated heatmap data** — DB returns top 1000 hot spots, frontend doesn't choke.
28. **Server-Sent Events for live admin feed** — no polling, no websockets.
29. **TiDB Cloud compatible** — `get_db_ssl_kwargs()` toggles SSL.
30. **CrimeVision branded emails (1000+ lines)** — every alert type personalised.
31. **Sparse-data stabilizer** — rare areas don't get wild scores.
32. **Adaptive decay** — old hotspots don't suddenly look safe just because no recent crime.
33. **Severity sync from law database** — closed loop between PPC and ML.
34. **Geocoding cache (`area_coordinates`)** — avoids hitting Nominatim's rate limit.
35. **PWA service worker registration** — survives page reloads.
36. **Refresh token interceptor** — transparent token renewal without user noticing.
37. **Pillow ANTIALIAS shim** — `Image.ANTIALIAS = Image.LANCZOS` for Pillow 10 compat.
38. **Bcrypt 72-byte safety truncation** — explicit `password[:72]` prevents silent bugs.
39. **Stratified k-fold cross-validation** — preserves class proportion in each fold.
40. **Public emergency endpoint** — works without login so guests can call SOS.

---

# CHAPTER 18 — CHALLENGES FACED & SOLUTIONS

| # | Challenge | Solution |
|---|---|---|
| 1 | No ground-truth risk labels in the dataset | Generated rule-based labels with weighted scoring + dynamic percentile thresholds |
| 2 | Unseen crime types appearing in production | 8-tier keyword inference + auto-save to severity_map.json |
| 3 | Urdu OCR accuracy was poor with single engine | Multi-engine voting + Urdu dictionary + 50-thana whitelist |
| 4 | VAPID key format (DER vs PEM) errors | Normalize to PEM and save as temp file before pywebpush call |
| 5 | Free AI quota limits | Cascade through Groq → OpenRouter → Gemini |
| 6 | OSRM only returning 1 route | Mathematically force via-points perpendicular to vector |
| 7 | Risk score going to 0 for sparse areas | Laplace smoothing + minimum-volume stabilizer |
| 8 | Old hotspots looking safe when no recent crime | Adaptive decay (0.85 to 0.60 based on historical volume) |
| 9 | Time selection didn't change predictions | Hour-multiplier amplification exponent (^2.2) |
| 10 | Heatmap performance with 25k crimes | DB-side aggregation → only top 1000 to client |
| 11 | Browser push not firing | Service worker root scope + `userVisibleOnly:true` + correct VAPID PEM |
| 12 | Token expiry mid-request | Refresh-token endpoint + axios interceptor retry once |
| 13 | CORS in production | `ALLOWED_ORIGINS` env var + middleware + force-headers middleware |
| 14 | Geocoding rate limits | Local cache table + fuzzy matcher |
| 15 | Time-zone inconsistencies | All DB timestamps stored as UTC; frontend converts to user's TZ |
| 16 | Pillow 10 removed `Image.ANTIALIAS` | Set `Image.ANTIALIAS = Image.LANCZOS` shim |
| 17 | Model file growing large | Joblib compression; load once at startup |
| 18 | Concurrent training and inference | Background thread for training, atomic model swap with `reload_model()` |
| 19 | Bcrypt silently truncating passwords > 72 bytes | Explicit `password[:72]` truncation in code |
| 20 | Email OTP login race conditions | Token expiry tied to single-use flag, cleared after first valid use |

---

# CHAPTER 19 — VIVA QUESTIONS AND ANSWERS (100+)

## 19.1 General project questions

**Q1: What is your project about? Explain in one minute.**
A: CrimeVision is an AI-powered web platform for public safety. It combines historical crime data with machine learning to (a) predict the risk level of any area on any future date and time, (b) plan the safest route between two points by comparing 3 alternatives, (c) digitize paper FIR documents using OCR, and (d) send real-time alerts to citizens via email and browser push notifications. It has three role-based dashboards — User, Admin, and Super-Admin — and is built with React, Python FastAPI, and MySQL.

**Q2: Why did you choose this project?**
A: Pakistan loses millions to crime every year, but citizens have no public tool to know where it's safe. Existing maps optimise for time, not safety. We saw an opportunity to combine ML with civic technology to make safety decisions data-driven for everyone, not just police.

**Q3: Who are your target users?**
A: Three primary groups. (1) Citizens (especially women and elderly) who need safety guidance for daily travel. (2) Police officers who need a digital tool to log FIRs and see crime patterns. (3) City administrators who need analytics to allocate patrols and resources.

**Q4: What is your contribution? What's novel?**
A: Five things are novel. (1) Combining a Random Forest classifier with a Poisson probability model so we get both class labels and time-aware probabilities. (2) A multi-engine OCR pipeline specifically tuned for Punjab Police FIRs in mixed Urdu-English. (3) A free AI cascade (Groq → OpenRouter → Gemini) that costs zero. (4) A safety-aware route planner that forces variety when the routing API doesn't provide it. (5) A closed loop between the verified PPC law database and the ML severity map.

**Q5: What's the size of your dataset?**
A: 25,500+ crime records from 2018–2025 spanning all major areas of Lahore. 18,025 verified Pakistani law sections (PPC, ATA, PECA, CNSA, ARMS, HUDOOD, EXPLOSIVE, WOMEN_PROTECTION). 49 registered users for testing. 43 areas in our master area table.

**Q6: How long did the project take?**
A: [Customize: roughly 8–12 months — initial planning 1 month, data collection 1 month, ML model development 2 months, OCR pipeline 2 months, frontend 3 months, integration + testing 2 months, deployment + iteration 1 month.]

**Q7: Did you work alone or in a team?**
A: [Customize based on your situation.]

**Q8: How is your project different from Google Maps?**
A: Google Maps optimises for time and distance only; we optimise for safety. Google Maps doesn't know about local crime patterns; we have 25k records of historical incidents. Google Maps can't predict tomorrow's risk; we can. Google Maps has no SOS integration; we do.

**Q9: How is it different from existing crime-mapping apps?**
A: Most crime apps just plot dots on a map. We do prediction, route planning, alerts, and OCR-based data ingestion. We also support multiple roles (citizen, police, admin) on the same platform.

## 19.2 Architecture & technology questions

**Q10: Why FastAPI and not Flask or Django?**
A: FastAPI is async by default — it can handle thousands of concurrent connections without blocking. It uses Pydantic for automatic request validation and generates Swagger documentation automatically. It's also one of the fastest Python web frameworks, benchmarked close to Node.js. Flask is older, synchronous, and needs extra libraries for what FastAPI gives out of the box. Django is heavier and oriented toward server-rendered HTML, not pure JSON APIs.

**Q11: Why MySQL and not PostgreSQL or MongoDB?**
A: MySQL is mature, free, well-supported, and our hosting (TiDB Cloud) is MySQL-compatible. Our data is highly relational (users → alerts → crimes → areas) so a relational database is the natural fit. MongoDB would have made joins painful. PostgreSQL would also have worked but MySQL has slightly better hosting compatibility for Pakistan.

**Q12: Why React and not Angular or Vue?**
A: React has the largest ecosystem, especially for maps (react-leaflet), charts (react-chartjs-2), and UI libraries (Ant Design). We had prior React experience. Vite as the build tool gives us sub-second hot reload during development.

**Q13: Why is your backend stateless?**
A: Stateless means the server keeps no session data between requests — every request carries its own JWT token containing user identity. This lets us run multiple backend instances behind a load balancer with no session-affinity. It also makes the system easier to test and deploy.

**Q14: Where do you deploy your code?**
A: Backend on Render.com as a Python web service. Frontend on Vercel as a static site. Database on TiDB Cloud (MySQL-compatible). All free-tier deployments.

**Q15: How do you handle CORS?**
A: Two layers. (1) FastAPI's CORSMiddleware reads `ALLOWED_ORIGINS` from the .env file. (2) A custom force-CORS middleware adds explicit headers on every response, including preflight OPTIONS, to handle edge browsers. This belt-and-suspenders approach has eliminated CORS bugs.

**Q16: How do you scale this system?**
A: (1) Backend is stateless → horizontal scaling by adding more Render instances. (2) Models are loaded into memory once at startup → repeated predictions cost only ~5ms. (3) Database has 100+ indexes on critical query paths. (4) Heatmap data is aggregated server-side so the client receives only top 1000 hotspots. (5) Heavy operations (OCR, training) run in background threads, not blocking the request pipeline.

## 19.3 Database questions

**Q17: How many tables do you have?**
A: 42 tables organised into 10 logical domains: Auth (8), Crime (3), Alerts (8), Location (4), Community (5), Emergency (2), Law (2), Reports (3), Audit (4), Resources (3).

**Q18: Why so many tables?**
A: Each table has a single responsibility. For example, alerts are split across 8 tables because we track subscriptions, browser push endpoints, multi-channel delivery status, per-user preferences, and a notification inbox separately. This normalization prevents data inconsistencies and makes queries fast.

**Q19: What is the primary key strategy?**
A: Every table has an auto-increment integer surrogate primary key called `id`. Some tables also have unique constraints on natural keys (e.g., `users_info.email`, `users_info.username`). For multi-column natural keys we use named UNIQUE constraints (e.g., `uk_law_section` on `law_sections(law_type, section_number)`).

**Q20: How do you handle foreign keys?**
A: We use `ON DELETE CASCADE` for child tables that have no value without the parent (e.g., when a user is deleted, their alerts cascade-delete). We use `ON DELETE SET NULL` when the child still has value (e.g., a community alert survives even if its creator is deleted).

**Q21: How do you handle Urdu text storage?**
A: All tables use `utf8mb4` charset and `utf8mb4_0900_ai_ci` collation. This stores Urdu, Arabic, and emojis correctly. The `ai_ci` collation is accent-insensitive, case-insensitive, which helps fuzzy matching.

**Q22: How big is your database?**
A: ~25k crimes + 18k law sections + 8k notifications + ~1k auxiliary records = roughly 50k rows total. Disk size around 100MB. Indexes add another 30MB.

**Q23: How do you back it up?**
A: TiDB Cloud has automatic daily snapshots. For local development we periodically run `mysqldump` and check the dump into version control as `schema.sql`.

## 19.4 Machine Learning questions

**Q24: Why Random Forest?**
A: Six reasons. (1) It handles mixed numeric and categorical features without preprocessing explosion. (2) Robust to outliers because it averages 200 trees. (3) Generalises well to unseen areas using our median fallback. (4) Provides feature importance for free. (5) Fast inference (~5 ms). (6) Handles class imbalance via `class_weight='balanced'`.

**Q25: Why not deep learning / neural networks?**
A: Three reasons. (1) Our dataset is small (25k rows) — neural networks excel with millions of rows. (2) Random Forest is more interpretable, which is critical for a safety application where users want to know **why** an area is dangerous. (3) Random Forest doesn't need GPU and runs fast on free hosting.

**Q26: Why also use Poisson?**
A: Random Forest only outputs a class (High/Med/Low). It can't say "what's the probability of a robbery in Gulberg next Tuesday at 9 PM specifically?" Poisson gives a continuous probability that smoothly varies with date and hour. We use them together — Poisson is primary, RF is fallback.

**Q27: What is the Poisson formula?**
A: P(at least one crime today) = 1 − e^(−λ), where λ is the expected number of events per day. We adjust λ by day-of-week, month, and hour multipliers learned from historical data, with Laplace smoothing to avoid zero probabilities.

**Q28: What features do you use for Random Forest?**
A: 11 features. Crime severity (1-10), hour of day, day of week, month, is_weekend flag, is_nighttime flag, time_risk (cosine peak at 2 AM), area crime frequency (share of all crimes), area frequency percentile, latitude, longitude.

**Q29: How did you create training labels?**
A: Our database had no ground-truth risk labels — every row defaulted to "Medium". So we generated rule-based labels using a weighted scoring formula: 40% severity + 25% time-of-day + 25% area hotspot rank + 10% weekend. Then we used dynamic percentile thresholds: top 30% of scores → High, bottom 25% → Low, rest → Medium. The Random Forest then learns to reverse-engineer this rule from the features.

**Q30: What is your model accuracy?**
A: Around 95% cross-validated accuracy with 5-fold stratified k-fold on the rule-generated labels. We acknowledge this is high because the labels themselves came from a deterministic formula — the model is essentially learning the rule. The real test is downstream: does it generalize to new areas and crime types? Our keyword inference and median fallback handle that gracefully.

**Q31: How do you handle class imbalance?**
A: Two ways. (1) `class_weight='balanced'` in Random Forest auto-adjusts loss function. (2) Dynamic percentile thresholds in label generation produce a fixed distribution (30% / 45% / 25%) regardless of dataset shifts.

**Q32: How do you handle new crime types?**
A: Four-tier resolution. (1) Manual severity_map.json is checked first. (2) Then 8-tier keyword inference (murder=10, theft=5, etc.). (3) Then frequency-derived severity from training data. (4) Finally statistical median. New types matched by keywords are auto-saved so the next training run treats them as known.

**Q33: How do you handle new areas?**
A: We use the `area_freq_median` from training artifacts as a fallback. So a brand-new area gets assigned the median frequency, neither penalised nor favoured.

**Q34: Why dynamic percentile thresholds?**
A: If we used fixed cutoffs like `score > 0.7 → High`, the label distribution would shift as new crime types arrived (could become 90% Medium). Dynamic percentiles guarantee a balanced distribution every training run, making the classifier well-conditioned.

**Q35: Why Laplace smoothing in Poisson?**
A: Without smoothing, any (area, crime, day) cell with zero observations would give multiplier = 0, which means probability = 0 — misleading. Laplace adds a +1 pseudo-count to every bucket so probabilities are never exactly 0 while preserving relative ordering.

**Q36: Why the 2.2 exponent on hour multipliers?**
A: Raw smoothed multipliers cluster very close to 1.0 because hour bucketing has 24 buckets and Laplace pulls everything toward 1/24. Raising them to the 2.2 power amplifies the differences so picking 9 PM vs 9 AM produces a visibly different risk percentage in the UI. Otherwise the user wouldn't see the value of choosing a different time.

**Q37: How do you validate your model?**
A: 5-fold stratified k-fold cross-validation. We also compute classification report (precision, recall, F1 per class) on the full training set. Feature importance is logged after every training run so we can spot if the model starts relying on a feature it shouldn't.

**Q38: What about overfitting?**
A: We mitigate three ways. (1) `max_depth=15` prevents trees from growing too deep. (2) `min_samples_leaf=10` requires every leaf to have at least 10 samples — no per-row memorization. (3) 200 trees ensemble averages noise. Cross-validation accuracy matching training accuracy confirms we're not overfitting.

**Q39: How often do you retrain?**
A: Auto-retrain triggers when 500+ new crime rows are added since last training. Plus every 12 hours, the scheduler checks if retraining is warranted. Super-admin can also manually trigger via the dashboard.

**Q40: What happens during retraining? Is the system down?**
A: No, retraining runs in a background thread. The current model continues serving predictions. When training completes, we call `reload_model()` to atomically swap the in-memory model. Zero downtime.

**Q41: How do you test the model?**
A: Three layers. (1) Unit tests for each helper function (severity resolution, feature engineering). (2) Cross-validation accuracy check during training. (3) A `test_safety_score_fixes.py` script that runs a fixed set of test cases and compares to expected outputs.

## 19.5 OCR pipeline questions

**Q42: How does your OCR work?**
A: It's a multi-stage pipeline. First we check an image hash cache in case we've seen this exact FIR before. Then we preprocess the image (grayscale, CLAHE contrast, deskew, sharpen). Then we crop fixed regions matching the Punjab Police FIR template. Then we run four OCR engines in parallel — EasyOCR, PaddleOCR, Tesseract, and Gemini Vision. We vote on the result, validate against a Urdu location dictionary, and finally geocode the extracted thana.

**Q43: Why four OCR engines?**
A: Each has strengths and weaknesses. EasyOCR is best for Urdu. PaddleOCR is fast for printed text. Tesseract is good for English. Gemini Vision is an LLM that handles blurry or unusual cases. By voting, we get accuracy higher than any single engine alone.

**Q44: How do you handle Urdu?**
A: Three ways. (1) EasyOCR is initialized with `['ur', 'en']` so it knows both languages. (2) After OCR we run text through `correct_location_text()` which fuzzy-matches against a Urdu location dictionary. (3) We have a hardcoded whitelist of 50+ Lahore thanas with all observed Urdu spelling variants.

**Q45: What's your OCR accuracy?**
A: On clean printed FIRs, we hit 90%+ accuracy. On blurry photocopies, around 70% with the Gemini fallback bringing it to 85%+. Hand-written sections are still a challenge — we extract the printed parts and leave handwritten descriptions for admin to fill in.

**Q46: Why image hashing?**
A: During development and demos, the same FIR is uploaded many times. The image hash lookup gives us sub-millisecond return for cached cases, saving compute and improving demo UX.

**Q47: What is CLAHE?**
A: Contrast-Limited Adaptive Histogram Equalization. A local-contrast enhancement that improves OCR on faded photocopies. Better than global histogram equalization because it doesn't blow out already-dark regions.

**Q48: How do you reject garbage OCR output?**
A: Multiple validation rules: reject if the text contains Arabic diacritics, two consecutive repeated characters, Urdu/Arabic digits in a location field, more than 55% short words, any word longer than 10 chars, or has space ratio above 35%. Plus a whitelist match — if the text doesn't contain any known thana keyword, it's discarded.

## 19.6 Authentication & security questions

**Q49: How do you store passwords?**
A: We hash them with bcrypt using a per-user salt. The cost factor is configurable. We use the `bcrypt_sha256` scheme on top of bcrypt to safely handle passwords longer than 72 bytes (bcrypt's hard limit). Passwords are never stored in plain text and never logged.

**Q50: What is JWT and why use it?**
A: JSON Web Token — a signed string containing user identity claims. Use is stateless: the server verifies the signature without consulting the database. Saves a DB round-trip on every request. We use it because our backend is stateless and horizontally scalable.

**Q51: What's the difference between access and refresh tokens?**
A: Access token is short-lived (30 days for users, 60 min for admins) and used to authenticate every API request. Refresh token is long-lived (90 days), kept secure, and used only to get a new access token when the current one expires. They're signed with different secrets so a leaked access secret doesn't compromise refresh tokens.

**Q52: How does 2FA work?**
A: We use TOTP (Time-based One-Time Password) via the pyotp library. When a user enables 2FA, we generate a 32-character random secret, encode it into a QR code, and the user scans it with Google Authenticator. The authenticator generates a fresh 6-digit code every 30 seconds. On login, we ask for that code and verify it with `pyotp.TOTP(secret).verify(code)`.

**Q53: What if a user loses their authenticator?**
A: We have an email-OTP fallback. The user requests a recovery code, we email them a 6-digit code valid for 10 minutes, they enter it, and we let them log in (or disable 2FA). All failed/successful 2FA recovery attempts are logged.

**Q54: How do you prevent brute-force attacks?**
A: Three ways. (1) `failed_attempts` column tracks per-user failures; after 5 in 10 min we lock for 30 min. (2) `login_attempts` table records IP + email per attempt; we can block an IP. (3) Rate limiting middleware caps requests per IP and per user.

**Q55: How does Google OAuth work?**
A: User clicks "Sign in with Google", Google's library returns an `id_token` (signed JWT). We send it to the backend, which verifies it with Google's public key, checks issuer and audience, and extracts email/name/photo. If user exists we log them in; if new we auto-register and download their profile picture.

**Q56: How do you handle role-based access?**
A: Each user has a `role` column ('user', 'admin', 'superadmin'). FastAPI dependencies inspect the JWT and reject requests where role doesn't meet the endpoint's requirement. Admins also have a JSON `permissions` column for fine-grained control inside admin endpoints.

**Q57: What is the approval workflow?**
A: Sensitive admin actions (delete user, change roles, modify settings) don't execute immediately. They insert into `approval_requests` with status='pending'. A super-admin reviews the JSON request_data, then approves or rejects with notes. Only after approval does the action execute. This prevents a single rogue admin from doing damage.

**Q58: What is logged for audit?**
A: Every admin write goes to `audit_logs` with: who (admin_username), what (action), target (target_type + target_id), before/after state (details JSON), where (ip_address + user_agent), when (created_at). The table is append-only — no UPDATE or DELETE allowed in code. This gives full forensics.

**Q59: How do you protect against SQL injection?**
A: We **always** use parameterized queries with `%s` placeholders and never concatenate user input into SQL strings. The mysql-connector library properly escapes parameters. We also have type validation via Pydantic on every endpoint, so a string doesn't get into a numeric field.

**Q60: How do you protect against XSS?**
A: React automatically escapes interpolated values in JSX, so `{userInput}` is safe by default. We use `dangerouslySetInnerHTML` only for our own pre-built email templates, never user content. Backend never returns raw HTML from user input.

## 19.7 Alert system questions

**Q61: How do you push notifications to browsers?**
A: We use the Web Push protocol with VAPID. Each user's browser subscribes via the service worker, giving us an endpoint URL plus encryption keys. We sign push requests with our VAPID private key (P-256 curve) and use pywebpush to send. The browser's push service forwards to the user's device, where the service worker shows the notification.

**Q62: What is VAPID?**
A: Voluntary Application Server Identification. A scheme where each app has a public/private key pair. The browser can verify that pushes come from your server, preventing third-party spam. The public key is embedded in the subscription request; the private key signs every push.

**Q63: What if a user is offline?**
A: Push notifications queue at the browser's push service for hours/days. When the user comes back online, the service worker wakes up and shows the stored notifications. Email also waits in their inbox forever. SMS is fire-and-forget but generally delivered within seconds even on weak networks.

**Q64: How do you avoid spamming users?**
A: Five mechanisms. (1) Cooldown cache — same user + same zone, we wait 60 min between alerts. (2) Quiet hours — alerts during user's DND window are deferred. (3) High-risk-only filter — users can opt out of Medium/Low alerts. (4) Channel preferences — per-category email/browser/SMS toggles. (5) Cooldown for community-reported alerts so a single incident doesn't trigger 10 messages.

**Q65: What if email fails?**
A: We log the failure in `notification_logs` with the error message, retry once, and try the next channel (browser push) if available. We also alert admins if email failure rate exceeds threshold.

**Q66: How fast is the alert pipeline?**
A: Sub-second from "new crime added" to "browser push delivered". The 1-minute scheduler picks up new crimes; for each user in radius (computed via haversine SQL), we send in parallel using asyncio.gather. Bottleneck is the push service, which typically delivers in 200–500ms.

## 19.8 Route safety questions

**Q67: How do you compute route safety?**
A: Two implementations. The rule-based one starts with a base score of 100, deducts points for high/medium/low crimes near the route, deducts more for poor lighting / far from police / isolated roads, adds bonuses for police proximity / hospital / main road / good lighting, and applies time-of-day multipliers (×2 late night, ×1.5 evening). The AI one samples 10–20 points along the route and queries the Poisson model for each.

**Q68: How do you get routes?**
A: We call OSRM (Open Source Routing Machine) via its public API. We ask for `alternatives=true` and `continue_straight=false` to get up to 3 paths.

**Q69: What if OSRM only returns 1 route?**
A: We force variety. We compute the start→end vector, then perpendicular vectors. We insert via-points 1.5km left and 1.5km right of the midpoint and re-call OSRM with each as a waypoint. This guarantees we always show 3+ different routes.

**Q70: Why use OSRM and not Google Directions?**
A: OSRM is free and open source. Google Directions costs money per call. OSRM serves billions of routes/day on its public server.

**Q71: How accurate is the route safety score?**
A: It's heuristic, not absolute. The score reflects historical patterns and infrastructure proximity. It works well for relative comparison (route A is safer than route B) but the absolute number shouldn't be over-interpreted. We display it as a range/level (Safe/Moderate/Risky) rather than a single number to communicate this uncertainty.

## 19.9 Frontend questions

**Q72: Why React 18?**
A: React 18 introduced concurrent rendering and automatic batching, making the UI feel more responsive. We use `useTransition` for non-urgent updates (e.g., recomputing the heatmap after filter change) so the UI remains interactive.

**Q73: Why Vite?**
A: Vite gives us hot module reload in under 100ms (Webpack would take seconds). For production it tree-shakes unused code and chunks the bundle for fast first paint.

**Q74: How do you handle the JWT token client-side?**
A: It's stored in localStorage (with a token-cleanup function on app load to remove invalid tokens). Axios has a request interceptor that attaches `Authorization: Bearer <token>` to every outgoing request. A response interceptor catches 401, calls `/auth/refresh-token`, retries the original request once.

**Q75: How does the dashboard stay fresh?**
A: Each card uses `useEffect` to fetch on mount and on key dependency changes. Some cards (alerts inbox, admin live feed) use Server-Sent Events for real-time updates. We don't poll because polling would burn battery on mobile.

**Q76: How do you make it mobile-responsive?**
A: We use Bootstrap's grid (col-12 col-md-6 col-lg-4 etc.) plus our own `responsive.css` for breakpoints. Charts auto-resize. Maps work on touch devices natively via Leaflet.

**Q77: How do you handle errors in the frontend?**
A: An ErrorBoundary at the App root catches uncaught exceptions and shows a friendly recovery UI. Toast notifications via react-toastify show transient errors. API errors are normalized in apiService_updated.js so components see a consistent error shape.

**Q78: What's the service worker?**
A: `sw.js` is registered at app load with scope `/`. It enables push notifications (handles `push` events and shows them) and provides offline caching of static assets. It also auto-updates when a new version is deployed.

## 19.10 Performance & scalability questions

**Q79: How fast is your API?**
A: Most endpoints return in 20–50 ms. The Poisson prediction is ~10 ms (no DB call). The heaviest is `/api/crimes/intelligence-dashboard` at ~200 ms because it aggregates many statistics. The OCR endpoint is the slowest at 1–3 seconds depending on image size.

**Q80: How do you handle high concurrent load?**
A: FastAPI is async, so multiple requests share the same process. Uvicorn workers can be scaled. The DB connection pool reuses connections. Models are in memory once. We've tested up to 100 concurrent requests on a single Render instance without degradation.

**Q81: How big is your codebase?**
A: Backend: ~25,000 lines of Python across 50+ files. Frontend: ~30,000 lines of JSX/CSS. SQL schema: ~1,000 lines. Total ~55k lines.

**Q82: How do you optimize the heatmap rendering?**
A: Server-side aggregation. The DB query buckets crimes into a coarse grid and returns only the top 1000 hottest cells. Leaflet.heat then renders them as gradients. The client never receives raw 25k records.

**Q83: How do you cache?**
A: Multiple layers. (1) ML models loaded once at startup (in-memory cache). (2) `area_coordinates` table is a persistent geocoding cache. (3) Image hash lookup for OCR. (4) Browser cache for static assets via service worker. (5) HTTP cache headers on static endpoints.

## 19.11 Deployment & DevOps questions

**Q84: How do you deploy backend?**
A: Push to GitHub → Render auto-builds (`pip install -r requirements.txt`) → starts uvicorn. Environment variables are set in Render dashboard. Logs are streamed there too.

**Q85: How do you deploy frontend?**
A: Push to GitHub → Vercel auto-builds (`npm install && vite build`) → deploys to its CDN. Environment variables (API base URL) are set in Vercel dashboard.

**Q86: How do you manage environment variables?**
A: Local dev uses `.env` file (loaded via python-dotenv). Production uses platform-native secret stores (Render env vars, Vercel env vars). Secret keys are different per environment.

**Q87: How do you handle database migrations?**
A: We have versioned `db_migrations*.sql` files in the backend folder. They're applied in order via `run_migrations.py`. New columns are added with `IF NOT EXISTS` clauses so re-running is idempotent.

**Q88: What about backups?**
A: TiDB Cloud has automatic daily snapshots with 7-day retention. We periodically export the schema to `schema.sql` and check it into version control as documentation.

**Q89: How do you monitor production?**
A: Render dashboard shows CPU, memory, response time. Application logs go to `error_log.txt` and Render's log viewer. Critical errors trigger alerts to admin emails via the same alert system we use for users.

## 19.12 Project management questions

**Q90: What was the hardest part?**
A: The OCR pipeline was the toughest because Pakistani FIRs have so many spelling variants of thana names in Urdu. We tried several approaches before settling on multi-engine voting + whitelist matching + Urdu dictionary. It took two months and many test images.

**Q91: What would you do differently?**
A: Three things. (1) Start the OCR pipeline earlier — we underestimated its complexity. (2) Build a proper testing harness with sample FIRs from day one. (3) Get user feedback earlier — we built features for two months before getting real users to try them.

**Q92: What did you learn?**
A: Many things. Technically: how to integrate ML into a production web app, how to design async pipelines, how to handle real-world messy data. Soft skills: how to debug production issues, how to balance feature scope vs deadlines, how to write maintainable code.

**Q93: Who would maintain this after the FYP?**
A: We've documented the codebase extensively (this document, README files in each folder, comments in complex functions). Our advisor or any successor with React + Python skills can take over. The OCR pipeline is the most complex part and needs the most ongoing attention as new FIR templates emerge.

## 19.13 Tricky / curveball questions

**Q94: What if your model gives wrong predictions?**
A: Three safeguards. (1) Risk levels are advisory, not authoritative — we don't tell users "this is dangerous", we say "elevated risk based on historical data". (2) We show confidence levels so users see when the model is uncertain. (3) Admins can manually override any prediction. (4) The model retrains regularly to incorporate new data.

**Q95: What about privacy?**
A: Location tracking is opt-in. Users can disable it any time. We never sell or share location data. Passwords are bcrypt-hashed. Login attempts are logged but personal data is minimized. Communication uses HTTPS in production. We also support email-OTP and 2FA so account takeover is hard.

**Q96: What if someone hacks the system?**
A: Multiple defences. (1) JWT signing prevents token forgery. (2) bcrypt password hashing protects credentials even if DB leaks. (3) audit_logs are append-only forensics. (4) Approval workflow prevents single-admin damage. (5) Rate limiting blocks brute-force. (6) HTTPS prevents man-in-the-middle. We also have a regular security review schedule.

**Q97: What if a user submits a fake report?**
A: Community reports are flagged as `unverified` until an admin reviews. They don't enter the ML training set without verification. Reporting users are tracked, so a pattern of false reports can lead to suspension. False reports of violent crimes could be prosecuted under existing laws.

**Q98: Is your data legally obtained?**
A: We use only public/published crime aggregations and synthesized samples for development. In production deployment, we'd partner with the Punjab Police under formal data-sharing agreement. We have a privacy policy in the public site.

**Q99: How accurate is the crime data?**
A: Crime data is inherently imperfect — many crimes go unreported (the "dark figure of crime"). Our model learns patterns from reported crimes only. We acknowledge this limitation in the disclaimer shown to users. The model is a guide, not a guarantee.

**Q100: What's next? How would you commercialize?**
A: Three paths. (1) Government partnership — sell as a SaaS tool to police departments and city governments. (2) B2C — premium features (real-time tracking for businesses with field staff, neighborhood association subscriptions). (3) API licensing — sell prediction API to logistics, ride-hailing, delivery companies who want safe-route APIs. The free tier remains for citizens.

## 19.14 Code-level questions

**Q101: Show me how a prediction works step by step.**
A: 1. Frontend POSTs `{area, crime_type, date, time}` to `/api/predict-risk`. 2. FastAPI matches to `crimes.py → predict_risk`. 3. Pydantic validates the body. 4. JWT dependency verifies the user. 5. Function calls `_poisson_predict(artifacts, area, crime_type, date_str, hour)`. 6. Poisson predictor builds the `key_pair_lc` string. 7. Looks up `pair_lambdas[key]` — gets a base λ. 8. Multiplies by `dow_multipliers[key][dow]` and `month_multipliers[key][month]` and `hour_multipliers[key][hour]^2.2`. 9. Computes `P = 1 - e^(-λ)`. 10. Maps to risk level. 11. Computes safest hours, days, months. 12. Returns JSON with all fields. 13. Frontend re-renders the card.

**Q102: Show me how OCR extraction works.**
A: 1. Admin uploads FIR.jpg. 2. Backend computes pHash, looks up cache. Miss. 3. `FIRImagePreprocessor` converts to grayscale, applies CLAHE, deskews. 4. `FIRRegions` crops Row 4 (thana region). 5. EasyOCR + PaddleOCR + Tesseract + Gemini all run on the crop. 6. Results are checked against `KNOWN_THANAS_MAP`. 7. First match wins. 8. Validation rules reject anything garbage. 9. Geocoder converts thana name to lat/lng. 10. Inserts into `crimes` with `status='unverified'`. 11. RF predicts `risk_level`. 12. Admin reviews and approves.

**Q103: Show me how an alert is delivered.**
A: 1. Background scheduler ticks. 2. SQL finds new crimes since last run. 3. For each new crime, SQL finds users in radius using haversine. 4. For each user, build `RiskZoneAlert`. 5. Check cooldown cache → skip if recently alerted. 6. Check quiet hours → defer if so. 7. For each enabled channel: render template, send. 8. Email: smtplib.sendmail. Browser: pywebpush.send. SMS: send via gateway email. 9. Log to notification_logs with success/error. 10. Insert into alert_notifications + browser_notifications. 11. Update user's `last_activity_at`.

**Q104: What does APScheduler do exactly?**
A: It's a Python library that runs functions on a schedule (cron-like) inside the same process as the FastAPI app. We register jobs with `add_job()` providing a function, a trigger (Interval / Cron), and parameters. The scheduler runs in a background thread, checking every few seconds whether any job is due. When due, it calls the function in a thread pool so the main event loop isn't blocked.

**Q105: How do you ensure data consistency across frontend and backend?**
A: Pydantic schemas in `models/schemas.py` define the exact shape of every request and response. The frontend uses TypeScript types (or PropTypes) matching those shapes. We also have the auto-generated Swagger docs at `/docs` as the contract.

---

# CHAPTER 20 — DEMO SCRIPT (12 MINUTES)

Here is a minute-by-minute demo plan.

### Minute 0–1: Open public site
- Show the landing page, hero section, statistics counters
- Click "Crime Map" → show heatmap with all crimes
- Filter by last 30 days → density updates
- Mention: "Anyone can use this without login"

### Minute 1–2: Public risk prediction
- Click "Risk Prediction" in the menu
- Enter "Anarkali", "Theft", today's date, "9 PM"
- Click Predict → shows "62% Medium Risk" with safest 3 hours, safest 3 days, visit-time comparison chart
- Mention: "This is the Poisson model running"

### Minute 2–3: Login as user
- Email: `zainwaseempgc1@gmail.com`, password
- Land on user dashboard
- Walk through cards: Safety Score, Risk Factors, Weekly Alerts, Safe Routes
- Click "Score Explainer" → shows 5 components

### Minute 3–4: AI Route Analysis
- Scroll to AI Route Analysis section
- Enter From: "Johar Town", To: "Anarkali"
- Time: "9 PM"
- Click Calculate → 3 routes drawn on map in different colors
- Right panel: Route 1 = Safe (84%), Route 2 = Moderate (68%), Route 3 = Risky (52%)
- Mention: "Recommended is the safest, not the fastest"

### Minute 4–5: Enable browser push
- Click "Enable Notifications" → permission popup → Accept
- Backend stores subscription
- Click "Send Test Notification" → push arrives in 1 second
- Mention: "Even if I close the tab, I'll still get pushes"

### Minute 5–6: Profile & 2FA
- Open profile modal
- Show alert preferences (email/browser per category)
- Show quiet hours
- Click "Enable 2FA" → QR code appears
- Mention: "Scan with Google Authenticator"

### Minute 6–8: Switch to admin
- Logout, login as admin
- Show admin dashboard with extra panels
- Click OCR Panel
- Upload a sample FIR image
- Watch extraction happen live (date, time, thana, sections)
- Click Save → goes into crimes table
- RF predicts risk_level automatically

### Minute 8–9: Reports
- Click Reports panel
- Select "Crime Summary", date range, PDF
- Click Generate → download starts
- Open the PDF — shows branded report with charts and tables

### Minute 9–10: Switch to super-admin
- Logout, login as super-admin
- Click Audit Logs panel
- Filter by today, action="update_settings"
- Click a row → see full JSON before/after diff

### Minute 10–11: PPC Management
- Click PPC Management
- Search "Section 302"
- Click row → AI Verify button
- AI returns verified title with citation
- Click Approve → marked verified

### Minute 11–12: Closing
- Show analytics dashboard with year-over-year trend
- Mention: "All this is one platform, deployed for free, ready to extend to other cities"
- Q&A

---

# CHAPTER 21 — CHEAT SHEETS (PRINT THESE)

## 21.1 One-page summary

| Aspect | Answer |
|---|---|
| Project | CrimeVision (SafeVision) |
| Type | Full-stack AI-powered safety platform |
| Backend | Python + FastAPI + MySQL |
| Frontend | React 18 + Vite + Leaflet |
| Deployment | Render (backend) + Vercel (frontend) |
| Tables | 42 |
| Endpoints | 60+ across 13 routers |
| ML models | 3 (Random Forest + Poisson + Rule-based route safety) |
| Crime records | 25,500+ |
| Law sections | 18,025 |
| OCR engines | 4 (EasyOCR + PaddleOCR + Tesseract + Gemini) |
| Alert channels | 3 (Email + Browser Push + SMS) |
| Authentication | bcrypt + JWT + 2FA + Google OAuth + Email OTP |
| Roles | User / Admin / Super-Admin |
| Background jobs | 6 (every 1/5/12h, Mondays, daily) |
| AI providers | Groq → OpenRouter → Gemini (free) |
| Routing | OSRM API |
| Charts | Chart.js |
| Map | Leaflet + leaflet.heat |

## 21.2 Three-formula cheat sheet

**1. Poisson probability:**
```
P(≥1 crime) = 1 - e^(-λ)
λ = base_λ × dow_mult × month_mult × hour_mult^2.2
```

**2. Rule-based label score:**
```
score = 0.40·severity + 0.25·time + 0.25·area_hotspot + 0.10·weekend
```

**3. Unified risk summary:**
```
risk = 0.35·volume + 0.15·severity + 0.30·recency + 0.10·trend + 0.10·time
safety = 100 - risk
```

## 21.3 Random Forest hyperparameters cheat sheet

```python
RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
```

## 21.4 Five most-asked viva answers (memorize verbatim)

**Q: Why Random Forest?**
A: Six reasons. Handles mixed feature types without preprocessing, robust to outliers, generalises with median fallback, gives feature importance for explainability, fast inference around 5 ms, and handles class imbalance via balanced class weights.

**Q: Why Poisson?**
A: Random Forest gives only a class label. Poisson gives a continuous probability that varies smoothly with date and hour. Crime occurrences fit a Poisson process — `P(at least 1) = 1 - e^(-λ)` where λ is adjusted by day-of-week, month, and hour multipliers from historical data.

**Q: How does VAPID work?**
A: VAPID is Voluntary Application Server Identification. Each app generates a P-256 key pair. The browser subscribes with the public key, returning an endpoint and encryption keys. Our backend signs every push with the private key using pywebpush. The browser verifies the signature so only our server can push to our subscribers.

**Q: Why FastAPI?**
A: It is async by default, validates with Pydantic, auto-generates Swagger docs, and is benchmarked among the fastest Python frameworks. Type hints become real run-time validation. It scales horizontally because it's stateless.

**Q: How does OCR pipeline work?**
A: Multi-stage. (1) Image hash cache. (2) Preprocessing — grayscale, CLAHE, deskew, sharpen. (3) Region cropping based on FIR template percentages. (4) Four OCR engines in parallel — EasyOCR, PaddleOCR, Tesseract, Gemini Vision. (5) Voting on result. (6) Validation against Urdu dictionary and 50-thana whitelist. (7) Geocoding. (8) Insert with `status='unverified'`. (9) RF predicts risk_level. (10) Admin reviews and approves.

## 21.5 Number cheat sheet (memorize)

- 42 tables
- 60+ API endpoints
- 13 routers
- 11 ML features
- 200 trees in Random Forest
- 15 max depth
- 10 min_samples_leaf
- 5-fold cross-validation
- ~95% accuracy
- 8-tier keyword severity
- 4 OCR engines
- 50+ Lahore thanas in whitelist
- 25,500 crime records
- 18,025 law sections
- 6 background jobs
- 30 days access token (user)
- 60 min access token (admin)
- 90 days refresh token
- 60 min cooldown
- 5 km default alert radius
- 1.5 km / 3 km via-point offsets
- ^2.2 hour amplification
- 0.40 / 0.25 / 0.25 / 0.10 label weights
- 0.35 / 0.15 / 0.30 / 0.10 / 0.10 unified risk weights
- 0.85 / 0.70 / 0.60 adaptive decay
- 30/25 percentile thresholds
- 25k features × 200 trees ≈ 5 ms inference

## 21.6 Things to NEVER say in viva

- "I copied this from..."
- "I don't know" (instead say: "Let me think — I believe it's X because Y")
- "It's just a demo" (instead say: "It's a working prototype that can be extended for production")
- "We didn't test that" (instead say: "Our test coverage focused on critical paths X and Y")
- "It always works" (instead say: "It works reliably for the scenarios we tested; edge cases like X are noted as future work")

## 21.7 Things to ALWAYS bring

- Working laptop (charged, with code running locally)
- Sample FIR image for OCR demo
- 3 test accounts (user, admin, super-admin) with passwords memorized
- Mobile phone for browser push demo
- Backup slides on USB stick
- Printed cheat sheet (this page)
- Bottle of water (your throat will dry out)

## 21.8 Final 30-second pitch (memorize)

*"CrimeVision is an end-to-end AI-powered public safety platform built with React, Python FastAPI, and MySQL. It combines a Random Forest classifier and a Poisson probability estimator to predict crime risk for any area at any future date and time. It plans the safest route between two points, comparing three alternatives. It digitizes paper FIRs using a multi-engine OCR pipeline tuned for Urdu and English. It sends real-time alerts via email, browser push, and SMS. It has three role-based dashboards — User, Admin, Super-Admin — and 60+ API endpoints across 13 routers. It is deployed free on Render and Vercel and ready to extend to any city in Pakistan."*

---

**End of Part 2. Good luck — you've got this!** 🎯
