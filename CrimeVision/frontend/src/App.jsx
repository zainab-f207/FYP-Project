// src/App.js
import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext_updated';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Hero from './components/Hero';
import Features from './components/Features';
import SafetyTips from './components/SafetyTips';
import News from './components/News';
import PredictionTool from './components/PredictionTool';
import CrimeMap from './components/CrimeMap/CrimeMap_updated';
import CrimeHeatmap from './components/CrimeHeatMap_updated_fixed';
import Statistics from './components/Statistics';
import Testimonials from './components/Testimonials';
import Footer from './components/Footer';
import LoginModal from './components/Modals/LoginModal_updated';
import ForgotPasswordModal from './components/Modals/ForgotPasswordModal';
import ReportModal from './components/Modals/ReportModal';
import DarkModeToggle from './components/DarkModeToggle';
import BackToTop from './components/BackToTop';
import UserDashboard from './components/UserDashboard/UserDashboard';
import AdminDashboard from './components/AdminDashboard/AdminDashboard';
import SuperAdminDashboard from './components/SuperAdminDashboard/SuperAdminDashboard_updated';
import ResetPasswordPage from './components/ResetPasswordPage';
import EmailVerificationPage from './components/EmailVerificationPage';
import { TokenValidator } from './contexts/TokenValidator';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function AppContent() {
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [forgotPasswordModalOpen, setForgotPasswordModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [selectedArea, setSelectedArea] = useState('');
  const [selectedCrimeType, setSelectedCrimeType] = useState('');

  const { isAuthenticated, logout, role } = useAuth();

  useEffect(() => {
    // Load dark mode preference from localStorage
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    setDarkMode(savedDarkMode);

    // Apply dark mode class to body
    if (savedDarkMode) {
      document.body.classList.add('dark-mode');
    }
  }, []);

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode);

    if (newDarkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const showLoginModal = () => {
    setLoginModalOpen(true);
    closeSidebar();
  };

  const closeLoginModal = () => {
    setLoginModalOpen(false);
  };

  const showForgotPasswordModal = () => {
    setLoginModalOpen(false);
    setForgotPasswordModalOpen(true);
  };

  const closeForgotPasswordModal = () => {
    setForgotPasswordModalOpen(false);
  };

  const showReportModal = () => {
    setReportModalOpen(true);
    closeSidebar();
  };

  const closeReportModal = () => {
    setReportModalOpen(false);
  };

  // Check URL parameters and pathname for special pages
  const urlParams = new URLSearchParams(window.location.search);
  const pathname = window.location.pathname;
  const token = urlParams.get('token');

  // Check for email verification page
  if (pathname.includes('verify-email') && token) {
    return <EmailVerificationPage />;
  }

  // Check if this is a password reset page
  if (pathname.includes('reset-password') && token) {
    return <ResetPasswordPage />;
  }

  // If user is authenticated, show the dashboard instead of the main website
  if (isAuthenticated) {
    let DashboardComponent;
    if (role === 'admin') {
      DashboardComponent = AdminDashboard;
    } else if (role === 'superadmin') {
      DashboardComponent = SuperAdminDashboard;
    } else {
      DashboardComponent = UserDashboard;
    }

    return (
      <div className="App">
        <TokenValidator />
        <DashboardComponent />

        <LoginModal
          isOpen={loginModalOpen}
          closeModal={closeLoginModal}
          onForgotPassword={showForgotPasswordModal}
        />

        <ForgotPasswordModal
          show={forgotPasswordModalOpen}
          onHide={closeForgotPasswordModal}
        />

        <ReportModal
          isOpen={reportModalOpen}
          closeModal={closeReportModal}
        />

        <DarkModeToggle
          darkMode={darkMode}
          toggleDarkMode={toggleDarkMode}
        />

        <BackToTop />
      </div>
    );
  }

  // Show regular website for non-authenticated users
  return (
    <div className="App">
      <TokenValidator />
      <Header
        toggleSidebar={toggleSidebar}
        showLoginModal={showLoginModal}
        showReportModal={showReportModal}
        onAreaSelect={setSelectedArea}
        onCrimeSelect={setSelectedCrimeType}
        isAuthenticated={isAuthenticated}
        onLogout={logout}
      />
      <Sidebar
        isOpen={sidebarOpen}
        closeSidebar={closeSidebar}
        showLoginModal={showLoginModal}
        showReportModal={showReportModal}
        onAreaSelect={setSelectedArea}
        onCrimeSelect={setSelectedCrimeType}
        isAuthenticated={isAuthenticated}
      />
      <Hero />
      <Features />
      <SafetyTips />
      <News />
      <PredictionTool
        selectedArea={selectedArea}
        selectedCrimeType={selectedCrimeType}
        isAuthenticated={isAuthenticated}
      />

      {/* Show basic crime map for non-logged-in users */}
      <CrimeMap
        showLoginModal={showLoginModal}
        isAuthenticated={isAuthenticated}
      />

      <Statistics />
      <Testimonials />
      <Footer />

      <LoginModal
        isOpen={loginModalOpen}
        closeModal={closeLoginModal}
        onForgotPassword={showForgotPasswordModal}
      />

      <ForgotPasswordModal
        show={forgotPasswordModalOpen}
        onHide={closeForgotPasswordModal}
      />

      <ReportModal
        isOpen={reportModalOpen}
        closeModal={closeReportModal}
      />

      <DarkModeToggle
        darkMode={darkMode}
        toggleDarkMode={toggleDarkMode}
      />

      <BackToTop />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
