import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext_updated';
import { useSystemSettings } from '../contexts/SystemSettingsContext';
import apiService from '../services/apiService_updated';
import './ResetPasswordPage.css';

const ResetPasswordPage = () => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState([]);
  const { settings: systemSettings } = useSystemSettings();
  const minPasswordLength = systemSettings?.password_min_length ?? 8;

  useEffect(() => {
    // Get token from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('token');
    if (resetToken) {
      setToken(resetToken);
    } else {
      setError('Invalid reset link. Please request a new password reset.');
    }
  }, []);

  const validatePassword = (password) => {
    const errors = [];
    if (password.length < minPasswordLength) {
      errors.push(`Password must be at least ${minPasswordLength} characters long`);
    }
    if (!/(?=.*[a-z])/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }
    if (!/(?=.*[A-Z])/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }
    if (!/(?=.*\d)/.test(password)) {
      errors.push('Password must contain at least one number');
    }
    return errors;
  };

  const handlePasswordChange = (password) => {
    setNewPassword(password);
    setPasswordErrors(validatePassword(password));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const passwordValidationErrors = validatePassword(newPassword);
    if (passwordValidationErrors.length > 0) {
      setError('Please fix the password requirements below');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await apiService.resetPassword(token, newPassword);
      setSuccess(true);
      setMessage('Password reset successfully! You can now log in with your new password.');
    } catch (error) {
      setError(error.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const SecurityIllustration = () => (
    <svg viewBox="0 0 200 200" className="security-illustration">
      <defs>
        <linearGradient id="securityGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--accent-teal)" />
          <stop offset="100%" stopColor="var(--accent-purple)" />
        </linearGradient>
        <filter id="glowSecurity">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <radialGradient id="shieldGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--accent-teal)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity="0.1" />
        </radialGradient>
      </defs>
      
      {/* Background Orb */}
      <circle cx="100" cy="100" r="85" fill="url(#shieldGlow)" opacity="0.6" />
      
      {/* Main Shield */}
      <path 
        d="M100 40 L140 60 V90 C140 120 125 140 100 155 C75 140 60 120 60 90 V60 Z" 
        fill="none" 
        stroke="url(#securityGradient)" 
        strokeWidth="8" 
        strokeLinejoin="round" 
        filter="url(#glowSecurity)"
      />
      
      {/* Shield Details */}
      <path 
        d="M100 50 L120 60 V85 C120 105 110 120 100 130 C90 120 80 105 80 85 V60 Z" 
        fill="none" 
        stroke="var(--accent-teal)" 
        strokeWidth="4" 
        strokeLinejoin="round"
      />
      
      {/* Lock */}
      <rect 
        x="85" 
        y="75" 
        width="30" 
        height="25" 
        rx="4" 
        fill="none" 
        stroke="var(--accent-purple)" 
        strokeWidth="3"
      />
      <circle 
        cx="100" 
        cy="85" 
        r="8" 
        fill="none" 
        stroke="var(--accent-purple)" 
        strokeWidth="3"
      />
      
      {/* Keyhole */}
      <circle 
        cx="100" 
        cy="90" 
        r="2" 
        fill="var(--accent-teal)"
      />
      <rect 
        x="99" 
        y="90" 
        width="2" 
        height="8" 
        fill="var(--accent-teal)"
      />
      
      {/* Floating Security Elements */}
      <circle cx="60" cy="50" r="3" fill="var(--accent-teal)" opacity="0.8">
        <animate attributeName="cy" values="50;45;50" dur="2s" repeatCount="indefinite" />
      </circle>
      <circle cx="140" cy="45" r="2" fill="var(--accent-purple)" opacity="0.6">
        <animate attributeName="cy" values="45;50;45" dur="2.5s" repeatCount="indefinite" />
      </circle>
      <circle cx="75" cy="140" r="2.5" fill="var(--accent-amber)" opacity="0.7">
        <animate attributeName="cx" values="75;80;75" dur="3s" repeatCount="indefinite" />
      </circle>
    </svg>
  );

  if (success) {
    return (
      <div className="reset-password-page">
        <div className="reset-password-bg-elements">
          <div className="reset-orb orb-1"></div>
          <div className="reset-orb orb-2"></div>
        </div>
        
        <div className="reset-password-container">
          <div className="success-section">
            <div className="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="success-title">Password Reset Successful</h2>
            <p className="success-message">{message}</p>
            <button
              onClick={() => window.location.href = '/'}
              className="back-to-login-btn"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="me-2">
                <path d="M19 12H5M12 19l-7-7 7-7" 
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="reset-password-page">
      <div className="reset-password-bg-elements">
        <div className="reset-orb orb-1"></div>
        <div className="reset-orb orb-2"></div>
      </div>
      
      <div className="reset-password-container">
        <div className="reset-password-header">
          <div className="reset-badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 15V17M9 12H7M17 12H15M12 7V9M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Reset Your Password
          </div>
          <p className="reset-subtitle">Create a strong new password for your account</p>
        </div>

        <SecurityIllustration />

        <form onSubmit={handleSubmit} className="reset-password-form">
          <div className="form-group-custom">
            <label className="form-label">
              New Password
            </label>
            <div className="input-with-icon">
              <div className="input-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 15V17M9 12H7M17 12H15M12 7V9M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <input
                type={showNewPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => handlePasswordChange(e.target.value)}
                required
                disabled={loading}
                placeholder="Enter your new password"
                className="form-input-custom"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowNewPassword(!showNewPassword)}
                tabIndex="-1"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  {showNewPassword ? (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <circle cx="12" cy="12" r="3" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 2l20 20" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </>
                  ) : (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <circle cx="12" cy="12" r="3" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </>
                  )}
                </svg>
              </button>
            </div>
            
            {/* Password Requirements */}
            {newPassword && (
              <div className="password-requirements">
                <div className="requirements-title">Password must contain:</div>
                  <div className={`requirement ${newPassword.length >= minPasswordLength ? 'met' : ''}`}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    {newPassword.length >= 6 ? (
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    ) : (
                      <circle cx="12" cy="12" r="9" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    )}
                  </svg>
                  At least {minPasswordLength} characters
                </div>
                <div className={`requirement ${/(?=.*[a-z])/.test(newPassword) ? 'met' : ''}`}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    {/(?=.*[a-z])/.test(newPassword) ? (
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    ) : (
                      <circle cx="12" cy="12" r="9" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    )}
                  </svg>
                  One lowercase letter
                </div>
                <div className={`requirement ${/(?=.*[A-Z])/.test(newPassword) ? 'met' : ''}`}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    {/(?=.*[A-Z])/.test(newPassword) ? (
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    ) : (
                      <circle cx="12" cy="12" r="9" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    )}
                  </svg>
                  One uppercase letter
                </div>
                <div className={`requirement ${/(?=.*\d)/.test(newPassword) ? 'met' : ''}`}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    {/(?=.*\d)/.test(newPassword) ? (
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    ) : (
                      <circle cx="12" cy="12" r="9" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    )}
                  </svg>
                  One number
                </div>
              </div>
            )}
          </div>

          <div className="form-group-custom">
            <label className="form-label">
              Confirm New Password
            </label>
            <div className="input-with-icon">
              <div className="input-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <input
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="Confirm your new password"
                className="form-input-custom"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                tabIndex="-1"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  {showConfirmPassword ? (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <circle cx="12" cy="12" r="3" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 2l20 20" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </>
                  ) : (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <circle cx="12" cy="12" r="3" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </>
                  )}
                </svg>
              </button>
            </div>
            
            {/* Password Match Indicator */}
            {confirmPassword && (
              <div className={`password-match ${newPassword === confirmPassword ? 'matched' : 'not-matched'}`}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  {newPassword === confirmPassword ? (
                    <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  ) : (
                    <path d="M18 6L6 18M6 6l12 12" 
                          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  )}
                </svg>
                {newPassword === confirmPassword ? 'Passwords match' : 'Passwords do not match'}
              </div>
            )}
          </div>

          {error && (
            <div className="custom-alert error-alert">
              <div className="alert-content">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 9V14M12 17V17.01M5.07183 19H18.9282C20.4678 19 21.4301 17.3333 20.6603 16L13.7321 4C12.9623 2.66667 11.0378 2.66667 10.268 4L3.33978 16C2.56998 17.3333 3.53223 19 5.07183 19Z" 
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {error}
              </div>
            </div>
          )}

          <button
            type="submit"
            className="submit-button"
            disabled={loading || !token || passwordErrors.length > 0 || newPassword !== confirmPassword}
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                Resetting Password...
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="me-2">
                  <path d="M15 7l-5 5 5 5M9 7l5 5-5 5" 
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Reset Password
              </>
            )}
          </button>
        </form>

        <div className="back-to-login">
          <button
            onClick={() => window.location.href = '/'}
            className="back-link"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="me-2">
              <path d="M19 12H5M12 19l-7-7 7-7" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Back to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
