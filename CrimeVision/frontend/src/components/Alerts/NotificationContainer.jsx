// Notification Container - Manages multiple notifications
import React from 'react';
import NotificationCard from './NotificationCard';
import './NotificationContainer.css';

const NotificationContainer = ({ notifications, onClose }) => {
  console.log('🔔 NotificationContainer rendering with notifications:', notifications);
  
  if (notifications.length === 0) {
    console.log('🔔 NotificationContainer: No notifications to show');
    return null;
  }

  console.log('🔔 NotificationContainer: Rendering', notifications.length, 'notifications');

  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <NotificationCard
          key={notification.id}
          {...notification}
          onClose={onClose}
        />
      ))}
    </div>
  );
};

export default NotificationContainer;
