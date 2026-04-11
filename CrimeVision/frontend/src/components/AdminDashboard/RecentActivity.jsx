import React, { useState, useEffect } from 'react';
import styles from './RecentActivity.module.css';
import apiService from '../../services/apiService_updated';

const typeColors = {
  report: '#1a4f72',
  crime: '#1a4f72',
  alert: '#ff6b6b',
  user: '#1dd1a1',
  login: '#1dd1a1',
  system: '#f9a826',
};

const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
  if (diff < 172800) return 'Yesterday';
  return `${Math.floor(diff / 86400)} days ago`;
};

const RecentActivity = ({ token, fullView }) => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchActivity = async () => {
      try {
        setLoading(true);
        // Fetch recent crimes as activity items
        const crimes = await apiService.get('/api/crimes?limit=10', token);
        const items = (Array.isArray(crimes) ? crimes : []).slice(0, fullView ? 20 : 5).map((crime, i) => ({
          id: crime.id || i,
          user: crime.reported_by || crime.username || 'System',
          action: `${crime.crime_type || 'Crime'} reported in ${crime.area || 'Unknown area'}`,
          time: crime.crime_date || crime.created_at,
          type: 'crime',
        }));
        setActivities(items);
      } catch (err) {
        console.error('Failed to fetch recent activity:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchActivity();
  }, [token, fullView]);

  return (
    <div className={styles.recentActivity}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <i className="fas fa-history"></i>
          <h3>{fullView ? 'All Recent Activity' : 'Recent Activity'}</h3>
        </div>
        {!fullView && (
          <span className={styles.viewAll} style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {activities.length} items
          </span>
        )}
      </div>
      {loading ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>Loading activity...</p>
      ) : activities.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>No recent activity</p>
      ) : (
        <ul className={styles.activityList}>
          {activities.map(act => (
            <li key={act.id} className={styles.activityItem}>
              <div className={styles.timeline}>
                <div
                  className={styles.avatar}
                  style={{ background: `${typeColors[act.type] || '#2d7fb8'}15`, color: typeColors[act.type] || '#2d7fb8' }}
                >
                  {getInitials(act.user)}
                </div>
                <div className={styles.timelineLine}></div>
              </div>
              <div className={styles.activityContent}>
                <div className={styles.activityTop}>
                  <span className={styles.user}>{act.user}</span>
                  <span className={styles.time}>
                    <i className="far fa-clock"></i> {formatTime(act.time)}
                  </span>
                </div>
                <div className={styles.action}>{act.action}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default RecentActivity;
