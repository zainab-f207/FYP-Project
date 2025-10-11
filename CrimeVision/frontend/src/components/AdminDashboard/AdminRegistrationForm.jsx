// src/components/SuperAdminDashboard/AdminRegistrationForm.js
import React, { useState } from 'react';
import styles from '../SuperAdminDashboard/SuperAdminDashboard.module.css';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService';

const AdminRegistrationForm = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    department: '',
    permissions: [],
    phone: '',
    address: ''
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const { token } = useAuth();

  const permissionsList = [
    'User Management',
    'Content Moderation',
    'Analytics Access',
    'System Settings',
    'Report Management',
    'API Access'
  ];

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (type === 'checkbox') {
      setFormData(prev => ({
        ...prev,
        permissions: checked 
          ? [...prev.permissions, value]
          : prev.permissions.filter(p => p !== value)
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setSuccess(false);

    // Validate password match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setIsSubmitting(false);
      return;
    }

    try {
      // Prepare data for API (remove confirmPassword)
      const adminData = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        department: formData.department,
        permissions: formData.permissions,
        phone: formData.phone,
        address: formData.address
      };

      const response = await apiService.registerAdmin(adminData, token);

      setSuccess(true);
      
      // Reset form after success
      setTimeout(() => {
        setFormData({
          name: '',
          email: '',
          password: '',
          confirmPassword: '',
          department: '',
          permissions: [],
          phone: '',
          address: ''
        });
        setSuccess(false);
      }, 3000);
    } catch (err) {
      console.error('Admin registration error:', err);
      setError(err.message || 'Failed to register admin. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.registrationForm}>
      <div className={styles.formHeader}>
        <h2>Register New Admin</h2>
        <p>Create administrator accounts with specific permissions</p>
      </div>

      <form onSubmit={handleSubmit} className={styles.adminForm}>
        <div className={styles.formGrid}>
          <div className={styles.formGroup}>
            <label htmlFor="name">Full Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
              placeholder="Enter full name"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              required
              placeholder="admin@crimevision.pk"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="department">Department</label>
            <select
              id="department"
              name="department"
              value={formData.department}
              onChange={handleInputChange}
              required
            >
              <option value="">Select Department</option>
              <option value="operations">Operations</option>
              <option value="analytics">Analytics</option>
              <option value="security">Security</option>
              <option value="support">Customer Support</option>
            </select>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="phone">Phone Number</label>
            <input
              type="tel"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleInputChange}
              placeholder="+92 XXX XXXXXXX"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              placeholder="Create strong password"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              required
              placeholder="Confirm password"
            />
          </div>
        </div>

        <div className={styles.permissionsSection}>
          <h3>Admin Permissions</h3>
          <div className={styles.permissionsGrid}>
            {permissionsList.map(permission => (
              <label key={permission} className={styles.permissionCheckbox}>
                <input
                  type="checkbox"
                  value={permission}
                  checked={formData.permissions.includes(permission)}
                  onChange={handleInputChange}
                />
                <span className={styles.checkmark}></span>
                {permission}
              </label>
            ))}
          </div>
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="address">Address (Optional)</label>
          <textarea
            id="address"
            name="address"
            value={formData.address}
            onChange={handleInputChange}
            placeholder="Enter address"
            rows="3"
          />
        </div>

        <div className={styles.formActions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Creating Admin...
              </>
            ) : (
              <>
                <i className="fas fa-user-plus"></i>
                Register Admin
              </>
            )}
          </button>
        </div>

        {success && (
          <div className={styles.successMessage}>
            <i className="fas fa-check-circle"></i>
            Admin registered successfully! Confirmation email sent.
          </div>
        )}
      </form>
    </div>
  );
};

export default AdminRegistrationForm;