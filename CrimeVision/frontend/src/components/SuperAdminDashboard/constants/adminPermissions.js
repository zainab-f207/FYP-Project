// Shared admin permission/department config used by Register Admin form and Admin Management edit modal.

export const DEPARTMENTS = [
  { value: 'Law Enforcement Operations', label: 'Law Enforcement Operations', icon: '🛡️', desc: 'Police liaison, crime investigation coordination & field enforcement' },
  { value: 'Crime Analytics & Intelligence', label: 'Crime Analytics & Intelligence', icon: '📊', desc: 'Data analysis, crime pattern recognition & prediction models' },
  { value: 'Emergency Response & Dispatch', label: 'Emergency Response & Dispatch', icon: '🚨', desc: 'Crisis management, emergency coordination & rapid response' },
  { value: 'IT & Cybersecurity', label: 'IT & Cybersecurity', icon: '🔒', desc: 'System administration, network security & technical support' },
  { value: 'Public Safety Communications', label: 'Public Safety Communications', icon: '📡', desc: 'Public outreach, media relations & community alerts' },
  { value: 'Forensics & Evidence Management', label: 'Forensics & Evidence Management', icon: '🔬', desc: 'Evidence handling, forensic analysis & case documentation' },
  { value: 'Strategic Planning & Policy', label: 'Strategic Planning & Policy', icon: '📋', desc: 'Policy development, resource allocation & strategic oversight' },
  { value: 'Community Policing & Outreach', label: 'Community Policing & Outreach', icon: '🤝', desc: 'Community engagement, neighborhood watch & public awareness' },
];

export const PERMISSION_CATEGORIES = [
  {
    category: 'User Management',
    iconClass: 'fas fa-users',
    color: '#1a4f72',
    permissions: [
      { value: 'view_users', label: 'View Users', desc: 'View all registered user profiles and details' },
      { value: 'manage_users', label: 'Manage User Accounts', desc: 'Edit user information and account settings' },
      { value: 'suspend_users', label: 'Suspend / Activate Users', desc: 'Temporarily suspend or reactivate user accounts' },
      { value: 'assign_roles', label: 'Assign Roles', desc: 'Change user roles and access levels (requires approval)' },
    ],
  },
  {
    category: 'Crime Data',
    iconClass: 'fas fa-shield-alt',
    color: '#ff6b6b',
    permissions: [
      { value: 'view_crime_data', label: 'View Crime Reports', desc: 'Access all crime reports, incidents & case files' },
      { value: 'manage_crime_data', label: 'Manage Crime Data', desc: 'Create, edit and organize crime records' },
      { value: 'verify_crime_reports', label: 'Verify Crime Reports', desc: 'Review and approve submitted crime reports' },
      { value: 'approve_firs', label: 'Approve FIR Reports', desc: 'Review and approve or reject submitted FIR applications' },
      { value: 'manage_fir_ocr', label: 'FIR OCR Submission', desc: 'Upload FIR images, extract data and submit FIRs for approval' },
      { value: 'export_crime_data', label: 'Export Crime Data', desc: 'Download crime data in various formats (CSV, PDF)' },
    ],
  },
  {
    category: 'Analytics & Predictions',
    iconClass: 'fas fa-chart-line',
    color: '#f9a826',
    permissions: [
      { value: 'view_analytics', label: 'View Analytics', desc: 'Access crime analytics dashboards and visualizations' },
      { value: 'access_predictions', label: 'Access Prediction Models', desc: 'Use AI-based crime prediction and hotspot models' },
      { value: 'generate_reports', label: 'Generate Reports', desc: 'Create custom analytical and summary reports' },
      { value: 'manage_reports', label: 'Manage Reports Dashboard', desc: 'Access and manage the system reports and analytics exports' },
      { value: 'view_heatmaps', label: 'View Crime Heatmaps', desc: 'Access geographic crime heatmap overlays' },
    ],
  },
  {
    category: 'Alerts & Emergency',
    iconClass: 'fas fa-bell',
    color: '#1dd1a1',
    permissions: [
      { value: 'manage_alerts', label: 'Manage Alerts', desc: 'Configure and send crime alerts to users' },
      { value: 'emergency_dispatch', label: 'Emergency Dispatch', desc: 'Coordinate emergency response dispatches' },
      { value: 'priority_alerts', label: 'Priority Alerts', desc: 'Issue high-priority public safety alerts' },
      { value: 'manage_emergency_contacts', label: 'Manage Emergency Contacts', desc: 'Maintain emergency contact directories' },
    ],
  },
  {
    category: 'System Administration',
    iconClass: 'fas fa-cog',
    color: '#2d7fb8',
    permissions: [
      { value: 'manage_settings', label: 'System Settings', desc: 'Configure platform settings and parameters' },
      { value: 'view_audit_logs', label: 'View Audit Logs', desc: 'Access system audit trails and activity logs' },
      { value: 'manage_law_sections', label: 'Manage Law Sections', desc: 'Add, edit and manage PPC/ATA/CNSA law section database' },
    ],
  },
];

export const DEPARTMENT_PERMISSIONS = {
  'Law Enforcement Operations': ['view_users', 'view_crime_data', 'verify_crime_reports', 'manage_crime_data', 'view_analytics', 'view_heatmaps', 'manage_fir_ocr'],
  'Crime Analytics & Intelligence': ['view_crime_data', 'export_crime_data', 'view_analytics', 'access_predictions', 'generate_reports', 'manage_reports', 'view_heatmaps', 'view_audit_logs'],
  'Emergency Response & Dispatch': ['view_crime_data', 'view_heatmaps'],
  'IT & Cybersecurity': ['view_users', 'manage_settings', 'view_audit_logs', 'manage_law_sections'],
  'Public Safety Communications': ['view_crime_data', 'view_analytics', 'view_heatmaps', 'generate_reports'],
  'Forensics & Evidence Management': ['view_crime_data', 'manage_crime_data', 'verify_crime_reports', 'export_crime_data', 'generate_reports', 'manage_fir_ocr'],
  'Strategic Planning & Policy': ['view_users', 'view_crime_data', 'view_analytics', 'access_predictions', 'generate_reports', 'manage_reports', 'view_heatmaps', 'view_audit_logs'],
  'Community Policing & Outreach': ['view_users', 'view_crime_data', 'view_analytics', 'view_heatmaps'],
};

export const ALL_PERMISSION_VALUES = PERMISSION_CATEGORIES.flatMap((c) => c.permissions.map((p) => p.value));
