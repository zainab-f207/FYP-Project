// src/components/SuperAdminDashboard/SuperAdminDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';

import AdminRegistrationForm from '../AdminDashboard/AdminRegistrationForm';
import UserManagement from './UserManagement';
import AdminManagement from './AdminManagement';
import AnalyticsDashboard from './AnalyticsDashboard';
import SystemSettings from './SystemSettings';
import SuperAdminMainDashboard from './SuperAdminMainDashboard';
import SuperAdminReportsPanel from './SuperAdminReportsPanel';
import PendingApprovalsPanel from '../AdminDashboard/PendingApprovalsPanel';
import PPCManagement from './PPCManagement';
import SuperAdminPredictionPanel from './SuperAdminPredictionPanel';
import CrimeHeatmapPanel from '../AdminDashboard/CrimeHeatmapPanel';
import styles from './SuperAdminDashboard.module.css';
import { 
  CrownIcon, 
  DashboardIcon, 
  AdminIcon, 
  UsersIcon, 
  AnalyticsIcon, 
  SettingsIcon,
  SystemIcon 
} from './SuperAdminIcons';

const getProfileImageUrl = (profilePicture) => {
  if (!profilePicture) return null;
  if (profilePicture.startsWith('http://') || profilePicture.startsWith('https://')) {
    return profilePicture;
  }
  return `${window.location.origin}/${profilePicture}`;
};

const SuperAdminDashboard = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('dashboard');
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, logout, token } = useAuth();

  // Fetch real data from API
  useEffect(() => {
    if (token) {
      fetchDashboardData();
    }
  }, [token]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch real dashboard data using SuperAdmin-specific endpoint
      const [statsData, alertsData] = await Promise.all([
        apiService.getSuperAdminStats(token),
        apiService.getUserAlerts(token)
      ]);

      // Transform stats data to match expected format
      const transformedStats = {
        totalUsers: statsData.total_users || 0,
        totalAdmins: statsData.total_admins || 0,
        totalCrimes: statsData.total_crimes || 0,
        recentCrimes: statsData.recent_crimes || 0,
        systemHealth: 98.5, // This could be calculated based on system metrics
        predictionsToday: statsData.predictions_today || 0,
        preventedCrimes: statsData.prevented_crimes || 0,
        crimesByRisk: statsData.crimes_by_risk || {},
        crimesByArea: statsData.crimes_by_area || {},
        highRiskAreas: statsData.high_risk_areas || 0
      };

      // Transform alerts to notifications format
      const transformedNotifications = alertsData.slice(0, 10).map((alert, index) => ({
        id: alert.id || index,
        type: alert.severity === 'High' ? 'error' : alert.severity === 'Medium' ? 'warning' : 'info',
        message: alert.message || alert.title || 'System notification',
        time: formatTimeAgo(alert.created_at),
        urgent: alert.severity === 'High' || alert.urgent === true
      }));

      setStats(transformedStats);
      setNotifications(transformedNotifications);

      // Initialize animations after data loads
      setTimeout(() => {
        initializeAnimations();
      }, 100);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError('Failed to load dashboard data');
      
      // Fallback to minimal data structure instead of mock data
      setStats({
        totalUsers: 0,
        totalAdmins: 0,
        totalCrimes: 0,
        recentCrimes: 0,
        systemHealth: 0,
        predictionsToday: 0,
        preventedCrimes: 0
      });
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to format timestamps
  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'Recently';
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  const initializeAnimations = () => {
    // GSAP-like animation helper
    const animateElements = () => {
      const elements = document.querySelectorAll(`.${styles.animateIn}`);
      elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
          el.style.transition = 'all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
        }, index * 100);
      });
    };

    animateElements();
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen(!mobileSidebarOpen);
  };

  const handleSectionChange = (section) => {
    setActiveSection(section);
    if (window.innerWidth < 576) {
      setMobileSidebarOpen(false);
    }
    
    // Animate section transition
    const content = document.querySelector(`.${styles.mainContent}`);
    if (content) {
      content.style.opacity = '0';
      content.style.transform = 'translateX(20px)';
      
      setTimeout(() => {
        content.style.transition = 'all 0.4s ease';
        content.style.opacity = '1';
        content.style.transform = 'translateX(0)';
      }, 200);
    }
  };

  const handleLogout = () => {
    // Add logout animation
    const container = document.querySelector(`.${styles.appContainer}`);
    if (container) {
      container.style.transform = 'scale(0.9)';
      container.style.opacity = '0';
      container.style.transition = 'all 0.3s ease';
    }
    
    setTimeout(() => {
      logout();
    }, 300);
  };

  const handleRefreshData = () => {
    fetchDashboardData();
  };

  const renderActiveSection = () => {
    // Show loading state for dashboard
    if (loading && activeSection === 'dashboard') {
      return (
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner}>
            <SystemIcon size={48} className={styles.spinningIcon} />
          </div>
          <h3>Loading Dashboard...</h3>
          <p>Fetching real-time system data</p>
        </div>
      );
    }

    // Show error state if data failed to load
    if (error && activeSection === 'dashboard') {
      return (
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>
            <i className="fas fa-exclamation-triangle"></i>
          </div>
          <h3>Failed to Load Dashboard</h3>
          <p>{error}</p>
          <button className={styles.retryButton} onClick={handleRefreshData}>
            <i className="fas fa-redo"></i>
            Try Again
          </button>
        </div>
      );
    }

    switch (activeSection) {
      case 'dashboard':
        return <SuperAdminMainDashboard token={token} onNavigate={handleSectionChange} />;
      case 'analytics':
        return <AnalyticsDashboard stats={stats} notifications={notifications} loading={loading} />;
      case 'crime-map':
        return <CrimeHeatmapPanel token={token} />;
      case 'register-admin':
        return <AdminRegistrationForm />;
      case 'user-management':
        return <UserManagement token={token} />;
      case 'admin-management':
        return <AdminManagement token={token} />;
      case 'system-settings':
        return <SystemSettings />;
      case 'reports':
        return <SuperAdminReportsPanel token={token} />;
      case 'approvals':
        return <PendingApprovalsPanel />;
      case 'law-sections':
        return <PPCManagement token={token} />;
      case 'predictions':
        return <SuperAdminPredictionPanel />;
      default:
        return <SuperAdminMainDashboard token={token} onNavigate={handleSectionChange} />;
    }
  };

  return (
    <div className={styles.appContainer}>
      {/* Floating Action Button for Mobile */}
      <button 
        className={styles.floatingActionBtn}
        onClick={toggleMobileSidebar}
      >
        <i className="fas fa-cogs"></i>
      </button>

      {/* Sidebar */}
      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`} aria-label="SuperAdmin Sidebar">
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <CrownIcon size={28} className={styles.logoIcon} />
          </div>
          <h3>SuperAdmin</h3>
          <div className={styles.adminBadge}>
            <span>SUPER</span>
            <div className={styles.badgeGlow}></div>
          </div>
        </div>

        <div className={styles.userProfileSidebar}>
          <div className={styles.avatarContainer}>
            <img 
              src={getProfileImageUrl(user?.profile_picture) || `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'Super Admin')}&background=8B4513&color=fff&bold=true`}
              alt="Super Admin" 
              className={styles.avatar}
            />
            <div className={styles.statusIndicator}></div>
          </div>
          <div className={styles.userInfoSidebar}>
            <h4>{user?.name || 'Super Admin'}</h4>
            <p>System Administrator</p>
          </div>
        </div>

        <nav className={styles.sidebarNav}>
          <ul className={styles.sidebarMenu}>
            <li className={styles.animateIn} style={{ transitionDelay: '0ms' }}>
              <a 
                href="#dashboard"
                className={activeSection === 'dashboard' ? styles.active : ''}
                onClick={() => handleSectionChange('dashboard')}
                aria-current={activeSection === 'dashboard' ? 'page' : undefined}
              >
                <i className="fas fa-shield-halved" style={{ fontSize: '18px', width: '20px', textAlign: 'center' }}></i>
                <span>Command Center</span>
                {activeSection === 'dashboard' && <div className={styles.menuPulse}></div>}
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '75ms' }}>
              <a
                href="#crime-map"
                className={activeSection === 'crime-map' ? styles.active : ''}
                onClick={() => handleSectionChange('crime-map')}
                aria-current={activeSection === 'crime-map' ? 'page' : undefined}
              >
                <i className="fas fa-map" style={{ fontSize: '18px', width: '20px', textAlign: 'center' }}></i>
                <span>Crime Intelligence Map</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '150ms' }}>
              <a
                href="#analytics"
                className={activeSection === 'analytics' ? styles.active : ''}
                onClick={() => handleSectionChange('analytics')}
                aria-current={activeSection === 'analytics' ? 'page' : undefined}
              >
                <AnalyticsIcon size={20} className={styles.menuIcon} />
                <span>Analytics</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '100ms' }}>
              <a 
                href="#register-admin"
                className={activeSection === 'register-admin' ? styles.active : ''}
                onClick={() => handleSectionChange('register-admin')}
                aria-current={activeSection === 'register-admin' ? 'page' : undefined}
              >
                <AdminIcon size={20} className={styles.menuIcon} />
                <span>Register Admin</span>
                <span className={styles.newBadge}>NEW</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '200ms' }}>
              <a 
                href="#user-management"
                className={activeSection === 'user-management' ? styles.active : ''}
                onClick={() => handleSectionChange('user-management')}
                aria-current={activeSection === 'user-management' ? 'page' : undefined}
              >
                <UsersIcon size={20} className={styles.menuIcon} />
                <span>User Management</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '300ms' }}>
              <a 
                href="#admin-management"
                className={activeSection === 'admin-management' ? styles.active : ''}
                onClick={() => handleSectionChange('admin-management')}
                aria-current={activeSection === 'admin-management' ? 'page' : undefined}
              >
                <AdminIcon size={20} className={styles.menuIcon} />
                <span>Admin Management</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '400ms' }}>
              <a
                href="#reports"
                className={activeSection === 'reports' ? styles.active : ''}
                onClick={() => handleSectionChange('reports')}
                aria-current={activeSection === 'reports' ? 'page' : undefined}
              >
                <AnalyticsIcon size={20} className={styles.menuIcon} />
                <span>Reports</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '500ms' }}>
              <a
                href="#approvals"
                className={activeSection === 'approvals' ? styles.active : ''}
                onClick={() => handleSectionChange('approvals')}
                aria-current={activeSection === 'approvals' ? 'page' : undefined}
              >
                <i className="fas fa-gavel" style={{ fontSize: '18px', width: '20px', textAlign: 'center' }}></i>
                <span>FIR Approvals</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '600ms' }}>
              <a
                href="#predictions"
                className={activeSection === 'predictions' ? styles.active : ''}
                onClick={() => handleSectionChange('predictions')}
                aria-current={activeSection === 'predictions' ? 'page' : undefined}
              >
                <i className="fas fa-brain" style={{ fontSize: '18px', width: '20px', textAlign: 'center' }}></i>
                <span>AI Predictions</span>
              </a>
            </li>
            <li className={styles.animateIn}>
              <a
                href="#law-sections"
                className={activeSection === 'law-sections' ? styles.active : ''}
                onClick={() => handleSectionChange('law-sections')}
                aria-current={activeSection === 'law-sections' ? 'page' : undefined}
              >
                <i className="fas fa-balance-scale" style={{ fontSize: '18px', width: '20px', textAlign: 'center' }}></i>
                <span>Law Sections</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '700ms' }}>
              <a
                href="#system-settings"
                className={activeSection === 'system-settings' ? styles.active : ''}
                onClick={() => handleSectionChange('system-settings')}
                aria-current={activeSection === 'system-settings' ? 'page' : undefined}
              >
                <SettingsIcon size={20} className={styles.menuIcon} />
                <span>System Settings</span>
              </a>
            </li>
          </ul>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.systemStatus}>
            <div className={styles.statusItem}>
              <span>System Health</span>
              <div className={styles.statusBar}>
                <div 
                  className={styles.statusFill} 
                  style={{width: `${stats.systemHealth || 98}%`}}
                ></div>
              </div>
              <span className={styles.statusValue}>{stats.systemHealth || 98}%</span>
            </div>
          </div>

          <button 
            className={styles.logoutBtn}
            onClick={handleLogout}
            aria-label="Logout"
          >
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </button>

          <button className={styles.toggleBtn} onClick={toggleSidebar} aria-label="Toggle Sidebar">
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        {/* Top Navigation Bar */}
        <header className={styles.topNavbar}>
          <div className={styles.navLeft}>
            <div className={styles.breadcrumb}>
              <span className={styles.breadcrumbItem}>SuperAdmin</span>
              <span className={styles.breadcrumbDivider}>/</span>
              <span className={styles.breadcrumbActive}>
                {activeSection.split('-').map(word => 
                  word.charAt(0).toUpperCase() + word.slice(1)
                ).join(' ')}
              </span>
            </div>
          </div>
          
          <div className={styles.navRight}>
            <div className={styles.notificationBell}>
              <i className="fas fa-bell"></i>
              {notifications.filter(n => n.urgent).length > 0 && (
                <span className={styles.notificationCount}>
                  {notifications.filter(n => n.urgent).length}
                </span>
              )}
            </div>
            
            <div className={styles.quickActions}>
              <button 
                className={styles.quickActionBtn}
                onClick={handleRefreshData}
                disabled={loading}
                title="Refresh Data"
              >
                <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
              </button>
              <button className={styles.quickActionBtn} title="Help">
                <i className="fas fa-question-circle"></i>
              </button>
            </div>
          </div>
        </header>
        
        {/* Dynamic Content Area */}
        <main className={styles.contentArea}>
          {renderActiveSection()}
        </main>
      </div>
    </div>
  );
};

export default SuperAdminDashboard;
