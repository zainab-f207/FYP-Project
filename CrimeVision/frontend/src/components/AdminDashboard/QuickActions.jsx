import React from 'react';
import styles from './QuickActions.module.css';

const actions = [
  { id: 'addReport', icon: 'fas fa-plus-circle', label: 'Add Crime Report', desc: 'Submit a new report' },
  { id: 'sendAlert', icon: 'fas fa-bell', label: 'Send Alert', desc: 'Broadcast alert to users' },
  { id: 'manageUsers', icon: 'fas fa-users-cog', label: 'Manage Users', desc: 'User roles & access' },
  { id: 'viewLogs', icon: 'fas fa-history', label: 'View Logs', desc: 'System activity logs' },
  { id: 'exportData', icon: 'fas fa-file-export', label: 'Export Data', desc: 'Download reports' },
  { id: 'mapView', icon: 'fas fa-map-marked-alt', label: 'Live Map', desc: 'Real-time crime map' },
];

const QuickActions = ({ onAction }) => {
  return (
    <div className={styles.quickActions}>
      <div className={styles.sectionHeader}>
        <div className={styles.headerLeft}>
          <i className="fas fa-bolt"></i>
          <h3>Quick Actions</h3>
        </div>
        <span className={styles.headerBadge}>
          {actions.length} Available
        </span>
      </div>
      <div className={styles.actionsGrid}>
        {actions.map((action) => (
          <button
            key={action.id}
            className={styles.actionBtn}
            onClick={() => onAction(action.id)}
          >
            <div className={styles.actionIcon}>
              <i className={action.icon}></i>
            </div>
            <div className={styles.actionInfo}>
              <span className={styles.actionLabel}>{action.label}</span>
              <span className={styles.actionDesc}>{action.desc}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
