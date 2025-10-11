import React, { useEffect, useState } from 'react';
import apiService from '../services/apiService';

const EmailVerificationPage = () => {
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');

      if (!token) {
        setStatus('error');
        setMessage('No verification token provided.');
        return;
      }

      try {
        const response = await apiService.verifyEmail(token);
        setStatus('success');
        setMessage(response.message || 'Email verified successfully! You can now log in.');
      } catch (error) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Failed to verify email. The token may be invalid or expired.');
      }
    };

    verifyEmail();
  }, []);

  const handleLoginRedirect = () => {
    window.location.href = '/';
  };

  return (
    <div className="email-verification-page">
      <div className="verification-container">
        <h2>Email Verification</h2>

        {status === 'verifying' && (
          <div className="verification-loading">
            <div className="spinner"></div>
            <p>Verifying your email...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="verification-success">
            <div className="success-icon">✓</div>
            <p>{message}</p>
            <button onClick={handleLoginRedirect} className="login-btn">
              Go to Login
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="verification-error">
            <div className="error-icon">✕</div>
            <p>{message}</p>
            <button onClick={() => window.location.href = '/'} className="home-btn">
              Go to Home
            </button>
          </div>
        )}
      </div>

      <style jsx>{`
        .email-verification-page {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background-color: #f5f5f5;
          font-family: Arial, sans-serif;
        }

        .verification-container {
          background: white;
          padding: 2rem;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
          text-align: center;
          max-width: 400px;
          width: 100%;
        }

        .verification-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #3498db;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .verification-success {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .success-icon {
          font-size: 3rem;
          color: #28a745;
          margin-bottom: 1rem;
        }

        .verification-error {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .error-icon {
          font-size: 3rem;
          color: #dc3545;
          margin-bottom: 1rem;
        }

        .login-btn, .home-btn {
          margin-top: 1rem;
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 1rem;
          transition: background-color 0.3s;
        }

        .login-btn {
          background-color: #007bff;
          color: white;
        }

        .login-btn:hover {
          background-color: #0056b3;
        }

        .home-btn {
          background-color: #6c757d;
          color: white;
        }

        .home-btn:hover {
          background-color: #545b62;
        }
      `}</style>
    </div>
  );
};

export default EmailVerificationPage;
