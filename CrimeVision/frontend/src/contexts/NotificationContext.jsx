// Professional Notification Context
import React, { createContext, useContext, useState, useCallback } from 'react';
import NotificationContainer from '../components/Alerts/NotificationContainer';

// Create context
const NotificationContext = createContext();

// Hook for consuming context
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};

// Provider component
export const NotificationProvider = ({ children }) => {
  // State to hold notifications
  const [notifications, setNotifications] = useState([]);

  // Remove notification (defined first to avoid temporal dead zone)
  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((notif) => notif.id !== id));
  }, []);

  // Show a new notification
  const showNotification = useCallback(
    ({
      type = 'info',
      title,
      message,
      duration = 5000,
      action = null,
      icon = null,
    }) => {
      const id = Date.now() + Math.random();
      const notification = {
        id,
        type,
        title,
        message,
        duration,
        action,
        icon,
        timestamp: new Date(),
      };
      setNotifications((prev) => [...prev, notification]);

      // Auto‑dismiss after duration
      if (duration > 0) {
        setTimeout(() => {
          removeNotification(id);
        }, duration);
      }
      return id;
    },
    [removeNotification]
  );

  // Clear all notifications
  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  // Convenience wrappers
  const success = useCallback((title, message, options = {}) => {
    return showNotification({ type: 'success', title, message, ...options });
  }, [showNotification]);

  const error = useCallback((title, message, options = {}) => {
    return showNotification({ type: 'error', title, message, ...options });
  }, [showNotification]);

  const warning = useCallback((title, message, options = {}) => {
    return showNotification({ type: 'warning', title, message, ...options });
  }, [showNotification]);

  const info = useCallback((title, message, options = {}) => {
    return showNotification({ type: 'info', title, message, ...options });
  }, [showNotification]);

  // Value provided to context consumers
  const value = {
    notifications,
    showNotification,
    removeNotification,
    clearAll,
    success,
    error,
    warning,
    info,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationContainer notifications={notifications} onClose={removeNotification} />
    </NotificationContext.Provider>
  );
};
