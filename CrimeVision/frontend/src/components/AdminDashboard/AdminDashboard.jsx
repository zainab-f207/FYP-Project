// src/components/AdminDashboard/AdminDashboard.js

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import apiService from '../../services/apiService_updated';
import styles from './AdminDashboard.module.css';
import AnalyticsPanel from './AnalyticsPanel';
import QuickActions from './QuickActions';
import NotificationsPanel from './NotificationsPanel';
import RecentActivity from './RecentActivity';
import UserManagementSummary from './UserManagementSummary';
import ApprovalRequests from './ApprovalRequests';
import PendingApprovalsPanel from './PendingApprovalsPanel';
import CrimeHeatmapPanel from './CrimeHeatmapPanel';
import ReportsPanel from './ReportsPanel';
import OCRPanel from './OCRPanel';
import AdminPredictionPanel from './AdminPredictionPanel';

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
  const SESSION_TIMEOUT = (systemSettings.session_timeout || 15) * 60; // from system settings (minutes → seconds)

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
    { id: 'ocr', icon: 'fas fa-file-image', label: 'FIR OCR', permission: 'view_crime_data' },
    { id: 'approvals', icon: 'fas fa-clipboard-check', label: 'Approvals', permission: null },
    { id: 'predictions', icon: 'fas fa-brain', label: 'AI Predictions', permission: 'view_analytics' },
    { id: 'alerts', icon: 'fas fa-exclamation-triangle', label: 'Alerts', permission: 'manage_alerts' },
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
    <div className={styles.appContainer}>
      <button className={styles.mobileToggle} onClick={toggleMobileSidebar}>
        <i className="fas fa-bars"></i>
      </button>

      {mobileSidebarOpen && <div className={styles.overlay} onClick={toggleMobileSidebar}></div>}

      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <i className="fas fa-shield-alt"></i>
          </div>
          <h3>SafeVision</h3>
          <p className={styles.sidebarSubtitle}>Admin Portal</p>
        </div>

        <div className={styles.adminProfileSidebar}>
          <img
            src={getProfileImageUrl(user?.profile_picture) || `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin')}&background=f9a826&color=0d2b4b&bold=true`}
            alt="Admin"
          />
          <div className={styles.adminInfoSidebar}>
            <h4>{user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username || 'Admin User'}</h4>
            <p><i className="fas fa-circle"></i> Online</p>
          </div>
        </div>

        <ul className={styles.sidebarMenu}>
          {navItems.map((item) => {
            const allowed = hasPermission(user, item.permission);
            return (
              <li key={item.id}>
                <a
                  href="#"
                  className={`${activeItem === item.id ? styles.active : ''} ${!allowed ? styles.disabledNav : ''}`}
                  onClick={(e) => {
                    e.preventDefault();
                    if (!allowed) return;
                    handleNavItemClick(item.id);
                  }}
                  title={allowed ? item.label : `${item.label} (No Permission)`}
                  style={!allowed ? { opacity: 0.4, cursor: 'not-allowed' } : {}}
                >
                  <i className={item.icon}></i>
                  <span>{item.label}</span>
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

      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        {/* Top Navbar */}
        <div className={styles.navbar}>
          <div className={styles.navbarLeft}>
            <div className={styles.searchBar}>
              <i className="fas fa-search"></i>
              <input type="text" placeholder="Search locations, crimes, users..." />
            </div>
          </div>
          <div className={styles.navbarRight}>
            <button className={styles.themeToggle} onClick={toggleTheme} title={isDarkTheme ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
              <i className={isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'}></i>
            </button>
            <div className={styles.notificationBtn} onClick={() => { if (hasPermission(user, 'manage_alerts')) setActiveItem('alerts'); }}>
              <i className="fas fa-bell"></i>
              <span className={styles.notificationBadge}>•</span>
            </div>
            <div className={styles.userProfile}>
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
            </div>
          </div>
        </div>

        {/* Welcome Section */}
        <div className={styles.welcomeSection}>
          <div className={styles.welcomeText}>
            <h2>Welcome back, {user?.first_name || user?.username || 'Admin'} <span className={styles.wave}>👋</span></h2>
            <p>{formatDate(currentTime)} — Here's your command center overview</p>
          </div>
          <div className={styles.welcomeBadge}>
            <i className="fas fa-shield-alt"></i>
            <span>Admin Access</span>
          </div>
        </div>

        {/* View-switched content based on active sidebar item */}
        {activeItem === 'dashboard' && (
          <>
            {/* Dashboard Stat Cards */}
            <div className={styles.dashboardCards}>
              {statCards.map((card, index) => (
                <div key={index} className={`${styles.card} ${styles[`card${card.color.charAt(0).toUpperCase() + card.color.slice(1)}`]}`}>
                  <div className={styles.cardHeader}>
                    <div className={styles.cardIcon}>
                      <i className={card.icon}></i>
                    </div>
                    <span className={`${styles.cardChange} ${card.positive ? styles.positive : styles.negative}`}>
                      {card.change}
                    </span>
                  </div>
                  <div className={styles.cardValue}>{card.value}</div>
                  <div className={styles.cardTitle}>{card.title}</div>
                  <div className={styles.cardProgress}>
                    <div className={styles.cardProgressBar}></div>
                  </div>
                </div>
              ))}
            </div>

            <QuickActions onAction={(action) => {
              const actionMap = { addReport: 'reports', sendAlert: 'alerts', manageUsers: 'users', viewLogs: 'dashboard', exportData: 'reports', mapView: 'heatmap' };
              const target = actionMap[action];
              if (target) {
                const nav = navItems.find(n => n.id === target);
                if (nav?.permission && !hasPermission(user, nav.permission)) {
                  alert('You do not have permission for this action.');
                  return;
                }
                setActiveItem(target);
              }
            }} />

            <AnalyticsPanel stats={stats} token={token} />

            <div className={styles.twoColumnGrid}>
              <NotificationsPanel token={token} />
              <RecentActivity token={token} />
            </div>
          </>
        )}

        {activeItem === 'analytics' && <AnalyticsPanel stats={stats} token={token} fullView />}
        {activeItem === 'users' && <UserManagementSummary token={token} fullView />}
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
          <div className={styles.card} style={{ padding: '40px', textAlign: 'center', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <i className="fas fa-cog" style={{ fontSize: '3rem', color: 'var(--primary-light)', marginBottom: '16px' }}></i>
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>System Settings</h3>
            <p style={{ color: 'var(--text-secondary)' }}>Administration settings — coming soon</p>
          </div>
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

      {/* Session Timeout Warning Modal */}
      {showSessionWarning && (
        <div className={styles.sessionOverlay}>
          <div className={styles.sessionModal}>
            <div className={styles.sessionModalIcon}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <h3>Session Expiring Soon</h3>
            <p>Your admin session will expire in <strong>{formatTimeLeft(sessionTimeLeft)}</strong> due to inactivity.</p>
            <p className={styles.sessionModalSub}>For security, admin sessions are limited to {systemSettings.session_timeout || 15} minutes.</p>
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
