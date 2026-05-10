// // src/components/SuperAdminDashboard/SuperAdminDashboard.js
// import React, { useState, useEffect } from 'react';
// import { useAuth } from '../../contexts/AuthContext_updated';
// import AdminRegistrationForm from '../AdminDashboard/AdminRegistrationForm';
// import UserManagement from './UserManagement';
// import AdminManagement from './AdminManagement';
// import AnalyticsDashboard from './AnalyticsDashboard';
// import SystemSettings from './SystemSettings';
// import ReportingDashboard from '../ReportingDashboard';
// import styles from './SuperAdminDashboard.module.css';
// import apiService from '../../services/apiService_updated';

// const SuperAdminDashboard = () => {
//   const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
//   const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
//   const [activeSection, setActiveSection] = useState('dashboard');
//   const [notifications, setNotifications] = useState([]);
//   const [stats, setStats] = useState({});
//   const { user, logout, token } = useAuth();

//   // Fetch real data from API
//   useEffect(() => {
//     const fetchDashboardData = async () => {
//       try {
//         // Fetch admin stats
//         const statsResponse = await apiService.getAdminStats(token);
//         setStats(statsResponse);

//         // Fetch admin notifications
//         const notificationsResponse = await apiService.getAdminNotifications(token);
//         setNotifications(notificationsResponse.notifications || []);
//       } catch (error) {
//         console.error('Error fetching dashboard data:', error);
//         // Fallback to mock data if API fails
//         const mockStats = {
//           totalUsers: 15427,
//           totalAdmins: 23,
//           activeReports: 342,
//           systemHealth: 98.7,
//           predictionsToday: 1245,
//           preventedCrimes: 89
//         };

//         const mockNotifications = [
//           { id: 1, type: 'warning', message: 'High traffic detected in Gulberg area', time: '2 min ago', urgent: true },
//           { id: 2, type: 'info', message: 'New admin registration pending approval', time: '15 min ago', urgent: false },
//           { id: 3, type: 'success', message: 'System backup completed successfully', time: '1 hour ago', urgent: false },
//           { id: 4, type: 'error', message: 'Database connection issue detected', time: '3 hours ago', urgent: true }
//         ];

//         setStats(mockStats);
//         setNotifications(mockNotifications);
//       }
//     };

//     fetchDashboardData();

//     // Initialize animations
//     initializeAnimations();
//   }, [token]);

//   const initializeAnimations = () => {
//     // GSAP-like animation helper
//     const animateElements = () => {
//       const elements = document.querySelectorAll(`.${styles.animateIn}`);
//       elements.forEach((el, index) => {
//         el.style.opacity = '0';
//         el.style.transform = 'translateY(30px)';

//         setTimeout(() => {
//           el.style.transition = 'all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
//           el.style.opacity = '1';
//           el.style.transform = 'translateY(0)';
//         }, index * 100);
//       });
//     };

//     animateElements();
//   };

//   const toggleSidebar = () => {
//     setSidebarCollapsed(!sidebarCollapsed);
//   };

//   const toggleMobileSidebar = () => {
//     setMobileSidebarOpen(!mobileSidebarOpen);
//   };

//   const handleSectionChange = (section) => {
//     setActiveSection(section);
//     if (window.innerWidth < 576) {
//       setMobileSidebarOpen(false);
//     }

//     // Animate section transition
//     const content = document.querySelector(`.${styles.mainContent}`);
//     if (content) {
//       content.style.opacity = '0';
//       content.style.transform = 'translateX(20px)';

//       setTimeout(() => {
//         content.style.transition = 'all 0.4s ease';
//         content.style.opacity = '1';
//         content.style.transform = 'translateX(0)';
//       }, 200);
//     }
//   };

//   const handleLogout = () => {
//     // Add logout animation
//     const container = document.querySelector(`.${styles.appContainer}`);
//     if (container) {
//       container.style.transform = 'scale(0.9)';
//       container.style.opacity = '0';
//       container.style.transition = 'all 0.3s ease';
//     }

//     setTimeout(() => {
//       logout();
//     }, 300);
//   };

//   const renderActiveSection = () => {
//     switch (activeSection) {
//       case 'dashboard':
//         return <AnalyticsDashboard stats={stats} notifications={notifications} />;
//       case 'register-admin':
//         return <AdminRegistrationForm />;
//       case 'user-management':
//         return <UserManagement token={token} />;
//       case 'admin-management':
//         return <AdminManagement token={token} />;
//       case 'reporting':
//         return <ReportingDashboard />;
//       case 'system-settings':
//         return <SystemSettings />;
//       default:
//         return <AnalyticsDashboard stats={stats} notifications={notifications} />;
//     }
//   };

//   return (
//     <div className={styles.appContainer}>
//       {/* Floating Action Button for Mobile */}
//       <button
//         className={styles.floatingActionBtn}
//         onClick={toggleMobileSidebar}
//       >
//         <i className="fas fa-cogs"></i>
//       </button>

//       {/* Sidebar */}
//       <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
//         <div className={styles.sidebarHeader}>
//           <div className={styles.logo}>
//             <i className="fas fa-crown"></i>
//           </div>
//           <h3>SuperAdmin</h3>
//           <div className={styles.adminBadge}>SUPER</div>
//         </div>

//         <div className={styles.userProfileSidebar}>
//           <div className={styles.avatarContainer}>
//             <img
//               src={user?.profile_picture ? `${window.location.origin}/${user.profile_picture}` : `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'Super Admin')}&background=8B4513&color=fff&bold=true`}
//               alt="Super Admin"
//               className={styles.avatar}
//             />
//             <div className={styles.statusIndicator}></div>
//           </div>
//           <div className={styles.userInfoSidebar}>
//             <h4>{user?.name || 'Super Admin'}</h4>
//             <p>System Administrator</p>
//           </div>
//         </div>

//         <nav className={styles.sidebarNav}>
//           <ul className={styles.sidebarMenu}>
//             <li>
//               <a
//                 href="#dashboard"
//                 className={activeSection === 'dashboard' ? styles.active : ''}
//                 onClick={() => handleSectionChange('dashboard')}
//               >
//                 <i className="fas fa-chart-network"></i>
//                 <span>Analytics Dashboard</span>
//                 <div className={styles.menuPulse}></div>
//               </a>
//             </li>

//             <li>
//               <a
//                 href="#register-admin"
//                 className={activeSection === 'register-admin' ? styles.active : ''}
//                 onClick={() => handleSectionChange('register-admin')}
//               >
//                 <i className="fas fa-user-plus"></i>
//                 <span>Register Admin</span>
//                 <span className={styles.newBadge}>NEW</span>
//               </a>
//             </li>

//             <li>
//               <a
//                 href="#user-management"
//                 className={activeSection === 'user-management' ? styles.active : ''}
//                 onClick={() => handleSectionChange('user-management')}
//               >
//                 <i className="fas fa-users-cog"></i>
//                 <span>User Management</span>
//               </a>
//             </li>

//             <li>
//               <a
//                 href="#admin-management"
//                 className={activeSection === 'admin-management' ? styles.active : ''}
//                 onClick={() => handleSectionChange('admin-management')}
//               >
//                 <i className="fas fa-user-shield"></i>
//                 <span>Admin Management</span>
//               </a>
//             </li>

//             <li>
//               <a
//                 href="#reporting"
//                 className={activeSection === 'reporting' ? styles.active : ''}
//                 onClick={() => handleSectionChange('reporting')}
//               >
//                 <i className="fas fa-chart-bar"></i>
//                 <span>Reporting Dashboard</span>
//               </a>
//             </li>

//             <li>
//               <a
//                 href="#system-settings"
//                 className={activeSection === 'system-settings' ? styles.active : ''}
//                 onClick={() => handleSectionChange('system-settings')}
//               >
//                 <i className="fas fa-sliders-h"></i>
//                 <span>System Settings</span>
//               </a>
//             </li>
//           </ul>
//         </nav>

//         <div className={styles.sidebarFooter}>
//           <div className={styles.systemStatus}>
//             <div className={styles.statusItem}>
//               <span>System Health</span>
//               <div className={styles.statusBar}>
//                 <div
//                   className={styles.statusFill}
//                   style={{width: `${stats.systemHealth || 98}%`}}
//                 ></div>
//               </div>
//               <span className={styles.statusValue}>{stats.systemHealth || 98}%</span>
//             </div>
//           </div>

//           <button
//             className={styles.logoutBtn}
//             onClick={handleLogout}
//           >
//             <i className="fas fa-sign-out-alt"></i>
//             <span>Logout</span>
//           </button>

//           <button className={styles.toggleBtn} onClick={toggleSidebar}>
//             <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
//           </button>
//         </div>
//       </div>

//       {/* Main Content */}
//       <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
//         {/* Top Navigation Bar */}
//         <header className={styles.topNavbar}>
//           <div className={styles.navLeft}>
//             <div className={styles.breadcrumb}>
//               <span className={styles.breadcrumbItem}>SuperAdmin</span>
//               <span className={styles.breadcrumbDivider}>/</span>
//               <span className={styles.breadcrumbActive}>
//                 {activeSection.split('-').map(word =>
//                   word.charAt(0).toUpperCase() + word.slice(1)
//                 ).join(' ')}
//               </span>
//             </div>
//           </div>

//           <div className={styles.navRight}>
//             <div className={styles.notificationBell}>
//               <i className="fas fa-bell"></i>
//               {notifications.filter(n => n.urgent).length > 0 && (
//                 <span className={styles.notificationCount}>
//                   {notifications.filter(n => n.urgent).length}
//                 </span>
//               )}
//             </div>

//             <div className={styles.quickActions}>
//               <button className={styles.quickActionBtn}>
//                 <i className="fas fa-sync-alt"></i>
//               </button>
//               <button className={styles.quickActionBtn}>
//                 <i className="fas fa-question-circle"></i>
//               </button>
//             </div>
//           </div>
//         </header>

//         {/* Dynamic Content Area */}
//         <main className={styles.contentArea}>
//           {renderActiveSection()}
//         </main>
//       </div>
//     </div>
//   );
// };

// export default SuperAdminDashboard;




// src/components/SuperAdminDashboard/SuperAdminDashboard.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../../contexts/AuthContext_updated';
import AdminRegistrationForm from '../AdminDashboard/AdminRegistrationForm';
import UserManagement from './UserManagement';
import AdminManagement from './AdminManagement';
import AnalyticsDashboard from './AnalyticsDashboard_updated';
import SystemSettings from './SystemSettings';
import SuperAdminReportsPanel from './SuperAdminReportsPanel';
import PendingApprovalsPanel from '../AdminDashboard/PendingApprovalsPanel';
import PPCManagement from './PPCManagement';
import SuperAdminPredictionPanel from './SuperAdminPredictionPanel';
import SuperAdminMainDashboard from './SuperAdminMainDashboard';
import CrimeHeatmapPanel from '../AdminDashboard/CrimeHeatmapPanel';
import AuditLogs from './AuditLogs';
import SessionTimer from '../common/SessionTimer';
import { 
  SystemMonitorSVG, 
  SecurityShieldSVG, 
  NetworkTopologySVG, 
  CrimeAnalyticsSVG, 
  DatabaseSVG 
} from './SVGComponents';
import styles from './SuperAdminDashboard.module.css';
import apiService from '../../services/apiService_updated';

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
  const [notifOpen, setNotifOpen] = useState(false);
  const [userCounts, setUserCounts] = useState({ locked_count: 0, unverified_count: 0 });
  const { user, logout, token } = useAuth();
  const contentRef = useRef(null);
  const notifRef = useRef(null);
  const notifPopupRef = useRef(null);

  // Close notif panel when clicking outside. The dropdown is portalled to
  // document.body so it's NOT inside notifRef — we must also check
  // notifPopupRef before deciding the click was outside.
  useEffect(() => {
    const handler = (e) => {
      const inBell = notifRef.current && notifRef.current.contains(e.target);
      const inPopup = notifPopupRef.current && notifPopupRef.current.contains(e.target);
      if (!inBell && !inPopup) setNotifOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Enhanced animations
  const animateSectionTransition = () => {
    const content = contentRef.current;
    if (content) {
      content.style.opacity = '0';
      content.style.transform = 'translateY(20px) scale(0.98)';
      
      setTimeout(() => {
        content.style.transition = 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        content.style.opacity = '1';
        content.style.transform = 'translateY(0) scale(1)';
      }, 150);
    }
  };

  // Fetch real data from API (hoisted for reuse by navbar refresh)
  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsResponse, notificationsResponse, countsResponse] = await Promise.all([
        apiService.getAdminStats(token),
        apiService.getAdminNotifications(token),
        apiService.getUserCounts(token),
      ]);

      setStats(statsResponse);
      setNotifications(Array.isArray(notificationsResponse) ? notificationsResponse : (notificationsResponse.notifications || []));
      setUserCounts({
        locked_count: countsResponse?.locked_count ?? 0,
        unverified_count: countsResponse?.unverified_count ?? 0,
      });
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchDashboardData(); }, [fetchDashboardData]);

  // Refresh user counts every 60s so the sidebar badge stays current
  useEffect(() => {
    if (!token) return undefined;
    const id = setInterval(async () => {
      try {
        const c = await apiService.getUserCounts(token);
        setUserCounts({
          locked_count: c?.locked_count ?? 0,
          unverified_count: c?.unverified_count ?? 0,
        });
      } catch (_e) { /* swallow */ }
    }, 60000);
    return () => clearInterval(id);
  }, [token]);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen(!mobileSidebarOpen);
  };

  const handleSectionChange = (section) => {
    setActiveSection(section);
    if (window.innerWidth < 768) {
      setMobileSidebarOpen(false);
    }
    animateSectionTransition();
  };

  const handleLogout = () => {
    const container = document.querySelector(`.${styles.appContainer}`);
    if (container) {
      container.style.transform = 'scale(0.95)';
      container.style.opacity = '0';
      container.style.transition = 'all 0.4s ease';
    }

    setTimeout(() => {
      logout();
    }, 400);
  };

  const renderActiveSection = () => {
    const sectionProps = {
      stats,
      notifications,
      token
    };

    switch (activeSection) {
      case 'dashboard':
        return <SuperAdminMainDashboard token={token} onNavigate={handleSectionChange} />;
      case 'analytics':
        return <AnalyticsDashboard {...sectionProps} />;
      case 'crime-map':
        return <CrimeHeatmapPanel token={token} />;
      case 'register-admin':
        return <AdminRegistrationForm />;
      case 'user-management':
        return <UserManagement token={token} />;
      case 'admin-management':
        return <AdminManagement token={token} />;
      case 'reporting':
        return <SuperAdminReportsPanel token={token} />;
      case 'system-settings':
        return <SystemSettings />;
      case 'approvals':
        return <PendingApprovalsPanel />;
      case 'law-sections':
        return <PPCManagement token={token} />;
      case 'predictions':
        return <SuperAdminPredictionPanel />;
      case 'audit-logs':
        return <AuditLogs token={token} />;
      default:
        return <SuperAdminMainDashboard token={token} onNavigate={handleSectionChange} />;
    }
  };

  const getSectionTitle = () => {
    const titles = {
      'dashboard': 'Analytics Dashboard',
      'register-admin': 'Register Admin',
      'user-management': 'User Management',
      'admin-management': 'Admin Management',
      'reporting': 'Reporting Dashboard',
      'system-settings': 'System Settings',
      'approvals': 'FIR Approvals',
      'law-sections': 'Law Sections (PPC/ATA/CNSA)',
      'predictions': 'AI Predictions',
      'audit-logs': 'Audit Logs'
    };
    return titles[activeSection] || 'Dashboard';
  };

  return (
    <div className={styles.appContainer}>
      {/* Enhanced Floating Action Button for Mobile */}
      <button
        className={`${styles.floatingActionBtn} ${mobileSidebarOpen ? styles.floatingActionBtnActive : ''}`}
        onClick={toggleMobileSidebar}
      >
        <i className="fas fa-bars"></i>
      </button>

      {/* Enhanced Sidebar */}
      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <i className="fas fa-crown"></i>
            <div className={styles.logoPulse}></div>
          </div>
          <h3>SafeVision</h3>
          <div className={styles.adminBadge}>
            <span>SUPER ADMIN</span>
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
            <div className={styles.avatarGlow}></div>
          </div>
          <div className={styles.userInfoSidebar}>
            <h4>{user?.name || 'Super Admin'}</h4>
            <p>System Administrator</p>
            <div className={styles.userStatus}>Online</div>
          </div>
        </div>

        <nav className={styles.sidebarNav}>
          <ul className={styles.sidebarMenu}>
            {[
              { 
                key: 'dashboard', 
                icon: 'fas fa-shield-halved', 
                label: 'Command Center', 
                pulse: true,
                svgComponent: <CrimeAnalyticsSVG className={styles.menuSvg} color="#6366f1" />
              },
              { 
                key: 'crime-map', 
                icon: 'fas fa-map', 
                label: 'Crime Intelligence Map',
                svgComponent: <NetworkTopologySVG className={styles.menuSvg} color="#06b6d4" />
              },
              { 
                key: 'analytics', 
                icon: 'fas fa-chart-bar', 
                label: 'Analytics',
                svgComponent: <SystemMonitorSVG className={styles.menuSvg} color="#8b5cf6" />
              },
              { 
                key: 'register-admin', 
                icon: 'fas fa-user-plus', 
                label: 'Register Admin', 
                badge: 'NEW',
                svgComponent: <SecurityShieldSVG className={styles.menuSvg} color="#ffc107" />
              },
              {
                key: 'user-management',
                icon: 'fas fa-users-cog',
                label: 'User Management',
                svgComponent: <NetworkTopologySVG className={styles.menuSvg} color="#06b6d4" />,
                countBadges: [
                  userCounts.locked_count > 0 && {
                    key: 'locked',
                    text: `${userCounts.locked_count} locked`,
                    color: '#ef4444',
                    bg: 'rgba(239,68,68,0.18)',
                    title: `${userCounts.locked_count} account(s) locked from failed logins`,
                  },
                  userCounts.unverified_count > 0 && {
                    key: 'unverified',
                    text: `${userCounts.unverified_count} unverified`,
                    color: '#f59e0b',
                    bg: 'rgba(245,158,11,0.18)',
                    title: `${userCounts.unverified_count} unverified account(s)`,
                  },
                ].filter(Boolean),
              },
              { 
                key: 'admin-management', 
                icon: 'fas fa-user-shield', 
                label: 'Admin Management',
                svgComponent: <SecurityShieldSVG className={styles.menuSvg} color="#dc2626" />
              },
              { 
                key: 'reporting', 
                icon: 'fas fa-chart-bar', 
                label: 'Reporting Dashboard',
                svgComponent: <SystemMonitorSVG className={styles.menuSvg} color="#22c55e" />
              },
              { 
                key: 'system-settings', 
                icon: 'fas fa-sliders-h', 
                label: 'System Settings',
                svgComponent: <DatabaseSVG className={styles.menuSvg} color="#8b5cf6" />
              },
              {
                key: 'approvals',
                icon: 'fas fa-gavel',
                label: 'FIR Approvals',
                svgComponent: <SecurityShieldSVG className={styles.menuSvg} color="#f9a826" />
              },
              {
                key: 'law-sections',
                icon: 'fas fa-balance-scale',
                label: 'Law Sections',
                svgComponent: <DatabaseSVG className={styles.menuSvg} color="#00d4ff" />
              },
              {
                key: 'predictions',
                icon: 'fas fa-brain',
                label: 'AI Predictions',
                svgComponent: <CrimeAnalyticsSVG className={styles.menuSvg} color="#a855f7" />
              },
              {
                key: 'audit-logs',
                icon: 'fas fa-clipboard-list',
                label: 'Audit Logs',
                svgComponent: <SecurityShieldSVG className={styles.menuSvg} color="#f4a261" />
              }
            ].map((item) => (
              <li key={item.key}>
                <a
                  href={`#${item.key}`}
                  className={activeSection === item.key ? styles.active : ''}
                  onClick={() => handleSectionChange(item.key)}
                >
                  <div className={styles.menuIconContainer}>
                    <i className={item.icon}></i>
                    {item.svgComponent}
                  </div>
                  <span>{item.label}</span>
                  {item.pulse && <div className={styles.menuPulse}></div>}
                  {item.badge && <span className={styles.newBadge}>{item.badge}</span>}
                  {Array.isArray(item.countBadges) && item.countBadges.length > 0 && !sidebarCollapsed && (
                    <span style={{ display: 'inline-flex', gap: 4, marginLeft: 'auto', flexWrap: 'wrap' }}>
                      {item.countBadges.map((b) => (
                        <span
                          key={b.key}
                          title={b.title}
                          style={{
                            background: b.bg,
                            color: b.color,
                            padding: '2px 8px',
                            borderRadius: 8,
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {b.text}
                        </span>
                      ))}
                    </span>
                  )}
                  <div className={styles.menuHoverEffect}></div>
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.systemStatus}>
            <div className={styles.statusItem}>
              <span>System Health</span>
              <div className={styles.statusBar}>
                <div
                  className={styles.statusFill}
                  style={{ width: `${stats.systemHealth || 98}%` }}
                ></div>
              </div>
              <span className={styles.statusValue}>{stats.systemHealth || 98}%</span>
            </div>
          </div>

          <button
            className={styles.logoutBtn}
            onClick={handleLogout}
          >
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
            <div className={styles.logoutHover}></div>
          </button>

          <button className={styles.toggleBtn} onClick={toggleSidebar}>
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>

      {/* Enhanced Main Content */}
      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        {/* Enhanced Top Navigation Bar */}
        <header className={styles.topNavbar}>
          <div className={styles.navLeft}>
            <div className={styles.breadcrumb}>
              <span className={styles.breadcrumbItem}>SuperAdmin</span>
              <span className={styles.breadcrumbDivider}>/</span>
              <span className={styles.breadcrumbActive}>
                {getSectionTitle()}
              </span>
            </div>
          </div>

          <div className={styles.navRight}>
            <SessionTimer />
            <div className={styles.notificationBell} ref={notifRef} style={{ position: 'relative' }}>
              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, position: 'relative' }}
                onClick={() => setNotifOpen(o => !o)}
              >
                <i className="fas fa-bell" style={{ fontSize: '1.1rem', color: notifOpen ? '#a5b4fc' : '#94a3b8' }}></i>
                {notifications.length > 0 && (
                  <span className={styles.notificationCount}>
                    {notifications.length}
                  </span>
                )}
                <div className={styles.notificationPulse}></div>
              </button>
            </div>

            {/* Notification dropdown is portalled into document.body so the
                navbar's backdrop-filter (which makes the navbar a containing
                block for fixed/absolute descendants) cannot trap it. */}
            {notifOpen && createPortal(
              <div
                ref={notifPopupRef}
                className={styles.notifDropdown}
                onClick={(e) => e.stopPropagation()}
                style={{
                  position: 'fixed',
                  top: '78px',
                  right: '28px',
                  zIndex: 9999,
                  width: '360px',
                  maxWidth: 'calc(100vw - 24px)',
                }}
              >
                <div className={styles.notifHeader}>
                  <span>Notifications</span>
                  <span className={styles.notifHeaderCount}>{notifications.length}</span>
                </div>
                <div className={styles.notifList}>
                  {notifications.length === 0 && (
                    <div className={styles.notifEmpty}>No notifications</div>
                  )}
                  {notifications.slice(0, 8).map((n, i) => {
                    const colorMap = { warning: '#f97316', error: '#dc2626', success: '#22c55e', info: '#06b6d4' };
                    const col = colorMap[n.type] || '#94a3b8';
                    return (
                      <div key={n.id || i} className={styles.notifItem} style={{ '--nc': col }}>
                        <div className={styles.notifDot} style={{ background: col }}></div>
                        <div className={styles.notifBody}>
                          <p className={styles.notifMsg}>{n.message}</p>
                          {n.time && <span className={styles.notifTime}>{n.time}</span>}
                        </div>
                        {n.urgent && <span className={styles.notifUrgent}>!</span>}
                      </div>
                    );
                  })}
                </div>
                <div style={{ display: 'flex', gap: 8, padding: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <button
                    className={styles.notifRefresh}
                    style={{ flex: 1 }}
                    onClick={() => { fetchDashboardData(); }}
                  >
                    <i className="fas fa-rotate"></i> Refresh
                  </button>
                  <button
                    className={styles.notifRefresh}
                    style={{
                      flex: 1,
                      background: 'rgba(244, 162, 97, 0.14)',
                      color: '#f4a261',
                      borderColor: 'rgba(244, 162, 97, 0.3)',
                    }}
                    onClick={() => { setNotifOpen(false); handleSectionChange('audit-logs'); }}
                  >
                    <i className="fas fa-clipboard-list"></i> Audit Logs
                  </button>
                </div>
              </div>,
              document.body
            )}

            <div className={styles.quickActions}>
              <button className={styles.quickActionBtn} onClick={fetchDashboardData} title="Refresh dashboard data">
                <i className="fas fa-sync-alt"></i>
              </button>
              <button className={styles.quickActionBtn} onClick={() => handleSectionChange('system-settings')} title="Settings">
                <i className="fas fa-cog"></i>
              </button>
            </div>

            <div className={styles.userQuickMenu}>
              <div className={styles.userAvatar}>
                <img
                  src={getProfileImageUrl(user?.profile_picture) || `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'Super Admin')}&background=8B4513&color=fff&bold=true`}
                  alt="User"
                />
              </div>
            </div>
          </div>
        </header>

        {/* Dynamic Content Area with Enhanced Animation */}
        <main ref={contentRef} className={styles.contentArea}>
          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.loadingSpinner}></div>
              <p>Loading Dashboard...</p>
            </div>
          ) : (
            renderActiveSection()
          )}
        </main>
      </div>
    </div>
  );
};

export default SuperAdminDashboard;
