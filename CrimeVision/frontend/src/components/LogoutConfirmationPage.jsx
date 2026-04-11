import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './LogoutConfirmationPage.css';

const LogoutConfirmationPage = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Auto redirect after 5 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="logout-page">
      <div className="logout-container">
        <div className="logout-card">
          <div className="logout-icon-wrapper">
            <svg className="logout-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 17L21 12L16 7" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M21 12H9" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="gradient" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#00d4ff"/>
                  <stop offset="1" stopColor="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
            <div className="icon-ring"></div>
            <div className="icon-ring-2"></div>
          </div>
          
          <h1>Logged Out Successfully</h1>
          <p>Thank you for using SafeVision. Your session has been securely terminated.</p>
          
          <div className="logout-actions">
            <Link to="/" className="btn-primary">
              <i className="fas fa-home"></i>
              Return to Home
            </Link>
            <Link to="/" className="btn-secondary" onClick={() => document.querySelector('.login-btn')?.click()}>
              <i className="fas fa-sign-in-alt"></i>
              Login Again
            </Link>
          </div>

          <div className="auto-redirect-msg">
            Redirecting to home in 5 seconds...
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogoutConfirmationPage;
