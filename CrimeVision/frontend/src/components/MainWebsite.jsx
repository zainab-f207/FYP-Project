// src/components/MainWebsite.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext_updated';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import Introduction from './Introduction';
import Features from './Features';
// import CrimeMapInterface from './CrimeMapInterface';
import Footer from './Footer';
import LoginModal from './Modals/LoginModal_updated';
import ForgotPasswordModal from './Modals/ForgotPasswordModal';
import ReportModal from './Modals/ReportModal';
import BackToTop from './BackToTop';
import { TokenValidator } from '../contexts/TokenValidator';

const MainWebsite = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [forgotPasswordModalOpen, setForgotPasswordModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [selectedArea, setSelectedArea] = useState('');
  const [selectedCrimeType, setSelectedCrimeType] = useState('');

  const { isAuthenticated, logout, token} = useAuth();
  const navigate = useNavigate();

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  },[isAuthenticated, navigate]);

//   useEffect(() => {
//     setupBrowserNotifications();
//   }, [token]);

//   const setupBrowserNotifications = async () => {
//   try {
//     console.log('🌐 Setting up browser notifications...');
    
//     // Check if service worker is supported
//     if (!('serviceWorker' in navigator)) {
//       console.log('❌ Service Worker not supported');
//       return;
//     }

//     // Register service worker
//     const registration = await navigator.serviceWorker.register('/sw.js');
//     console.log('✅ Service Worker registered');

//     // Request notification permission
//     const permission = await Notification.requestPermission();
//     console.log('📢 Notification permission:', permission);
    
//     if (permission === 'granted' && token) {
//       // Subscribe to push notifications
//       const subscription = await registration.pushManager.subscribe({
//         userVisibleOnly: true,
//         applicationServerKey: urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY') // Add your VAPID key
//       });
      
//       console.log('📱 Push subscription created');
      
//       // Send subscription to server
//       await apiService.subscribeToBrowserNotifications(token, subscription);
//       console.log('✅ Browser notifications subscribed successfully');
//     }
//   } catch (error) {
//     console.error('❌ Error setting up browser notifications:', error);
//   }
// };

//   // Utility function for VAPID key conversion
//   const urlBase64ToUint8Array = (base64String) => {
//     const padding = '='.repeat((4 - base64String.length % 4) % 4);
//     const base64 = (base64String + padding)
//       .replace(/\-/g, '+')
//       .replace(/_/g, '/');
    
//     const rawData = window.atob(base64);
//     const outputArray = new Uint8Array(rawData.length);
    
//     for (let i = 0; i < rawData.length; ++i) {
//       outputArray[i] = rawData.charCodeAt(i);
//     }
//     return outputArray;
//   };
  
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

  return (
    <div className="MainWebsite">
      <TokenValidator />
      <Header
        showLoginModal={showLoginModal}
        showReportModal={showReportModal}
        onAreaSelect={setSelectedArea}
        onCrimeSelect={setSelectedCrimeType}
        isAuthenticated={isAuthenticated}
        onLogout={logout}
      />

      <Introduction />
      <Features />
      {/* <CrimeMapInterface /> */}
      <Footer />

      {/* Modals */}
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

      <BackToTop />
    </div>
  );
};

export default MainWebsite;
