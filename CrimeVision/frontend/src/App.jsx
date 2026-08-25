/**
 * App.jsx — root of the entire CrimeVision frontend.
 *
 * What this file is in plain words:
 *   This is the very first React component the browser mounts when the user
 *   opens the site. Think of it as the front door of the application: it
 *   wires every "global" piece (routing, login state, system settings,
 *   notifications, error catching, push-notification service worker) around
 *   the actual page content. Every screen the user ever sees is rendered
 *   somewhere INSIDE the tree returned by <App />.
 *
 * Why the imports look the way they do:
 *   - React + useEffect    → so we can run a one-time "on page load" effect
 *                            (registering the service worker).
 *   - BrowserRouter        → enables clean URLs like /login or /dashboard
 *                            instead of hash-style #/login URLs.
 *   - AuthProvider         → React Context that makes "who is logged in"
 *                            available to every screen without prop-drilling.
 *   - SystemSettingsProvider → exposes admin-controlled global toggles
 *                            (theme, feature flags, maintenance mode).
 *   - NotificationProvider → in-app toast / banner notifications.
 *   - cleanupInvalidTokens → housekeeping helper that wipes any leftover
 *                            broken JWTs from localStorage on page load so a
 *                            stale token never crashes the auth flow.
 *   - AppRouter            → the table of all <Route> definitions.
 *   - The three CSS imports load Bootstrap base styles, our admin dashboard
 *     theme tokens, and our responsive breakpoints in that exact order so
 *     our project rules win over Bootstrap defaults.
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { SystemSettingsProvider } from './contexts/SystemSettingsContext';
import { cleanupInvalidTokens } from './utils/tokenCleanup';

import AppRouter from './components/AppRouter';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import './components/AdminDashboard/dashboard-theme.css';
import './responsive.css';
import { NotificationProvider } from './contexts/NotificationContext';

// Run the localStorage token-sweep at module load (before React even mounts).
// This guarantees that if a previous session left behind a malformed token,
// the AuthProvider below will start with a clean slate instead of crashing
// while parsing it.
cleanupInvalidTokens();

/**
 * registerServiceWorker
 *
 * Asks the browser to install our /sw.js service worker so the app can
 * receive Web Push notifications even when the tab is closed.
 *
 * Step-by-step:
 *   1) Check the browser actually supports service workers (older browsers
 *      and some in-app webviews do not).
 *   2) Call navigator.serviceWorker.register('/sw.js') — the file lives in
 *      the public/ folder so it is served from the site root, which is
 *      required (a worker cannot control pages above its own URL).
 *   3) Listen for "updatefound" so that when we ship a new sw.js, we know
 *      a new worker is installing and can log it (production builds could
 *      also show a "Refresh to update" banner here).
 *   4) Wrap everything in try/catch + an availability check so failures
 *      degrade silently — the rest of the app keeps working without push.
 */
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

/**
 * ErrorBoundary
 *
 * React's safety net for "uncaught" rendering errors. If any component
 * deeper in the tree throws while rendering (e.g. tries to read .map of
 * undefined data, or a network helper throws synchronously), React would
 * normally unmount the WHOLE app and show a blank white page. This class
 * intercepts that situation and displays a friendly fallback screen with
 * a "Try Again" button instead.
 *
 * How error boundaries work in React:
 *   - getDerivedStateFromError() runs during render and lets us flip a
 *     boolean ("hasError") into state so the next render shows the
 *     fallback UI.
 *   - componentDidCatch() runs as a side effect after the error is caught
 *     and is the right place for logging / telemetry.
 *
 * Limitations to remember:
 *   Error boundaries do NOT catch errors inside event handlers, async
 *   code (promises, setTimeout) or server-side rendering. Those still
 *   need their own try/catch.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    // Three pieces of state:
    //   hasError  → the flag that toggles between "render children" and
    //               "render fallback UI".
    //   error     → the actual Error object so we could display its message
    //               in development if we ever want to.
    //   errorInfo → React's component stack trace, useful for debugging
    //               which component blew up.
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  // Pure function — must NOT cause side effects. React calls it on the way
  // down so the very first re-render after the crash already shows the
  // fallback UI.
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  // Called after the error has already been "handled" by getDerivedState.
  // Side effects (logging, telemetry, capturing extra info into state) live
  // here. We keep both error and errorInfo so a future "Send report" feature
  // can include the React component stack.
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

  // "Try Again" button handler. We clear the error flag in state AND force
  // a hard navigation back to "/". Hard navigation (assigning to
  // window.location.href instead of using react-router) is intentional —
  // it gives the broken sub-tree a clean reload so we don't immediately
  // re-trigger the same error from cached component state.
  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
    window.location.href = '/';
  };

  // Standard React render: when an error has been caught we replace the
  // children with the fallback UI. Otherwise we transparently pass the
  // children through, so during normal operation this component is
  // effectively invisible.
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

/**
 * App
 *
 * The root functional component. Its only job is to assemble the global
 * "providers" in the correct order and hand off to <AppRouter /> which
 * decides what page to show based on the URL.
 *
 * The order of providers MATTERS:
 *   1) ErrorBoundary       — outermost, so even crashes inside Router or
 *                            Auth still hit our friendly fallback.
 *   2) Router              — must wrap anything that uses useNavigate /
 *                            <Link> / route hooks.
 *   3) SystemSettingsProvider — needs to be above AuthProvider because
 *                            login screens read system flags (e.g. is
 *                            registration enabled?).
 *   4) NotificationProvider — sits above AuthProvider so login/logout flows
 *                            can themselves push toasts.
 *   5) AuthProvider        — holds current_user + token; everything below
 *                            reads it via useAuth().
 *   6) <div className="App"> + <AppRouter />   — the actual page tree.
 */
function App() {
  // useEffect with [] runs exactly once after the component mounts in the
  // browser. We use it to register the push-notification service worker.
  // This must NOT run during render (which is why it lives in useEffect)
  // because service-worker registration is a side effect that touches the
  // browser globals.
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
