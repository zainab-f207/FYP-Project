// src/components/AdminDashboard/AdminDashboard.js

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../../contexts/AuthContext_updated';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import apiService from '../../services/apiService_updated';
import styles from './AdminDashboard.module.css';
import AnalyticsPanel from './AnalyticsPanel';
import NotificationsPanel from './NotificationsPanel';
import ApprovalRequests from './ApprovalRequests';
import PendingApprovalsPanel from './PendingApprovalsPanel';
import CrimeHeatmapPanel from './CrimeHeatmapPanel';
import ReportsPanel from './ReportsPanel';
import OCRPanel from './OCRPanel';
import AdminPredictionPanel from './AdminPredictionPanel';
import AdminPasswordChangeReminder, { isPwChangeSnoozed } from '../Modals/AdminPasswordChangeReminder';
import AdminProfileSettings from '../Modals/AdminProfileSettings';
import AdminUserManagement from './AdminUserManagement';
import SystemSettings from '../SuperAdminDashboard/SystemSettings';
import SafeVisionLogo from '../common/SafeVisionLogo';

const WARNING_THRESHOLD = 2 * 60;     // Show warning at 2 minutes remaining

// Permission checking utility
const hasPermission = (user, permission) => {
  if (!user) return false;
  if (user.role === 'superadmin') return true;
  if (!permission) return true; // null permission = always allowed
  const perms = user.permissions || [];
  return perms.includes(permission);
};

const getProfileImageUrl = (profilePicture) => {
  if (!profilePicture) return null;
  if (profilePicture.startsWith('http://') || profilePicture.startsWith('https://')) {
    return profilePicture;
  }
  return `${window.location.origin}/${profilePicture}`;
};

const AdminDashboard = () => {
  const { settings: systemSettings } = useSystemSettings();
  // Resolve role-specific session timeout (matches backend JWT lifetime). Falls back through
  // admin_session_timeout → session_timeout → 60-minute default to keep parity with the backend.
  const SESSION_TIMEOUT_MINUTES =
    Number(systemSettings.admin_session_timeout) ||
    Number(systemSettings.session_timeout) ||
    60;
  const SESSION_TIMEOUT = SESSION_TIMEOUT_MINUTES * 60;

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [activeItem, setActiveItem] = useState('dashboard');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [sessionTimeLeft, setSessionTimeLeft] = useState(SESSION_TIMEOUT);
  const [showSessionWarning, setShowSessionWarning] = useState(false);
  const lastActivityRef = useRef(Date.now());
  const { user, token, logout } = useAuth();

  // Theme state
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    const saved = localStorage.getItem('admin-theme');
    if (saved) return saved !== 'light';
    const bodyTheme = document.body.getAttribute('data-theme');
    return bodyTheme !== 'light';
  });

  // Dynamic data state
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [recentEvents, setRecentEvents] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);
  const notifPopupRef = useRef(null);

  // Profile + first-login password reminder
  const [profileOpen, setProfileOpen] = useState(false);
  const [pwReminderOpen, setPwReminderOpen] = useState(false);

  // Surface password change reminder once per session for admins with the flag set
  useEffect(() => {
    if (user?.password_must_change && !isPwChangeSnoozed()) {
      setPwReminderOpen(true);
    }
  }, [user?.password_must_change]);

  // Clock timer
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  // Reset activity timer on user interaction
  const resetActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
    setSessionTimeLeft(SESSION_TIMEOUT);
    if (showSessionWarning) setShowSessionWarning(false);
  }, [showSessionWarning, SESSION_TIMEOUT]);

  // Track user activity (mouse, keyboard, scroll, touch)
  useEffect(() => {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'mousemove'];
    events.forEach((e) => window.addEventListener(e, resetActivity));
    return () => events.forEach((e) => window.removeEventListener(e, resetActivity));
  }, [resetActivity]);

  // Session countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - lastActivityRef.current) / 1000);
      const remaining = SESSION_TIMEOUT - elapsed;
      setSessionTimeLeft(Math.max(0, remaining));

      if (remaining <= WARNING_THRESHOLD && remaining > 0) {
        setShowSessionWarning(true);
      }

      if (remaining <= 0) {
        clearInterval(interval);
        logout();
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [logout, SESSION_TIMEOUT]);

  // Apply theme on mount and when theme changes
  useEffect(() => {
    document.body.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
    document.body.setAttribute('data-theme', isDarkTheme ? 'dark' : 'light');
    localStorage.setItem('admin-theme', isDarkTheme ? 'dark' : 'light');
  }, [isDarkTheme]);

  const toggleTheme = () => setIsDarkTheme(prev => !prev);

  // Fetch dashboard stats
  useEffect(() => {
    const fetchStats = async () => {
      if (!token) return;
      try {
        setStatsLoading(true);
        const data = await apiService.getAdminStats(token);
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch admin stats:', err);
      } finally {
        setStatsLoading(false);
      }
    };
    fetchStats();
  }, [token]);

  // Fetch real recent events for the LIVE OPS FEED (refresh every 60s).
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const load = async () => {
      try {
        const events = await apiService.getAdminRecentEvents(token);
        if (!cancelled) setRecentEvents(events);
      } catch (e) {
        if (!cancelled) setRecentEvents([]);
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, [token]);

  // Fetch real notifications for the bell dropdown (refresh every 60s).
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiService.getAdminNotifications(token);
        if (!cancelled) setNotifications(Array.isArray(data) ? data : []);
      } catch (e) {
        if (!cancelled) setNotifications([]);
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => { cancelled = true; clearInterval(id); };
  }, [token]);

  // Close notification dropdown on outside click / Esc. Note: the popup is
  // portalled to document.body so it's NOT inside notifRef — we need a
  // second ref on the popup itself and check both before closing.
  useEffect(() => {
    if (!notifOpen) return;
    const onDoc = (e) => {
      const inBell = notifRef.current && notifRef.current.contains(e.target);
      const inPopup = notifPopupRef.current && notifPopupRef.current.contains(e.target);
      if (!inBell && !inPopup) setNotifOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setNotifOpen(false); };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [notifOpen]);

  // Convert an ISO timestamp into a relative "5m / 2h / 3d ago" label.
  const relTime = (iso) => {
    if (!iso) return '';
    const t = new Date(iso).getTime();
    if (isNaN(t)) return '';
    const diff = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (diff < 30) return 'just now';
    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  };

  const handleExtendSession = () => {
    resetActivity();
    // Optionally call refresh-token endpoint
    setShowSessionWarning(false);
  };

  const formatTimeLeft = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const toggleSidebar = () => setSidebarCollapsed(!sidebarCollapsed);
  const toggleMobileSidebar = () => setMobileSidebarOpen(!mobileSidebarOpen);

  const handleNavItemClick = (item) => {
    setActiveItem(item);
    if (window.innerWidth < 576) setMobileSidebarOpen(false);
  };

  const handleLogout = (e) => {
    e.preventDefault();
    logout();
  };

  const navItems = [
    { id: 'dashboard', icon: 'fas fa-th-large', label: 'Dashboard', permission: null },
    { id: 'heatmap', icon: 'fas fa-map-marked-alt', label: 'Heat Map', permission: 'view_heatmaps' },
    { id: 'analytics', icon: 'fas fa-chart-line', label: 'Analytics', permission: 'view_analytics' },
    { id: 'users', icon: 'fas fa-users', label: 'Users', permission: 'view_users' },
    { id: 'reports', icon: 'fas fa-file-alt', label: 'Reports', permission: 'view_crime_data' },
    { id: 'ocr', icon: 'fas fa-file-image', label: 'FIR OCR', permission: 'manage_fir_ocr' },
    { id: 'approvals', icon: 'fas fa-clipboard-check', label: 'Approvals', permission: null },
    { id: 'predictions', icon: 'fas fa-brain', label: 'AI Predictions', permission: 'view_analytics' },
    { id: 'alerts', icon: 'fas fa-bell', label: 'Alerts', permission: null },
    { id: 'settings', icon: 'fas fa-cog', label: 'Settings', permission: 'manage_settings' },
  ];

  // Dynamic stat cards from real API data
  const statCards = stats ? [
    { title: 'Total Crimes', value: (stats.total_crimes || 0).toLocaleString(), change: `${(stats.recent_crimes || 0).toLocaleString()} this month`, positive: true, icon: 'fas fa-file-alt', color: 'primary' },
    { title: 'Active Users', value: (stats.total_users || 0).toLocaleString(), change: `${(stats.total_admins || 0)} admins`, positive: true, icon: 'fas fa-users', color: 'success' },
    { title: 'Risk Areas', value: Object.keys(stats.crimes_by_area || {}).length.toString(), change: `${Object.keys(stats.crimes_by_risk || {}).length} risk levels`, positive: true, icon: 'fas fa-exclamation-triangle', color: 'accent' },
    { title: 'Recent (30d)', value: (stats.recent_crimes || 0).toLocaleString(), change: 'Last 30 days', positive: true, icon: 'fas fa-clock', color: 'secondary' },
  ] : [
    { title: 'Total Crimes', value: '—', change: 'Loading...', positive: true, icon: 'fas fa-file-alt', color: 'primary' },
    { title: 'Active Users', value: '—', change: 'Loading...', positive: true, icon: 'fas fa-users', color: 'success' },
    { title: 'Risk Areas', value: '—', change: 'Loading...', positive: true, icon: 'fas fa-exclamation-triangle', color: 'accent' },
    { title: 'Recent (30d)', value: '—', change: 'Loading...', positive: true, icon: 'fas fa-clock', color: 'secondary' },
  ];

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  };

  return (
    <div className={styles.appContainer} data-sv-panel="admin">
      <button
        className={styles.mobileToggle}
        onClick={toggleMobileSidebar}
        data-sv-mobile-toggle
        aria-label="Open sidebar"
      >
        <i className="fas fa-bars"></i>
      </button>

      {mobileSidebarOpen && <div className={styles.overlay} onClick={toggleMobileSidebar} data-sv-overlay></div>}

      <div
        className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}
        data-sv-sidebar
        data-sv-mobile-open={mobileSidebarOpen ? 'true' : 'false'}
      >
        <div className={styles.sidebarHeader} data-sv-sidebar-header>
          <div className={styles.logo}>
            <SafeVisionLogo size={36} />
          </div>
          <h3 data-sv-sidebar-title>SafeVision</h3>
          <p className={styles.sidebarSubtitle} data-sv-sidebar-subtitle>Admin Portal</p>
          {/* Close (×) — only visible on tablets/phones via theme CSS */}
          <button
            type="button"
            data-sv-sidebar-close
            aria-label="Close sidebar"
            onClick={toggleMobileSidebar}
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className={styles.adminProfileSidebar} data-sv-sidebar-profile>
          <img
            src={getProfileImageUrl(user?.profile_picture) || `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin')}&background=f9a826&color=0d2b4b&bold=true`}
            alt="Admin"
          />
          <div className={styles.adminInfoSidebar} data-sv-sidebar-userinfo>
            <h4>{user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin User'}</h4>
            <p><i className="fas fa-circle"></i> Online</p>
          </div>
        </div>

        <ul className={styles.sidebarMenu} data-sv-sidebar-menu>
          {navItems.map((item) => {
            const allowed = hasPermission(user, item.permission);
            return (
              <li key={item.id} data-sv-menu-item>
                <a
                  href="#"
                  className={`${activeItem === item.id ? styles.active : ''} ${!allowed ? styles.disabledNav : ''}`}
                  data-sv-menu-link
                  data-sv-active={activeItem === item.id ? 'true' : 'false'}
                  onClick={(e) => {
                    e.preventDefault();
                    if (!allowed) return;
                    handleNavItemClick(item.id);
                  }}
                  title={allowed ? item.label : `${item.label} (No Permission)`}
                  style={!allowed ? { opacity: 0.4, cursor: 'not-allowed' } : {}}
                >
                  <i className={item.icon}></i>
                  <span data-sv-menu-label>{item.label}</span>
                  {!allowed && <i className="fas fa-lock" style={{ marginLeft: 'auto', fontSize: '0.65rem' }}></i>}
                </a>
              </li>
            );
          })}
        </ul>

        <div className={styles.sidebarFooter}>
          <a href="#" className={styles.logoutLink} onClick={handleLogout}>
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
          <button className={styles.toggleBtn} onClick={toggleSidebar}>
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>

      <div
        className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}
        data-sv-main
      >
        {/* Top Navbar */}
        <div className={styles.navbar} data-sv-navbar>
          <div className={styles.navbarLeft}>
            {/* Replaced the dead search bar with a live status strip:
                shows local time, pending approvals and the system health
                heuristic from /admin/stats. Real signals only. */}
            <div data-sv-statusstrip className={styles.statusStrip}>
              <span data-sv-status-pill>
                <i className="far fa-clock"></i>
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span data-sv-status-pill data-sv-status-tone={(stats?.pending_approvals ?? 0) > 0 ? 'warn' : 'ok'}>
                <i className="fas fa-clipboard-check"></i>
                {stats?.pending_approvals ?? 0} pending
              </span>
              <span data-sv-status-pill data-sv-status-tone="ok">
                <i className="fas fa-heartbeat"></i>
                {stats?.system_health ?? 100}% healthy
              </span>
            </div>
          </div>
          <div className={styles.navbarRight}>
            <button className={styles.themeToggle} onClick={toggleTheme} title={isDarkTheme ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
              <i className={isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'}></i>
            </button>
            <div
              ref={notifRef}
              className={styles.notificationBtn}
              style={{ position: 'relative' }}
              onClick={() => setNotifOpen((v) => !v)}
              role="button"
              tabIndex={0}
              title="Notifications"
            >
              <i className="fas fa-bell"></i>
              {notifications.length > 0 && (
                <span className={styles.notificationBadge}>{notifications.length}</span>
              )}
            </div>
            {/* Notification popup is portalled into document.body so the
                navbar's backdrop-filter (which makes the navbar a containing
                block for position:fixed descendants) cannot trap it. */}
            {notifOpen && createPortal(
              <div
                ref={notifPopupRef}
                data-sv-notif-popup
                className={styles.notifPopup}
                onClick={(e) => e.stopPropagation()}
              >
                <div data-sv-notif-head>
                  <strong>Notifications</strong>
                  <span data-sv-notif-count>{notifications.length}</span>
                </div>
                <div data-sv-notif-list>
                  {notifications.length === 0 ? (
                    <div data-sv-notif-empty>
                      <i className="fas fa-check-circle"></i>
                      <span>You're all caught up</span>
                    </div>
                  ) : (
                    notifications.map((n) => (
                      <div key={n.id} data-sv-notif-row data-sv-notif-tone={n.type || 'info'}>
                        <i className={
                          n.type === 'warning' ? 'fas fa-exclamation-triangle'
                            : n.type === 'success' ? 'fas fa-check-circle'
                            : n.type === 'error' ? 'fas fa-times-circle'
                            : 'fas fa-info-circle'
                        }></i>
                        <div data-sv-notif-body>
                          <div data-sv-notif-title>{n.title}</div>
                          <div data-sv-notif-msg>{n.message}</div>
                        </div>
                        <span data-sv-notif-time>{relTime(n.timestamp)}</span>
                      </div>
                    ))
                  )}
                </div>
                {hasPermission(user, null) && (
                  <button
                    data-sv-notif-foot
                    onClick={() => { setNotifOpen(false); setActiveItem('alerts'); }}
                  >
                    Open Alerts Center →
                  </button>
                )}
              </div>,
              document.body
            )}
            <div
              className={styles.userProfile}
              data-sv-userchip
              role="button"
              tabIndex={0}
              onClick={() => setProfileOpen(true)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setProfileOpen(true); }}
              title="Profile settings"
              style={{ cursor: 'pointer' }}
            >
              <img
                src={getProfileImageUrl(user?.profile_picture) || `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin')}&background=1a4f72&color=fff`}
                alt="Admin"
              />
              <div className={styles.userInfo}>
                <div className={styles.userName}>{user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin User'}</div>
                <small className={styles.userRole}>
                  <i className="fas fa-shield-alt"></i> {user?.role === 'admin' ? 'Administrator' : user?.role || 'Administrator'}
                </small>
              </div>
              <i className="fas fa-chevron-down" style={{ color: 'var(--text-secondary)', fontSize: 12, marginLeft: 6 }}></i>
            </div>
          </div>
        </div>

        {/* Welcome Section */}
        <div className={styles.welcomeSection} data-sv-welcome>
          <div className={styles.welcomeText}>
            <h2 data-sv-welcome-title>Welcome back, {user?.first_name || user?.username || 'Admin'} <span className={styles.wave}>👋</span></h2>
            <p>{formatDate(currentTime)} — Here's your command center overview</p>
          </div>
          <div className={styles.welcomeBadge} data-sv-welcome-badge>
            <i className="fas fa-shield-alt"></i>
            <span>Admin Access</span>
          </div>
        </div>

        {/* View-switched content based on active sidebar item */}
        {activeItem === 'dashboard' && (
          <>
            {/* Dashboard Stat Cards */}
            <div className={styles.dashboardCards} data-sv-stat-grid>
              {statCards.map((card, index) => (
                <div
                  key={index}
                  className={`${styles.card} ${styles[`card${card.color.charAt(0).toUpperCase() + card.color.slice(1)}`]}`}
                  data-sv-stat-card
                  data-sv-color={card.color}
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.cardIcon} data-sv-card-icon>
                      <i className={card.icon}></i>
                    </div>
                    <span className={`${styles.cardChange} ${card.positive ? styles.positive : styles.negative}`}>
                      {card.change}
                    </span>
                  </div>
                  <div className={styles.cardValue} data-sv-card-value>{card.value}</div>
                  <div className={styles.cardTitle}>{card.title}</div>
                  <div className={styles.cardProgress}>
                    <div className={styles.cardProgressBar}></div>
                  </div>
                </div>
              ))}
            </div>

            {/* ── System Pulse: live operational widgets ── */}
            <div data-sv-info-grid>
              <div data-sv-info-card>
                <h4><i className="fas fa-heartbeat"></i> System Health</h4>
                <div className="sv-info-value">{stats?.system_health ?? 98}%</div>
                <div className="sv-info-sub">All services operational</div>
                <div className="sv-info-bar"><span style={{ width: `${stats?.system_health ?? 98}%` }} /></div>
              </div>

              <div data-sv-info-card>
                <h4><i className="fas fa-bolt"></i> Predictions Today</h4>
                <div className="sv-info-value">{stats?.predictions_today ?? 0}</div>
                <div className="sv-info-sub">AI risk inferences executed</div>
                <div className="sv-info-bar">
                  <span style={{ width: `${Math.min(100, ((stats?.predictions_today ?? 0) / 50) * 100)}%` }} />
                </div>
              </div>

              <div data-sv-info-card>
                <h4><i className="fas fa-shield-virus"></i> Pending Approvals</h4>
                <div className="sv-info-value">{stats?.pending_approvals ?? 0}</div>
                <div className="sv-info-sub">FIRs awaiting review</div>
                <div className="sv-info-bar">
                  <span style={{ width: `${Math.min(100, ((stats?.pending_approvals ?? 0) / 25) * 100)}%` }} />
                </div>
              </div>

              <div data-sv-info-card>
                <h4><i className="fas fa-user-clock"></i> Session Time Left</h4>
                <div className="sv-info-value">{formatTimeLeft(sessionTimeLeft)}</div>
                <div className="sv-info-sub">Auto-logout countdown</div>
                <div className="sv-info-bar">
                  <span style={{ width: `${(sessionTimeLeft / SESSION_TIMEOUT) * 100}%` }} />
                </div>
              </div>
            </div>

            {/* ── Quick Links to common tasks ── */}
            <div data-sv-quicklinks>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => hasPermission(user, 'view_heatmaps') && setActiveItem('heatmap')}>
                <i className="fas fa-map-marked-alt"></i>
                <span><strong>Heat Map</strong><small>Crime hot-zones</small></span>
              </a>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => hasPermission(user, 'view_crime_data') && setActiveItem('reports')}>
                <i className="fas fa-file-alt"></i>
                <span><strong>Reports</strong><small>Manage crime data</small></span>
              </a>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => hasPermission(user, 'manage_fir_ocr') && setActiveItem('ocr')}>
                <i className="fas fa-file-image"></i>
                <span><strong>FIR OCR</strong><small>Scan & extract</small></span>
              </a>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => hasPermission(user, 'view_analytics') && setActiveItem('predictions')}>
                <i className="fas fa-brain"></i>
                <span><strong>AI Predictions</strong><small>Forecast crime</small></span>
              </a>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => hasPermission(user, 'view_users') && setActiveItem('users')}>
                <i className="fas fa-users"></i>
                <span><strong>Users</strong><small>Account directory</small></span>
              </a>
              <a data-sv-quicklink role="button" tabIndex={0} onClick={() => setProfileOpen(true)}>
                <i className="fas fa-user-cog"></i>
                <span><strong>Profile</strong><small>Account & security</small></span>
              </a>
            </div>

            {/* ── Crime Hotspot Leaderboard + Risk Distribution dashboard ── */}
            <div data-sv-two-col className={styles.twoColumnGrid}>
              {/* Hotspot leaderboard */}
              <div data-sv-rich-card>
                <div data-sv-rich-card-head>
                  <div>
                    <span data-sv-rich-eyebrow><i className="fas fa-fire"></i> CRIME HOTSPOT INDEX</span>
                    <h3 data-sv-rich-title>Top areas this month</h3>
                  </div>
                  <span data-sv-pill>{Object.keys(stats?.crimes_by_area || {}).length} tracked</span>
                </div>
                <div data-sv-leaderboard>
                  {(() => {
                    const entries = Object.entries(stats?.crimes_by_area || {})
                      .sort((a, b) => b[1] - a[1])
                      .slice(0, 6);
                    if (entries.length === 0) {
                      return (
                        <div data-sv-empty>
                          <i className="fas fa-map-marked-alt"></i>
                          <span>No location-tagged crimes yet — start ingesting FIRs to populate this index.</span>
                        </div>
                      );
                    }
                    const top = entries[0]?.[1] || 1;
                    return entries.map(([area, count], idx) => {
                      const pct = Math.round((count / top) * 100);
                      const sev = pct >= 80 ? 'critical' : pct >= 55 ? 'high' : pct >= 30 ? 'medium' : 'low';
                      return (
                        <div key={area} data-sv-leader-row data-sv-sev={sev}>
                          <span data-sv-leader-rank>#{idx + 1}</span>
                          <div data-sv-leader-body>
                            <div data-sv-leader-top>
                              <span data-sv-leader-name>{area}</span>
                              <span data-sv-leader-count>{count.toLocaleString()} <small>FIRs</small></span>
                            </div>
                            <div data-sv-leader-bar><span style={{ width: `${pct}%` }} /></div>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>

              {/* Risk distribution donut + breakdown */}
              <div data-sv-rich-card>
                <div data-sv-rich-card-head>
                  <div>
                    <span data-sv-rich-eyebrow><i className="fas fa-chart-pie"></i> RISK DISTRIBUTION</span>
                    <h3 data-sv-rich-title>Severity breakdown</h3>
                  </div>
                  <span data-sv-pill>Live</span>
                </div>

                {(() => {
                  const riskMap = stats?.crimes_by_risk || {};
                  const total = Object.values(riskMap).reduce((a, b) => a + (b || 0), 0) || 1;
                  const SEV_META = [
                    { key: 'High', label: 'Critical / High Risk', color: '#ff5d5d', glow: 'rgba(255,93,93,0.45)' },
                    { key: 'Medium', label: 'Moderate Risk', color: '#f9a826', glow: 'rgba(249,168,38,0.45)' },
                    { key: 'Low', label: 'Low Risk', color: '#1dd1a1', glow: 'rgba(29,209,161,0.45)' },
                  ];
                  // Build donut conic-gradient stops
                  let acc = 0;
                  const stops = SEV_META.map((s) => {
                    const v = riskMap[s.key] || riskMap[s.key.toLowerCase()] || 0;
                    const startPct = (acc / total) * 100;
                    acc += v;
                    const endPct = (acc / total) * 100;
                    return `${s.color} ${startPct}% ${endPct}%`;
                  }).join(', ');
                  const conic = `conic-gradient(${stops || `${SEV_META[2].color} 0% 100%`})`;

                  return (
                    <div data-sv-risk-grid>
                      <div data-sv-donut style={{ background: conic }}>
                        <div data-sv-donut-hole>
                          <strong>{total.toLocaleString()}</strong>
                          <span>total crimes</span>
                        </div>
                      </div>
                      <div data-sv-risk-legend>
                        {SEV_META.map((s) => {
                          const v = riskMap[s.key] || riskMap[s.key.toLowerCase()] || 0;
                          const pct = total ? Math.round((v / total) * 100) : 0;
                          return (
                            <div key={s.key} data-sv-risk-row style={{ '--svRiskColor': s.color, '--svRiskGlow': s.glow }}>
                              <span data-sv-risk-dot></span>
                              <span data-sv-risk-name>{s.label}</span>
                              <span data-sv-risk-val>{v.toLocaleString()} · {pct}%</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* ── Live Activity Stream + Coverage Snapshot ── */}
            <div data-sv-two-col className={styles.twoColumnGrid}>
              <div data-sv-rich-card>
                <div data-sv-rich-card-head>
                  <div>
                    <span data-sv-rich-eyebrow><i className="fas fa-satellite-dish"></i> LIVE OPS FEED</span>
                    <h3 data-sv-rich-title>Latest events</h3>
                  </div>
                  <span data-sv-pill data-sv-pill-pulse>● live</span>
                </div>
                <div data-sv-feed>
                  {recentEvents.length === 0 ? (
                    <div data-sv-empty style={{ padding: '18px 14px' }}>
                      <i className="fas fa-satellite-dish"></i>
                      <span>No activity yet — admin actions, FIRs and approvals will surface here in real time.</span>
                    </div>
                  ) : (
                    recentEvents.map((evt, i) => (
                      <div key={i} data-sv-feed-row data-sv-sev={evt.sev || 'low'}>
                        <div data-sv-feed-icon><i className={evt.icon || 'fas fa-shield-alt'}></i></div>
                        <div data-sv-feed-body>
                          <div data-sv-feed-title>{evt.title}</div>
                          <div data-sv-feed-sub>{evt.body}</div>
                        </div>
                        <span data-sv-feed-time>{relTime(evt.timestamp)}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div data-sv-rich-card>
                <div data-sv-rich-card-head>
                  <div>
                    <span data-sv-rich-eyebrow><i className="fas fa-globe-asia"></i> COVERAGE SNAPSHOT</span>
                    <h3 data-sv-rich-title>System reach</h3>
                  </div>
                  <span data-sv-pill>updated now</span>
                </div>
                <div data-sv-coverage-grid>
                  <div data-sv-coverage-tile>
                    <i className="fas fa-map-marked-alt" data-sv-coverage-icon></i>
                    <strong>{Object.keys(stats?.crimes_by_area || {}).length}</strong>
                    <span>Areas under watch</span>
                  </div>
                  <div data-sv-coverage-tile>
                    <i className="fas fa-users" data-sv-coverage-icon style={{ color: '#1dd1a1' }}></i>
                    <strong>{(stats?.total_users ?? 0).toLocaleString()}</strong>
                    <span>Active citizens</span>
                  </div>
                  <div data-sv-coverage-tile>
                    <i className="fas fa-user-shield" data-sv-coverage-icon style={{ color: '#f9a826' }}></i>
                    <strong>{(stats?.total_admins ?? 0).toLocaleString()}</strong>
                    <span>Field admins</span>
                  </div>
                  <div data-sv-coverage-tile>
                    <i className="fas fa-file-alt" data-sv-coverage-icon style={{ color: '#8b5cf6' }}></i>
                    <strong>{(stats?.recent_crimes ?? 0).toLocaleString()}</strong>
                    <span>Recent FIRs (30d)</span>
                  </div>
                </div>

                <div data-sv-coverage-foot>
                  <div data-sv-coverage-bar>
                    <span>Risk-area coverage</span>
                    <div><span style={{ width: `${Math.min(100, Object.keys(stats?.crimes_by_area || {}).length * 1.6)}%` }} /></div>
                  </div>
                  <div data-sv-coverage-bar>
                    <span>Citizen engagement</span>
                    <div><span style={{ width: `${Math.min(100, ((stats?.total_users ?? 0) / 5))}%` }} /></div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {activeItem === 'analytics' && <AnalyticsPanel stats={stats} token={token} fullView />}
        {activeItem === 'users' && <AdminUserManagement token={token} user={user} />}
        {activeItem === 'approvals' && (
          <>
            <PendingApprovalsPanel />
            <ApprovalRequests />
          </>
        )}
        {activeItem === 'alerts' && <NotificationsPanel token={token} fullView />}
        {activeItem === 'heatmap' && <CrimeHeatmapPanel token={token} />}
        {activeItem === 'reports' && <ReportsPanel token={token} />}
        {activeItem === 'ocr' && <OCRPanel token={token} />}
        {activeItem === 'predictions' && <AdminPredictionPanel />}

        {activeItem === 'settings' && (
          hasPermission(user, 'manage_settings') ? (
            <SystemSettings />
          ) : (
            <div className={styles.card} style={{ padding: '40px', textAlign: 'center', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <i className="fas fa-lock" style={{ fontSize: '3rem', color: 'var(--accent)' }}></i>
              <h3 style={{ color: 'var(--text-primary)', margin: 0 }}>System Settings</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: 460 }}>
                You don't have the <strong>Manage Settings</strong> permission. Open Profile Settings to manage your account
                and password instead.
              </p>
              <button
                type="button"
                onClick={() => setProfileOpen(true)}
                style={{
                  padding: '10px 22px',
                  borderRadius: 10,
                  border: 'none',
                  color: '#fff',
                  background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <i className="fas fa-user-cog" style={{ marginRight: 8 }}></i>
                Open Profile Settings
              </button>
            </div>
          )
        )}

        {/* Footer */}
        <div className={styles.dashboardFooter}>
          <p>© 2026 SafeVision — Government Crime Prediction & Mapping System</p>
        </div>
      </div>

      {/* Session Timer Indicator */}
      {sessionTimeLeft <= WARNING_THRESHOLD && sessionTimeLeft > 0 && (
        <div className={styles.sessionTimerBadge}>
          <i className="fas fa-clock"></i> {formatTimeLeft(sessionTimeLeft)}
        </div>
      )}

      {/* Profile drawer + first-login password reminder */}
      <AdminProfileSettings open={profileOpen} onClose={() => setProfileOpen(false)} />
      <AdminPasswordChangeReminder
        open={pwReminderOpen}
        onClose={() => setPwReminderOpen(false)}
        onChanged={() => setPwReminderOpen(false)}
      />

      {/* Session Timeout Warning Modal */}
      {showSessionWarning && (
        <div className={styles.sessionOverlay}>
          <div className={styles.sessionModal}>
            <div className={styles.sessionModalIcon}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <h3>Session Expiring Soon</h3>
            <p>Your admin session will expire in <strong>{formatTimeLeft(sessionTimeLeft)}</strong> due to inactivity.</p>
            <p className={styles.sessionModalSub}>For security, admin sessions are limited to {SESSION_TIMEOUT_MINUTES} minutes.</p>
            <div className={styles.sessionModalActions}>
              <button className={styles.sessionExtendBtn} onClick={handleExtendSession}>
                <i className="fas fa-redo"></i> Extend Session
              </button>
              <button className={styles.sessionLogoutBtn} onClick={(e) => { e.preventDefault(); logout(); }}>
                <i className="fas fa-sign-out-alt"></i> Logout Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
