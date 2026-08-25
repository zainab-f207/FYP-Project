// import React, { useState } from 'react';
// import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
// import apiService from '../../services/apiService';
// import './LoginModal.css'; // Ensure we reuse the login modal styles

// const EmailIllustration = () => (
//   <svg viewBox="0 0 200 200" className="mb-4 mx-auto d-block" style={{ maxHeight: '120px', width: 'auto' }}>
//     <defs>
//       <linearGradient id="emailGradient" x1="0%" y1="0%" x2="100%" y2="100%">
//         <stop offset="0%" stopColor="#00d4ff" />
//         <stop offset="100%" stopColor="#6366f1" />
//       </linearGradient>
//       <filter id="glowEmail">
//         <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
//         <feMerge>
//           <feMergeNode in="coloredBlur"/>
//           <feMergeNode in="SourceGraphic"/>
//         </feMerge>
//       </filter>
//     </defs>
//     <circle cx="100" cy="100" r="90" fill="url(#emailGradient)" opacity="0.1" />
//     <path d="M40 70 L100 110 L160 70 V150 H40 V70 Z" fill="none" stroke="url(#emailGradient)" strokeWidth="6" strokeLinejoin="round" filter="url(#glowEmail)" />
//     <path d="M40 70 L100 110 L160 70" fill="none" stroke="url(#emailGradient)" strokeWidth="6" strokeLinecap="round" filter="url(#glowEmail)" />
//     <circle cx="140" cy="60" r="15" fill="#6366f1" />
//     <path d="M135 60 L140 65 L150 55" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
//   </svg>
// );

// const ForgotPasswordModal = ({ show, onHide }) => {
//   const [email, setEmail] = useState('');
//   const [loading, setLoading] = useState(false);
//   const [message, setMessage] = useState('');
//   const [error, setError] = useState('');
//   const [success, setSuccess] = useState(false);

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setLoading(true);
//     setError('');
//     setMessage('');

//     try {
//       const response = await apiService.forgotPassword(email);
//       setMessage(response.message || 'Password reset email sent successfully!');
//       setSuccess(true);
//     } catch (err) {
//       setError(err.message || 'Failed to send password reset email');
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleClose = () => {
//     setEmail('');
//     setError('');
//     setMessage('');
//     setSuccess(false);
//     onHide();
//   };

//   return (
//     <Modal show={show} onHide={handleClose} centered className="login-modal-content">
//       <Modal.Header closeButton className="border-0 pb-0">
//         <Modal.Title className="w-100 text-center">Forgot Password</Modal.Title>
//       </Modal.Header>
//       <Modal.Body className="pt-0">
//         <EmailIllustration />
//         {success ? (
//           <Alert variant="success" className="text-center">
//             <h5>Check Your Email</h5>
//             <p>{message}</p>
//             <p className="mb-0">If you don't see the email, check your spam folder.</p>
//           </Alert>
//         ) : (
//           <>
//             <p className="text-center text-muted mb-4">Enter your email address and we'll send you a link to reset your password.</p>
//             {error && <Alert variant="danger">{error}</Alert>}
//             {message && <Alert variant="info">{message}</Alert>}
//             <Form onSubmit={handleSubmit}>
//               <Form.Group className="mb-4">
//                 <Form.Label>Email Address</Form.Label>
//                 <Form.Control
//                   type="email"
//                   placeholder="Enter your email"
//                   value={email}
//                   onChange={(e) => setEmail(e.target.value)}
//                   required
//                   disabled={loading}
//                 />
//               </Form.Group>
//               <div className="d-grid">
//                 <Button
//                   variant="primary"
//                   type="submit"
//                   className="py-2 fw-bold"
//                   style={{ background: 'linear-gradient(135deg, #00d4ff 0%, #6366f1 100%)', border: 'none' }}
//                   disabled={loading || !email.trim()}
//                 >
//                   {loading ? (
//                     <>
//                       <Spinner animation="border" size="sm" className="me-2" />
//                       Sending...
//                     </>
//                   ) : (
//                     'Send Reset Link'
//                   )}
//                 </Button>
//               </div>
//             </Form>
//           </>
//         )}
//       </Modal.Body>
//     </Modal>
//   );
// };

// export default ForgotPasswordModal;



import React, { useState } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import apiService from '../../services/apiService';
import './ForgotPasswordModal.css';

const EmailIllustration = () => (
  <svg viewBox="0 0 200 200" className="email-illustration">
    <defs>
      <linearGradient id="emailGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="var(--accent-teal)" />
        <stop offset="100%" stopColor="var(--accent-purple)" />
      </linearGradient>
      <filter id="glowEmail">
        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <radialGradient id="orbGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="var(--accent-teal)" stopOpacity="0.3" />
        <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity="0.1" />
      </radialGradient>
    </defs>
    
    {/* Background Orb */}
    <circle cx="100" cy="100" r="85" fill="url(#orbGlow)" opacity="0.6" />
    
    {/* Main Email Envelope */}
    <path 
      d="M40 70 L100 110 L160 70 V150 H40 V70 Z" 
      fill="none" 
      stroke="url(#emailGradient)" 
      strokeWidth="8" 
      strokeLinejoin="round" 
      filter="url(#glowEmail)"
    />
    
    {/* Email Flap */}
    <path 
      d="M40 70 L100 110 L160 70" 
      fill="none" 
      stroke="url(#emailGradient)" 
      strokeWidth="8" 
      strokeLinecap="round" 
      filter="url(#glowEmail)"
    />
    
    {/* Security Shield */}
    <path 
      d="M100 50 L120 60 V80 C120 95 110 105 100 110 C90 105 80 95 80 80 V60 Z" 
      fill="none" 
      stroke="var(--accent-teal)" 
      strokeWidth="4" 
      strokeLinejoin="round"
    />
    
    {/* Checkmark */}
    <path 
      d="M95 75 L105 85 L115 70" 
      fill="none" 
      stroke="var(--accent-teal)" 
      strokeWidth="4" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
    
    {/* Floating Particles */}
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

const ForgotPasswordModal = ({ show, onHide }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await apiService.forgotPassword(email);
      setMessage(response.message || 'Password reset email sent successfully!');
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to send password reset email');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setError('');
    setMessage('');
    setSuccess(false);
    onHide();
  };

  return (
    <Modal show={show} onHide={handleClose} centered className="forgot-password-modal">
      <div className="modal-bg-elements">
        <div className="modal-orb orb-1"></div>
        <div className="modal-orb orb-2"></div>
      </div>
      
      <Modal.Header closeButton className="modal-header border-0 pb-0">
        <Modal.Title className="w-100 text-center">
          <div className="modal-badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 15V17M9 12H7M17 12H15M12 7V9M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Reset Your Password
          </div>
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body className="modal-body pt-0">
        <EmailIllustration />
        
        {success ? (
          <div className="success-section">
            <div className="success-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" 
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h5 className="success-title">Check Your Email</h5>
            <p className="success-message">{message}</p>
            <p className="success-note">If you don't see the email, check your spam folder.</p>
          </div>
        ) : (
          <>
            <div className="instruction-text">
              <p>Enter your email address and we'll send you a secure link to reset your password.</p>
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
                  Email Address
                </Form.Label>
                <div className="input-with-icon">
                  <div className="input-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M4 4H20C21.1 4 22 4.9 22 6V18C22 19.1 21.1 20 20 20H4C2.9 20 2 19.1 2 18V6C2 4.9 2.9 4 4 4Z" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M22 6L12 13L2 6" 
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <Form.Control
                    type="email"
                    placeholder="Enter your email address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                    className="form-input-custom"
                  />
                </div>
              </Form.Group>
              
              <div className="d-grid">
                <Button
                  type="submit"
                  className="submit-button"
                  disabled={loading || !email.trim()}
                >
                  {loading ? (
                    <>
                      <Spinner animation="border" size="sm" className="me-2" />
                      Sending Secure Link...
                    </>
                  ) : (
                    <>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="me-2">
                        <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" 
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      Send Reset Link
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

export default ForgotPasswordModal;
