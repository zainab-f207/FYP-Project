This folder holds files quarantined from the live project that the dead-code
audit determined are not referenced anywhere in the runtime code path.

Each file is kept under its ORIGINAL relative path inside this folder so it
can be restored by simply moving it back to the same location relative to the
repository root.

Audit basis (zero live incoming imports — only self-references or
commented-out imports were found):

Frontend
  CrimeVision/frontend/src/components/MapInterface/MapInterface.jsx
  CrimeVision/frontend/src/components/MapInterface/MapInterface.css
  CrimeVision/frontend/src/components/MapInterface/index.jsx
      The only outside reference is a commented-out import in MainWebsite.jsx.
      The live map is CrimeMapInterface_real_insights.jsx, unrelated.

  CrimeVision/frontend/src/components/SuperAdminDashboard/SuperAdminIcons.jsx
      Zero references. SuperAdminDashboard uses SVGComponents.jsx instead.

  CrimeVision/frontend/src/components/UserDashboard/NavigationComingSoon.css
  CrimeVision/frontend/src/components/UserDashboard/PredictionComingSoon.css
      Zero JSX imports; only their own self-comments.

  CrimeVision/frontend/src/components/UserDashboard/UserDashboard.css
      Zero JSX imports. The active styles live in UserDashboard.module.css.

  CrimeVision/frontend/src/components/ReportingDashboard.module.css
      Only references are commented-out imports in
      SuperAdminDashboard_updated.jsx. The corresponding JSX file does not
      even exist.

Backend
  CrimeVision/backend/app/generate_key.py
      Three-line VAPID-key script. Not imported by anything. The proper
      utilities live at backend root: generate_vapid_keys.py and
      generate_vapid_simple.py.

NOT MOVED (stay in place — they are USED despite suspicious naming):
  *_updated.jsx files (LoginModal_updated, SuperAdminDashboard_updated,
    AnalyticsDashboard_updated, CrimeMap_updated, apiService_updated)
  CrimeMap2.css, SystemSettings.jsx, MiniHeatmap, PermissionMatrix,
  AdminPasswordChangeReminder, AdminProfileSettings, BrowserPushSetup,
  RealPredictionMap, HeatMapLayer, AlertsComingSoon.css, UserDropdown.css,
  auth_updated.py, password_reset_fixed.py, alert_tester.py.

NOT MOVED (operational scripts / generated artifacts — separate decision):
  backend/__pycache__/ caches, backend/reports/ generated files,
  one-off DB migration scripts at backend root, top-level *.md docs.

Restoration:
  To restore any file, move it from
    _deleted/<original-relative-path>
  back to
    <original-relative-path>
