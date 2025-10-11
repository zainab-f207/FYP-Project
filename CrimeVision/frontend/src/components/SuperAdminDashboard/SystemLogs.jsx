import React from 'react';
import styles from './SystemLogs.module.css';

const logs = [
  { id: 1, event: 'Backup completed', time: 'Today 02:00 AM', status: 'success' },
  { id: 2, event: 'Admin login', time: 'Today 09:15 AM', status: 'info' },
  { id: 3, event: 'Database error', time: 'Yesterday 11:30 PM', status: 'error' },
  { id: 4, event: 'User deleted', time: 'Yesterday 05:20 PM', status: 'warning' },
];

const SystemLogs = () => (
  <div className={styles.systemLogs}>
    <h3>System Logs</h3>
    <ul className={styles.logList}>
      {logs.map(log => (
        <li key={log.id} className={`${styles.logItem} ${styles[log.status]}`}>
          <span className={styles.event}>{log.event}</span>
          <span className={styles.time}>{log.time}</span>
        </li>
      ))}
    </ul>
  </div>
);

export default SystemLogs;
