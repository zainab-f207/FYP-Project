
import React, { useState } from 'react';
import styles from './SuperAdminQuickActions.module.css';

const SuperAdminQuickActions = () => {
  const [modal, setModal] = useState(null);

  const handleAction = (action) => {
    setModal(action);
  };

  const closeModal = () => setModal(null);

  return (
    <div className={styles.quickActions}>
      <h3>SuperAdmin Quick Actions</h3>
      <div className={styles.actionsGrid}>
        <button className={styles.actionBtn} onClick={() => handleAction('approveAdmin')}>
          <i className="fas fa-user-check"></i>
          Approve Admin
        </button>
        <button className={styles.actionBtn} onClick={() => handleAction('systemBackup')}>
          <i className="fas fa-database"></i>
          System Backup
        </button>
        <button className={styles.actionBtn} onClick={() => handleAction('viewLogs')}>
          <i className="fas fa-file-alt"></i>
          View System Logs
        </button>
        <button className={styles.actionBtn} onClick={() => handleAction('settings')}>
          <i className="fas fa-sliders-h"></i>
          System Settings
        </button>
      </div>

      {/* Modal Dialogs for Actions */}
      {modal === 'approveAdmin' && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h4>Approve Admin</h4>
            <p>Review and approve pending admin registrations.</p>
            <button className={styles.closeBtn} onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
      {modal === 'systemBackup' && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h4>System Backup</h4>
            <p>Backup in progress... All data will be securely saved.</p>
            <button className={styles.closeBtn} onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
      {modal === 'viewLogs' && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h4>System Logs</h4>
            <p>View recent system events and logs for audit and troubleshooting.</p>
            <button className={styles.closeBtn} onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
      {modal === 'settings' && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h4>System Settings</h4>
            <p>Configure system preferences, security, and integrations.</p>
            <button className={styles.closeBtn} onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminQuickActions;
