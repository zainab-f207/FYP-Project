import React, { useState, useEffect } from 'react';
import styles from './UserManagementSummary.module.css';
import apiService from '../../services/apiService_updated';

const roleColors = {
  user: '#1a4f72',
  admin: '#f9a826',
  superadmin: '#ff6b6b',
};

const getInitials = (firstName, lastName, username) => {
  if (firstName && lastName) return `${firstName[0]}${lastName[0]}`.toUpperCase();
  if (firstName) return firstName.slice(0, 2).toUpperCase();
  if (username) return username.slice(0, 2).toUpperCase();
  return '??';
};

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  const d = new Date(dateStr);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
  return d.toLocaleDateString();
};

const UserManagementSummary = ({ token, fullView }) => {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const limit = fullView ? 50 : 5;
        const data = await apiService.getUsers(token, { limit });
        setUsers(data.users || []);
        setTotal(data.total || 0);
      } catch (err) {
        console.error('Failed to fetch users:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, [token, fullView]);

  return (
    <div className={styles.userManagementSummary}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <i className="fas fa-users"></i>
          <h3>{fullView ? 'All Users' : 'User Management'}</h3>
          <span className={styles.countBadge}>{loading ? '...' : `${total} Total`}</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.activeStat}>
            <i className="fas fa-list"></i> Showing {users.length}
          </span>
        </div>
      </div>
      {loading ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>Loading users...</p>
      ) : users.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0' }}>No users found</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.userTable}>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Registered</th>
                <th>Area</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => {
                const roleColor = roleColors[user.role] || '#2d7fb8';
                return (
                  <tr key={user.id}>
                    <td>
                      <div className={styles.userCell}>
                        <div
                          className={styles.userAvatar}
                          style={{ background: `${roleColor}15`, color: roleColor }}
                        >
                          {getInitials(user.firstName, user.lastName, user.username)}
                        </div>
                        <span className={styles.userName}>
                          {user.firstName && user.lastName ? `${user.firstName} ${user.lastName}` : user.username}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span
                        className={styles.roleBadge}
                        style={{ background: `${roleColor}12`, color: roleColor }}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className={styles.lastActive}>{formatDate(user.createdAt)}</td>
                    <td>
                      <span className={styles.statusBadge} style={{ opacity: 0.8 }}>
                        {user.homeArea || user.workArea || 'N/A'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default UserManagementSummary;
