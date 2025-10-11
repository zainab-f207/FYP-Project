// src/components/SuperAdminDashboard/SuperAdminDashboard.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';

import AdminRegistrationForm from '../AdminDashboard/AdminRegistrationForm';
import UserManagement from './UserManagement';
import AdminManagement from './AdminManagement';
import AnalyticsDashboard from './AnalyticsDashboard';
import SystemSettings from './SystemSettings';
import SuperAdminQuickActions from './SuperAdminQuickActions';
import SystemLogs from './SystemLogs';
import styles from './SuperAdminDashboard.module.css';

const SuperAdminDashboard = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('dashboard');
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});
  const { user, logout, token } = useAuth();

  // Mock data for demonstration
  useEffect(() => {
    // Simulate fetching data
    const mockStats = {
      totalUsers: 15427,
      totalAdmins: 23,
      activeReports: 342,
      systemHealth: 98.7,
      predictionsToday: 1245,
      preventedCrimes: 89
    };
    
    const mockNotifications = [
      { id: 1, type: 'warning', message: 'High traffic detected in Gulberg area', time: '2 min ago', urgent: true },
      { id: 2, type: 'info', message: 'New admin registration pending approval', time: '15 min ago', urgent: false },
      { id: 3, type: 'success', message: 'System backup completed successfully', time: '1 hour ago', urgent: false },
      { id: 4, type: 'error', message: 'Database connection issue detected', time: '3 hours ago', urgent: true }
    ];

    setStats(mockStats);
    setNotifications(mockNotifications);

    // Initialize animations
    initializeAnimations();
  }, []);

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

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'dashboard':
        return (
          <>
            <SuperAdminQuickActions />
            <AnalyticsDashboard stats={stats} notifications={notifications} />
            <SystemLogs />
          </>
        );
      case 'register-admin':
        return <AdminRegistrationForm />;
      case 'user-management':
        return <UserManagement token={token} />;
      case 'admin-management':
        return <AdminManagement token={token} />;
      case 'system-settings':
        return <SystemSettings />;
      default:
        return (
          <>
            <SuperAdminQuickActions onAction={(action) => alert(`SuperAdmin Action: ${action}`)} />
            <AnalyticsDashboard stats={stats} notifications={notifications} />
            <SystemLogs />
          </>
        );
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
            <i className="fas fa-crown"></i>
          </div>
          <h3>SuperAdmin</h3>
          <div className={styles.adminBadge}>SUPER</div>
        </div>

        <div className={styles.userProfileSidebar}>
          <div className={styles.avatarContainer}>
            <img 
              src={user?.profile_picture ? `${window.location.origin}/${user.profile_picture}` : `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'Super Admin')}&background=8B4513&color=fff&bold=true`}
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
                <i className="fas fa-chart-network"></i>
                <span>Analytics Dashboard</span>
                <div className={styles.menuPulse}></div>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '100ms' }}>
              <a 
                href="#register-admin"
                className={activeSection === 'register-admin' ? styles.active : ''}
                onClick={() => handleSectionChange('register-admin')}
                aria-current={activeSection === 'register-admin' ? 'page' : undefined}
              >
                <i className="fas fa-user-plus"></i>
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
                <i className="fas fa-users-cog"></i>
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
                <i className="fas fa-user-shield"></i>
                <span>Admin Management</span>
              </a>
            </li>
            <li className={styles.animateIn} style={{ transitionDelay: '400ms' }}>
              <a 
                href="#system-settings"
                className={activeSection === 'system-settings' ? styles.active : ''}
                onClick={() => handleSectionChange('system-settings')}
                aria-current={activeSection === 'system-settings' ? 'page' : undefined}
              >
                <i className="fas fa-sliders-h"></i>
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
              <button className={styles.quickActionBtn}>
                <i className="fas fa-sync-alt"></i>
              </button>
              <button className={styles.quickActionBtn}>
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