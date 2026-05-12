# Model Fallback Chain & Testing Guide

## Current Implementation

Your risk prediction system now has a **fallback chain** in place:

```
PRIMARY:   Poisson Model
    ↓ (if fails)
FALLBACK 1: Random Forest Model  
    ↓ (if fails)
FALLBACK 2: Legacy Random Forest Model
    ↓ (if fails)
ULTIMATE:   Log-Scale Volume (pure mathematical fallback)
```

### Location
File: `app/utils/risk.py` → Function: `_volume_score()` (line ~355)

---

## How to Test Each Model

### ✅ Test 1: Poisson Model (Currently Active - DEFAULT)
1. **No changes needed** — just run your app normally
2. Check the logs for: `[POISSON-PRIMARY] Volume score: XX.X`
3. View results at: `/api/crime/predict` endpoint

**What you're seeing:**
- Risk score = 60% Poisson probability + 40% log-scaled volume
- Shows probability of at least one crime happening
- Example result: `10.53% EST. RISK`

---

### ✅ Test 2: Random Forest Model (FALLBACK 1)

To force the Random Forest model to be used:

**Option A: Comment out Poisson (forces fallback)**
In `app/utils/risk.py`, line 361-370:

```python
# COMMENT OUT THESE LINES:
# lam = tc / float(days)
# poisson_score = 100.0 * (1.0 - math.exp(-max(lam, 1e-9)))

# This forces the code to skip Poisson and jump to Random Forest
raise Exception("Testing Random Forest fallback")
```

**Option B: Enable the full Random Forest prediction (requires area/crime data)**
Modify `_predict_risk_random_forest()` function to integrate with your data flow.

**What to expect:**
- Logs will show: `[POISSON-PRIMARY] Failed: ..., trying RANDOM FOREST fallback...`
- Risk score based on crime volume thresholds:
  - >500 crimes = 75% (High)
  - 100-500 crimes = 50% (Medium)
  - <100 crimes = 25% (Low)

---

### ✅ Test 3: Legacy Random Forest Model (FALLBACK 2)

To force the Legacy model to be used:

**In `app/utils/risk.py`, line ~373:**

```python
# COMMENT OUT THE TRY BLOCK THAT HANDLES RANDOM FOREST:
# try:
#     if tc > 500:
#         rf_score = 75.0
#     ...

# ADD THIS INSTEAD:
raise Exception("Testing Legacy fallback")
```

**What to expect:**
- Logs will show: `[RANDOM-FOREST-FALLBACK1] Failed: ..., trying LEGACY fallback...`
- Risk score follows same thresholds as Random Forest:
  - >500 crimes = 75% (High)
  - 100-500 crimes = 50% (Medium)
  - <100 crimes = 25% (Low)

---

## Viewing Logs

To see which model is being used, check your application logs:

```bash
# Look for these log messages:
[POISSON-PRIMARY] Volume score: ...      # Poisson is working
[RANDOM-FOREST-FALLBACK1] Volume score: ... # Poisson failed, RF active
[LEGACY-FALLBACK2] Volume score: ...     # Both failed, Legacy active
[LOG-SCALE-FALLBACK] Volume score: ...   # All failed, using math-only
```

---

## Testing Strategy

### Test the Fallback Chain:
1. **Run normally** → See Poisson results
2. **Comment Poisson** → See Random Forest results
3. **Comment Random Forest** → See Legacy results
4. **Compare the three outputs** for the same area/crime

### Command to Check Logs:
```bash
# In your backend terminal where uvicorn is running
# Watch for the [MODEL-NAME] prefix in logs
```

---

## Restore to Original

To go back to pure Poisson (undo all changes):
1. Delete any comment markers you added
2. Ensure lines 361-370 are uncommented
3. Restart uvicorn: `uvicorn main:app --reload`

---

## Code Structure

```python
# In app/utils/risk.py:

def _volume_score(total_crimes, observation_days=365):
    """
    FALLBACK CHAIN:
    1. Try Poisson calculation
    2. If fails → try Random Forest
    3. If fails → try Legacy
    4. If all fail → use pure log-scale math
    """
```

Each fallback logs which model was used, so you can track in real-time which one is active.
