import React from 'react';
import styles from './RecentActivity.module.css';

const activities = [
  { id: 1, user: 'Inspector Ali', action: 'Added new crime report', time: '10 min ago' },
  { id: 2, user: 'Admin Zainab', action: 'Sent alert to Gulberg', time: '1 hour ago' },
  { id: 3, user: 'Officer Sara', action: 'Updated user permissions', time: '3 hours ago' },
  { id: 4, user: 'Admin Zainab', action: 'Reviewed system logs', time: 'Yesterday' },
];

const RecentActivity = () => {
  return (
    <div className={styles.recentActivity}>
      <h3>Recent Activity</h3>
      <ul className={styles.activityList}>
        {activities.map(act => (
          <li key={act.id} className={styles.activityItem}>
            <div className={styles.user}>{act.user}</div>
            <div className={styles.action}>{act.action}</div>
            <div className={styles.time}>{act.time}</div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RecentActivity;
