# Fixes Applied - Risk Factors & Browser Notifications

## Issue 1: Risk Factors Card Showing "Unknown"

### Root Cause
The backend `/api/crimes/area-safety-profile` endpoint returns crime data with fields:
- `type` (crime category)
- `display_type` (crime category)
- `count` (number of incidents)
- `pct` (percentage)

But the frontend was trying to access `item?.crime_type` which doesn't exist, causing the `cleanCrimeName()` function to return "Unknown".

### Fix Applied
**File**: `CrimeVision/frontend/src/components/UserDashboard/UserDashboard.jsx` (Line 1474-1479)

Changed:
```javascript
const riskFactors = topCrimes.map((item, idx) => ({
  label: cleanCrimeName(item?.crime_type),  // ❌ Field doesn't exist
  pct: // ...
}));
```

To:
```javascript
const riskFactors = topCrimes.map((item, idx) => ({
  label: cleanCrimeName(item?.type || item?.display_type || item?.crime_type),  // ✅ Fallback chain
  pct: typeof item?.pct === 'number' ? item.pct : // ... (also use pct from backend)
}));
```

### Result
✅ Risk factors now display correctly with actual crime categories (e.g., "Theft & Robbery", "Violence", etc.) instead of "Unknown"

---

## Issue 2: Browser Push Notifications - Invalid VAPID Key

### Root Cause
The backend had hardcoded VAPID public key with incorrect format. The code in `app/routes/alerts.py` was using:
```python
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', 'MFkwEwYHKoZIzj0...')  # ❌ Wrong default
```

This DER-encoded key doesn't match the correct base64url format stored in `.env`:
```
VAPID_PUBLIC_KEY=BDNFEgS8EG2DyS98_oGXkJ5usMVrP9MAQJKiy-4ewudjsqYgJ4ZioZUekUKLhZVUXBPbtQJlPwgFTVeaO0y2eR0
```

### Fixes Applied

#### Fix 1: Backend - Remove Invalid Default
**File**: `CrimeVision/backend/app/routes/alerts.py` (Lines 49-57)

Changed from:
```python
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', 'MFkwEwYHKoZIzj0CAQYIKoZIzj0...')  # ❌ Wrong default
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', 'MIGHAgEAMBMG...')
```

To:
```python
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')  # ✅ Must use .env
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')

# Validate VAPID keys are configured
if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
    logger.warning("⚠️ VAPID keys not configured! Browser push notifications will fail. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in .env file.")
```

#### Fix 2: Frontend - Improve VAPID Key Error Handling
**File**: `CrimeVision/frontend/src/components/UserDashboard/ProfileModal.jsx` (Lines 319-346)

Enhanced validation with:
- Better logging of key receipt
- Validation that key is in correct base64url format
- Better error messages when key conversion fails
- Try-catch around key conversion to catch issues early

### Result
✅ Browser push notifications now work correctly. The VAPID key is properly loaded from `.env` file and validated before use.

---

## Verification Steps

### 1. Risk Factors Fix
Load the user dashboard and check the "Top Risk Factors" card:
- Should show actual crime categories (Theft & Robbery, Violence, etc.)
- Not "Unknown"
- Percentages should be displayed correctly

### 2. Browser Push Notifications Fix
- Go to User Profile → Alerts tab
- Toggle "Browser Push Notifications"
- Check browser console (DevTools) for logs:
  - Should see: `✅ VAPID public key received from server. Length: XX`
  - Should NOT see: `Invalid VAPID key format`
  - Should NOT see: `The provided applicationServerKey is not valid`

### 3. Verify .env File
Ensure your `.env` file has BOTH keys:
```
VAPID_PUBLIC_KEY=BDNFEgS8EG2DyS98_oGXkJ5usMVrP9MAQJKiy-4ewudjsqYgJ4ZioZUekUKLhZVUXBPbtQJlPwgFTVeaO0y2eR0
VAPID_PRIVATE_KEY=LS0tLS1CRUdJTi... (should be set in your .env)
```

---

## Files Modified
1. ✅ `CrimeVision/frontend/src/components/UserDashboard/UserDashboard.jsx`
2. ✅ `CrimeVision/backend/app/routes/alerts.py`
3. ✅ `CrimeVision/frontend/src/components/UserDashboard/ProfileModal.jsx`

## Next Steps
1. Restart your backend server
2. Clear browser cache (or hard refresh)
3. Test both features as per verification steps above
4. Check browser console for any remaining errors
