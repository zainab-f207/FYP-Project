# Repository Overview

## Project Structure
- **CrimeVision**: Main application folder containing backend, frontend, datasets, machine-learning assets, and shared documentation.
  - **backend**: FastAPI service for authentication, crime data management, ML-driven risk prediction, and administrative APIs.
  - **frontend**: React (Vite) client, with modular components organized under `src/components`, centralized API utilities in `src/services`, and authentication providers under `src/contexts`.
  - **data**: CSV datasets used for analytics and testing.
  - **OCRModel**: OCR-related assets and supporting virtual environment.
- **CrimeVision_Database_Query.sql**: SQL helper script for database setup and queries.
- **data**: Root-level dataset samples used outside the main app.

## Back-End Quick Facts
1. **Entry Point**: `CrimeVision/backend/app/main_enhanced_final_fixed.py` (FastAPI).
2. **Dependencies**: Listed in `CrimeVision/backend/requirements.txt`; includes FastAPI, MySQL connector, joblib, pandas, NumPy, and supporting auth libraries.
3. **Environment**: `.env` in the backend directory provides database credentials and CORS origins.
4. **Auth**: Custom JWT-based system with password hashing in `auth_updated.py` and role-permission enforcement via the `/admin/*` endpoints.
5. **Database**: MySQL schema handled in `db_migrations.sql` with migration helper scripts (`run_migrations.py`, `setup_roles.py`).

## Front-End Quick Facts
1. **Framework**: React with Vite build tooling (`npm run dev`, `npm run build`).
2. **Entry Point**: `CrimeVision/frontend/src/main.jsx` bootstraps the app; `App.jsx` wires routing/layout.
3. **State Management**: Authentication context lives in `src/contexts/AuthContext.jsx` and `AuthContext_updated.jsx` (permission-aware extension).
4. **API Layer**: `src/services/apiService.js` centralizes REST calls and now exposes helpers like `buildQueryString`.
5. **SuperAdmin UI**: Located in `src/components/SuperAdminDashboard`; updated versions (e.g., `SuperAdminDashboard_updated.jsx`) represent the WIP Phase 1 enhancements.

## Development Workflows
1. **Backend Setup**
   - `pip install -r CrimeVision/backend/requirements.txt`
   - Configure `.env` with database/access credentials.
   - Launch server: `uvicorn app.main_enhanced_final_fixed:app --reload` (from backend root).
2. **Frontend Setup**
   - `cd CrimeVision/frontend`
   - `npm install`
   - `npm run dev` (default Vite port 5173).
3. **Data/Migrations**
   - Apply SQL from `db_migrations.sql`.
   - Use `setup_roles.py` after migrations to seed roles/permissions.

## Testing & QA Notes
- **Backend**: `test_api.py` contains API smoke tests; extend for new endpoints.
- **Frontend**: No testing framework configured yet—add React Testing Library/Jest as needed.
- **Integration**: Ensure `.env` CORS origins match the Vite dev server.

## SuperAdmin Phase 1 Status
- Auth context now exposes granular permissions for UI gating.
- API service supports query-string filters for admin endpoints.
- Pending tasks: implement full SuperAdmin management UI (user/admin tables, modals, logs) and wire bulk actions to the new endpoints.

## Contributing Tips
- Maintain consistent naming between backend response properties and frontend table columns.
- Reuse the `buildQueryString` helper for new service methods.
- When introducing new admin components, gate them via permission checks supplied by `AuthContext_updated` to prevent unauthorized rendering.