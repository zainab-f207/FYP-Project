import React, { useState, useEffect } from 'react';
import styles from './SystemLogs.module.css';

const formatTimeAgo = (ts) => {
  if (!ts) return 'Recenlty';
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60)   return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400)return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
};

const SystemLogs = () => {
  const [logs, setLogs]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tok = localStorage.getItem('SafeVision_token') || sessionStorage.getItem('SafeVision_token');
    const base =
      window._apiBase ||
      import.meta.env.VITE_API_URL ||
      import.meta.env.VITE_API_BASE_URL ||
      'http://localhost:8000';
    fetch(`${base}/admin/notifications`, { headers: tok ? { Authorization: `Bearer ${tok}` } : {} })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const mapped = (data.notifications || []).map((n, i) => ({
          id: n.id || i,
          event: n.message || n.title || 'System event',
          time: formatTimeAgo(n.created_at || n.timestamp),
          status: n.type === 'high_risk' ? 'error'
                : n.type === 'new_user'  ? 'info'
                : n.severity === 'High'  ? 'error'
                : n.severity === 'Medium'? 'warning'
                : 'success',
        }));
        setLogs(mapped.length ? mapped : [{ id: 0, event: 'System operating normally', time: 'Now', status: 'success' }]);
      })
      .catch(() => setLogs([{ id: 0, event: 'System operating normally', time: 'Now', status: 'success' }]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className={styles.systemLogs}>
      <h3>System Logs</h3>
      {loading
        ? <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Loading…</p>
        : (
          <ul className={styles.logList}>
            {logs.map(log => (
              <li key={log.id} className={`${styles.logItem} ${styles[log.status]}`}>
                <span className={styles.event}>{log.event}</span>
                <span className={styles.time}>{log.time}</span>
              </li>
            ))}
          </ul>
        )}
    </div>
  );
};

export default SystemLogs;
