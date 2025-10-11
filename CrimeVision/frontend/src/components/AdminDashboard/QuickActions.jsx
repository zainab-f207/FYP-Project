import React from 'react';
import styles from './QuickActions.module.css';

const QuickActions = ({ onAction }) => {
  return (
    <div className={styles.quickActions}>
      <h3>Quick Actions</h3>
      <div className={styles.actionsGrid}>
        <button className={styles.actionBtn} onClick={() => onAction('addReport')}>
          <i className="fas fa-plus-circle"></i>
          Add Crime Report
        </button>
        <button className={styles.actionBtn} onClick={() => onAction('sendAlert')}>
          <i className="fas fa-bell"></i>
          Send Alert
        </button>
        <button className={styles.actionBtn} onClick={() => onAction('manageUsers')}>
          <i className="fas fa-users-cog"></i>
          Manage Users
        </button>
        <button className={styles.actionBtn} onClick={() => onAction('viewLogs')}>
          <i className="fas fa-history"></i>
          View Logs
        </button>
      </div>
    </div>
  );
};

export default QuickActions;
