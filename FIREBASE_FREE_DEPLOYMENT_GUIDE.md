# Firebase Free Deployment Guide - CrimeVision Project

## Overview
This guide deploys your CrimeVision project to Firebase **completely free**. Your project has:
- **Frontend**: React + Vite (easy to deploy to Firebase Hosting)
- **Backend**: Python FastAPI (needs alternative as Firebase doesn't support Python on free tier)
- **Database**: MySQL (should migrate to Firestore or Realtime Database)

## Recommended Architecture for 100% Free Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│  Frontend                          Backend              Database  │
│  (React + Vite)                   (FastAPI)            (MySQL)   │
│        │                               │                  │      │
│        └──→ Firebase Hosting      Render.com          Firestore  │
│           (Free Tier)           (Free Tier)        or Realtime DB │
│           Custom Domain         PostgreSQL           (Free Tier)  │
│           SSL/TLS               Node.js Runtime                   │
│           CDN Included           Cron Jobs                        │
└─────────────────────────────────────────────────────────────────┘
```

## Three Deployment Options

### ✅ OPTION 1: RECOMMENDED - Mixed Stack (Best Balance)
**Firebase Hosting (Frontend) + Render.com (Backend) + Firestore (Database)**

**Pros:**
- 100% free (Render free tier, Firebase free tier, Firestore free tier)
- Minimal code changes
- Scalable as you grow
- Generous free quotas

**Cons:**
- Backend deployed separately from Firebase
- Requires database migration from MySQL to Firestore

**Cost Breakdown:**
- Firebase Hosting: FREE (10 GB/month storage, 360 MB/day bandwidth)
- Render.com: FREE (0.5 GB RAM, auto-pause after 15 min inactivity)
- Firestore: FREE (1 GB storage, 50K reads/day, 20K writes/day)

---

### ✅ OPTION 2: Firebase Native (More Integrated)
**Firebase Hosting (Frontend) + Cloud Functions (Backend) + Firestore (Database)**

**Pros:**
- All in Firebase ecosystem
- Better integration with Firebase services
- Automatic scaling

**Cons:**
- Limited Python support (need Node.js rewrite)
- Very restricted free tier for backend (125K invocations/month)
- Python functions have more limitations

**Cost Breakdown:**
- Firebase Hosting: FREE
- Cloud Functions: FREE (125K invocations/month, 40K GB-seconds/month)
- Firestore: FREE

---

### ❌ OPTION 3: NOT RECOMMENDED - Keep Everything Free
**Firebase Hosting (Frontend) + Firebase only (no separate backend)**

**Cons:**
- Requires complete backend rewrite to JavaScript/Node.js
- Loses Flask/FastAPI advantages
- Significant development effort
- Not suitable for your project complexity

---

## STEP-BY-STEP DEPLOYMENT (Option 1 - RECOMMENDED)

### Step 1: Prepare Frontend for Firebase Hosting

#### 1.1 Install Firebase CLI
```bash
npm install -g firebase-tools
```

#### 1.2 Build your frontend
```bash
cd CrimeVision/frontend
npm run build
```

This creates a `dist/` folder with production-ready files.

#### 1.3 Initialize Firebase in your project
```bash
firebase login
firebase init hosting
```

When prompted:
- **What do you want to use as your public directory?** → `frontend/dist`
- **Configure as a single-page app?** → `Yes`
- **Set up automatic builds and deploys?** → `No` (for now)

#### 1.4 Update firebase.json
Edit `firebase.json` to handle routing properly:
```json
{
  "hosting": {
    "public": "frontend/dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

#### 1.5 Deploy frontend to Firebase
```bash
firebase deploy --only hosting
```

Your frontend will be live at: `https://your-project-id.web.app`

---

### Step 2: Deploy Backend to Render.com (Free)

#### 2.1 Prepare your backend for Render
Create a `render.yaml` file in your project root:

```yaml
services:
  - type: web
    name: crimevision-backend
    env: python
    plan: free
    buildCommand: pip install -r CrimeVision/backend/requirements.txt
    startCommand: uvicorn CrimeVision.backend.main:app --host 0.0.0.0 --port $PORT
    
    envVars:
      - key: DATABASE_URL
        scope: build,runtime
        value: your_firestore_connection_string
      - key: CORS_ORIGINS
        value: "https://your-project-id.web.app"
```

#### 2.2 Prepare requirements.txt with proper versioning
Ensure all dependencies in `CrimeVision/backend/requirements.txt` are pinned:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
requests==2.31.0
# ... etc
```

#### 2.3 Update main.py for environment variables
```python
# Add this at the top of main.py
import os
from dotenv import load_dotenv

load_dotenv()

# Update CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        "https://your-project-id.web.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 2.4 Push to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

#### 2.5 Deploy on Render
1. Go to https://render.com
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Fill in:
   - **Name**: `crimevision-backend`
   - **Environment**: `Python 3.9`
   - **Build Command**: `pip install -r CrimeVision/backend/requirements.txt`
   - **Start Command**: `uvicorn CrimeVision.backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
6. Add environment variables:
   - `CORS_ORIGINS`: `https://your-project-id.web.app`
   - Database connection variables (see Step 3)
7. Deploy!

Your backend will be at: `https://crimevision-backend.onrender.com`

---

### Step 3: Migrate Database to Firestore (Free)

#### 3.1 Install Firebase Admin SDK
```bash
pip install firebase-admin
```

#### 3.2 Download Firebase service account key
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key"
3. Save as `CrimeVision/backend/.env.local` (add to .gitignore)

#### 3.3 Create Firestore migration script
Create `CrimeVision/backend/migrate_to_firestore.py`:

```python
import firebase_admin
from firebase_admin import credentials, firestore
import mysql.connector
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Connect to existing MySQL database
mysql_conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

cursor = mysql_conn.cursor(dictionary=True)

# Example: Migrate users table
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

for user in users:
    db.collection('users').document(str(user['id'])).set({
        'email': user['email'],
        'phone': user['phone'],
        'created_at': user['created_at'].isoformat() if hasattr(user['created_at'], 'isoformat') else user['created_at'],
        # ... map all fields
    })
    print(f"Migrated user {user['id']}")

cursor.close()
mysql_conn.close()
print("Migration complete!")
```

#### 3.4 Update backend to use Firestore
In `CrimeVision/backend/main.py`:

```python
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Replace MySQL queries with Firestore queries
# Example:
async def get_user(user_id: str):
    user_doc = db.collection('users').document(user_id).get()
    if user_doc.exists:
        return user_doc.to_dict()
    raise HTTPException(status_code=404, detail="User not found")
```

#### 3.5 Important Firestore Migration Considerations

**Data Structure Changes:**
```python
# MySQL: Multiple tables
# Firestore: Collections with subcollections

# MySQL Structure:
# users table → Firestore: /users/{userId} documents

# MySQL Structure:
# crimes table → Firestore: /crimes/{crimeId} documents

# MySQL Structure:
# alerts table → Firestore: /alerts/{alertId} documents
```

---

### Step 4: Update Frontend API Endpoints

Edit `CrimeVision/frontend/.env.production`:
```
VITE_API_URL=https://crimevision-backend.onrender.com
```

Update API calls in components:
```javascript
// OLD:
const response = await axios.get('http://localhost:8000/api/...');

// NEW:
const API_URL = import.meta.env.VITE_API_URL || 'https://crimevision-backend.onrender.com';
const response = await axios.get(`${API_URL}/api/...`);
```

---

### Step 5: Configure Custom Domain (Optional)

#### 5.1 Firebase Hosting Domain
1. Firebase Console → Hosting → Add custom domain
2. Point your domain DNS to Firebase
3. Free SSL/TLS certificate included!

#### 5.2 Render Backend Domain
- Your free Render URL is: `https://crimevision-backend.onrender.com`
- To connect custom domain:
  1. Render Dashboard → Settings → Custom Domains
  2. Add your domain
  3. Follow CNAME instructions

---

## FREE TIER QUOTAS & LIMITS

### Firebase Hosting (FREE)
- **Storage**: 10 GB
- **Bandwidth**: 360 MB/day (10.8 GB/month)
- **Requests**: Unlimited
- **SSL**: Free
- **CDN**: Included

### Render.com (FREE)
- **RAM**: 0.5 GB
- **CPU**: Shared
- **Auto-sleep**: After 15 minutes inactivity
- **Max Execution Time**: 30 seconds per request
- **Data Transfer**: 100 GB/month

### Firestore (FREE)
- **Storage**: 1 GB
- **Reads**: 50,000/day
- **Writes**: 20,000/day
- **Deletes**: 20,000/day
- **Bandwidth**: 1 GB/day

---

## STEP-BY-STEP QUICK CHECKLIST

- [ ] Build frontend: `npm run build`
- [ ] Install Firebase CLI: `npm install -g firebase-tools`
- [ ] Initialize Firebase: `firebase init hosting`
- [ ] Deploy frontend: `firebase deploy --only hosting`
- [ ] Create GitHub repository and push code
- [ ] Create Render.com account
- [ ] Deploy backend to Render
- [ ] Create Firebase project
- [ ] Set up Firestore database
- [ ] Migrate data from MySQL to Firestore
- [ ] Update API endpoints in frontend
- [ ] Update CORS settings in backend
- [ ] Test deployment
- [ ] Set up custom domain (optional)

---

## TROUBLESHOOTING

### Frontend deploy fails
```bash
# Clear cache and rebuild
rm -rf frontend/dist
npm run build --force
firebase deploy --only hosting
```

### Backend can't connect to Firestore
```bash
# Verify credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/serviceAccountKey.json"
python -c "import firebase_admin; print('Firebase initialized')"
```

### CORS errors
- Update `CORS_ORIGINS` in Render environment variables
- Include your Firebase domain in backend CORS settings

### Render auto-sleep causing timeouts
- Consider upgrading to paid plan if you need constant uptime
- Or use a free uptime monitor to prevent auto-sleep

---

## NEXT STEPS FOR SCALING (Still Free)

1. **Monitor Usage**: Firebase Console → Usage tab
2. **Optimize Firestore Queries**: Use proper indexing
3. **Cache Strategy**: Implement caching in frontend
4. **Upgrade Path**: When free tier isn't enough:
   - Firebase Blaze plan (pay-as-you-go)
   - Render paid plans start at $7/month
   - Firestore pricing scales with usage

---

## IMPORTANT NOTES

⚠️ **Render Free Tier Limitations:**
- Backend goes to sleep after 15 min inactivity
- First request after sleep takes longer (cold start)
- Not suitable for production high-traffic apps
- Consider upgrade to paid when needed

✅ **Best for Your Project:**
- Option 1 (Mixed Stack) is recommended
- Gives you room to scale
- Keeps costs at $0 initially
- Easy to migrate components as needed

---

## ESTIMATED MIGRATION TIME

| Task | Time |
|------|------|
| Frontend deployment | 15 min |
| Backend setup | 30 min |
| Database migration | 1-2 hours |
| Code updates | 30 min |
| Testing | 1 hour |
| **Total** | **4-5 hours** |

---

## SUPPORT & RESOURCES

- Firebase Docs: https://firebase.google.com/docs
- Render Docs: https://render.com/docs
- Firestore Migration: https://firebase.google.com/docs/firestore/migrate-data
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/

---

## NEXT: Would you like me to help you with:
1. Setting up Firebase project and deploying frontend?
2. Creating the Firestore migration script?
3. Updating your code for the new deployment?
4. All of the above?
