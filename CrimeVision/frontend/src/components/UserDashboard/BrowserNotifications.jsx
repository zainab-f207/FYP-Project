// src/components/UserDashboard/BrowserNotifications.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import styles from './BrowserNotifications.module.css';

const BrowserNotifications = () => {
  const { user, token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [ws, setWs] = useState(null);

  // Request browser notification permission
  const requestNotificationPermission = useCallback(async () => {
    if (!("Notification" in window)) {
      console.log("This browser does not support notifications");
      return false;
    }

    if (Notification.permission === "granted") {
      return true;
    } else if (Notification.permission !== "denied") {
      const permission = await Notification.requestPermission();
      return permission === "granted";
    }
    return false;
  }, []);

  // Show browser notification
  const showBrowserNotification = useCallback((title, body, data = {}) => {
    if (Notification.permission === "granted") {
      const notification = new Notification(title, {
        body: body,
        icon: '/warning-icon.png',
        badge: '/badge-icon.png',
        tag: 'SafeVision-alert',
        data: data
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
        
        // Handle notification click (e.g., open map to location)
        if (data.latitude && data.longitude) {
          const mapUrl = `https://www.google.com/maps?q=${data.latitude},${data.longitude}`;
          window.open(mapUrl, '_blank');
        }
      };

      setTimeout(() => notification.close(), 10000); // Auto-close after 10 seconds
    }
  }, []);

  // Load notifications from API
  const loadNotifications = useCallback(async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const response = await apiService.getBrowserNotifications(token);
      
      // FIX: Ensure notifications have proper data structure
      const processedNotifications = (response.notifications || []).map(notification => ({
        ...notification,
        // Ensure data object exists with safe defaults
        data: notification.notification_data || notification.data || {},
        // Ensure safety_score has a default value
        safety_score: (notification.notification_data?.safety_score || 
                      notification.data?.safety_score || 
                      notification.safety_score || 50),
        // Ensure risk_level has a default value
        risk_level: (notification.notification_data?.risk_level ||
                    notification.data?.risk_level ||
                    notification.risk_level || 'Unknown')
      }));
      
      setNotifications(processedNotifications);
      setUnreadCount(processedNotifications.filter(n => !n.is_read).length || 0);
    } catch (error) {
      console.error('Error loading notifications:', error);
      // Set empty array on error to prevent crashes
      setNotifications([]);
      setUnreadCount(0);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Mark notification as read
  const markAsRead = async (notificationId) => {
    try {
      await apiService.markBrowserNotificationRead(token, notificationId);
      setNotifications(prev => 
        prev.map(n => 
          n.id === notificationId ? { ...n, is_read: true } : n
        )
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  // Mark all as read
  const markAllAsRead = async () => {
    try {
      await apiService.markAllBrowserNotificationsRead(token);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  };

  // Setup WebSocket connection for real-time notifications
  useEffect(() => {
    if (!user?.id) return;

    const setupWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/notifications/${user.id}`;
      
      const websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log('WebSocket connected for notifications');
      };
      
      websocket.onmessage = (event) => {
        try {
          const notification = JSON.parse(event.data);
          
          // FIX: Ensure incoming notification has proper data structure
          const safeNotification = {
            ...notification,
            data: notification.data || {},
            safety_score: notification.data?.safety_score || notification.safety_score || 50,
            risk_level: notification.data?.risk_level || notification.risk_level || 'Unknown'
          };
          
          // Show browser notification
          if (Notification.permission === 'granted') {
            showBrowserNotification(
              safeNotification.title, 
              safeNotification.message, 
              safeNotification.data
            );
          }
          
          // Add to local state with safe structure
          setNotifications(prev => [safeNotification, ...prev]);
          setUnreadCount(prev => prev + 1);
          
          // Reload notifications to get latest from server
          loadNotifications();
        } catch (parseError) {
          console.error('Error parsing WebSocket message:', parseError);
        }
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(setupWebSocket, 5000);
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      setWs(websocket);
    };

    setupWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [user?.id, showBrowserNotification, loadNotifications]);

  // Load notifications on component mount
  useEffect(() => {
    loadNotifications();
    requestNotificationPermission();
  }, [loadNotifications, requestNotificationPermission]);

  // Poll for new notifications (fallback if WebSocket fails)
  useEffect(() => {
    const interval = setInterval(() => {
      loadNotifications();
    }, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [loadNotifications]);

  // FIX: Safe rendering of notification data
  const renderNotificationItem = (notification, index) => {
    // Safe data access with defaults
    const safeData = notification.data || {};
    const safetyScore = safeData.safety_score || notification.safety_score || 50;
    const riskLevel = safeData.risk_level || notification.risk_level || 'Unknown';
    const address = safeData.address || notification.address || 'Unknown location';
    
    return (
      <div 
        key={notification.id || `notification-${index}`} 
        className={`${styles.notificationItem} ${!notification.is_read ? styles.unread : ''}`}
        onClick={() => notification.id && markAsRead(notification.id)}
      >
        <div className={styles.notificationIcon}>
          {notification.alert_type === 'high_risk_zone' && (
            <i className="fas fa-exclamation-triangle"></i>
          )}
          {notification.alert_type === 'safe_area' && (
            <i className="fas fa-check-circle"></i>
          )}
          {!['high_risk_zone', 'safe_area'].includes(notification.alert_type) && (
            <i className="fas fa-info-circle"></i>
          )}
        </div>
        
        <div className={styles.notificationContent}>
          <h4>{notification.title || 'Safety Alert'}</h4>
          <p>{notification.message || notification.body || 'No message provided'}</p>
          <div className={styles.notificationMeta}>
            <span className={styles.safetyScore}>
              Safety: {safetyScore}%
            </span>
            <span className={styles.riskLevel}>
              Risk: {riskLevel}
            </span>
            <span className={styles.timestamp}>
              {notification.created_at ? new Date(notification.created_at).toLocaleTimeString() : 'Recently'}
            </span>
          </div>
        </div>
        
        {!notification.is_read && notification.id && (
          <div className={styles.unreadIndicator}></div>
        )}
      </div>
    );
  };

  return (
    <div className={styles.notificationsContainer}>
      <div className={styles.notificationsHeader}>
        <h3>Safety Alerts</h3>
        {unreadCount > 0 && (
          <button 
            className={styles.markAllReadBtn}
            onClick={markAllAsRead}
            disabled={loading}
          >
            Mark all as read
          </button>
        )}
      </div>

      <div className={styles.notificationsList}>
        {loading ? (
          <div className={styles.loading}>
            <i className="fas fa-spinner fa-spin"></i>
            Loading notifications...
          </div>
        ) : notifications.length === 0 ? (
          <div className={styles.emptyState}>
            <i className="fas fa-bell-slash"></i>
            <p>No notifications</p>
            <small>New safety alerts will appear here</small>
          </div>
        ) : (
          notifications.map(renderNotificationItem)
        )}
      </div>

      {unreadCount > 0 && (
        <div className={styles.unreadBadge}>
          {unreadCount} unread
        </div>
      )}
    </div>
  );
};

export default BrowserNotifications;
