// src/components/UserDashboard/BrowserPushSetup.jsx
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService, { API_BASE_URL } from '../../services/apiService_updated';
import styles from './BrowserPushSetup.module.css';

const BrowserPushSetup = ({ onClose, onSuccess }) => {
  const { user, token, updateUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const setupBrowserPush = async () => {
    try {
      setLoading(true);
      setError(null);

      // Request notification permission
      const permission = await Notification.requestPermission();
      
      if (permission !== 'granted') {
        throw new Error('Notification permission denied');
      }

      // Register service worker
      if (!('serviceWorker' in navigator)) {
        throw new Error('Service workers not supported');
      }

      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });

      // Fetch VAPID public key from server and subscribe
  const vapidResp = await fetch(`${API_BASE_URL}/api/alerts/vapid-public-key`);
      if (!vapidResp.ok) {
        throw new Error('Failed to fetch VAPID public key from server');
      }
      const { publicKey: vapidPublicKey } = await vapidResp.json();
      if (!vapidPublicKey) {
        throw new Error('VAPID public key not configured on server');
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      });

      // Send subscription to server
      await apiService.subscribeToBrowserNotifications(token, subscription);

      // Update user profile to enable browser notifications
      const updateData = {
        browser_notifications_enabled: true
      };
      
      await apiService.updateProfile(updateData, token);
      
      // Refresh user data
      const updatedUser = await apiService.getCurrentUser(token);
      updateUser(updatedUser);

      onSuccess?.();
      onClose?.();
      
    } catch (err) {
      console.error('Browser push setup error:', err);
      setError(err.message || 'Failed to setup browser notifications');
    } finally {
      setLoading(false);
    }
  };

  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  };

  return (
    <div className={styles.setupContainer}>
      <h3>Enable Browser Notifications</h3>
      <p>Get instant safety alerts directly in your browser</p>
      
      <div className={styles.features}>
        <div className={styles.feature}>
          <i className="fas fa-bell"></i>
          <span>Real-time safety alerts</span>
        </div>
        <div className={styles.feature}>
          <i className="fas fa-desktop"></i>
          <span>Works even when tab is closed</span>
        </div>
        <div className={styles.feature}>
          <i className="fas fa-shield-alt"></i>
          <span>Immediate high-risk zone warnings</span>
        </div>
      </div>

      {error && (
        <div className={styles.error}>
          <i className="fas fa-exclamation-triangle"></i>
          {error}
        </div>
      )}

      <div className={styles.actions}>
        <button
          onClick={setupBrowserPush}
          disabled={loading}
          className={styles.primaryButton}
        >
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin"></i> Setting up...
            </>
          ) : (
            <>
              <i className="fas fa-bell"></i> Enable Notifications
            </>
          )}
        </button>
        
        <button
          onClick={onClose}
          disabled={loading}
          className={styles.secondaryButton}
        >
          Maybe Later
        </button>
      </div>
    </div>
  );
};

export default BrowserPushSetup;
