import React, { useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext_updated';
import { SystemSettingsProvider } from './contexts/SystemSettingsContext';
import { cleanupInvalidTokens } from './utils/tokenCleanup';

import AppRouter from './components/AppRouter';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { NotificationProvider } from './contexts/NotificationContext';

// Initialize token cleanup
cleanupInvalidTokens();

// Register service worker for push notifications
const registerServiceWorker = async () => {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });
      console.log('✅ Service Worker registered successfully:', registration);

      // Handle updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New content is available, notify user
              console.log('🔄 New service worker available, consider refreshing');
            }
          });
        }
      });

    } catch (error) {
      console.error('❌ Service Worker registration failed:', error);
    }
  } else {
    console.warn('⚠️ Service Workers not supported in this browser');
  }
};

// Enhanced error boundary
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false,
      error: null,
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('App Error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    
    // Log to error reporting service
    if (process.env.NODE_ENV === 'production') {
      // Add your error logging service here
    }
  }

  handleReset = () => {
    this.setState({ 
      hasError: false,
      error: null,
      errorInfo: null 
    });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '20px',
          textAlign: 'center'
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '20px',
            padding: '3rem',
            maxWidth: '500px',
            width: '90%',
            backdropFilter: 'blur(20px)'
          }}>
            <i className="fas fa-exclamation-triangle" style={{
              fontSize: '4rem',
              color: '#fbbf24',
              marginBottom: '1.5rem'
            }}></i>
            <h2 style={{
              color: 'white',
              marginBottom: '1rem',
              fontSize: '1.8rem'
            }}>Something went wrong</h2>
            <p style={{
              color: 'rgba(255, 255, 255, 0.8)',
              marginBottom: '2rem',
              fontSize: '1.1rem',
              lineHeight: '1.5'
            }}>
              We encountered an unexpected error. Don't worry, your data is safe.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button 
                onClick={this.handleReset}
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
                onMouseOver={(e) => {
                  e.target.style.transform = 'translateY(-2px)';
                  e.target.style.boxShadow = '0 8px 25px rgba(16, 185, 129, 0.4)';
                }}
                onMouseOut={(e) => {
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = 'none';
                }}
              >
                <i className="fas fa-redo" style={{ marginRight: '0.5rem' }}></i>
                Try Again
              </button>
              <button 
                onClick={() => window.location.reload()}
                style={{
                  background: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
                onMouseOver={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.3)';
                  e.target.style.transform = 'translateY(-2px)';
                }}
                onMouseOut={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.2)';
                  e.target.style.transform = 'translateY(0)';
                }}
              >
                <i className="fas fa-sync" style={{ marginRight: '0.5rem' }}></i>
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  // Register service worker on app load
  useEffect(() => {
    registerServiceWorker();
  }, []);

  return (
    <ErrorBoundary>
      <Router>
        <SystemSettingsProvider>
          <NotificationProvider>
            <AuthProvider>
              <div className="App">
                <AppRouter />
              </div>
            </AuthProvider>
          </NotificationProvider>
        </SystemSettingsProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
