# SafeVision: ML Models & OCR Deep Technical Explanation
*For Defense Script & Presentation - Child-Friendly Language*

---

## PART 1: THE 3 MACHINE LEARNING MODELS

### Model 1: Crime Risk Model - Random Forest (PRIMARY)
**File Location:** `CrimeVision/backend/app/crime_risk_model/models/rf_model.pkl`

**What It Does (Simple):**
Think of it like a **magic decision-maker**. You show it a crime case from history:
- Area: Anarkali
- Crime Type: Theft
- Severity: Medium
- How recent: Last month

It says: "Based on 1,000+ cases I've learned from, crimes like this in Anarkali are usually **HIGH DANGER**."

**Technical Details (For evaluators):**
- Uses numeric engineered features: severity score, temporal trends, spatial density
- Handles unseen areas: if an area wasn't in training data, uses median fallback (no hardcoded default)
- Output: **Categorical** — High / Medium / Low risk label
- Where it's used: `app/routes/crimes.py` lines 80-96 (loaded as `_crm_model`)
- Also used in: `app/approval_workflow.py` for sensitive action risk assessment

**Loading Mechanism:**
```python
from app.crime_risk_model.utils.helpers import load_model
_crm_model, _crm_scaler, _crm_artifacts = load_model(
    os.path.join(_CRM_DIR, 'models')
)
```

**Why It's Good:**
- Learns from actual case patterns, not hardcoded rules
- Fast decision (milliseconds)
- Explains *categories* clearly: "This is a HIGH-risk situation"

---

### Model 2: Poisson Probability Model (SECONDARY)
**File Location:** `CrimeVision/backend/app/crime_risk_model/models/poisson_artifacts.json`

**What It Does (Simple):**
Think of it like **predicting the weather**. 
- Past data shows: In Gulberg, theft happens on average 0.5 times per day
- But Mondays are 2× worse (happens 1.0 times per day on Mondays)
- And nighttime (10 PM) is 1.5× worse again

So we calculate: **P(theft in Gulberg on Monday night) = 55%**

This is NOT a guess — it's pure statistics from crime *history*.

**Technical Details (For evaluators):**
- Mathematical Foundation: Poisson process model
- Formula: P(≥1 crime) = 1 - e^(-λ)
  - λ (lambda) = expected crimes per day for that (area, crime_type, day_of_week, hour_of_day) combination
  - Laplace-smoothed to avoid zero-probability artifacts for rare combinations
- Artifacts stored: 
  - `pair_lambdas`: (area, crime_type) → avg crimes/day
  - `dow_multipliers`: day-of-week adjustment
  - `month_multipliers`: seasonal adjustment
  - `hour_multipliers`: time-of-day adjustment (amplified by 2.2 exponent for visibility)
- Where it's used: `app/routes/crimes.py` lines 80-96 (loaded as `_poisson_artifacts`)

**Loading Mechanism:**
```python
from app.crime_risk_model.utils.poisson_predictor import load_artifacts
_poisson_artifacts = load_artifacts(
    os.path.join(_CRM_DIR, 'models', 'poisson_artifacts.json')
)
# Returns dict with pair_lambdas, dow_multipliers, month_multipliers, etc.
```

**Why It's Good:**
- Statistically grounded (not machine learning, but rigorous math)
- Handles temporal patterns: crime is different on Monday vs Sunday, 10 PM vs 10 AM
- Gives *percentages* (0-100%), making it easy to understand: "60% chance"
- Sparse data safe: Laplace smoothing means even rare area×crime pairs get reasonable estimates

---

### Model 3: Legacy Random Forest (FALLBACK)
**File Location:** `CrimeVision/backend/app/predict_risk_level/model/random_forest_model.joblib`

**Plus 3 Label Encoders:**
- `label_encoder_area.joblib` — converts area names to numbers for the model
- `label_encoder_crime.joblib` — converts crime types to numbers
- `label_encoder_risk.joblib` — converts High/Medium/Low back to text

**What It Does (Simple):**
This is an **older version** of the Random Forest model. It works exactly like Model 1, but uses label encoders to convert text to numbers.

**Technical Details:**
- Where it's loaded: `app/routes/crimes.py` lines 138-142 (as fallback if CRM model fails)
- Also loaded in: `app/approval_workflow.py` (for admin approval decisions)
- Status: **ACTIVE but LEGACY** — it works, but newer CRM model is preferred
- Why we keep it: Redundancy. If the newer model fails to load, the system still has a working model for risk prediction

**Why It's Good:**
- Simple, reliable, been tested in production
- Label encoders make it interpretable: you can see exactly which area was encoded as what number

---

## HOW THE 3 MODELS WORK TOGETHER

**Risk Scoring Pipeline:**

```
Input Crime Case
       ↓
   [Model 1: CRM Random Forest]
       ↓ outputs: High / Medium / Low label
       ↓
   [Model 2: Poisson Probability]
       ↓ outputs: percentage 0-100%
       ↓
   [5-Factor Unified Formula]
       ↓
       Combines:
       - Volume (35%): How many crimes
       - Recency (30%): How recent they are
       - Severity (15%): How serious they were
       - Trend (10%): Is crime getting worse
       - Time-of-Day (10%): Dangerous hour?
       ↓
   Final Risk Score: 0-100
```

**Model 3 (Legacy RF):**
- Used only if Models 1 & 2 fail
- Provides exact same risk label: High / Medium / Low
- Ensures system never crashes due to missing model

---

## PART 2: IMAGE PROCESSING FOR OCR (BEFORE READING TEXT)

### Why Images Need Cleaning

Imagine you're trying to read a **damaged, folded, and badly photographed handwritten letter**. That's what our system faces with FIR scans.

Problems:
- **Dust & creases** on the paper (visible as black spots)
- **Poor lighting** — some parts bright, some dark
- **Hand-written text** — irregular, varying sizes
- **Table lines** — interfere with digit reading
- **Low resolution** — old mobile camera quality

Before we try to read text, we **clean up** the image like a detective polishing a crime scene photo.

---

### Image Processing Pipeline (3 Approaches)

**APPROACH 1: PURE OCR (What We Use)**
```
Original FIR Image (JPG/PNG)
    ↓
[NO PREPROCESSING - Use directly]
    ↓
EasyOCR / Tesseract / Gemini
    ↓
Extracted Text
```

**Why?** Modern OCR engines (especially EasyOCR) are trained on natural, messy images. Aggressive preprocessing actually makes results *worse* by destroying subtle cues the neural network learned to recognize.

**Analogy:** If a detective team knows how to read bad handwriting, don't give them just outlines — give them the actual letter to study.

---

**APPROACH 2: GENTLE ENHANCEMENT (For Difficult Rows)**
*Used when pure OCR fails*

```
Original Image
    ↓
1. Convert to Grayscale (remove color noise)
    ↓
2. CLAHE Contrast Enhancement
   (makes dark parts darker, light parts lighter)
    ↓
3. Adaptive Threshold
   (turns gray image into pure black & white,
    adapts to local lighting conditions)
    ↓
4. Morphological Cleaning
   (removes small noise spots, keeps digits intact)
    ↓
Enhanced Black & White Image
    ↓
Tesseract (for digits/English)
    ↓
Extracted Numbers
```

**When Used:** If main OCR gets low confidence (<60%), we try this pipeline only on that specific region.

**Analogy:** Like enhancing the contrast on a security camera photo to spot a license plate — but we do it only when we really need to.

---

**APPROACH 3: AGGRESSIVE UPSCALING (For Tiny Text)**
*Used as last resort*

```
Original Image (maybe 100×50 pixels for date)
    ↓
Upscale 4× using cubic interpolation
    (from 100×50 → 400×200)
    ↓
CLAHE Enhancement
    ↓
English-only EasyOCR
    (Urdu model sometimes interferes with digits)
    ↓
Extracted Date Digits
```

**When Used:** Only when region is < 100 pixels wide.

**Analogy:** Like magnifying a tiny label with a magnifying glass to read the expiry date.

---

## PART 3: EXTRACTING THE 4 FIELDS FROM FIR

The system needs to extract exactly 4 pieces of information from each FIR:

### Field 1: DATE (When Did Crime Happen?)
**Location:** Top-left section of FIR table, around 10-15% down the page

**Extraction Logic:**
1. Extract region covering date cell: 10-15% vertical, 2-57% horizontal
2. Send to EasyOCR (trained on natural images, works on handwriting)
3. Look for date patterns: DD/MM/YYYY or DD-MM-YYYY or similar
4. Validate: Is it a real date? Not in the future? (sanity check)
5. Store as: `YYYY-MM-DD` format in database

**Code Location:** `app/ocr/fir_specialized_ocr.py`, class `FIRExtractor`, method `extract_date()`

**Example:**
```
Raw OCR Output: "23 / 10 2024"
Parsed Result: "2024-10-23"
```

---

### Field 2: TIME (What Time Did It Happen?)
**Location:** Same region as date, but further right; includes AM/PM indicator

**Extraction Logic:**
1. Same region as date (they sit in same table row)
2. OCR reads: "03:22 AM" or "15:45" (24-hour format)
3. Convert to 24-hour format internally: 3:22 AM → 3, 3:45 PM → 15, etc.
4. Extract hour (0-23) for Poisson model's time-of-day multiplier
5. Store as: `HH:MM AM/PM` in database

**Code Location:** `app/ocr/fir_specialized_ocr.py`, method `_parse_time_from_text()`

**Example:**
```
Raw OCR Output: "3:22 AM"
Parsed Hour: 3 (for Poisson multiplier lookup)
Stored as: "03:22 AM"
```

---

### Field 3: LAW SECTIONS (Which Law Was Broken?)
**Location:** Middle-right of FIR table, around 22-50% down the page

**Why Sections Matter:**
Each law section is a crime code. Examples:
- Section 302 (Murdar) = Murder
- Section 380 (Choori) = Theft  
- Section 376 = Rape
- ATA (Anti-Terrorism Act) = Terrorism charges

**Extraction Logic:**
1. Extract region: 22% down to 50% down, right half of table
2. OCR reads numbers/codes: "302", "379-B", "120-B", etc.
3. **Correction Rules** (because OCR makes mistakes):
   - "341" probably meant "134" (common digit swap)
   - "302 तब" meant "302" (Urdu symbol misread as number)
4. Validate: Is this a real PPC section? (1-500), ATA, or CNSA?
5. Store: List of law codes (["302", "379-B", "120-B"])
6. Map to crime names: 302 → Murder, 379 → Theft, etc.

**Code Location:** `app/ocr/fir_specialized_ocr.py`, methods:
- `extract_sections()` — main extraction
- `_extract_sections_from_region()` — region-specific OCR
- `_apply_ocr_corrections()` — fix common misreads

**Example:**
```
Raw OCR Output: "302 उर्दू-A"
After Correction: ["302"]
Mapped to Crime: "Murder"
```

**Fallback Strategy:**
- Primary region (right column): lines 22-50%, x: 40-76%
- If <3 sections found, try expanded region
- If still <2 sections, try left column (alternate FIR layout)

---

### Field 4: CRIME AREA (Where Did Crime Happen? Which Thana?)
**Location:** Lower section of FIR table, around 38-45% down the page

**Why Areas Matter:**
Each police station (thana) covers a specific neighborhood:
- Anarkali Thana → Old City
- Defence Thana → upscale residential
- Gulberg Thana → commercial area

Knowing the thana tells us:
1. Exact geographic region (via lat/long lookup)
2. Which police station to notify
3. Which risk zone for alerts

**Extraction Logic:**
1. Extract region: 38-45% down, x: 29-62% (middle section)
2. OCR reads Urdu/English thana name: "انارکلی" (Anarkali) or "ANARKALI"
3. **Urdu-to-English conversion table:**
   - انارکلی → Anarkali
   - ماڈل ٹاؤن → Model Town
   - شالیمار → Shalimar
   - (30+ mappings total)
4. **Geocoding via OpenStreetMap Nominatim API:**
   - Search: "Anarkali, Lahore, Pakistan"
   - Returns: Latitude & Longitude
   - Cached to avoid repeated API calls
5. Validate: 
   - Not empty?
   - Space ratio < 35% (reject garbled text)
   - Actually a real area in Lahore?
6. Store: Area name + lat/long coordinates

**Code Location:** `app/ocr/fir_specialized_ocr.py`, methods:
- `extract_crime_area()` — main extraction
- `_clean_crime_area_text()` — remove noise (dashes, extra spaces)
- `geocode_crime_area()` — convert name to lat/long via API

**Example:**
```
Raw OCR Output: "  انارکلی         ----"
After Cleaning: "Anarkali"
After Geocoding: {
  "area": "Anarkali",
  "latitude": 31.5590,
  "longitude": 74.3210,
  "source": "nominatim_api"
}
```

---

## PART 4: THE 3 OCR ENGINES (Which Ones Read What?)

### Active Engines:

**Engine 1: Tesseract (LOCAL, FAST)**
- **Speed:** Milliseconds (runs on server)
- **Best for:** Clear printed text, English digits
- **Language:** English, limited Urdu support
- **Where:** Used first for dates, times, sections
- **Advantage:** No network latency, no API costs

**Engine 2: Google Gemini Vision (API, POWERFUL)**
- **Speed:** 1-2 seconds (network call)
- **Best for:** Handwritten Urdu, blurry regions
- **Language:** Excellent Urdu, perfect English
- **Where:** Used when Tesseract gets <60% confidence
- **Advantage:** Understands Urdu script at human level

**Engine 3: OpenRouter / Mistral Vision (BACKUP API)**
- **Speed:** 1-2 seconds (network call)
- **Best for:** Fallback if Gemini times out
- **Language:** Multilingual including Urdu
- **Where:** Last resort if both Tesseract and Gemini fail
- **Advantage:** Redundancy, ensures we always get *something*

### Disabled Engines:

**PaddleOCR:** Tested but disabled (too slow on CPU, high memory)
**EasyOCR:** Tested but disabled (conflicted with date/time parsing in production)

---

## SUMMARY: 3 MODELS + 4 FIELDS + 3 ENGINES

```
When a FIR arrives:

1. IMAGE PROCESSING
   Raw Scan → Validate Resolution → Check Hash Cache

2. FIELD EXTRACTION
   ├─ DATE: Extract via Tesseract/Gemini → Validate Format → Store
   ├─ TIME: Extract from same region → Parse Hour → Store
   ├─ SECTIONS: Extract from middle region → Correct OCR Errors → Map to Crime → Store
   └─ AREA: Extract from lower region → Geocode via API → Store Coordinates

3. RISK CALCULATION
   ├─ Model 1 (RF): Predict High/Medium/Low
   ├─ Model 2 (Poisson): Predict Percentage (0-100%)
   ├─ Fallback (Legacy RF): If Models 1-2 fail
   └─ 5-Factor Blend: Final Risk Score (0-100)

4. ALERT DELIVERY
   Push to all users within 5 km radius
```

---

## KEY TAKEAWAY FOR DEFENSE

**When asked about "3 models":**
"We use 2 primary machine learning models — Random Forest and Poisson — plus a legacy Random Forest as fallback. The Random Forest categorizes risk (High/Medium/Low) based on crime history. The Poisson model calculates the statistical probability of crime happening right now, at this exact time of day, in this specific area. Together they feed into a 5-factor unified formula that produces the final 0-100 risk score."

**When asked about OCR:**
"We use three OCR engines in sequence: Tesseract (local, fast), Gemini Vision (AI, understands Urdu), and OpenRouter/Mistral (backup). We extract 4 fields from each FIR: date, time, law sections, and crime area. The date and time go into our time-of-day risk multiplier. The law sections tell us the crime type and severity. The area name gets geocoded to latitude/longitude, which powers alerts within 5 km."

**When asked about image processing:**
"Modern OCR is trained on natural, messy images, so we use the image as-is for best results. We only apply enhancement as a fallback — gentle contrast boost via CLAHE, adaptive thresholding, and morphological cleaning — when main OCR fails. This mirrors how a human would approach an old, damaged document: try to read it naturally first, only use magnifying glass if needed."
