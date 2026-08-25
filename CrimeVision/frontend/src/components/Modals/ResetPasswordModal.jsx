import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import { useSearchParams, useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import './ResetPasswordModal.css';

const LockIllustration = () => (
  <svg viewBox="0 0 200 200" className="lock-illustration">
    <defs>
      <linearGradient id="lockGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="var(--accent-teal)" />
        <stop offset="100%" stopColor="var(--accent-purple)" />
      </linearGradient>
      <filter id="glow">
        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <radialGradient id="lockOrbGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="var(--accent-teal)" stopOpacity="0.3" />
        <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity="0.1" />
      </radialGradient>
    </defs>
    
    {/* Background Orb */}
    <circle cx="100" cy="100" r="85" fill="url(#lockOrbGlow)" opacity="0.6" />
    
    {/* Main Lock Body */}
    <path 
      d="M100 40 C70 40 45 65 45 95 V110 H40 V170 H160 V110 H155 V95 C155 65 130 40 100 40 M100 60 C120 60 135 75 135 95 V110 H65 V95 C65 75 80 60 100 60" 
      fill="none" 
      stroke="url(#lockGradient)" 
      strokeWidth="8" 
      strokeLinecap="round" 
      filter="url(#glow)" 
    />
    
    {/* Lock Body Fill */}
    <rect x="60" y="110" width="80" height="60" rx="5" fill="rgba(255,255,255,0.05)" stroke="url(#lockGradient)" strokeWidth="2" />
    
    {/* Keyhole */}
    <circle cx="100" cy="130" r="8" fill="var(--accent-teal)" opacity="0.8">
      <animate attributeName="r" values="8;10;8" dur="2s" repeatCount="indefinite" />
    </circle>
    <path 
      d="M100 138 V158" 
      stroke="var(--accent-teal)" 
      strokeWidth="4" 
      strokeLinecap="round"
    >
      <animate attributeName="stroke-width" values="4;6;4" dur="2s" repeatCount="indefinite" />
    </path>
    
    {/* Security Shield */}
    <path 
      d="M85 50 L100 40 L115 50 V65 C115 75 110 80 100 85 C90 80 85 75 85 65 V50 Z" 
      fill="none" 
      stroke="var(--accent-purple)" 
      strokeWidth="3" 
      strokeLinejoin="round"
    />
    
    {/* Security Lines */}
    <path d="M75 75 L85 85" stroke="var(--accent-teal)" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <path d="M125 75 L115 85" stroke="var(--accent-teal)" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    <path d="M100 90 V100" stroke="var(--accent-purple)" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
    
    {/* Floating Security Dots */}
    <circle cx="70" cy="60" r="2" fill="var(--accent-teal)" opacity="0.6">
      <animate attributeName="cy" values="60;55;60" dur="3s" repeatCount="indefinite" />
    </circle>
    <circle cx="130" cy="65" r="1.5" fill="var(--accent-purple)" opacity="0.6">
      <animate attributeName="cx" values="130;135;130" dur="2.5s" repeatCount="indefinite" />
    </circle>
    <circle cx="85" cy="150" r="2" fill="var(--accent-amber)" opacity="0.7">
      <animate attributeName="cx" values="85;90;85" dur="4s" repeatCount="indefinite" />
    </circle>
  </svg>
);

const ResetPasswordModal = ({ show, onHide }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false
  });
  const { settings: systemSettings } = useSystemSettings();
  const minPasswordLength = systemSettings?.password_min_length ?? 8;

  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset link.');
    }
  }, [token]);

  const validatePassword = (password) => {
    const validations = {
      length: password.length >= minPasswordLength,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password)
    };
    
    setPasswordValidation(validations);
    
    if (!validations.length) return `Password must be at least ${minPasswordLength} characters long`;
    if (!validations.uppercase) return 'Password must contain at least one uppercase letter';
    if (!validations.lowercase) return 'Password must contain at least one lowercase letter';
    if (!validations.number) return 'Password must contain at least one number';
    return null;
  };

  const handlePasswordChange = (password) => {
    setNewPassword(password);
    validatePassword(password);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      setLoading(false);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      const response = await apiService.resetPassword(token, newPassword);
      setMessage(response.message || 'Password reset successfully!');
      setSuccess(true);

      // Redirect to login after a short delay
      setTimeout(() => {
        navigate('/login');
        onHide();
      }, 3000);
    } catch (err) {
      setError(err.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setMessage('');
    setSuccess(false);
    setPasswordValidation({
      length: false,
      uppercase: false,
      lowercase: false,
      number: false
    });
    onHide();
  };

  const ValidationIndicator = ({ isValid, text }) => (
    <div className={`validation-item ${isValid ? 'valid' : 'invalid'}`}>
      <div className="validation-icon">
        {isValid ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
          </svg>
        )}
      </div>
      <span className="validation-text">{text}</span>
    </div>
  );

  return (
    <Modal show={show} onHide={handleClose} centered className="reset-password-modal">
      <div className="modal-bg-elements">
        <div className="modal-orb orb-1"></div>
        <div className="modal-orb orb-2"></div>
      </div>
      
      <Modal.Header closeButton className="modal-header border-0 pb-0">
        <Modal.Title className="w-100 text-center">
          <div className="modal-badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M15 7C15 5.67392 14.4732 4.40215 13.5355 3.46447C12.5979 2.52678 11.3261 2 10 2C8.67392 2 7.40215 2.52678 6.46447 3.46447C5.52678 4.40215 5 5.67392 5 7M12 12L15 15M15 15L18 12M15 15V9M5 21H15C16.1046 21 17 20.1046 17 19V11C17 9.89543 16.1046 9 15 9H5C3.89543 9 3 9.89543 3 11V19C3 20.1046 3.89543 21 5 21Z" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Reset Your Password
          </div>
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body className="modal-body pt-0">
        <LockIllustration />
        
        {success ? (
          <div className="success-section">
            <div className="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h5 className="success-title">Password Reset Successful!</h5>
            <p className="success-message">{message}</p>
            <p className="success-note">You will be redirected to the login page shortly...</p>
          </div>
        ) : (
          <>
            <div className="instruction-text">
              <p>Create a strong new password to secure your account.</p>
            </div>
            
            {error && (
              <Alert variant="danger" className="custom-alert error-alert">
                <div className="alert-content">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M12 9V14M12 17V17.01M5.07183 19H18.9282C20.4678 19 21.4301 17.3333 20.6603 16L13.7321 4C12.9623 2.66667 11.0378 2.66667 10.268 4L3.33978 16C2.56998 17.3333 3.53223 19 5.07183 19Z" 
                          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {error}
                </div>
              </Alert>
            )}
            
            {message && (
              <Alert variant="info" className="custom-alert info-alert">
                <div className="alert-content">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M13 16H12V12H11M12 8H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {message}
                </div>
              </Alert>
            )}
            
            <Form onSubmit={handleSubmit} className="custom-form">
              <Form.Group className="form-group-custom">
                <Form.Label className="form-label">
                  New Password
                </Form.Label>
                <div className="input-with-icon">
                  <div className="input-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 15V17M9 12H7M17 12H15M12 7V9M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <Form.Control
                    type="password"
                    placeholder="Enter new password"
                    value={newPassword}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    required
                    disabled={loading || !token}
                    className="form-input-custom"
                  />
                </div>
                
                {/* Password Validation */}
                {newPassword && (
                  <div className="password-validation">
                    <ValidationIndicator 
                      isValid={passwordValidation.length} 
                      text={`At least ${minPasswordLength} characters`} 
                    />
                    <ValidationIndicator 
                      isValid={passwordValidation.uppercase} 
                      text="One uppercase letter" 
                    />
                    <ValidationIndicator 
                      isValid={passwordValidation.lowercase} 
                      text="One lowercase letter" 
                    />
                    <ValidationIndicator 
                      isValid={passwordValidation.number} 
                      text="One number" 
                    />
                  </div>
                )}
              </Form.Group>
              
              <Form.Group className="form-group-custom">
                <Form.Label className="form-label">
                  Confirm New Password
                </Form.Label>
                <div className="input-with-icon">
                  <div className="input-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <Form.Control
                    type="password"
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={loading || !token}
                    className="form-input-custom"
                  />
                </div>
                
                {/* Password Match Validation */}
                {confirmPassword && (
                  <div className="password-validation">
                    <ValidationIndicator 
                      isValid={newPassword === confirmPassword && newPassword.length > 0} 
                      text="Passwords match" 
                    />
                  </div>
                )}
              </Form.Group>
              
              <div className="d-grid">
                <Button
                  type="submit"
                  className="submit-button"
                  disabled={loading || !token || !newPassword.trim() || !confirmPassword.trim()}
                >
                  {loading ? (
                    <>
                      <Spinner animation="border" size="sm" className="me-2" />
                      Securing Password...
                    </>
                  ) : (
                    <>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="me-2">
                        <path d="M15 7C15 5.67392 14.4732 4.40215 13.5355 3.46447C12.5979 2.52678 11.3261 2 10 2C8.67392 2 7.40215 2.52678 6.46447 3.46447C5.52678 4.40215 5 5.67392 5 7M12 12L15 15M15 15L18 12M15 15V9M5 21H15C16.1046 21 17 20.1046 17 19V11C17 9.89543 16.1046 9 15 9H5C3.89543 9 3 9.89543 3 11V19C3 20.1046 3.89543 21 5 21Z" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      Reset Password
                    </>
                  )}
                </Button>
              </div>
            </Form>
          </>
        )}
      </Modal.Body>
    </Modal>
  );
};

export default ResetPasswordModal;
