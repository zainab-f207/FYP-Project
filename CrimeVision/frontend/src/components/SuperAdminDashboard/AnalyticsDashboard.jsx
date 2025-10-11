import React from 'react';
import styles from './SuperAdminDashboard.module.css';

const AnalyticsDashboard = ({ stats, notifications }) => {
  const getIconForType = (type) => {
    switch (type) {
      case 'warning': return 'fas fa-exclamation-triangle';
      case 'info': return 'fas fa-info-circle';
      case 'success': return 'fas fa-check-circle';
      case 'error': return 'fas fa-times-circle';
      default: return 'fas fa-bell';
    }
  };

  const getColorForType = (type) => {
    switch (type) {
      case 'warning': return '#ffc107';
      case 'info': return '#17a2b8';
      case 'success': return '#28a745';
      case 'error': return '#dc3545';
      default: return '#6c757d';
    }
  };

  return (
    <div className={styles.analyticsDashboard}>
      <div className={styles.dashboardHeader}>
        <h2><i className="fas fa-chart-network"></i> Analytics Dashboard</h2>
        <p>Real-time system overview and insights</p>
      </div>

      {/* Stats Cards */}
      <div className={styles.statsGrid}>
        {stats.total_users !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-users"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.total_users.toLocaleString()}</h3>
              <p>Total Users</p>
              <span className={styles.statTrend}>+12% from last month</span>
            </div>
          </div>
        )}

        {stats.total_admins !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-user-shield"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.total_admins}</h3>
              <p>Total Admins</p>
              <span className={styles.statTrend}>+2 this week</span>
            </div>
          </div>
        )}

        {stats.total_crimes !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.total_crimes.toLocaleString()}</h3>
              <p>Total Crimes</p>
              <span className={styles.statTrend}>+8% this month</span>
            </div>
          </div>
        )}

        {stats.recent_crimes !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-clock"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.recent_crimes}</h3>
              <p>Recent Crimes (30 days)</p>
              <span className={styles.statTrend}>Active monitoring</span>
            </div>
          </div>
        )}
      </div>

      {/* Risk Breakdown */}
      {stats.crimes_by_risk && (
        <div className={styles.riskSection}>
          <h3><i className="fas fa-chart-pie"></i> Risk Level Distribution</h3>
          <div className={styles.riskGrid}>
            {Object.entries(stats.crimes_by_risk).map(([level, count]) => (
              <div key={level} className={`${styles.riskCard} ${styles[`risk${level}`]}`}>
                <div className={styles.riskIcon}>
                  <i className={`fas fa-${level === 'High' ? 'exclamation-triangle' : level === 'Medium' ? 'info-circle' : 'check-circle'}`}></i>
                </div>
                <div className={styles.riskContent}>
                  <h4>{level}</h4>
                  <p>{count} incidents</p>
                  <div className={styles.riskBar}>
                    <div 
                      className={styles.riskFill} 
                      style={{ width: `${(count / stats.total_crimes) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Areas */}
      {stats.crimes_by_area && (
        <div className={styles.areaSection}>
          <h3><i className="fas fa-map-marker-alt"></i> High-Risk Areas</h3>
          <div className={styles.areaList}>
            {Object.entries(stats.crimes_by_area).slice(0, 5).map(([area, count]) => (
              <div key={area} className={styles.areaItem}>
                <span className={styles.areaName}>{area}</span>
                <span className={styles.areaCount}>{count} crimes</span>
                <div className={styles.areaBar}>
                  <div 
                    className={styles.areaFill} 
                    style={{ width: `${(count / stats.total_crimes) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notifications */}
      <div className={styles.notificationsSection}>
        <h3><i className="fas fa-bell"></i> Recent Notifications</h3>
        <div className={styles.notificationsList}>
          {notifications.map((notification) => (
            <div key={notification.id} className={`${styles.notificationItem} ${styles[`notification${notification.type}`]}`}>
              <div className={styles.notificationIcon} style={{ color: getColorForType(notification.type) }}>
                <i className={getIconForType(notification.type)}></i>
              </div>
              <div className={styles.notificationContent}>
                <h4>{notification.title || notification.message.split(' ')[0]}</h4>
                <p>{notification.message}</p>
                <span className={styles.notificationTime}>{notification.timestamp ? new Date(notification.timestamp).toLocaleTimeString() : 'Just now'}</span>
              </div>
              {notification.urgent && <div className={styles.urgentBadge}>URGENT</div>}
            </div>
          ))}
          {notifications.length === 0 && (
            <div className={styles.noNotifications}>
              <i className="fas fa-check-circle"></i>
              <p>All systems operational - No active alerts</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
