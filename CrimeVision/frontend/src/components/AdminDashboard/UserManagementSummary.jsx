import React from 'react';
import styles from './UserManagementSummary.module.css';

const users = [
  { id: 1, name: 'Inspector Ali', role: 'Inspector', status: 'Active' },
  { id: 2, name: 'Admin Zainab', role: 'Admin', status: 'Active' },
  { id: 3, name: 'Officer Sara', role: 'Officer', status: 'Inactive' },
  { id: 4, name: 'Officer Bilal', role: 'Officer', status: 'Active' },
];

const UserManagementSummary = () => {
  return (
    <div className={styles.userManagementSummary}>
      <h3>User Management</h3>
      <table className={styles.userTable}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.id} className={styles[user.status.toLowerCase()]}> 
              <td>{user.name}</td>
              <td>{user.role}</td>
              <td>{user.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UserManagementSummary;
