import React, { useState, useEffect } from 'react';
import styles from './NotificationsPanel.module.css';
import apiService from '../../services/apiService_updated';

const iconMap = {
  alert: 'fas fa-exclamation-triangle',
  warning: 'fas fa-exclamation-triangle',
  report: 'fas fa-file-alt',
  info: 'fas fa-info-circle',
  system: 'fas fa-cog',
  success: 'fas fa-check-circle',
};

const NotificationsPanel = ({ token, fullView }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [readIds, setReadIds] = useState(new Set());

  useEffect(() => {
    if (!token) return;
    const fetchNotifications = async () => {
      try {
        setLoading(true);
        const data = await apiService.getAdminNotifications(token);
        const items = Array.isArray(data) ? data : (data?.notifications || []);
        setNotifications(items);
      } catch (err) {
        console.error('Failed to fetch notifications:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchNotifications();
  }, [token]);

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const d = new Date(timestamp);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return `${Math.floor(diff / 86400)} days ago`;
  };

  const markAllRead = () => {
    setReadIds(new Set(notifications.map(n => n.id)));
  };

  const displayed = fullView ? notifications : notifications.slice(0, 5);
  const unreadCount = notifications.filter(n => !readIds.has(n.id)).length;

  return (
    <div className={styles.notificationsPanel}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <i className="fas fa-bell"></i>
          <h3>{fullView ? 'All Notifications' : 'Notifications'}</h3>
          {unreadCount > 0 && (
            <span className={styles.unreadBadge}>{unreadCount}</span>
          )}
        </div>
        <a href="#" className={styles.markAllRead} onClick={(e) => { e.preventDefault(); markAllRead(); }}>Mark all read</a>
      </div>
      {loading ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>Loading notifications...</p>
      ) : displayed.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>No notifications</p>
      ) : (
        <ul className={styles.notificationsList}>
          {displayed.map(note => {
            const type = note.type || 'info';
            const isUnread = !readIds.has(note.id);
            const detailEntries = note.details && typeof note.details === 'object'
              ? Object.entries(note.details).filter(([, value]) => value !== null && value !== undefined && value !== '')
              : [];
            return (
              <li key={note.id} className={`${styles.notificationItem} ${styles[type] || ''} ${isUnread ? styles.unread : ''}`}>
                <div className={styles.icon}>
                  <i className={iconMap[type] || 'fas fa-bell'}></i>
                </div>
                <div className={styles.content}>
                  <div className={styles.message}>{note.title || note.message}</div>
                  {note.message && note.title && <div className={styles.time}>{note.message}</div>}
                  {detailEntries.length > 0 && (
                    <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {detailEntries.map(([key, value]) => (
                        <span key={key} style={{ fontSize: 11, color: '#cbd5e1', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 999, padding: '3px 8px' }}>
                          {key.replace(/_/g, ' ')}: {String(value)}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className={styles.time}>
                    <i className="far fa-clock"></i> {formatTime(note.timestamp || note.time)}
                  </div>
                </div>
                {isUnread && <div className={styles.unreadDot}></div>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default NotificationsPanel;
