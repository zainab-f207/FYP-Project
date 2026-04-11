import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService, { API_BASE_URL } from '../../services/apiService_updated';
import QRCode from 'qrcode';
import styles from '../UserDashboard/ProfileModal.module.css';
import './AlertsComingSoon.css';

const getProfileImageUrl = (profilePicture) => {
  if (!profilePicture) return null;
  if (profilePicture.startsWith('http://') || profilePicture.startsWith('https://')) {
    return profilePicture;
  }
  return `${window.location.origin}/${profilePicture}`;
};

const ProfileModal = ({ isOpen, onClose }) => {
  const { user, token, updateUser } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    home_area: '',
    work_area: '',
    alert_radius: 5,
    phone_number: '',
    browser_notifications_enabled: false,
    email_alerts_enabled: true,
    monitor_live_location: false,
    weekly_reports_enabled: true,
    incident_alerts_enabled: true,
    live_alerts_enabled: true
  });

  const [profilePhoto, setProfilePhoto] = useState(null);
  const [previewPhoto, setPreviewPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [qrCodeUrl, setQrCodeUrl] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorLoading, setTwoFactorLoading] = useState(false);
  const [alertStatus, setAlertStatus] = useState(null);
  const [browserPushSupported, setBrowserPushSupported] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(()=>{
    setIsVisible(true);
  },[]);
  // Utility function for VAPID key conversion
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

  // Enhanced browser push support detection
  useEffect(() => {
    const checkBrowserSupport = () => {
      const supports = {
        serviceWorker: 'serviceWorker' in navigator,
        pushManager: 'PushManager' in window,
        notification: 'Notification' in window,
        isSecureContext: window.isSecureContext,
        userAgent: navigator.userAgent
      };

      console.log('🔍 Browser capabilities check:', supports);

      // More lenient check for Chrome and other modern browsers
      const isSupported = 
        'serviceWorker' in navigator && 
        'PushManager' in window &&
        'Notification' in window;

      setBrowserPushSupported(isSupported);

      if (!isSupported) {
        console.warn('❌ Browser push not supported. Details:', supports);
      } else {
        console.log('✅ Browser push supported');
      }
    };

    checkBrowserSupport();
  }, []);

  // Debug browser capabilities
  const debugBrowserCapabilities = () => {
    const capabilities = {
      // Basic API support
      serviceWorker: 'serviceWorker' in navigator,
      pushManager: 'PushManager' in window,
      notification: 'Notification' in window,
      
      // Browser details
      userAgent: navigator.userAgent,
      isChrome: /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor),
      isFirefox: /Firefox/.test(navigator.userAgent),
      isEdge: /Edg/.test(navigator.userAgent),
      isSafari: /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent),
      
      // Context
      isSecureContext: window.isSecureContext,
      protocol: window.location.protocol,
      host: window.location.host,
      
      // Notification permissions
      permission: Notification.permission
    };

    console.log('🛠️ Browser Capabilities Debug:', capabilities);
    
    // Check if it's actually Chrome
    if (/Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor)) {
      console.log('✅ This is definitely Chrome browser');
    } else {
      console.log('❌ This might not be Chrome, or Chrome version is outdated');
    }

    return capabilities;
  };

  // Add this function to test Chrome-specific issues
const testChromeSpecificIssures = () => {
  console.log('🧪 Testing Chrome-specific issues...');
  
  // Check for common Chrome problems
  const issues = [];
  
  // 1. Check if it's actually Chrome
  const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
  if (!isChrome) {
    issues.push('Not actually Chrome browser');
  }
  
  // 2. Check Chrome version
  const chromeVersion = navigator.userAgent.match(/Chrome\/([0-9]+)/);
  if (chromeVersion) {
    const version = parseInt(chromeVersion[1]);
    console.log(`Chrome version: ${version}`);
    if (version < 50) {
      issues.push(`Chrome version ${version} is too old. Push requires Chrome 50+`);
    }
  }
  
  // 3. Check if running in incognito mode (some APIs are restricted)
  if (navigator.userAgent.includes('Incognito')) {
    issues.push('Running in incognito mode - some APIs may be restricted');
  }
  
  // 4. Check for enterprise policies that might disable push
  if (navigator.userAgent.includes('Enterprise')) {
    issues.push('Enterprise Chrome detected - push might be disabled by policy');
  }
  
  if (issues.length > 0) {
    console.warn('❌ Chrome issues found:', issues);
  } else {
    console.log('✅ No Chrome-specific issues detected');
  }
  
  return issues;
};

// Call this when debugging
useEffect(() => {
  testChromeSpecificIssures();
}, []);


  // Load user data
  useEffect(() => {
    if (user) {
      console.log('👤 User data loaded:', {
        browser_notifications_enabled: user.browser_notifications_enabled,
        fullUser: user
      });
      
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        home_area: user.home_area || '',
        work_area: user.work_area || '',
        alert_radius: user.alert_radius || 5,
        phone_number: user.phone_number || '',
        browser_notifications_enabled: user.browser_notifications_enabled || false,
        email_alerts_enabled: user.email_alerts_enabled !== undefined ? user.email_alerts_enabled : true,
        monitor_live_location: user.monitor_live_location || false,
        weekly_reports_enabled: user.weekly_reports_enabled !== undefined ? user.weekly_reports_enabled : true,
        incident_alerts_enabled: user.incident_alerts_enabled !== undefined ? user.incident_alerts_enabled : true,
        live_alerts_enabled: user.live_alerts_enabled !== undefined ? user.live_alerts_enabled : true
      });

      setPreviewPhoto(getProfileImageUrl(user.profile_picture));
      
      // Load alert status
      loadAlertStatus();
    }
  }, [user, token]);

  useEffect(() => {
    if (twoFactorSetup && twoFactorSetup.uri) {
      QRCode.toDataURL(twoFactorSetup.uri)
        .then(url => setQrCodeUrl(url))
        .catch(err => {
          console.error('Error generating QR code:', err);
          setError('Failed to generate QR code');
        });
    }
  }, [twoFactorSetup]);

  const loadAlertStatus = async () => {
    try {
      const status = await apiService.getAlertStatus(token);
      setAlertStatus(status);
    } catch (error) {
      console.error('Error loading alert status:', error);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? checked : value 
    }));
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProfilePhoto(file);
      setPreviewPhoto(URL.createObjectURL(file));
    }
  };

  const handleSetup2FA = async () => {
    setTwoFactorLoading(true);
    setError(null);
    setQrCodeUrl(null);
    try {
      const result = await apiService.setup2FA(token);
      setTwoFactorSetup(result);
    } catch (err) {
      setError(err.message || 'Failed to setup 2FA');
    } finally {
      setTwoFactorLoading(false);
    }
  };

  const handleVerify2FA = async () => {
    if (!twoFactorCode.trim()) {
      setError('Please enter the 2FA code');
      return;
    }
    setTwoFactorLoading(true);
    setError(null);
    try {
      await apiService.verify2FA(token, twoFactorCode);
      setTwoFactorSetup(null);
      setTwoFactorCode('');
      setQrCodeUrl(null);
      const updatedUser = await apiService.getCurrentUser(token);
      updateUser(updatedUser);
      setSuccess('Two-factor authentication enabled successfully!');
    } catch (err) {
      setError(err.message || 'Failed to verify 2FA code');
    } finally {
      setTwoFactorLoading(false);
    }
  };

  const handleDisable2FA = async () => {
    setTwoFactorLoading(true);
    setError(null);
    try {
      await apiService.disable2FA(token);
      const updatedUser = await apiService.getCurrentUser(token);
      updateUser(updatedUser);
      setSuccess('Two-factor authentication disabled successfully!');
    } catch (err) {
      setError(err.message || 'Failed to disable 2FA');
    } finally {
      setTwoFactorLoading(false);
    }
  };

  const setupBrowserPushNotifications = async () => {
    try {
      console.log('🔄 Starting browser push notification setup...');

      // Check if we're in a secure context (required for service workers)
      if (!window.isSecureContext) {
        throw new Error('Browser notifications require HTTPS or localhost');
      }

      // Request notification permission
      const permission = await Notification.requestPermission();
      
      if (permission !== 'granted') {
        throw new Error('Notification permission denied by user');
      }

      // Check service worker support
      if (!('serviceWorker' in navigator)) {
        throw new Error('Service workers not supported in this browser');
      }

      // Register service worker with proper scope
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });
      
      console.log('✅ Service worker registered:', registration);

      // Wait for service worker to be ready
      await navigator.serviceWorker.ready;

  // Fetch VAPID public key from server (keeps keys out of client code and allows runtime configuration)
  // Add cache-busting parameter to avoid stale cached responses
  const cacheBuster = Date.now();
  const vapidResp = await fetch(`${API_BASE_URL}/api/alerts/vapid-public-key?t=${cacheBuster}`, {
    cache: 'no-store'
  });
      if (!vapidResp.ok) {
        throw new Error('Failed to fetch VAPID public key from server');
      }
      const vapidData = await vapidResp.json();
      const vapidPublicKey = vapidData?.publicKey;

      if (!vapidPublicKey) {
        throw new Error('VAPID public key not configured on server');
      }

      console.log('✅ VAPID public key received from server. Length:', vapidPublicKey.length);
      console.log('🔑 VAPID key starts with:', vapidPublicKey.substring(0, 10));

      // Validate the key format (should be base64url string)
      if (!vapidPublicKey.match(/^[A-Za-z0-9_-]+$/)) {
        throw new Error(`Invalid VAPID key format. Expected base64url string, got: ${vapidPublicKey.substring(0, 50)}...`);
      }

      // Convert VAPID key
      let applicationServerKey;
      try {
        applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
        console.log('✅ VAPID key converted to Uint8Array successfully');
      } catch (keyConvertError) {
        throw new Error(`Failed to convert VAPID key: ${keyConvertError.message}`);
      }

      // Handle existing subscription: if one exists with a different key the
      // browser will throw InvalidStateError when trying to subscribe.
      // Unsubscribe any existing subscription first to allow re-subscribe.
      try {
        const existing = await registration.pushManager.getSubscription();
        if (existing) {
          console.log('ℹ️ Existing push subscription found — attempting to unsubscribe to refresh key');
          try {
            await existing.unsubscribe();
            console.log('✅ Existing subscription unsubscribed');
          } catch (unsubErr) {
            console.warn('⚠️ Failed to unsubscribe existing subscription:', unsubErr);
            // continue — we'll still attempt to subscribe and handle errors below
          }
        }
      } catch (e) {
        console.warn('⚠️ Error checking existing subscription:', e);
      }

      // Subscribe to push notifications (may still throw if something unexpected)
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey
      });

      console.log('✅ Push subscription created:', subscription);

      // Prepare subscription data for server
      const subscriptionData = {
        endpoint: subscription.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('p256dh')))),
          auth: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('auth'))))
        }
      };

      console.log('📤 Sending subscription to server...');
      
      // Send subscription to server
      await apiService.subscribeToBrowserNotifications(token, subscriptionData);
      
      console.log('✅ Browser push notifications setup completed successfully');
      
      return true;
      
    } catch (error) {
      console.error('❌ Browser push setup error:', error);
      throw new Error(`Browser notifications setup failed: ${error.message}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Upload photo if changed
      let profile_picture_path = user.profile_picture;
      if (profilePhoto) {
        const uploadResult = await apiService.uploadProfilePhoto(profilePhoto, token);
        profile_picture_path = uploadResult.profile_picture;
      }

      // Update profile data - ensure ALL fields are included
      const updateData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        home_area: formData.home_area,
        work_area: formData.work_area,
        alert_radius: formData.alert_radius,
        profile_picture: profile_picture_path,
        phone_number: formData.phone_number,
        browser_notifications_enabled: formData.browser_notifications_enabled,
        email_alerts_enabled: formData.email_alerts_enabled,
        monitor_live_location: Boolean(formData.monitor_live_location),
        weekly_reports_enabled: Boolean(formData.weekly_reports_enabled),
        incident_alerts_enabled: Boolean(formData.incident_alerts_enabled),
        live_alerts_enabled: Boolean(formData.live_alerts_enabled)
      };


      console.log('🔄 Updating profile with data:', updateData);
      
      // Update profile first
      const result = await apiService.updateProfile(updateData, token);
      console.log('✅ Profile update API response:', result);

      // Only setup browser push if enabled AND supported
      if (formData.browser_notifications_enabled && browserPushSupported) {
        try {
          console.log('🚀 Setting up browser push notifications...');
          await setupBrowserPushNotifications();
          setSuccess('Profile updated successfully! Browser notifications enabled.');
        } catch (pushError) {
          console.error('❌ Browser push setup failed:', pushError);
          // Don't fail the entire profile update, but inform the user
          setSuccess('Profile updated successfully! Note: Browser notifications setup failed - you may need to check browser permissions.');
        }
      } else {
        setSuccess('Profile updated successfully!');
      }
      
      // Refresh user data to ensure UI is in sync
      console.log('🔄 Refreshing user data...');
      const updatedUser = await apiService.getCurrentUser(token);
      updateUser(updatedUser);
      
      // Update local form data with the actual server state
      setFormData(prev => ({
        ...prev,
        browser_notifications_enabled: updatedUser.browser_notifications_enabled || false,
        email_alerts_enabled: updatedUser.email_alerts_enabled !== undefined ? updatedUser.email_alerts_enabled : true,
        monitor_live_location: updatedUser.monitor_live_location || false,
        weekly_reports_enabled: updatedUser.weekly_reports_enabled !== undefined ? updatedUser.weekly_reports_enabled : true,
        incident_alerts_enabled: updatedUser.incident_alerts_enabled !== undefined ? updatedUser.incident_alerts_enabled : true,
        live_alerts_enabled: updatedUser.live_alerts_enabled !== undefined ? updatedUser.live_alerts_enabled : true
      }));


      console.log('✅ Profile update completed successfully');
      
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      console.error('❌ Profile update error:', err);
      setError(err.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const toggleAlerts = async () => {
    try {
      if (alertStatus?.is_subscribed) {
        await apiService.unsubscribeFromAlerts(token);
        setSuccess('Alerts disabled successfully!');
      } else {
        // Subscribe with current location and preferences - Independent toggling
        const notificationTypes = [];
        if (formData.email_alerts_enabled) notificationTypes.push('email');
        if (formData.browser_notifications_enabled && browserPushSupported) {
          notificationTypes.push('browser');
        }

        const subscriptionData = {
          alert_types: ['crime', 'safety', 'emergency'],
          areas: [formData.home_area].filter(Boolean),
          radius: formData.alert_radius,
          notification_types: notificationTypes,
          is_active: true
        };
        await apiService.subscribeToAlerts(token, subscriptionData);
        setSuccess('Alerts enabled successfully!');
      }
      await loadAlertStatus();
    } catch (error) {
      setError(error.message || 'Failed to update alert preferences');
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div className={styles.modalTabs}>
            <button 
              className={`${styles.tab} ${activeTab === 'profile' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              <i className="fas fa-user"></i>
              Personal Info
            </button>
            <button 
              className={`${styles.tab} ${activeTab === 'security' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('security')}
            >
              <i className="fas fa-shield-alt"></i>
              Security
            </button>
            <button 
              className={`${styles.tab} ${activeTab === 'alerts' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('alerts')}
            >
              <i className="fas fa-bell"></i>
              Alerts
            </button>
          </div>
          <button className={styles.modalCloseBtn} onClick={onClose}>
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className={styles.profileForm}>
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <>
              <div className={styles.profileImageContainer}>
                <img
                  src={previewPhoto || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-1.2.1&auto=format&fit=crop&w=200&q=80"}
                  alt="Profile Preview"
                  className={styles.profileModalImage}
                />
                <label className={styles.profileImageUpload}>
                  <i className="fas fa-camera"></i>
                  <input 
                    type="file" 
                    accept="image/*" 
                    onChange={handlePhotoChange} 
                    className={styles.fileInput}
                  />
                </label>
              </div>

              <div className={styles.formGrid}>
                <div className={styles.formGroup}>
                  <label htmlFor="first_name">First Name</label>
                  <input 
                    id="first_name"
                    name="first_name" 
                    value={formData.first_name} 
                    onChange={handleChange} 
                    required 
                    className={styles.formInput}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="last_name">Last Name</label>
                  <input 
                    id="last_name"
                    name="last_name" 
                    value={formData.last_name} 
                    onChange={handleChange} 
                    required 
                    className={styles.formInput}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="email">Email</label>
                  <input 
                    id="email"
                    name="email" 
                    type="email" 
                    value={formData.email} 
                    onChange={handleChange} 
                    required 
                    className={styles.formInput}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="phone_number">Phone Number</label>
                  <input 
                    id="phone_number"
                    name="phone_number" 
                    type="tel" 
                    value={formData.phone_number} 
                    onChange={handleChange} 
                    className={styles.formInput}
                    placeholder="+1 (555) 123-4567"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="home_area">Home Area</label>
                  <input 
                    id="home_area"
                    name="home_area" 
                    value={formData.home_area} 
                    onChange={handleChange} 
                    className={styles.formInput}
                    placeholder="Enter your home area"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="work_area">Work Area</label>
                  <input 
                    id="work_area"
                    name="work_area" 
                    value={formData.work_area} 
                    onChange={handleChange} 
                    className={styles.formInput}
                    placeholder="Enter your work area"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="alert_radius">Alert Radius (km)</label>
                  <input 
                    id="alert_radius"
                    name="alert_radius" 
                    type="number" 
                    min="1" 
                    max="50" 
                    value={formData.alert_radius} 
                    onChange={handleChange} 
                    className={styles.formInput}
                  />
                </div>

                {/* Browser Push Toggle */}
                {/* <div className={styles.formGroup}>
                  <label className={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      name="browser_notifications_enabled"
                      checked={formData.browser_notifications_enabled}
                      onChange={handleChange}
                      disabled={!browserPushSupported}
                      className={styles.checkboxInput}
                    />
                    <span className={styles.checkboxCustom}></span>
                    Browser Push Notifications
                    {!browserPushSupported && (
                      <div className={styles.unsupportedDetails}>
                        <span className={styles.unsupportedText}>
                          (Not supported in your browser)
                        </span>
                        <button 
                          type="button" 
                          className={styles.debugButton}
                          onClick={debugBrowserCapabilities}
                        >
                          Debug Browser
                        </button>
                      </div>
                    )}
                  </label>
                  <p className={styles.settingDescription}>
                    Receive instant safety alerts directly in your browser
                  </p>
                  
                  
                  {process.env.NODE_ENV === 'development' && (
                    <div className={styles.debugInfo}>
                      <p><strong>Debug Info:</strong></p>
                      <ul>
                        <li>Browser Supported: {browserPushSupported ? 'Yes' : 'No'}</li>
                        <li>Service Worker: {'serviceWorker' in navigator ? 'Yes' : 'No'}</li>
                        <li>Push Manager: {'PushManager' in window ? 'Yes' : 'No'}</li>
                        <li>Notifications: {'Notification' in window ? 'Yes' : 'No'}</li>
                        <li>Secure Context: {window.isSecureContext ? 'Yes' : 'No'}</li>
                        <li>User Agent: {navigator.userAgent}</li>
                      </ul>
                    </div>
                  )}
                </div> */}
              </div> 
            </>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className={styles.securitySection}>
              <div className={styles.twoFactorSection}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Two-Factor Authentication</h4>
                    <p>Add an extra layer of security to your account</p>
                  </div>
                  <div className={styles.settingStatus}>
                    {user?.two_factor_enabled ? (
                      <span className={styles.statusEnabled}>Enabled</span>
                    ) : (
                      <span className={styles.statusDisabled}>Disabled</span>
                    )}
                  </div>
                </div>

                {user?.two_factor_enabled ? (
                  <div className={styles.twoFactorActions}>
                    <button
                      type="button"
                      onClick={handleDisable2FA}
                      disabled={twoFactorLoading}
                      className={styles.btnDanger}
                    >
                      {twoFactorLoading ? (
                        <>
                          <i className="fas fa-spinner fa-spin"></i> Disabling...
                        </>
                      ) : (
                        <>
                          <i className="fas fa-times"></i> Disable 2FA
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className={styles.twoFactorSetup}>
                    {twoFactorSetup ? (
                      <div className={styles.twoFactorSetupForm}>
                        <div className={styles.qrCodeContainer}>
                          {qrCodeUrl ? (
                            <img
                              src={qrCodeUrl}
                              alt="2FA QR Code"
                              className={styles.qrCode}
                            />
                          ) : (
                            <div className={styles.qrCodePlaceholder}>
                              <i className="fas fa-spinner fa-spin"></i>
                              <p>Generating QR code...</p>
                            </div>
                          )}
                          <p className={styles.qrInstructions}>
                            Scan this QR code with your authenticator app
                          </p>
                        </div>

                        <div className={styles.formGroup}>
                          <label htmlFor="twoFactorCode">Verification Code</label>
                          <input
                            type="text"
                            id="twoFactorCode"
                            value={twoFactorCode}
                            onChange={(e) => setTwoFactorCode(e.target.value)}
                            placeholder="Enter 6-digit code"
                            maxLength="6"
                            className={styles.formInput}
                            disabled={twoFactorLoading}
                          />
                        </div>

                        <div className={styles.twoFactorActions}>
                          <button
                            type="button"
                            onClick={handleVerify2FA}
                            disabled={twoFactorLoading || !twoFactorCode.trim()}
                            className={styles.btnPrimary}
                          >
                            {twoFactorLoading ? (
                              <>
                                <i className="fas fa-spinner fa-spin"></i> Verifying...
                              </>
                            ) : (
                              <>
                                <i className="fas fa-check"></i> Enable 2FA
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setTwoFactorSetup(null);
                              setTwoFactorCode('');
                              setQrCodeUrl(null);
                            }}
                            disabled={twoFactorLoading}
                            className={styles.btnSecondary}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={handleSetup2FA}
                        disabled={twoFactorLoading}
                        className={styles.btnPrimary}
                      >
                        {twoFactorLoading ? (
                          <>
                            <i className="fas fa-spinner fa-spin"></i> Setting up...
                          </>
                        ) : (
                          <>
                            <i className="fas fa-shield-alt"></i> Enable Two-Factor Authentication
                          </>
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className={styles.alertsSection}>
              <h3 className={styles.sectionTitle}>Alert Preferences</h3>
              
              <div className={styles.alertStatusCard}>
                <div className={styles.alertStatusHeader}>
                  <div className={styles.statusInfo}>
                    <h4>Safety Alerts</h4>
                    <p>Real-time crime and safety notifications</p>
                  </div>
                  <div className={styles.statusToggle}>
                    <button
                      type="button"
                      onClick={toggleAlerts}
                      className={`${styles.toggleBtn} ${
                        alertStatus?.is_subscribed ? styles.toggleOn : styles.toggleOff
                      }`}
                    >
                      <span className={styles.toggleSlider}></span>
                    </button>
                    <span className={styles.toggleLabel}>
                      {alertStatus?.is_subscribed ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>

                {alertStatus?.is_subscribed && (
                  <div className={styles.alertDetails}>
                    <div className={styles.alertStat}>
                      <i className="fas fa-bell"></i>
                      <span>Active Subscriptions: {alertStatus.active_subscriptions || 1}</span>
                    </div>
                    <div className={styles.alertStat}>
                      <i className="fas fa-map-marker-alt"></i>
                      <span>Monitoring Radius: {formData.alert_radius} km</span>
                    </div>
                    <div className={styles.alertStat}>
                      <i className="fas fa-desktop"></i>
                      <span>Browser Notifications: {formData.browser_notifications_enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Browser Push Settings */}
              <div className={styles.browserPushSettings}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Browser Push Notifications</h4>
                    <p>Receive alerts directly in your browser</p>
                  </div>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      name="browser_notifications_enabled"
                      checked={formData.browser_notifications_enabled}
                      onChange={handleChange}
                      disabled={!browserPushSupported}
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>

                {!browserPushSupported && (
                  <p className={styles.browserPushNote}>
                    \u26A0\uFE0F Browser push notifications are not supported in your current browser. 
                    Consider using Chrome, Firefox, or Edge for this feature.
                  </p>
                )}

                {formData.browser_notifications_enabled && browserPushSupported && (
                  <p className={styles.browserPushNote}>
                    \u2705 You will receive instant safety alerts directly in your browser, 
                    even when the tab is closed.
                  </p>
                )}
              </div>

              {/* Email Alerts Settings */}
              <div className={styles.browserPushSettings} style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1.5rem' }}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Email Notifications</h4>
                    <p>Receive alerts via your registerd email: {formData.email}</p>
                  </div>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      name="email_alerts_enabled"
                      checked={formData.email_alerts_enabled}
                      onChange={handleChange}
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>

                <p className={styles.browserPushNote}>
                  {formData.email_alerts_enabled ? 
                    "\u2705 You will receive email alerts for high-risk activity in your areas." :
                    "\u26A0\uFE0F Email alerts are disabled. You will not receive any notifications via email."
                  }
                </p>
              </div>

              {/* Live Location Tracking Settings */}
              <div className={styles.browserPushSettings} style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1.5rem' }}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Live Location Alerts</h4>
                    <p>Alert me when I enter a high-risk zone in real-time</p>
                  </div>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      name="monitor_live_location"
                      checked={formData.monitor_live_location}
                      onChange={handleChange}
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>

                <p className={styles.browserPushNote}>
                  {formData.monitor_live_location ? 
                    "✅ We will monitor your live location and alert you if you enter a high crime area." :
                    "⚠️ Live location monitoring is disabled. You will not receive alerts based on your current movement."
                  }
                </p>
              </div>

              {/* Weekly Reports Settings */}
              <div className={styles.browserPushSettings} style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1.5rem' }}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Weekly Safety Reports</h4>
                    <p>Receive comprehensive 7-day safety trend analysis</p>
                  </div>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      name="weekly_reports_enabled"
                      checked={formData.weekly_reports_enabled}
                      onChange={handleChange}
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>

                <p className={styles.browserPushNote}>
                  {formData.weekly_reports_enabled ? 
                    "✅ You will receive a weekly digest of safety trends and insights for your area." :
                    "⚠️ Weekly reports are disabled."
                  }
                </p>
              </div>

              {/* Incident Alerts Settings */}
              <div className={styles.browserPushSettings} style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1.5rem' }}>
                <div className={styles.settingHeader}>
                  <div className={styles.settingInfo}>
                    <h4>Incident Alerts</h4>
                    <p>Get notified immediately of incidents near your saved locations</p>
                  </div>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      name="incident_alerts_enabled"
                      checked={formData.incident_alerts_enabled}
                      onChange={handleChange}
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>

                <p className={styles.browserPushNote}>
                  {formData.incident_alerts_enabled ? 
                    "✅ You will receive immediate alerts for medium/high severity incidents." :
                    "⚠️ Instant incident alerts are disabled."
                  }
                </p>
              </div>

            </div>
          )}

          {error && (
            <div className={styles.errorMessage}>
              <i className="fas fa-exclamation-triangle"></i>
              {error}
            </div>
          )}

          {success && (
            <div className={styles.successMessage}>
              <i className="fas fa-check-circle"></i>
              {success}
            </div>
          )}

          <div className={styles.modalActions}>
            <button 
              type="submit" 
              disabled={loading} 
              className={styles.btnPrimary}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i> Saving...
                </>
              ) : (
                <>
                  <i className="fas fa-save"></i> Save Changes
                </>
              )}
            </button>
            <button 
              type="button" 
              onClick={onClose} 
              disabled={loading} 
              className={styles.btnSecondary}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileModal;
