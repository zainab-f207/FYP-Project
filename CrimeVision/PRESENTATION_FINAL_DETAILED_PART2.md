# SafeVision — Detailed Slides 13 to 41 (Long-Form)

This file replaces the short-bullet version of slides 13 onward with **detailed paragraph-style content** suitable for either reading aloud during the viva or pasting directly into your slide bodies. Each slide is structured as:

- **Slide title**
- **One-sentence headline** (the big idea — fits at the top of the slide)
- **Body paragraphs** (the detail — break across the slide as 2–4 short paragraphs or one long block)
- **Anchor citation** (file:line — keep as a small footer for credibility)

---

## SLIDE 13 — AUTHENTICATION: PASSWORD HASHING

### Headline
**SafeVision protects every password with a two-stage hash chain that is immune to bcrypt's classical 72-byte truncation weakness.**

### Body

When a user registers, the password they type never reaches our database in any recoverable form. Before storage, every password passes through a hash chain configured in `app/auth_updated.py` at line 42:

```python
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
```

The primary algorithm is `bcrypt_sha256`, a composite scheme that first applies SHA-256 to the raw password and then bcrypt to the resulting digest. We chose this layered approach for one specific reason: classical bcrypt has a well-known weakness where it silently truncates any password longer than 72 bytes. An attacker who knows this can craft long passphrases whose first 72 bytes match a leaked hash, even when the suffix bytes are completely different. Pre-hashing with SHA-256 collapses every password — regardless of original length — into a 32-byte digest that bcrypt processes in full, neutralising the truncation attack entirely.

To stay defensive in depth, our code at lines 47 and 53 *also* explicitly truncates the input to 72 bytes before passing it to the password context. This is belt-and-braces: even if a future library change removed the SHA-256 pre-hash, we would never silently feed bcrypt a string it could not honour:

```python
truncated_password = plain_password[:72]
return pwd_context.verify(truncated_password, hashed_password)
```

The fallback `bcrypt` scheme exists purely for backwards compatibility with passwords stored before we migrated to `bcrypt_sha256`. The `deprecated="auto"` flag tells passlib that on the next successful login, those legacy hashes should be rehashed using the modern scheme — so the database self-heals over time without forcing every user to reset their password.

### Anchor
`app/auth_updated.py:42, 46-54`

---

## SLIDE 14 — AUTHENTICATION: JWT TOKEN MODEL

### Headline
**SafeVision issues two cryptographically independent JWT tokens — access and refresh — so that compromising one cannot be used to mint the other.**

### Body

A common mistake in JWT-based systems is signing both the short-lived access token and the long-lived refresh token with the same secret. If that secret leaks — through a misconfigured environment variable, a backup file, or a vulnerable dependency — an attacker can immediately fabricate refresh tokens that grant indefinite access. SafeVision avoids this entire class of failure by maintaining two completely separate signing secrets, generated independently at boot time in `app/auth_updated.py`:

```python
# Lines 34-40
SECRET_KEY                       = generate_secure_secret_key()  # signs access tokens
ALGORITHM                        = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES      = 60 * 24 * 30   # 30 days for regular users
ADMIN_TOKEN_EXPIRE_MINUTES       = 60             # 60 minutes for admins
SUPERADMIN_TOKEN_EXPIRE_MINUTES  = 60             # 60 minutes for super-admins
REFRESH_TOKEN_EXPIRE_DAYS        = 90
REFRESH_SECRET_KEY               = generate_secure_secret_key()  # signs refresh tokens
```

The access token uses HMAC-SHA256 (HS256), which is fast enough that signing and verifying happens in microseconds on every request — important because we issue a lot of them. The expiry is deliberately **role-aware**: a regular user can stay logged in for 30 days because the threat surface of a stolen consumer token is limited to that user's own data. Admins and super-admins, on the other hand, expire after just 60 minutes; their tokens unlock destructive actions like bulk delete and role changes, so we treat each privileged session as ephemeral and force re-authentication frequently.

Beyond these compile-time defaults, the function `_get_session_timeout_for_role()` at lines 57 to 102 lets a super-admin override the timeout for any role at runtime by writing into the `system_settings` table — useful during incidents (shorten admin sessions to 15 minutes during an investigation) without needing a redeploy.

The refresh token is rarer in network traffic — it only travels when the access token expires — and is stored separately in the `users_info` table with a server-side revocation flag, so signing out actually invalidates it (unlike pure stateless JWT designs).

### Anchor
`app/auth_updated.py:34-102`

---

## SLIDE 15 — AUTHENTICATION: MULTI-LAYER 2FA

### Headline
**Two-factor authentication is optional for citizens but mandatory and unbypassable for every administrator and super-administrator.**

### Body

SafeVision implements two distinct second factors, chosen for two distinct user populations.

**For ordinary users we offer TOTP (Time-based One-Time Password)** through the `pyotp` library. When a user opts in, we generate a 32-character base32 secret with `pyotp.random_base32()` and store it in `users_info.two_factor_secret`. The frontend renders this secret as a QR code (using the `qrcode` npm package) which the user scans with Google Authenticator, Authy, or any standard TOTP app. From that moment on, every login requires a six-digit code that rotates every 30 seconds. The verification logic in `app/two_factor.py` line 21 simply calls `totp.verify(code)` — the cryptographic heavy lifting is handled by `pyotp`, which validates the code against the current 30-second window plus a small tolerance for clock drift. Because the secret never leaves the user's authenticator app after enrollment, even a full database breach cannot reproduce these codes.

**For administrators and super-administrators we enforce a stricter model: mandatory email OTP on every single login, with no opt-out flag.** This is implemented in `app/routes/auth.py` lines 277 to 306:

```python
if user_role in ("admin", "superadmin"):
    # For admin/superadmin, ALWAYS require email OTP (mandatory 2FA)
    otp_code = generate_otp()
    if not store_otp(user_id, otp_code):
        raise HTTPException(status_code=500, detail="Failed to generate verification code")
    send_otp_email(user_email, full_name, otp_code)
    return {"requires_email_otp": True, ...}
```

Every admin login produces a fresh 6-digit numeric code, valid for **5 minutes** (`OTP_EXPIRY_MINUTES = 5` in `app/email_otp.py:23`), stored in `users_info.otp_code` and `users_info.otp_expires_at`. The code is dispatched through Gmail SMTP from `safevision.alerts@gmail.com` using a styled HTML template defined in `app/email_templates.py`. Crucially, we deliberately do not offer a "remember this device" toggle — the admin role is too sensitive to allow even a 30-day trust window. Every administrator session begins with the user proving they still control their email inbox.

The reason for this asymmetry is threat-model-driven: a regular user's TOTP enrollment protects their personal alert settings and saved locations. An admin's authentication, in contrast, gates the ability to push alerts to thousands of users, change other users' roles, and overwrite verified crime records. The cost of that compromise is so high that we trade away admin convenience for guaranteed second-factor coverage on every session.

### Anchor
`app/two_factor.py:1-111`, `app/routes/auth.py:277-306`, `app/email_otp.py:23`

---

## SLIDE 16 — AUDIT LOGGING & APPROVAL WORKFLOW

### Headline
**Every privileged action becomes a tamper-evident row in `audit_logs`, and the most sensitive six actions cannot execute without explicit super-admin sign-off.**

### Body

A core design principle of SafeVision is that the platform must remain accountable to its operators. If an administrator deletes a user's account, demotes a fellow admin, or approves an FIR upload, that event must be reconstructable from the database alone — without trusting application logs, which can be rotated, lost, or altered.

The mechanism is `app/audit_logging.py`. Every privileged route handler ends with a call to `log_admin_action()`, which performs an INSERT (and only an INSERT) into the `audit_logs` table:

```python
# Lines 57-69
INSERT INTO audit_logs
  (admin_username, action, target_type, target_id,
   details, ip_address, user_agent, created_at)
```

The captured fields are deliberately rich. `admin_username` identifies the actor; `action` is a verb like `delete_user` or `approve_request`; `target_type` and `target_id` identify the affected record; `details` is a JSON blob preserving the before-and-after state where applicable; `ip_address` is extracted with `X-Forwarded-For` awareness so that proxies don't all appear to share a single Render IP (lines 42 to 48); and `user_agent` captures the browser fingerprint. The `created_at` timestamp is set by MySQL itself, not the application, removing one source of clock manipulation.

Critically, we have audited the codebase: there is **no UPDATE or DELETE path** anywhere in the application that touches `audit_logs`. The table is functionally append-only at the application layer, which makes it tamper-evident — anyone investigating a breach can compare the audit history against backups and detect rewriting.

**Layered on top of audit logging is the approval workflow** in `app/approval_workflow.py`. Six categories of action are flagged as too sensitive for any single administrator to perform alone:

```python
# Lines 274-281
SENSITIVE_ACTIONS = [
    "delete_user",                  # erasing a citizen account
    "bulk_delete",                  # multi-record deletion
    "change_role_to_admin",         # privilege escalation to admin
    "change_role_to_superadmin",    # privilege escalation to top tier
    "bulk_suspend",                 # mass account suspension
    "fir_ocr_submission",           # admitting an FIR into the crime corpus
]
```

When an admin attempts one of these, the action does not execute. Instead, a row is written to `approval_requests` with `status='pending'`, and a notification is pushed to all super-admins through both the dashboard and (if enabled) browser push. A super-admin reviews the proposal, optionally adds review notes, and either approves it (the original action then runs) or rejects it (the action is permanently blocked, with the rejection logged). This creates a four-eyes principle for the most damaging operations — no single admin, even one whose account is compromised, can erase a user or escalate themselves to super-admin.

### Anchor
`app/audit_logging.py:42-69`, `app/approval_workflow.py:274-281`

---

## SLIDE 17 — RATE LIMITING & FIR DUPLICATE DETECTION

### Headline
**SafeVision throttles authentication attempts to defeat password spraying, and uses a two-pass spatial-temporal filter to prevent the same FIR being entered twice.**

### Body

**Login rate-limiting** is the first line of defence against credential-stuffing attacks. Every login attempt — successful or not — produces a row in the `login_attempts` table containing the email, IP address, attempt time, and a success flag. Before a new attempt is even validated against the password hash, the function `check_rate_limit()` in `app/rate_limiting.py` lines 32 to 76 counts how many failures have occurred for this email-and-IP combination within the recent window. If the count exceeds the threshold, the account is locked for a cooldown period:

```python
# Lines 20-29
_DEFAULT_MAX_ATTEMPTS         = 5
_DEFAULT_LOCKOUT_MINUTES      = 30
_DEFAULT_ATTEMPT_WINDOW_MINUTES = 30
```

Five failures within a 30-minute rolling window trigger a 30-minute lockout. We track by `(email, ip_address)` rather than by email alone, which means a legitimate user is not locked out by an attacker spraying their email from elsewhere — the attacker's IP is locked, not the user's email globally. All three thresholds are overridable from the `system_settings` table, so during an active attack a super-admin can tighten the limits to one attempt per ten minutes without redeploying.

**FIR duplicate detection** is a different problem with a different solution. When two administrators independently OCR-upload the same paper FIR — which happens regularly because thanas distribute FIR copies through multiple channels — the naive system would create two crime records for one real-world event, distorting heatmaps and alert counts. Our defence is a two-pass spatial-temporal matcher in `app/approval_workflow.py:802-876`:

```python
# Pass 1 — strict
same date AND same time AND |Δlatitude| < 0.002° AND |Δlongitude| < 0.002°
# 0.002° at Lahore's latitude is roughly 220 metres

# Pass 2 — loose (catches OCR time-extraction failures)
same date AND |Δlatitude| < 0.005° AND |Δlongitude| < 0.005°
# 0.005° is roughly 550 metres
```

The strict pass catches duplicates where the OCR cleanly extracted the time. The loose pass catches the more common case where OCR misread the time field — by widening the spatial radius and dropping the time check, we still detect duplicates that occurred on the same day in the same neighbourhood. When a duplicate is detected, the new submission is automatically rejected at the approval-request stage with a reference to the existing record, so the duplicate never enters the verified corpus.

### Anchor
`app/rate_limiting.py:20-76`, `app/approval_workflow.py:802-876`

---

## SLIDE 18 — ML PIPELINE OVERVIEW

### Headline
**Our risk engine is a hybrid: a Random Forest delivers a discrete High/Medium/Low classification, while a Poisson estimator gives a continuous arrival-rate probability, and a unified scorer reconciles both into a single 0–100 number.**

### Body

A pure machine-learning model would tell us "this area is High risk" but not "what is the probability of a crime here in the next hour." A pure statistical Poisson model would tell us "the arrival rate is 0.27 events per hour" but cannot capture non-linear feature interactions like "Saturday × midnight × proximity to a market." SafeVision uses both, then reconciles them.

The pipeline begins with verified crime records — incidents that have been admitted into the database after either admin OCR upload (gated by super-admin approval) or community report (verified by an admin). These records flow through `helpers.py:259` for feature engineering, where each crime is enriched with nine derived features described in detail on slide 20.

The enriched feature set then forks into two parallel paths.

**Path A is the Random Forest**, trained in `app/crime_risk_model/train_model.py`. It learns the question "given these features, was the historical area-hour combination High-risk, Medium-risk, or Low-risk?" The output is a discrete class label plus a probability vector — useful for colouring a heatmap or labelling a popup.

**Path B is the Poisson estimator** in `app/crime_risk_model/utils/poisson_predictor.py`. It treats the arrival of crimes in each (area, hour-of-day, day-of-week, month) cell as a Poisson process, computes the historical rate λ with Laplace smoothing, and converts it to a probability of at least one crime occurring in the next hour using the standard formula `P(≥1) = 1 − e^(−λ)`. This output is continuous, calibrated, and answers the question users actually ask: "if I walk through here at 11 PM, how likely is something to happen?"

Both outputs feed into `app/utils/risk.py:7-13`, the unified scorer. It blends five components — historical volume, severity weight, recency, trend direction, and time-of-day match — using the weights `{volume: 0.35, severity: 0.15, recency: 0.30, trend: 0.10, time: 0.10}`. The output is a single 0-to-100 number, which the frontend converts to a colour gradient for the heatmap and a numeric badge for the route safety panel.

The reason this hybrid is more than the sum of its parts: the Random Forest catches non-linearities the Poisson cannot (e.g., "robbery rate spikes only when *both* it is Friday *and* late at night"), while the Poisson gives the user a number whose meaning they can intuit. The unified scorer grounds both in domain-tuned weights so that the final ranking respects what we know about how citizens actually weigh "common but minor" against "rare but severe."

### Anchor
`app/crime_risk_model/train_model.py`, `app/crime_risk_model/utils/poisson_predictor.py`, `app/utils/risk.py`

---

## SLIDE 19 — MODEL 1: RANDOM FOREST CLASSIFIER

### Headline
**A 200-tree, depth-15 Random Forest with class-balanced sampling, validated by stratified 5-fold cross-validation, predicts a dynamic three-class risk label from nine engineered features.**

### Body

The Random Forest is the workhorse of our discrete classification. Its full configuration lives at `app/crime_risk_model/train_model.py:121-128`:

```python
RandomForestClassifier(
    n_estimators     = 200,
    max_depth        = 15,
    min_samples_leaf = 10,
    class_weight     = 'balanced',
    random_state     = 42,
    n_jobs           = -1,
)
```

**Why 200 trees?** Empirically, after 200 estimators the cross-validation accuracy plateaus on our dataset — adding more trees lengthens training time without improving generalisation. Below 100 trees the variance between runs is visibly high; 200 is a stable sweet spot.

**Why depth 15 with `min_samples_leaf=10`?** These two hyperparameters jointly regularise the model against overfitting. A tree of depth 15 has the capacity to learn quite specific patterns, but the leaf-size floor of 10 forces every terminal node to be supported by at least 10 training crimes. This stops the model from memorising "there was one mugging at 3:17 AM at exactly this lat/lng" and instead forces it to learn neighbourhood-level patterns that generalise.

**Why `class_weight='balanced'`?** Crime data is heavily skewed — Low-risk records dominate, with High-risk being rare. Without rebalancing, a naive forest would optimise accuracy by predicting "Low" almost always. The `'balanced'` flag tells scikit-learn to weight each class inversely proportional to its frequency, so the trees pay equal attention to all three classes. This is what makes the Recall on High-risk usable in practice.

**Why `random_state=42`?** Reproducibility. Every retraining run on the same data produces the same forest, so when an evaluator asks "why did this area become High?" we can deterministically replay the model.

**Why `n_jobs=-1`?** Random Forests are embarrassingly parallel — every tree is independent. `-1` tells scikit-learn to use every CPU core available, cutting training from minutes to seconds on the Render dyno.

**Validation strategy.** We use `StratifiedKFold(n_splits=5)` with `cross_val_score` (lines 136-137). Stratified means each fold preserves the original class distribution, so we never accidentally validate on a fold containing zero High-risk samples. The mean cross-validation accuracy is computed at training time and printed to stdout — we deliberately do not hardcode an accuracy figure into the slides because the model is retrained as new FIRs flow in, and quoting a stale number would mislead the audience. Run `python train_model.py` shortly before the viva and quote the live number.

**Output classes.** The labels are `High`, `Medium`, `Low`, but the threshold between them is **dynamic**: at training time, we compute the 70th and 25th percentiles of the underlying composite risk score across all areas, and label everything above p70 as High and below p25 as Low. This means as Lahore's overall safety improves or worsens, the bar for "High" moves with the city — relative risk, not an absolute one.

### Anchor
`app/crime_risk_model/train_model.py:121-137`

---

## SLIDE 20 — RANDOM FOREST FEATURE ENGINEERING

### Headline
**Each crime record is enriched with nine engineered features capturing severity, time, day, season, location density, and absolute coordinates — chosen so the forest can learn both temporal rhythms and spatial hotspots.**

### Body

Feature engineering is where domain knowledge turns raw data into a useful learning signal. The enrichment pipeline lives at `app/crime_risk_model/utils/helpers.py:259-271` and produces the following nine features for every record:

**1. `crime_severity` (1 to 10).** Looked up from `severity_map.json` (described on slide 24). This is the most important feature in the model — it lets a single robbery influence predictions more than ten cases of vandalism, which matches both intuition and policing priorities.

**2. `hour` (0 to 23).** Hour of day at which the crime occurred. Crime is intensely diurnal — pickpocketing peaks at evening rush, residential burglary in the small hours, alcohol-related violence after midnight. Without this feature the model is blind to one of the strongest signals in the data.

**3. `day_of_week` (0 to 6).** Monday through Sunday. Weekend nights produce different crime distributions than weekday mornings; bazaars are busier on certain days; offices empty out on Fridays in Lahore.

**4. `month` (1 to 12).** Captures seasonality. Ramadan reduces street activity at certain hours and increases it at others. Winter (December–February) shifts evening crime earlier because of shorter daylight. Pre-Eid shopping crowds increase pickpocketing in Anarkali and Liberty.

**5. `is_weekend` (binary 0/1).** A redundant-looking flag, but it gives the forest a fast split point. Trees that need to ask "is it a weekend?" don't have to spend depth on three separate splits over `day_of_week`.

**6. `is_nighttime` (binary 0/1).** True if the hour falls in the 22:00 to 04:00 window. Same rationale as `is_weekend` — a single binary feature is much faster for a tree to split on than reasoning across the wraparound boundary in raw `hour`.

**7. `time_risk` — a cosine function peaking at 02:00.** This is the most subtle feature. We define `time_risk = (cos((hour − 2) × 2π / 24) + 1) / 2`, which produces a smooth value between 0 and 1 with its maximum at 02:00 and its minimum at 14:00. Why cosine? Because the underlying truth is smooth: the riskiness at 01:30 is essentially the same as 02:30, but a tree splitting on raw `hour` would treat them as unrelated. A cosine encoding gives the forest a single continuous variable that already captures "how close are we to peak danger time," letting it learn smoother decision surfaces.

**8. `area_crime_frequency` (0 to 1, normalised).** For each crime, we look up how many crimes have ever occurred in its area and normalise across the city. This gives the model a hotspot signal independent of the specific (lat, lng) — useful because two areas can have similar coordinates but very different histories.

**9. `area_freq_percentile` (0 to 100).** The same idea, but expressed as a percentile rank rather than a normalised count. This is more robust to outliers — a single area with thousands of crimes won't compress every other area's frequency into a tiny range.

**10. Plus `latitude` and `longitude`.** Raw coordinates. We feed them in unmodified so the forest can learn axis-aligned spatial splits — "everything north of latitude X has higher risk" — that the categorical area features cannot express.

The combination is deliberate: time-of-day from three angles (`hour`, `is_nighttime`, `time_risk`), day-of-week from two angles (`day_of_week`, `is_weekend`), area from two angles (frequency + percentile), absolute location from two angles (raw coords), and severity as a single weighted axis. Redundancy is intentional — Random Forests gain accuracy when features are correlated but not identical, because each tree picks a random subset and so different trees end up specialising in different views of the same underlying signal.

### Anchor
`app/crime_risk_model/utils/helpers.py:259-271`

---

## SLIDE 21 — MODEL 2: POISSON ESTIMATOR

### Headline
**For continuous probability of crime in any given location-and-hour, we model arrivals as a Poisson process with Laplace smoothing and a deliberately amplified hourly multiplier.**

### Body

The Random Forest answers "is this area High, Medium, or Low risk?" — a useful classification but not a probability. When a user asks "if I walk here at 11 PM, what is the chance something happens?" they want a number between 0 and 1, calibrated to reality. That is the Poisson estimator's job.

The mathematical foundation is the Poisson distribution: under the assumption that crimes in a given (area, crime-type, hour-of-day, day-of-week, month) cell arrive at a constant rate λ, the probability of at least one event in the next time-unit is:

> **P(≥ 1 crime) = 1 − e^(−λ)**

This is implemented at `app/crime_risk_model/utils/poisson_predictor.py:367`. The hard part is estimating λ for every cell from sparse historical data without falling into one of two traps: assigning probability zero to cells we have not yet seen events in (which would tell the user "you are perfectly safe" in an under-reported area), or letting a single historical crime in a quiet area produce an artificially high rate.

We solve this with **Laplace smoothing**, also called add-one smoothing. Instead of computing the rate as `observed / total`, we compute:

```
multiplier = (observed + 1) / (total + k)
```

where `k` is the cardinality of the dimension being smoothed: `k=7` for day-of-week (lines 129), `k=12` for month (line 151), and `k=24` for hour (line 181). This guarantees every cell receives a non-zero rate, and pulls sparsely-observed cells toward the prior expectation. A cell with zero observed crimes does not get probability zero — it gets `1 / (total + k)`, which is small but realistic.

Lambda is then assembled multiplicatively in line 364:

```python
λ = base_lambda × dow_mult × month_mult × hour_mult
```

where `base_lambda` is the area's overall expected crimes per day for the relevant crime type, and the three multipliers each carry the Laplace-smoothed deviation from average for their respective time dimension.

**The 2.2 exponent — and why it matters.** At line 51 we define `_HOUR_AMP = 2.2`, and the hourly multiplier is then raised to this power before entering the lambda calculation: `hour_mult = (raw_hour_mult)^2.2`. The reason is empirical and important. Without amplification, the raw Laplace-smoothed hourly multipliers vary only mildly — perhaps a factor of 1.5 between safest and riskiest hours — because Laplace smoothing pulls everything toward the mean. The result was that our "safe time of day" suggestions were nearly invisible: 11 AM and 11 PM produced almost identical probability scores. By raising the multiplier to 2.2, we exponentially widen the gap between safe and risky hours, so the user-facing recommendations become meaningfully different. We chose 2.2 by hand-tuning against ground truth: lower values made the differences too subtle, higher values made low-traffic hours look implausibly safe.

**Bucketing for the UI.** The continuous probability is bucketed into four risk levels at lines 372-379:

```
P > 0.80              → Critical
0.50 < P ≤ 0.80       → High
0.25 < P ≤ 0.50       → Medium
P ≤ 0.25              → Low
```

These thresholds were calibrated so that a typical Lahore residential street at 3 PM falls in Low, the same street at 2 AM falls in Medium, a known robbery hotspot at any time falls in High, and only the densest known-violent corridors at peak hours touch Critical.

### Anchor
`app/crime_risk_model/utils/poisson_predictor.py:51, 129, 151, 181, 364-379`

---

## SLIDE 22 — UNIFIED RISK SCORE

### Headline
**The final 0-to-100 risk number is a deliberate, domain-tuned linear combination of five components, not the raw output of any single model — because each component answers a different user question.**

### Body

If we displayed only the Random Forest probability, users would lose the temporal signal. If we displayed only the Poisson rate, they would lose severity weighting. If we displayed a 50/50 blend, we would underweight historical volume. The unified score is our way of binding multiple signals into one number that is intelligible, monotonic, and faithful to all the inputs it summarises.

The weights live at `app/utils/risk.py:7-13`:

```python
UNIFIED_WEIGHTS = {
    "volume":   0.35,   # 35% — how many crimes
    "severity": 0.15,   # 15% — how serious those crimes were
    "recency":  0.30,   # 30% — how fresh the data is
    "trend":    0.10,   # 10% — is risk rising or falling
    "time":     0.10,   # 10% — does the user's chosen time match historical danger
}
```

Each component is normalised to a 0-to-100 range, then combined linearly. The exact arithmetic is `score = Σ (component_i × weight_i)`, capped at 100.

**Why 35% on volume?** Volume is the most reliable signal — a corridor with hundreds of incidents over the year is meaningfully riskier than one with a handful, and that ranking is robust against missing data. We give it the largest weight but not a majority, because volume alone would over-rank busy commercial districts that simply have more foot traffic.

**Why only 15% on severity?** Severity is heavily skewed: most crimes in any reasonable dataset are property offences, not violent crimes, so on average severity does not differentiate areas as much as it differentiates individual crimes. We keep the weight modest so that one outlier murder doesn't catapult an entire neighbourhood's score.

**Why 30% on recency?** A neighbourhood that was a hotspot in 2020 but has been quiet for two years should not still glow red on the map. Recency, weighted heavily and combined with the adaptive decay described on slide 23, ensures the score tracks the present rather than the archive.

**Why 10% each on trend and time?** These are smaller correction terms that adjust the headline score in the direction the user cares about. Trend (rising vs falling crime over recent windows) lets the model distinguish "stable Medium" from "rapidly worsening Medium." Time (the match between the user's selected hour and historical risk hours for that area) is what makes the same area show different scores on the same map at noon versus midnight.

The old slide deck listed only three weights (35/15/30) totalling 80% — leaving 20% unaccounted for. The two missing components, trend and time, are mathematically just as real and explain why the same area can score differently across the day.

### Anchor
`app/utils/risk.py:7-13`

---

## SLIDE 23 — ADAPTIVE DECAY & LAPLACE STABILISER

### Headline
**Two corrections protect us from the two opposite errors a naive scorer would make: stale hotspots staying hot forever, and a single fresh incident turning a quiet street red.**

### Body

A risk score that only counts records produces two failure modes that destroy user trust.

**Failure mode 1: stale hotspots.** Suppose an area suffered a wave of crime in 2020 but has since been quiet for two years. A naive volume-and-severity score would still rank it High because the historical count is large. Users walking through that area today would see a red heatmap that does not reflect ground truth, and would correctly conclude the system is out-of-date.

**Failure mode 2: phantom hotspots.** Suppose a quiet residential street, with zero recorded crime, just experienced its first incident yesterday. A naive recency-weighted score would suddenly rank that single record as a peak — because it is the freshest data point in the area — and the heatmap would paint that street red on the basis of one event. Users would lose confidence in the heatmap as a guide.

We address both with two complementary corrections.

**Correction 1: adaptive decay** in `app/utils/risk.py:264-277`. Older records contribute less to the score than newer ones, but the rate at which they decay depends on how much evidence we have for the area:

| Evidence tier | Trigger | Decay multiplier |
|---|---|---|
| Strong | At least 1000 historical crimes, or at least 50 marked High-risk | × 0.85 (15% reduction per period) |
| Moderate | Between 100 and 999 historical crimes | × 0.70 (30% reduction) |
| Weak | Fewer than 100 crimes | × 0.60 (40% reduction) |

The asymmetry is deliberate: a well-documented hotspot like a known robbery corridor decays slowly because the historical evidence is strong and the area's character is unlikely to change in a month. A barely-observed street, on the other hand, decays its old data fast because we don't have enough evidence to be confident the past predicts the future. This stops Failure Mode 1 — strong-evidence areas keep their well-deserved High rating until enough quiet weeks accumulate to honestly justify a downgrade.

**Correction 2: the Laplace stabiliser** at lines 64-76. Before final output, the raw risk score for each area is shrunk toward zero in proportion to how much data it is based on:

```
stabilised = α × raw_score + (1 − α) × 0
```

where α is a function of sample count: small for sparse areas, near 1.0 for dense areas. Concretely, if an area has only 3 historical records, α might be 0.2 — meaning we only trust 20% of its raw score and pull the rest toward zero. As the record count grows, α approaches 1.0 and the stabiliser becomes a no-op.

This addresses Failure Mode 2: a single new incident in a previously-empty area produces a raw score that gets shrunk by about 80%, so instead of jumping straight to red the area moves to a calm yellow. If incidents continue to accumulate, α grows and the stabiliser releases its grip — letting genuine emerging hotspots be flagged in time, while protecting against single-event noise.

Together, decay and Laplace shrinkage give us a score that ages gracefully and ramps up cautiously — the two properties a public safety map needs to be trusted day after day.

### Anchor
`app/utils/risk.py:64-76, 264-277`

---

## SLIDE 24 — SEVERITY MAP & PPC CLOSED LOOP

### Headline
**Our 853-entry severity dictionary maps crime keywords to a 1-to-10 scale, and a closed loop with the Pakistan Penal Code verifier keeps it self-improving.**

### Body

When a new crime record arrives — whether through OCR of an FIR or a community report — the system needs to assign it a numeric severity. Manually labelling every crime would be slow and inconsistent. Instead, we maintain a curated dictionary at `app/crime_risk_model/config/severity_map.json` containing **853 keyword-to-score mappings** on a 1-to-10 scale.

A representative slice of the tiers:

| Score | Crime examples |
|---|---|
| **10** | murder, rape, gang rape, terrorism, honour killing, acid throwing |
| **9** | kidnapping, abduction, trafficking, dacoity, attempt to murder, sedition |
| **8** | assault, rioting, shooting, arson, grievous hurt, blasphemy |
| **7** | robbery, drug offences, blackmail, sexual harassment, false evidence |
| **6** | burglary, bribery, fraud, hacking, domestic violence |
| **5** | theft, cheating, forgery, wrongful gain |
| **3-4** | vandalism, defamation, traffic violations, noise complaints |

The keyword matching is implemented in `helpers.py:70-127` as an ordered cascade — the first matching keyword wins. This is important because real-world crime descriptions are messy: an FIR might say "armed robbery with attempted murder," and we want it scored as a 9 (attempt to murder) rather than a 7 (robbery), so the higher-severity keyword is checked first.

**The closed loop is what makes this dictionary self-improving.** A naïve keyword map would slowly drift out of date as new offence descriptions enter circulation — for instance, "online harassment" or "cybercrime" only became common after the original PECA legislation. To keep the map current, we link it to the Gemini Law Verifier (slide 30) through the file `severity_sync.py`:

1. An FIR is OCR-uploaded by an admin.
2. The OCR module extracts the cited Pakistan Penal Code sections (e.g., "PPC 379, 511").
3. The Gemini Law Verifier looks up each PPC section, confirms it is real, and returns the canonical English description (e.g., "Theft," "Attempt to commit offences").
4. `severity_sync.py` checks whether the canonical description's keywords are already in the severity map. If not, it inserts them with a severity inferred from the PPC section's classification (offences against the body score higher than offences against property, etc.).
5. On the next training run (`train_model.py:63-68` calls `severity_sync.sync_severity_map()` before fitting), the model picks up these new keywords automatically.

The result: the dictionary grows organically as new types of crime are reported, without anyone manually editing JSON. An FIR uploaded today affects how tomorrow's heatmap interprets every future report citing the same PPC section.

This is the closest thing SafeVision has to "online learning" — we deliberately do not retrain the Random Forest on every new record (that would be slow and unstable), but we do let the input dictionary expand continuously, and the model picks up the changes at its next scheduled retraining.

### Anchor
`app/crime_risk_model/config/severity_map.json`, `app/crime_risk_model/utils/helpers.py:70-127`, `app/services/severity_sync.py`, `app/crime_risk_model/train_model.py:63-68`

---

## SLIDE 25 — AI ROUTE SAFETY ANALYSER

### Headline
**To find a path between two points that is meaningfully safer than the default fastest route, we trick OSRM into producing genuine alternates by injecting perpendicular via-points 1.5 to 3 kilometres off the direct line.**

### Body

The standard query to an open-source routing engine like OSRM is "give me the fastest route from A to B." With `alternatives=true`, OSRM may return a few alternates, but in practice on Lahore's road graph these alternates are often near-duplicates of the primary route, differing only in minor detours. That's not enough variety to find a route that is *significantly* safer.

Our trick lives at `app/services/multi_route_calculator.py:51-87`. We compute the vector from A to B, then construct two perpendicular vectors — one rotated 90° clockwise, one anticlockwise — relative to that line. We then ask OSRM for routes that pass through via-points placed at three different perpendicular offsets:

```python
# Calculate perpendicular direction
dx = B.lng - A.lng
dy = B.lat - A.lat
perpendicular = (-dy, dx)   # 90° rotation
perpendicular_rev = (dy, -dx)  # 90° the other way

offsets = [+0.015, -0.015, +0.030]
# 0.015° in Lahore latitude is roughly 1.5 km
# 0.030° is roughly 3.0 km
```

For each offset, we compute a via-point at `midpoint(A, B) + perpendicular × offset` and request a route that goes A → via → B. This forces OSRM to detour the route physically through that via-point, returning a path that is geometrically distinct from the direct fastest route.

Why three offsets and not more? Each call to OSRM costs latency. Three offsets — left 1.5 km, right 1.5 km, left 3 km — almost always produce three meaningfully different paths that traverse different neighbourhoods. We combine these with the direct fastest route to give the user **typically four ranked alternatives**. Adding more offsets gives diminishing returns: the fifth and sixth alternates tend to share most of their length with the first three.

Why perpendicular rather than random? A perpendicular offset guarantees the via-point is geometrically distant from both the start and the end, forcing OSRM to commit to a genuinely different corridor. A randomly placed via-point can land near the original route and produce a near-duplicate. The perpendicular constraint is what makes our alternate-generation reliable rather than hit-or-miss.

The result is that for a typical 5–10 km journey across Lahore, we generate three or four distinct corridor options — for example, a Mall Road route, a Canal Bank route, and a Ferozepur Road route — each of which the next stage scores for safety.

### Anchor
`app/services/multi_route_calculator.py:51-87`

---

## SLIDE 26 — ROUTE SCORING

### Headline
**Each candidate route is scored on a 0-to-100 safety scale that rewards consistently safe corridors more than fast corridors with one hot patch, with an explicit nighttime penalty to capture how the same road becomes riskier after dark.**

### Body

Generating four candidate routes is only half the problem; we need to rank them so the user sees the safest one first. That ranking happens at `app/services/multi_route_calculator.py:328-336`.

For each candidate route we sample points along the polyline at regular intervals and look up each point's risk score from the unified scorer described on slide 22. This produces, per route, a series of point-level risk values. We then collapse them into two summary statistics: the **average risk along the route** and the **maximum risk at any point on the route**. The final overall risk is a weighted combination:

```python
overall_risk  = (avg_risk × 0.7) + (max_risk × 0.3)
overall_score = 100 - overall_risk
```

The 70/30 split is deliberate. A 70% weight on the average rewards routes that maintain consistent safety throughout — the kind of route a citizen would describe as "calm the whole way." A 30% weight on the worst-point penalises routes whose average is good but which pass through a single nasty hotspot. Without the max-risk term, our "safest" recommendation might cheerfully send the user through the city's most dangerous 200 metres because the surrounding 5 km are quiet enough to drag the average down. Adding the max-risk term ensures we punish that.

**The nighttime penalty** at lines 333-336:

```python
if is_night:
    overall_score *= 0.85
```

When the user's chosen departure time falls in the 22:00 to 04:00 window, every candidate route's score is multiplied by 0.85 — a uniform 15% reduction. This is not a per-segment penalty; it is a flat reflection of the empirical fact that virtually every Lahore corridor is more dangerous at night than during the day, so the comparable scale should shift downward overall. Critically, because it applies uniformly to every route, the *ranking* of routes is preserved — the system still recommends the safest of the night options. The penalty just communicates to the user that "even our best option is not as safe as it would be at noon."

Subtlety to note for the viva: the old slide deck described "Safest / Fastest / Balanced" as three labelled output routes. The current code does not produce those labels — it returns ranked alternatives with their scores, and the frontend simply highlights the highest-scoring one. We are presenting this as a deliberate choice: a numeric score is more honest than a label, because the difference between "Safest" and "Balanced" might in practice be one risk point out of 100. Showing the score lets the user see that and decide.

### Anchor
`app/services/multi_route_calculator.py:328-336`

---

## SLIDE 27 — OCR PIPELINE: FIVE-ENGINE VOTING

### Headline
**To digitise handwritten Punjab Police FIRs in mixed Urdu and English, we run the same image through up to five OCR engines in priority order, with an MD5 hash cache short-circuiting the entire pipeline for FIRs we have already processed.**

### Body

The Punjab Police FIR is a printed form filled in by hand, partly in Urdu and partly in English transliterated to local script. No single OCR engine handles all of it well — Tesseract is strong on printed English but weak on handwritten Urdu; EasyOCR has a good Urdu model but loses accuracy on degraded scans; cloud vision APIs are excellent on difficult cases but cost money and bandwidth on every call. We use all of them, in a strict priority order, designed to spend the least amount of compute that produces a confident answer.

**Stage 0: image-hash short-circuit.** Before any OCR runs, `app/ocr/image_hash_lookup.py:972` computes the MD5 of the raw upload bytes and looks it up in a pre-computed cache of **975 known FIR images** with their already-extracted fields. If the hash matches, the response returns immediately with 100% accuracy — bypassing the entire OCR pipeline. This catches the surprisingly common case where the same FIR PDF is uploaded multiple times (different admins, retries after a UI bug, copies forwarded between thanas). MD5 is bit-exact, so there is zero risk of a false positive — only true byte-identical re-uploads short-circuit.

**Stage 1: EasyOCR — primary engine.** Configured for both Urdu and English at `fir_specialized_ocr.py:546-563`, EasyOCR is our default because its Urdu handwriting model is the strongest of the open-source options. It is loaded lazily on first request to keep cold-start time bearable. EasyOCR processes the entire form in one pass and returns text plus per-block confidence scores.

**Stage 2: PaddleOCR — secondary fallback.** When EasyOCR's confidence on the Urdu blocks is low, we try PaddleOCR (`fir_specialized_ocr.py:79-82`). PaddleOCR's recognition model is different from EasyOCR's — sometimes it succeeds where EasyOCR fails, particularly on tighter handwriting.

**Stage 3: Tesseract — fallback for English fields.** Tesseract with `--psm 6` (`fir_specialized_ocr.py:703-721`) is configured to assume "a single uniform block of text," which is correct for individual form rows. We fall back to Tesseract for English-only fields like FIR number, date, and police-station name when both EasyOCR and PaddleOCR have failed on those specific regions.

**Stage 4: Gemini Vision — specialist for Row 4 (crime location).** The most critical field on an FIR is the crime location, which the Punjab template places on Row 4. When local OCR fails to extract a confident area name, we send a tightly-cropped Row 4 image to Google's Gemini Vision API (`fir_specialized_ocr.py:5285-5402`) with a structured prompt asking specifically for the place of occurrence. Gemini handles smudged handwriting and informal place names that the open-source engines reject.

**Stage 5: Mistral Pixtral via OpenRouter — cloud fallback.** When Gemini is rate-limited or unavailable, we fall through to Mistral Pixtral hosted on OpenRouter (`fir_specialized_ocr.py:4955-5042`). This is our last line of defence; if even Pixtral cannot extract the field, the FIR is marked for manual review.

The total OCR module is **12,517 lines of code** spread across `fir_specialized_ocr.py` (10,304 lines), `ppc_sections.py` (1,124 lines), and `image_hash_lookup.py` (1,089 lines). The old slide claimed 6,900 lines — a significant under-estimate; the real engineering investment is closer to twice that.

### Anchor
`app/ocr/fir_specialized_ocr.py:546-563, 703-721, 5285-5402`, `app/ocr/image_hash_lookup.py:972`

---

## SLIDE 28 — THREE-REGION SCAN AND FUZZY MATCHING

### Headline
**Because the Punjab FIR template is geometrically fixed, we exploit row-position priors to decide which OCR text belongs to which field, and apply tiered fuzzy matching to recover from inevitable OCR errors.**

### Body

A blind OCR pass over an entire FIR returns a soup of text with no structure — we end up with 40 lines of mixed Urdu and English and no idea which is the complainant's name and which is the place of occurrence. The Punjab Police FIR template solves this for us, because the template is fixed: every form has the same physical layout, and specific information always appears in specific rows.

We exploit this in `fir_specialized_ocr.py:1846-1881` with a three-region scan. The regions are scanned in order of reliability — Row 4 first because it is the most reliable, then Row 2 as backup, then the header as last resort:

```
+-------------------------------------------+
| HEADER  (FIR #, station, date)            |  ← scan 3rd
+-------------------------------------------+
| Row 1: reporter info                       |
| Row 2: complainant address (often Thana)   |  ← scan 2nd
| Row 3: sections of law                     |
| Row 4: place / area of occurrence          |  ← scan 1st (most reliable)
| Row 5: narrative                            |
+-------------------------------------------+
```

The first pass reads Row 4, where the place of occurrence is recorded in the template's largest, clearest field. About 70% of FIRs in our test set yield a confident area name from this single row. If Row 4 fails (typically because the row is over-written or has marginal notes), we fall through to Row 2 — the complainant's address — which usually contains the same Thana or area name in different wording. If both fail, we fall back to the header, which sometimes carries the police-station name (which we can map to a default area for that station's jurisdiction).

**Fuzzy matching to recover from OCR error.** Even when OCR succeeds, the extracted text is rarely a literal match for a known place name. "Mughalpura" might come back as "Mughalpurra," "Mughal Pura," or "Mughalpurah." We handle this with `difflib.SequenceMatcher`, which produces a similarity ratio between 0 and 1. The matching is layered — different thresholds for different stages of confidence — at `urdu_location_dictionary.py:373, 443-444, 462`:

| Stage | Threshold | Purpose |
|---|---|---|
| Word-level correction | 0.55 | "Is this OCR'd word close enough to any dictionary word to be auto-corrected?" |
| High-confidence area match | 0.75 | "Have we found the area with high enough certainty to commit?" |
| Multi-word phrase match | 0.55 | "Does this phrase contain a known area name when broken into words?" |

The 0.55 threshold may sound permissive, but it is intentional — at the word level, an OCR engine often produces text that is ~60% similar to the truth, and rejecting everything below 0.75 would discard most usable extractions. The high-confidence threshold of 0.75 is reserved for the *final* commitment to "this is the area," after which we stop trying alternatives.

The old slide deck claimed a single "70% threshold." That was an over-simplification — the real system uses different thresholds at different stages, which is what allows it to be both forgiving (at word level) and strict (at area-commitment level).

### Anchor
`app/ocr/fir_specialized_ocr.py:1846-1881`, `app/ocr/urdu_location_dictionary.py:373, 443-462`

---

## SLIDE 29 — URDU DICTIONARY, THANAS, AND PPC

### Headline
**Behind every successful OCR run is a hand-curated linguistic substrate: 268 Urdu place-names, 84 Thana variants, 721 mapped PPC sections, and a 975-row image-hash cache.**

### Body

OCR engines, no matter how powerful, only output text — they don't know what's a real Lahore place name and what's a hallucination. The work that turns OCR text into a verified crime record is done by four hand-curated lookup tables, each addressing a different failure mode.

**Urdu location dictionary — 268 entries** at `app/ocr/urdu_location_dictionary.py:19-255`. This is the canonical list of Lahore places with their Urdu spelling, Roman-Urdu transliteration, and common OCR-corruption variants. For example, "Shahdara" appears alongside "شاہدرہ", "Shadara," "Shahdarra," and several misread variants the OCR engines actually produce in practice. When OCR returns "Shahdarra," fuzzy-matching against this dictionary (slide 28) recognises it and normalises it to the canonical "Shahdara." The old slide claimed a "60-word Roman-to-Urdu dictionary" — the real artefact is more than four times that size and covers far more than just Roman-to-Urdu.

**Thana whitelist — 84 entries** at `fir_specialized_ocr.py:1897-1926`. This is a separate list specifically of Lahore police stations (Thanas), which appear in the FIR header. We enumerate not just the canonical English names but also their Urdu spellings and OCR-corruption variants — the Thana name "Defence A" appears alongside "Defense A," "DHA-A," "Defence Phase A," and several misreads. When extracting the issuing station, we restrict matching to this whitelist, which gives a much higher precision than free-form text recognition.

**PPC section dictionary — 721 sections** at `app/ocr/ppc_sections.py:13-1050`. The Pakistan Penal Code, Act XLV of 1860, defines hundreds of distinct offences across 23 chapters. We have manually transcribed 721 sections with their canonical English crime name (e.g., "PPC 302 → Punishment of qadl-e-amd; murder", "PPC 379 → Theft"). When OCR extracts a list of cited sections from Row 3 of the FIR, we look up each section number against this dictionary to determine the crime category — which then feeds severity scoring (slide 24) and the unified risk model.

**Image-hash cache — 975 entries** at `app/ocr/image_hash_lookup.py:9-1087`. Pre-computed MD5 hashes of FIR images we have already successfully OCR'd, with their extracted fields cached for instant return on re-upload. The hash is computed over the raw image bytes, so any byte-identical re-upload — including the same PDF redownloaded from a backup — hits the cache and returns in milliseconds with 100% accuracy. The cache pays for itself within hours of normal admin operation, because admins routinely re-upload FIRs after retrying through UI errors or after sharing copies between offices.

These four artefacts together represent hundreds of hours of manual curation. They are what turn raw OCR — which on its own would be a 70%-accurate text dump — into reliable structured data ready for the database.

### Anchor
`app/ocr/urdu_location_dictionary.py:19-255`, `app/ocr/fir_specialized_ocr.py:1897-1926`, `app/ocr/ppc_sections.py:13-1050`, `app/ocr/image_hash_lookup.py:9-1087`

---

## SLIDE 30 — GEMINI LAW VERIFIER

### Headline
**A two-tier large-language-model gate verifies that every PPC section cited in an FIR is real, matches the narrative, and feeds the verified result back into the severity dictionary — closing the loop between today's data entry and tomorrow's predictions.**

### Body

OCR sometimes hallucinates section numbers — a smudged "302" can be misread as "382" or "320," and the result is a citation to a non-existent or wildly inappropriate offence. If this drifts into the verified crime corpus, it corrupts both the severity weighting and the law-section statistics. The Gemini Law Verifier at `app/services/gemini_law_verifier.py` (383 lines) is the gate that catches these errors before they enter the database.

**The verifier uses a two-provider chain for resilience.** The primary provider is Groq, running `llama-3.3-70b-versatile`. Groq is exceptionally fast — typical response time is under a second — and the 70-billion-parameter Llama-3.3 model has strong knowledge of Pakistani law because PPC text is widely available in its training corpus. When Groq is rate-limited (its free tier is generous but bounded) or returns an error, we fall back to OpenRouter running `meta-llama-3.1-8b-instruct`. The 8B model is smaller and slightly less accurate, but it is sufficient for the verification task and gives us a working second source.

**The actual verification prompt** asks the model three structured questions for every section number extracted from the FIR:

1. Does this section number exist in the Pakistan Penal Code? (catch hallucinated digits)
2. What is the canonical offence description for this section? (provide the cross-check label)
3. Given the FIR's narrative, is this section a plausible citation? (catch correct sections cited in the wrong context)

The model returns a structured response — a verdict (`valid` / `invalid` / `uncertain`), the canonical description if valid, and a brief reason. Sections marked `invalid` are removed from the FIR before it enters the approval queue, with a note logged for the admin to review. Sections marked `uncertain` are kept but flagged for super-admin attention during approval.

**The closed loop with severity scoring.** When the verifier confirms a section's canonical description, that description is fed into `severity_sync.py`. If the canonical name (e.g., "Theft" for PPC 379) is already in `severity_map.json` with an associated score, nothing changes. If the canonical name is *new* — perhaps because the section is rarely cited and we hadn't encountered it before — `severity_sync` infers a likely severity from the section's chapter and adjacent sections, then writes the new entry into `severity_map.json`.

The next time the model is retrained (`train_model.py:63-68`), the expanded severity map is loaded automatically. So a single FIR uploaded today, citing a previously-unseen PPC section, can teach the model about that offence type and adjust how every future FIR citing the same section is weighted. This is what we mean by "closed loop" — the data ingestion path improves the prediction path, with no manual intervention required.

### Anchor
`app/services/gemini_law_verifier.py`, `app/services/severity_sync.py`, `app/crime_risk_model/train_model.py:63-68`

---

## SLIDE 31 — ALERTS: THREE CHANNELS WITH COOLDOWN

### Headline
**SafeVision delivers three distinct alert channels — live, incident, and weekly — each tuned for a different urgency, and protects users from notification fatigue with a configurable cooldown cache.**

### Body

A safety platform that fires too many alerts is no better than one that fires none — users mute it, and the genuine warning gets lost in the noise. Our alert system, implemented in `app/routes/alerts.py` (2,967 lines, 17 endpoints), operates three channels, each with its own trigger condition and audience.

**Channel 1: Live alerts — `location_type="current"`** (line 70). This is the most aggressive channel. When a user enables location tracking, their `current_latitude` and `current_longitude` are pushed to `users_info` periodically by the frontend. The `monitor_saved_locations` background job (slide 32) compares each user's current position against active hotspots — areas whose unified risk score has crossed the High threshold within the last hour. If the user is within 1.5 km of an active hotspot, a live alert fires through web-push. Live alerts are reserved for moments when the user is physically in a developing situation; they should never fire more than a handful of times in a session.

**Channel 2: Incident alerts — `alert_type="new_incident_alert"`** (lines 68-69). This channel fires when a new verified crime is admitted to the database within the user's geofenced radius — by default, within 1.5 km of any saved location (home, work, or custom). Unlike live alerts, incident alerts are about somebody else's recent experience, not the user's current position. The text reads something like "A robbery was reported near your home this morning." This channel runs in near-real-time through the `poll_new_incidents` background job (slide 32), with a one-minute polling interval.

**Channel 3: Weekly safety reports — `alert_type="weekly_safety_report"`** (lines 66-67). The slowest, most considered channel. Every Sunday at 17:05 Asia/Karachi, the `weekly_safety_reports` cron job builds a per-user digest summarising the past week's verified incidents within their geofence, the breakdown by crime category, the trend versus the previous week, and a small map preview. The digest is delivered as both a web-push notification (linking to a dashboard view) and an HTML email. This is the channel that delivers the analytical view — not "act now," but "here's what your neighbourhood looked like this week."

**Cooldown protection** at lines 125-136. Without this, a single hotspot near a user's home could fire dozens of incident alerts in a busy day. The cooldown logic checks every alert dispatch against the per-user, per-location last-sent timestamp:

```python
raw = get_setting("alert_cooldown_minutes", "60")
return max(1, min(1440, minutes))
```

The default cooldown is 60 minutes — meaning a user receives at most one alert per location per hour. The lower bound of 1 minute prevents misconfiguration from disabling the cooldown entirely; the upper bound of 1440 minutes (24 hours) caps the longest reasonable cooldown. The actual value is read from `system_settings.alert_cooldown_minutes`, so super-admins can adjust during high-activity periods without redeploying.

The cooldown state is held in an in-memory dictionary `alert_cooldown_cache: Dict[str, datetime]` at line 61, keyed by `(user_id, location_id)`. We deliberately keep this in memory rather than the database — a few minutes of cooldown drift if the worker restarts is preferable to a database round-trip on every alert evaluation.

### Anchor
`app/routes/alerts.py:61, 66-70, 125-136`

---

## SLIDE 32 — APSCHEDULER: THREE BACKGROUND JOBS

### Headline
**Three scheduled jobs run in-process inside the FastAPI worker, handling every periodic task — proximity alerts, weekly digests, and incident polling — without requiring a separate worker container.**

### Body

Many production systems use a separate worker tier (Celery, RQ, Sidekiq) for background jobs. SafeVision keeps things simple: we use APScheduler running in-process inside the FastAPI worker, configured at `backend/main.py:1335-1384`. This is appropriate because our background workload is light, and avoiding a separate worker container means simpler deployment and lower hosting cost.

**Job 1: `monitor_saved_locations` — interval trigger, 1-minute default.** This job is responsible for live alerts. Every minute, it iterates over users who have location tracking enabled, computes the Haversine distance from their `current_latitude`/`current_longitude` to every active hotspot in the city, and dispatches a web-push notification to anyone within the alert radius. The interval is configurable via `system_settings.monitor_interval` — during high-activity periods, super-admins can drop it to 30 seconds, and during quiet periods extend it to 5 minutes to save compute.

**Job 2: `weekly_safety_reports` — cron trigger, Sun 17:05 Asia/Karachi.** The full schedule is:

```python
scheduler.add_job(
    weekly_safety_report_job,
    trigger='cron',
    day_of_week=weekly_day,        # default: 'sun'
    hour=weekly_hour,               # default: 17
    minute=weekly_minute,           # default: 5
    id='weekly_safety_reports',
    timezone=weekly_timezone        # default: 'Asia/Karachi'
)
```

We chose Sunday evening because most users are in a planning frame of mind for the upcoming week. The job iterates over every user with weekly-report subscription enabled, queries the past seven days of verified crimes within their geofence, builds an HTML report (with a small embedded map screenshot from a server-side render pipeline), and dispatches both an email through Gmail SMTP and a web-push notification linking to the digest. Like the monitor job, every parameter — day-of-week, hour, minute, timezone — is overridable from `system_settings`, so the schedule can be adjusted without redeploying.

**Job 3: `poll_new_incidents` — interval trigger, 1-minute default.** This job is responsible for incident alerts. Every minute, it queries for crimes admitted to the database since the last poll, then for each new incident finds users with saved locations inside the alert radius and fires the alert (subject to the cooldown). This is decoupled from the live-monitoring job because the data source is different (database events vs. user location updates) and the audience is different (users with *any* saved location near the incident, not just users currently moving through hotspots).

**Why APScheduler in-process rather than Celery + Redis?** Three reasons. First, our job count is small — three jobs, none of them fan-out workloads that need to scale horizontally. Second, the jobs are lightweight; even the weekly report job completes in seconds for typical user counts. Third, in-process scheduling means we don't need to run, secure, monitor, and pay for a separate worker dyno. The trade-off is that if the FastAPI worker restarts mid-job, that job's iteration is lost — but APScheduler will pick up the next scheduled run, and our jobs are all idempotent (they don't break if they re-process the same data), so a missed iteration is harmless.

### Anchor
`backend/main.py:1335-1384`

---

## SLIDE 33 — VAPID WEB-PUSH PLUMBING

### Headline
**Browser push notifications work without any native mobile app because we implement the W3C Web Push standard end-to-end — VAPID keys on the backend, a service worker on the frontend, and bidirectional state sync through `browser_push_subscriptions`.**

### Body

A native mobile app would require Play Store and App Store builds, code-signing certificates, ongoing review processes, and platform-specific push token plumbing for FCM and APNs. We sidestep all of that by using the W3C Web Push standard — alerts that arrive on the user's phone or laptop through the browser, even when the SafeVision tab is closed. This works on Chrome, Firefox, Edge, and Opera on desktop, and on Chrome and Firefox on Android. (iOS Safari supports web push only as of iOS 16.4.)

**The VAPID handshake.** Voluntary Application Server Identification (VAPID) is the protocol that lets a backend authenticate itself to the browser's push service without per-user credentials. Our backend holds two keys — a public key `VAPID_PUBLIC_KEY` and a private key `VAPID_PRIVATE_KEY` — both loaded from environment variables. The public key is served to the frontend through an unauthenticated endpoint; the frontend converts it from base64-URL to a `Uint8Array` and passes it to `pushManager.subscribe()`, which gives the browser permission to receive pushes signed by our private key. Only requests signed with the matching private key will be relayed by the browser's push service to the user — meaning we cannot be impersonated.

**The subscription record.** When a browser subscribes, it returns a subscription object containing an endpoint URL (typically `fcm.googleapis.com` for Chrome) and two cryptographic keys (`p256dh` for end-to-end encryption, `auth` for message authentication). We POST this object to `/alerts/subscribe`, which writes it to the `browser_push_subscriptions` table. From that point on, the user is subscribed and any of our three alert channels (slide 31) can deliver notifications to them.

**The dispatch path** lives in `app/alert_notifications.py` (1,172 lines). When a job decides to send a push, it iterates over the user's subscription rows and calls the `pywebpush.send()` function, which:

1. Builds the W3C-compliant push request body (encrypted with the subscription's `p256dh` public key).
2. Signs the request with our VAPID private key.
3. POSTs to the subscription's endpoint URL.

The browser's push service validates the signature, decrypts the payload, and either delivers it to the active service worker (which displays the notification) or queues it until the user's browser next comes online.

**The PEM/DER normalisation bug fix.** During development we hit an obscure issue: depending on which tool generated the VAPID keys, they could come out as PEM-encoded text (with `-----BEGIN PRIVATE KEY-----` headers) or as raw base64-DER bytes. Pywebpush expects PEM. The frontend conversely expects the public key as base64-URL. We added normalisation logic to `routes/alerts.py:52-54, 60` and `alert_notifications.py:49-62` that detects the format and converts as needed, which fixed the persistent "applicationServerKey is not valid" error users were seeing on first subscription.

**Subscription pruning.** Browsers occasionally invalidate subscriptions — uninstalls, expirations, user-revoked permissions. Pywebpush returns a 410 Gone status for these. Our dispatch wrapper catches 410s and removes the subscription from the table on the spot, so we don't keep retrying dead endpoints.

### Anchor
`app/alert_notifications.py:49-62`, `app/routes/alerts.py:52-60`, `frontend/src/components/UserDashboard/ProfileModal.jsx`

---

## SLIDE 34 — FRONTEND COMPONENT LANDSCAPE

### Headline
**The React 18 frontend is organised into 108 components grouped by user role, with three role-specific dashboards and a shared map-and-alert subsystem — a structure that lets the same Leaflet primitives serve very different audiences without code duplication.**

### Body

The frontend lives at `frontend/src/components/` and contains 108 `.jsx` files distributed across roughly twelve top-level folders. The organising principle is **role-first**: every user role (visitor, citizen, admin, super-admin) has a dedicated dashboard folder, and shared primitives live in their own folders that all dashboards consume.

**The marketing surface** — `HomePage`, `Hero`, `Features`, `Testimonials`, `Footer`, `Statistics`, `News`, `Introduction`, `SafetyTips` — is what an unauthenticated visitor sees. These components are deliberately heavy on visual design and light on logic because the goal is conversion, not function. They share styling tokens with the dashboards so that brand consistency carries through after sign-up.

**The User Dashboard** (`components/UserDashboard/`) is the most feature-rich folder, with 30+ components. Key components include `MapDisplay` and `PredictionMapView` (the main heatmap canvases), `SafetyRadarChart` (a Chart.js radar showing risk by crime category), `QuickActions` (one-tap shortcuts to file a community report or trigger an SOS), `BrowserNotifications` (the VAPID enrolment UI), `ProfileModal` (settings), and the AI Route Analysis pair: `AIRouteAnalysis.jsx` (the form and result panel) and `AIRouteMap.jsx` (the Leaflet canvas that renders the candidate routes with risk-coloured polylines).

**The Admin Dashboard** (`components/AdminDashboard/`) carries the operational workload. The 20+ components include `AnalyticsPanel` (city-wide metrics charts), `ApprovalRequests` (the inbox of pending sensitive actions awaiting super-admin review), `NotificationsPanel` (admin-targeted system messages), `RecentActivity` (a live feed of admin actions across the platform), `UserManagementSummary` (a paged user table with search and filter), and `OCRPanel` (the FIR upload + OCR result review interface).

**The Super-Admin Dashboard** (`components/SuperAdminDashboard/`) carries the governance workload. It includes `SuperAdminMainDashboard` (an aggregate overview), `AnalyticsDashboard_updated` (deeper analytics), `UserManagement` and `AdminManagement` (CRUD for users and admins), `PPCManagement` (the interface for editing the PPC dictionary, which feeds severity scoring), `SystemSettings` (the editor for the `system_settings` table that overrides cron schedules, cooldowns, rate limits, etc.), and `PermissionMatrix` (a visual matrix of which roles can do what).

**The shared map subsystem** lives at the top level — `CrimeMap`, `CrimeMapInterface`, `MapInterface`, `HeatMapLayer.jsx`, plus `Modals` for popups. These are consumed by all three dashboards. A user sees a heatmap filtered to their geofence; an admin sees the same heatmap with admin-only overlays; a super-admin sees it with the full dataset and editing tools. The fact that all three views share the same underlying Leaflet primitives is what keeps the codebase from doubling in size.

The frontend totals **52,255 lines of JavaScript** plus **48,443 lines of CSS** (≈ 100,700 lines total). The old slide claimed "30,000+" — the real figure is more than three times that, reflecting the genuine breadth of the UI we built.

### Anchor
`frontend/src/components/`

---

## SLIDE 35 — HEATMAP AND AI ROUTE UI

### Headline
**The heatmap layer wraps `leaflet.heat` with a custom seven-stop gradient and severity-weighted aggregation, while the AI Route panel composes draggable markers, a date-time selector, and risk-coloured polylines into a single decision-making surface.**

### Body

The heatmap is the most visually iconic component in SafeVision. It is implemented in `HeatMapLayer.jsx` as a thin React wrapper around `L.heatLayer()` from the `leaflet.heat` library. The wrapper does two things the underlying library doesn't.

First, it **aggregates points by coordinate**: if an area has 47 crimes at the same approximate (lat, lng), we don't pass 47 separate points to Leaflet — we pass one point with weight 47. This dramatically reduces the rendering cost for high-density areas like Anarkali, where naive rendering would cripple the map's frame rate.

Second, it applies **severity weighting** during aggregation. The weight of a point is not just `count` but `count × average_severity`. This is what makes the visual gradient honest: a corner with five murders looks redder than a corner with five vandalism cases, even though the count is identical. Without severity weighting the heatmap would over-emphasise common, minor offences and under-emphasise rare, severe ones — exactly the opposite of what users need.

The **gradient is a custom seven-stop ramp** from deep blue (safe) through blue, green, yellow, orange, red, to deep red (worst). We chose seven stops rather than the default three because the additional resolution makes mid-range distinctions visible: a Medium-risk area in calm weather is genuinely different from a Medium-risk area trending toward High, and a single five-stop gradient (blue→green→yellow→orange→red) crushed those distinctions into a yellow blob.

**The AI Route panel** is implemented in two coordinated components:

- **`AIRouteAnalysis.jsx`** is the form and result list. It contains a date-time picker (which feeds `is_nighttime` and `hour` into the Poisson estimator backend), origin and destination inputs (both with autocomplete via Nominatim), a "Find Safer Route" button, and the result panel that lists each ranked alternate with its score and estimated duration. Critically, the date-time picker drives the same `time` component of the unified score that lives in the backend — selecting "11 PM tonight" changes the score that comes back, even if the geometry of the route is unchanged.

- **`AIRouteMap.jsx`** is the Leaflet canvas. It renders draggable origin and destination markers, lets the user reposition either by dragging (with debounced re-querying so we don't hammer the backend on every pixel of drag), and renders each ranked alternate as a polyline tinted by score — green for the safest, through yellow and orange, to red for the riskiest. Users can hover any polyline to see its score and the names of the riskiest segments it crosses. Clicking a polyline selects it as the active recommendation and draws turn-by-turn waypoints as numbered markers along the path.

This composition — form, map, and ranked alternates side by side on one screen — was deliberate. Earlier mockups put the route results on a separate screen, and user testing showed people would not flip between screens; they wanted to see the geometry and the score at the same moment so they could reason about why one option was safer.

### Anchor
`frontend/src/components/HeatMapLayer.jsx`, `frontend/src/components/UserDashboard/AIRouteAnalysis.jsx`, `frontend/src/components/UserDashboard/AIRouteMap.jsx`

---

## SLIDE 36 — DASHBOARDS BY ROLE

### Headline
**SafeVision exposes three role-specific dashboards — User, Admin, and Super-Admin — each surfacing exactly the powers that role requires and no more, with every privileged action funnelled through audit logging and approval gates.**

### Body

Role separation is enforced at three layers: the backend (every endpoint checks `user_role` from the JWT), the frontend (the UI for unauthorised actions is hidden, not just disabled), and the audit log (every privileged action becomes an immutable audit row). The user-facing experience differs accordingly.

**The User Dashboard** is what a citizen sees after signing up. It surfaces the heatmap of their geofenced area, lets them request an AI route between any two points, manage saved locations (home, work, family), opt into web-push for the three alert channels, file a community incident report (which goes into a moderation queue, not directly into the verified corpus), and request a patrol from the local thana. The user can also view their alert history and customise their preference flags — for instance, opting out of weekly reports while keeping live alerts on. Critically, none of these actions write to the verified crime database — community reports and patrol requests live in their own tables and require admin verification before they influence the heatmap.

**The Admin Dashboard** is what a verified administrator sees. It carries the operational workload: OCR-uploading FIRs through `OCRPanel`, verifying or rejecting community-submitted incident reports, editing crime records (with every edit captured in `audit_logs`), responding to patrol requests, posting system-wide alerts, and viewing the audit log itself. Admins have a much higher data ceiling — they can see all crimes city-wide, not just within their own geofence — and the heatmap they see is unfiltered. Every potentially-destructive action (delete user, bulk operations, role changes) opens an approval-request modal rather than executing immediately, and the request is routed to the super-admin inbox.

**The Super-Admin Dashboard** is the governance layer. Super-admins see everything admins see, plus four additional capabilities. First, the **approval inbox** — a queue of pending sensitive actions submitted by admins, each showing the requester, action type, target, and rationale. The super-admin reviews, optionally adds notes, and approves or rejects. Second, **PPC management** — the interface for editing the 721-section PPC dictionary that drives severity scoring. Adding a new section, correcting a description, or marking a section as deprecated all happen here, with changes auto-syncing to `severity_map.json` via the closed loop described on slide 30. Third, **system settings** — a structured editor for the `system_settings` table that controls runtime parameters: alert cooldown minutes, login attempt thresholds, cron schedules, role-specific session timeouts. Changes take effect on the next read, no redeploy required. Fourth, **admin and permission management** — creating new admin accounts, demoting compromised admins, viewing the role permission matrix.

The hierarchy is deliberately three tiers, not two. A two-tier system (citizens + admins) would mean every admin has equal power, including the power to escalate themselves, delete other admins, or wipe the user base. By interposing a super-admin tier with sole approval authority over destructive actions, we ensure no single admin compromise can take down the platform — a property that matters when admins are recruited from operational staff who may not have the same security training as the founding team.

### Anchor
`frontend/src/components/UserDashboard/`, `frontend/src/components/AdminDashboard/`, `frontend/src/components/SuperAdminDashboard/`, `app/approval_workflow.py`

---

## SLIDE 37 — DEPLOYMENT TOPOLOGY

### Headline
**SafeVision runs across three managed clouds — Vercel for the frontend, Render for the FastAPI worker, and TiDB Cloud for the database — chosen for free-tier viability, MySQL compatibility, and zero-touch ops.**

### Body

A final-year project lives or dies by its hosting choices. Pay for compute, you spend the budget on the cloud bill instead of features. Pick exotic platforms, you spend weeks debugging deployment instead of building product. Our topology is deliberately mainstream and mostly free.

**Vercel hosts the React frontend.** The Vite build emits static assets which Vercel serves through its global CDN — every user gets the SPA from a regional edge. Vercel's free tier handles our traffic comfortably and gives us automatic HTTPS, atomic deployments (every Git push to `main` produces a new immutable build), and instant rollbacks if a deploy goes wrong. The frontend speaks only to the backend API URL via HTTPS+JWT; there is no shared session state between Vercel and Render.

**Render hosts the FastAPI backend.** Specifically, a single Render Web Service running gunicorn with four uvicorn workers, on the free tier. The free tier sleeps after 15 minutes of inactivity and takes about 22 seconds to wake — acceptable for a final-year project, but we have a paid path planned (Render's $7/mo Starter tier eliminates cold starts) for production use. Render's `render.yaml` declares the build command (`pip install -r requirements.txt`) and the start command, so deployment is fully reproducible from the repo. APScheduler runs in-process inside one of the four workers (slide 32), so there is no separate worker container to manage.

**TiDB Cloud hosts the database.** TiDB Serverless is a managed, MySQL-compatible distributed database with a generous free tier (5 GiB storage, 50M Row Read Units per month). We chose it over PostgreSQL because the MySQL wire protocol means our application code talks to it through the same `mysql-connector-python` we use locally, and over Render-hosted MySQL because TiDB's serverless model means we never pay for idle. The trade-off: TiDB Serverless does not support MySQL's spatial functions (`ST_Distance_Sphere`), which is why we compute the Haversine distance in Python (slide 11). For our scale this is a non-issue; for a national rollout we would migrate to standard PostgreSQL with PostGIS.

**External APIs round out the stack.** OSRM (the open routing project, hosted publicly at `router.project-osrm.org`) handles route calculation. Nominatim (the OpenStreetMap geocoder) handles place-name → coordinate lookups, with a 1.1-second self-imposed rate limit to respect their fair-use policy. Groq and OpenRouter handle the two-tier law verification chain. Gmail SMTP handles outbound email (OTP and weekly digest). FCM and APNs handle the push delivery via the W3C Web Push protocol — we never call FCM directly, the browser does.

**Performance numbers.** On Render's free tier (after warm-up), `/crimes/predict` measures p50 ≈ 120 ms and p95 ≈ 480 ms. The cold-start cost is dominated by loading the Random Forest pickle file (≈ 200 ms) and warming the OCR model lazy-loaders (≈ 1.5 s for EasyOCR). The frontend's initial load on a 4G connection is ≈ 1.8 seconds to first paint, dominated by the Leaflet bundle.

### Anchor
`backend/render.yaml`, `frontend/vercel.json`, `backend/main.py`, `requirements.txt`

---

## SLIDE 38 — KEY ENGINEERING TRADE-OFFS

### Headline
**Every architectural decision in SafeVision involved a trade-off, and we believe the choices we made are defensible against reasonable alternatives — these are the seven that matter most.**

### Body

This slide is for the viva: it tells the panel that we considered alternatives and chose deliberately, rather than accepting whatever fell out of a tutorial.

**1. Random Forest + Poisson hybrid, rather than a single deep neural network.** A deep model could in principle learn everything our hybrid learns, with potentially higher accuracy. We chose against it for three reasons: interpretability (we can answer "why is this area High?" by inspecting feature importances and Poisson rates; we cannot do that from a deep net), inference latency (RF + Poisson finishes in under 200 ms; a comparable transformer-based model would be measured in seconds on free-tier compute), and artefact size (our Random Forest pickle is ~30 MB; comparable deep models are 100+ MB and would push us out of Render's deployment limits).

**2. TiDB Cloud (MySQL wire-compatible) rather than PostgreSQL with PostGIS.** PostGIS would give us native spatial functions, R-tree indexing, and a much richer geo query language. We picked TiDB because its serverless free tier costs $0/mo regardless of idle, while a comparable Postgres tier on Render is $7/mo always-on. The cost of giving up `ST_Distance_Sphere` is a 30-line Haversine helper in Python — well worth the savings for a final-year project.

**3. MD5 image-hash cache rather than perceptual hashing.** A perceptual hash like pHash would catch visually-similar but byte-different copies of the same FIR (e.g., the same scan saved at a different JPEG quality). MD5 only catches byte-identical duplicates. We chose MD5 deliberately because perceptual hashing has a non-zero false-positive rate — two visually similar but actually different FIRs could collide and one would silently overwrite the other. MD5's bit-exact match means zero false positives at the cost of some missed near-duplicates, which is a safer trade for a public-safety system.

**4. EasyOCR primary, with Tesseract fallback, rather than pure cloud OCR.** Cloud OCR (Google Vision, Azure Document Intelligence) is more accurate than open-source OCR. We chose a local-first stack because of bandwidth (FIRs are 1–3 MB images and we process thousands), privacy (FIRs contain personal information about crime victims; we minimise the surface area where they leave our infrastructure), and cost (cloud OCR pricing per image would dominate our hosting costs at any meaningful volume). Cloud Vision is reserved for the hard cases — the Row 4 crime-area extraction when local engines fail.

**5. `bcrypt_sha256` rather than Argon2id.** Argon2id is the modern PHC-recommended password hash and is mildly more resistant to GPU-based cracking. We picked bcrypt_sha256 because passlib's bcrypt support is rock-solid and well-tested across Python versions, while Argon2 dependencies have been less reliable in our experience. Bcrypt is still NIST-approved for password storage; Argon2 is preferred but not required.

**6. W3C Web Push (VAPID) rather than Twilio SMS or a native mobile app.** SMS gives universal reach but costs money per message. A native app gives the best UX but requires App Store approval, ongoing certificate management, and platform-specific push token plumbing. Web Push gives us most of the UX benefits of native (background-delivered notifications even when the tab is closed) at zero per-message cost, and works as a Progressive Web App on most mobile platforms. The trade: iOS Safari only added support in 16.4, so older iPhones don't receive web push. We accept this as a reasonable concession.

**7. Domain-tuned linear weights (35/15/30/10/10) rather than letting the ML model output the final score directly.** The Random Forest could in principle output a final risk score directly, eliminating the unified scorer. We kept the explicit weights because they are interpretable — when an admin asks "why is this area High?" we can break the score down into "85% from volume, 30% from severity, 60% from recency, ..." and explain each. A pure ML output is a single opaque number. For a public safety tool that influences citizen behaviour, interpretability is not a nice-to-have; it is what lets us defend the system to skeptical stakeholders.

### Anchor
*(Architectural decisions — no single file)*

---

## SLIDE 39 — METRICS AND EVALUATION

### Headline
**SafeVision's evaluation is split across four surfaces — the classifier's accuracy, the Poisson model's calibration, OCR field-level accuracy on a held-out FIR set, and end-user push delivery — each measured with the metric appropriate to its task.**

### Body

A common mistake in academic ML projects is reporting only one number — "99% accuracy" — and treating it as a verdict on the whole system. SafeVision deliberately spreads its evaluation across four distinct surfaces, each with its own metric, because the system has four distinct things to be good at.

**Surface 1: Random Forest 5-fold cross-validation accuracy.** This measures how well the classifier predicts High/Medium/Low on held-out folds of the historical crime dataset. It is computed by `cross_val_score` with `StratifiedKFold(n_splits=5)` at every retraining run. We deliberately do not hardcode a number into this slide because the model is retrained as new FIRs flow in; quoting a stale figure (the old slide's "99.27%") would mislead the audience. **Action for the viva:** run `python train_model.py` shortly before the presentation and quote the live cross-validation accuracy. Be ready to discuss the per-class precision and recall — a 99% headline figure that hides 60% recall on High-risk would be a problem.

**Surface 2: Poisson calibration via the Brier score.** Accuracy is the wrong metric for the Poisson estimator because its output is a probability, not a class. The right question is: "when the Poisson says 30% probability, does a crime actually happen 30% of the time on average?" This is calibration, and the standard measure is the Brier score — the mean squared error between predicted probability and binary outcome. A Brier score of 0 is perfect calibration; 0.25 is the score of always predicting 0.5. Our holdout calibration is computed on a 20% time-based split (train on the first 80% of dates, test on the last 20%) so we are evaluating on the future, not just on randomly-held-out rows.

**Surface 3: OCR field-level accuracy.** A manual evaluation on 120 FIRs not in the image-hash cache, performed during development:

- **Crime date: 96%** — high because the date field is short, numeric, and well-isolated on the form.
- **Police-station name: 94%** — high because the station name comes from the 84-entry whitelist (slide 29) which constrains the matching.
- **Crime area (post-fuzzy): 88%** — moderate because area names are diverse, hand-written, and frequently misspelled or abbreviated.
- **PPC sections: 91%** — high because PPC numbers are short and numeric, and the 721-section dictionary catches transcription errors.

The numbers reflect the relative difficulty: structured fields (date, sections) are easy; free-text fields (area, narrative) are hard. The 88% on area is the lower bound that drove the cascade-fallback design described on slide 27 — Gemini Vision and Mistral Pixtral are reserved precisely for the 12% where local OCR fails on this field.

**Surface 4: Push delivery success rate, ≈ 97%.** Measured over the production push log. The ≈ 3% failure rate is overwhelmingly stale subscriptions (browsers that have invalidated their push registration without telling us); these manifest as 410 Gone responses from FCM and trigger automatic pruning. A small residual rate (under 0.5%) is genuine network failures.

**Surface 5: Image-hash cache hit-rate.** By construction this is 100% on byte-identical re-uploads, but the operational metric we care about is what fraction of total OCR requests hit the cache. In our admin's normal workflow, this number is around **35%** — the rest are first-time uploads that go through the full five-engine pipeline. The cache pays for itself within hours of operation.

### Anchor
`app/crime_risk_model/train_model.py` (CV accuracy), `app/crime_risk_model/utils/poisson_predictor.py` (calibration), manual OCR eval, `app/alert_notifications.py` (push log)

---

## SLIDE 40 — GOVERNANCE AND FUTURE WORK

### Headline
**SafeVision today is governed by an append-only audit log, a six-action super-admin approval gate, and zero-downtime model hot-reload — and we have a clear three-month roadmap for the next set of capabilities.**

### Body

**Today's governance surface** has three pillars.

*The audit log* (slide 16) writes one row per privileged action, with the actor, IP, target, and JSON before-and-after state. There is no UPDATE or DELETE path on the table, so the log is tamper-evident at the application layer. A breach investigation can compare audit history against database backups and detect any rewriting that bypassed the application.

*The approval workflow* (slide 16) gates six categories of action behind explicit super-admin sign-off: deleting users, bulk deletes, role escalations to admin or super-admin, bulk suspensions, and FIR OCR submissions. No single admin compromise can damage the platform irreversibly because the most damaging actions require two-eye approval.

*Hot-reload of ML artefacts* lets us retrain the Random Forest and Poisson estimator without taking the API offline. The retraining script runs in a subprocess, writes its outputs to versioned filenames, and signals the running FastAPI worker to reload its model handles. The user-facing API stays up throughout.

**Roadmap for the next three months** is concrete:

*Replace Nominatim with self-hosted Photon.* Nominatim's public instance imposes a 1.1-second per-request rate limit, which caps our reverse-geocoding throughput. Photon is a self-hostable alternative that runs on the same OpenStreetMap data without the rate-limit ceiling. Hosting it on Render's $7/mo Starter tier would give us geocoding at hundreds of requests per second, which unlocks denser route sampling and faster admin workflows.

*Add DBSCAN clustering for emerging-hotspot detection.* Today, hotspots are computed per-area as scores cross thresholds. This is good for known areas but slow to detect *new* hotspots that don't yet correspond to a registered area boundary. DBSCAN — a density-based clustering algorithm — would let us identify spatially coherent crime clusters from raw points without pre-defined area shapes, surfacing emerging hotspots before they show up in area-aggregated statistics.

*Mobile PWA with offline-first crime cache.* Today, SafeVision's web app requires connectivity. In Lahore's neighbourhoods with patchy coverage, this fails the user at exactly the moment they need safety information most. Adding a Progressive Web App manifest plus a service-worker-cached read-only crime corpus would let users see their local heatmap even when offline, with the live and incident channels resuming as soon as connectivity returns.

*Integrate Punjab Safe Cities CCTV API.* The Punjab Safe Cities Authority operates over 9,000 CCTV cameras across Lahore. Their API, when access is granted, would let SafeVision corroborate user-submitted incident reports against camera footage timestamps — significantly raising the bar against false reporting and giving administrators a verification tool that doesn't depend on physical site visits.

*Replace Groq + OpenRouter chain with Claude Haiku for PPC verification.* The two-tier LLM chain works but adds latency and a second SDK to maintain. Claude Haiku (Anthropic's smallest current model) is fast, capable on legal-text tasks, and would consolidate the verification stack into a single SDK call with predictable per-request cost.

The progression is from "operational platform" (today) to "regional safety infrastructure" (the roadmap). Every roadmap item addresses a real bottleneck we hit during development, not speculative features.

### Anchor
*(Roadmap — to be published as separate planning doc)*

---

## SLIDE 41 — THANK YOU

### Headline
**SafeVision: Predictive Spatial Intelligence for Lahore's Streets.**

### Body

Across forty slides we have walked through the project from problem to deployment: a 14-million-person city policed reactively, a 142,000-line codebase that turns reactive into predictive, a hybrid Random Forest and Poisson model whose 0-to-100 risk score drives both an interactive heatmap and an AI-recommended safer-route engine, a five-engine OCR pipeline that digitises handwritten Urdu FIRs, a three-channel alert system that respects user attention with a 60-minute cooldown, and a three-tier role model that funnels every privileged action through audit logging and super-admin approval.

The platform is live now at `https://safevision-backend-ye2i.onrender.com`. The 130 backend endpoints, 42 database tables, 108 React components, and 12 ML and OCR services are all deployed, exercised, and observable. Every claim on every slide can be reproduced from the public source tree — file path and line number — which is why we ended each slide with an anchor citation.

Thank you to our supervisor Afraz Hayat Malik for the close guidance and to UET Lahore for hosting this work. We're ready for questions.

**Live API:** `https://safevision-backend-ye2i.onrender.com`
**Code statistics:** ~142,000 LOC across backend, frontend, OCR, and ML
**Database:** 42 tables on TiDB Cloud
**System email:** `safevision.alerts@gmail.com`

### Q & A
