// src/components/AdminDashboard/AdminDashboard.js

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import styles from './AdminDashboard.module.css';
import AnalyticsPanel from './AnalyticsPanel';
import QuickActions from './QuickActions';
import NotificationsPanel from './NotificationsPanel';
import RecentActivity from './RecentActivity';
import UserManagementSummary from './UserManagementSummary';

const AdminDashboard = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [recentReports, setRecentReports] = useState([]);
  const [activeItem, setActiveItem] = useState('dashboard');
  const { user, logout } = useAuth();

  useEffect(() => {
    // Simulate fetching recent reports
    const mockReports = [
      { id: 1, type: 'theft', title: 'Car Theft', location: 'Gulberg, Lahore', time: '2 hours ago', risk: 'high' },
      { id: 2, type: 'assault', title: 'Street Fight', location: 'Model Town, Lahore', time: '5 hours ago', risk: 'medium' },
      { id: 3, type: 'burglary', title: 'House Break-in', location: 'Johar Town, Lahore', time: '12 hours ago', risk: 'high' },
      { id: 4, type: 'theft', title: 'Phone Snatching', location: 'Iqbal Town, Lahore', time: '1 day ago', risk: 'medium' },
      { id: 5, type: 'assault', title: 'Robbery', location: 'DHA, Lahore', time: '2 days ago', risk: 'low' }
    ];
    setRecentReports(mockReports);

    // Set up intersection observer for fade-in animations
    const fadeElements = document.querySelectorAll(`.${styles.fadeIn}`);
    
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add(styles.visible);
        }
      });
    }, { threshold: 0.1 });

    fadeElements.forEach(element => {
      element.style.opacity = 0;
      observer.observe(element);
    });

    return () => {
      fadeElements.forEach(element => {
        observer.unobserve(element);
      });
    };
  }, []);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen(!mobileSidebarOpen);
  };

  const handleNavItemClick = (item) => {
    setActiveItem(item);
    if (window.innerWidth < 576) {
      setMobileSidebarOpen(false);
    }
  };

  const handleLogout = () => {
    logout();
    setActiveItem('logout');
  };

  return (
    <div className={styles.appContainer}>
      <button className={styles.mobileToggle} onClick={toggleMobileSidebar}>
        <i className="fas fa-bars"></i>
      </button>

      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <i className="fas fa-shield-alt"></i>
          </div>
            <h3>SafeVision AI</h3>
        </div>
        <ul className={styles.sidebarMenu}>
          <li>
            <a href="#" className={activeItem === 'dashboard' ? styles.active : ''} onClick={() => handleNavItemClick('dashboard')}>
              <i className="fas fa-home"></i>
              <span>Dashboard</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'heatmap' ? styles.active : ''} onClick={() => handleNavItemClick('heatmap')}>
              <i className="fas fa-map-marked-alt"></i>
              <span>Heat Map</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'analytics' ? styles.active : ''} onClick={() => handleNavItemClick('analytics')}>
              <i className="fas fa-chart-bar"></i>
              <span>Analytics</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'users' ? styles.active : ''} onClick={() => handleNavItemClick('users')}>
              <i className="fas fa-users"></i>
              <span>Users</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'reports' ? styles.active : ''} onClick={() => handleNavItemClick('reports')}>
              <i className="fas fa-file-alt"></i>
              <span>Reports</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'alerts' ? styles.active : ''} onClick={() => handleNavItemClick('alerts')}>
              <i className="fas fa-bell"></i>
              <span>Alerts</span>
            </a>
          </li>
          <li>
            <a href="#" className={activeItem === 'settings' ? styles.active : ''} onClick={() => handleNavItemClick('settings')}>
              <i className="fas fa-cog"></i>
              <span>Settings</span>
            </a>
          </li>
        </ul>
        <div className={styles.sidebarFooter}>
          <a href="#" onClick={handleLogout} style={{color: 'white', textDecoration: 'none', display: 'block', marginBottom: '15px'}}>
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
          <button className={styles.toggleBtn} onClick={toggleSidebar}>
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>

      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        <div className={styles.navbar}>
          <div className={styles.searchBar}>
            <i className="fas fa-search"></i>
            <input type="text" placeholder="Search for locations, crimes, users..." />
          </div>
          <div className={styles.userProfile}>
            <img src={user?.profile_picture ? `${window.location.origin}/${user.profile_picture}` : `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'Admin User')}&background=1a4f72&color=fff`} alt="User" />
            <div className={styles.userInfo}>
              <div>{user?.name || 'Admin User'}</div>
              <small className={styles.role}>{user?.role || 'Lahore Police'}</small>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <QuickActions onAction={(action) => alert(`Action: ${action}`)} />

        {/* Analytics Panel */}
        <AnalyticsPanel />

        {/* Notifications Panel */}
        <NotificationsPanel />

        {/* Recent Activity */}
        <RecentActivity />

        {/* User Management Summary */}
        <UserManagementSummary />

        {/* Existing dashboard cards and map can be moved to AnalyticsPanel or kept as needed */}
      </div>
    </div>
  );
};

export default AdminDashboard;