import React from 'react';
import styles from './NotificationsPanel.module.css';

const notifications = [
  { id: 1, type: 'alert', message: 'New high-risk area detected: Gulberg', time: '5 min ago' },
  { id: 2, type: 'report', message: 'Crime report submitted by user', time: '30 min ago' },
  { id: 3, type: 'system', message: 'System update scheduled for tonight', time: '2 hours ago' },
  { id: 4, type: 'alert', message: 'Alert sent to all users in DHA', time: '1 day ago' },
];

const NotificationsPanel = () => {
  return (
    <div className={styles.notificationsPanel}>
      <h3>Notifications</h3>
      <ul className={styles.notificationsList}>
        {notifications.map(note => (
          <li key={note.id} className={`${styles.notificationItem} ${styles[note.type]}`}>
            <div className={styles.icon}>
              <i className={`fas fa-${note.type === 'alert' ? 'bell' : note.type === 'report' ? 'file-alt' : 'cog'}`}></i>
            </div>
            <div className={styles.message}>{note.message}</div>
            <div className={styles.time}>{note.time}</div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default NotificationsPanel;
