import React from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { TokenValidator } from '../contexts/TokenValidator';

// Import components directly
import UserDashboard from './UserDashboard/UserDashboard';
import AdminDashboard from './AdminDashboard/AdminDashboard';
import SuperAdminDashboard from './SuperAdminDashboard/SuperAdminDashboard';
import ResetPasswordPage from './ResetPasswordPage';
import EmailVerificationPage from './EmailVerificationPage';
import MainWebsite from './MainWebsite';
import LoginPage from './Modals/LoginModal'; // This component now supports both modal and page rendering
import LogoutConfirmationPage from './LogoutConfirmationPage';
import AutoLoginPage from './AutoLoginPage';

// Import new dedicated pages
import RiskPredictionPage from './HomePage/RiskPredictionPage';
import CrimeMapPage from './HomePage/CrimeMapPage';
import EmergencyPage from './HomePage/EmergencyPage';
import ProjectVideoPage from './HomePage/ProjectVideoPage';

const LoadingSpinner = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  }}>
    <div style={{ textAlign: 'center', color: 'white' }}>
      <i className="fas fa-spinner fa-spin" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
      <p>Loading SafeVision...</p>
    </div>
  </div>
);

// Protected Route component
const ProtectedRoute = ({ children, requiredRole = null }) => {
  const { isAuthenticated, user, loading, initialized } = useAuth();
  const location = useLocation();

  // Show loading spinner only during initial auth check (not during login/register operations)
  if (!initialized) {
    return <LoadingSpinner />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role if required
  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Public Route component (redirect to dashboard if already authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading, initialized } = useAuth();
  const location = useLocation();

  // Show loading spinner only during initial auth check
  if (!initialized) {
    return <LoadingSpinner />;
  }

  if (isAuthenticated) {
    // Redirect to the page they tried to access or dashboard
    // FIXED: Preserve search parameters and hash
    const fromLocation = location.state?.from;
    const fromPath = fromLocation 
      ? `${fromLocation.pathname}${fromLocation.search}${fromLocation.hash}` 
      : '/dashboard';
    
    return <Navigate to={fromPath} replace />;
  }

  return children;
};

const AppRouter = () => {
  const { isAuthenticated, user, loading, initialized } = useAuth();
  const location = useLocation();

  // Save current path to localStorage - FIXED: Only save non-root paths
  React.useEffect(() => {
    if (location.pathname !== '/' && location.pathname !== '/login') {
      localStorage.setItem('last_path', location.pathname);
    }
  }, [location.pathname]);

  // Show loading spinner only during initial auth initialization
  if (!initialized) {
    return <LoadingSpinner />;
  }

  return (
    <>
    <TokenValidator />
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />
      <Route path="/logout" element={<LogoutConfirmationPage />} />
      <Route path="/verify-email" element={<EmailVerificationPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/autologin" element={<AutoLoginPage />} />
      
      {/* New dedicated public pages */}
      <Route path="/risk-prediction" element={<RiskPredictionPage />} />
      <Route path="/crime-map" element={<CrimeMapPage />} />
      <Route path="/emergency" element={<EmergencyPage />} />
      <Route path="/about-project" element={<ProjectVideoPage />} />
      
      {/* Protected dashboard routes */}
      <Route path="/dashboard/*" element={
        <ProtectedRoute>
          {user?.role === 'admin' ? (
            <AdminDashboard />
          ) : user?.role === 'superadmin' ? (
            <SuperAdminDashboard />
          ) : (
            <UserDashboard />
          )}
        </ProtectedRoute>
      } />
      
      {/* Main website - public */}
      <Route path="/" element={
        <MainWebsite />
      } />
      
      {/* Catch all route */}
      <Route path="*" element={
        isAuthenticated ? (
          <Navigate to="/dashboard" replace />
        ) : (
          <Navigate to="/" replace />
        )
      } />
    </Routes>
    </>
  );
};

export default AppRouter;
