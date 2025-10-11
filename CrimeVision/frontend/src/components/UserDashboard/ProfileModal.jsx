import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import QRCode from 'qrcode';
import styles from './UserDashboard.module.css';

const ProfileModal = ({ isOpen, onClose }) => {
  const { user, token, setUser } = useAuth();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    home_area: '',
    work_area: '',
    alert_radius: 5,
  });
  const [profilePhoto, setProfilePhoto] = useState(null);
  const [previewPhoto, setPreviewPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [qrCodeUrl, setQrCodeUrl] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorLoading, setTwoFactorLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        home_area: user.home_area || '',
        work_area: user.work_area || '',
        alert_radius: user.alert_radius || 5,
      });
      setPreviewPhoto(user.profile_picture ? `${window.location.origin}/${user.profile_picture}` : null);
    }
  }, [user]);

  useEffect(() => {
    if (twoFactorSetup && twoFactorSetup.uri) {
      QRCode.toDataURL(twoFactorSetup.uri)
        .then(url => {
          setQrCodeUrl(url);
        })
        .catch(err => {
          console.error('Error generating QR code:', err);
          setError('Failed to generate QR code');
        });
    }
  }, [twoFactorSetup]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
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
    setQrCodeUrl(null); // Reset QR code URL
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
      // Refresh user data to get updated 2FA status
      const updatedUser = await apiService.getCurrentUser(token);
      setUser(updatedUser);
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
      // Refresh user data to get updated 2FA status
      const updatedUser = await apiService.getCurrentUser(token);
      setUser(updatedUser);
    } catch (err) {
      setError(err.message || 'Failed to disable 2FA');
    } finally {
      setTwoFactorLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Upload photo if changed
      let profile_picture_path = user.profile_picture;
      if (profilePhoto) {
        const uploadResult = await apiService.uploadProfilePhoto(profilePhoto, token);
        profile_picture_path = uploadResult.profile_picture;
      }

      // Update profile data
      const updateData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        home_area: formData.home_area,
        work_area: formData.work_area,
        alert_radius: formData.alert_radius,
        profile_picture: profile_picture_path,
      };

      await apiService.updateProfile(updateData, token);

      // Refresh user data
      const updatedUser = await apiService.getCurrentUser(token);
      setUser(updatedUser);

      onClose();
    } catch (err) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2>Edit Profile</h2>
          <button className={styles.modalCloseBtn} onClick={onClose}>
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className={styles.profileForm}>
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
          </div>

          {/* Two-Factor Authentication Section */}
          <div className={styles.twoFactorSection}>
            <h3>Two-Factor Authentication</h3>
            <p className={styles.twoFactorDescription}>
              Add an extra layer of security to your account by enabling two-factor authentication.
            </p>

            {user?.two_factor_enabled ? (
              <div className={styles.twoFactorStatus}>
                <div className={styles.statusEnabled}>
                  <i className="fas fa-shield-alt"></i>
                  <span>Two-Factor Authentication is enabled</span>
                </div>
                <button
                  type="button"
                  onClick={handleDisable2FA}
                  disabled={twoFactorLoading}
                  className={styles.btnDisable2FA}
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
                        Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                      </p>
                      <p className={styles.secretKey}>
                        Or manually enter this key: <code>{twoFactorSetup.secret}</code>
                      </p>
                    </div>

                    <div className={styles.formGroup}>
                      <label htmlFor="twoFactorCode">Enter 6-digit code from your app</label>
                      <input
                        type="text"
                        id="twoFactorCode"
                        value={twoFactorCode}
                        onChange={(e) => setTwoFactorCode(e.target.value)}
                        placeholder="000000"
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
                            <i className="fas fa-check"></i> Verify & Enable
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
                    className={styles.btnEnable2FA}
                  >
                    {twoFactorLoading ? (
                      <>
                        <i className="fas fa-spinner fa-spin"></i> Setting up...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-shield-alt"></i> Enable 2FA
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>

          {error && <div className={styles.errorMessage}>{error}</div>}

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