import React, { useState, useEffect, useCallback, useRef, memo, useMemo } from "react";
import { toast, ToastContainer } from 'react-toastify';
import { useAuth } from "../../contexts/AuthContext";
import { useNavigate } from 'react-router-dom';
import { apiService } from "../../services/apiService";
import "./LoginModal.css";
import ForgotPasswordModal from "./ForgotPasswordModal";
import { useNotification } from "../../contexts/NotificationContext";
import { useSystemSettings } from "../../contexts/SystemSettingsContext";

// Field definitions moved outside component to prevent re-creation on every render
const commonFields = [
  {
    id: "email",
    name: "email",
    label: "Email",
    type: "email",
    required: true,
    placeholder: "Enter your email address"
  },
  {
    id: "password",
    name: "password",
    label: "Password",
    type: "password",
    required: true,
    placeholder: "Enter your password"
  }
];

const registerFields = [
  {
    id: "firstName",
    name: "firstName",
    label: "First Name",
    type: "text",
    required: true,
    placeholder: "Enter your first name"
  },
  {
    id: "lastName",
    name: "lastName",
    label: "Last Name",
    type: "text",
    required: true,
    placeholder: "Enter your last name"
  },
  {
    id: "confirmPassword",
    name: "confirmPassword",
    label: "Confirm Password",
    type: "password",
    required: true,
    placeholder: "Confirm your password"
  }
];

// SafeVision Security Guardian - Enhanced for Crime Mapping & Safety
// Moved outside component and memoized to prevent re-renders
const SafeVisionCharacter = memo(({ isLogin }) => (
  <div className="SafeVision-character">
    <svg viewBox="0 0 800 1000" className="character-svg" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="skyGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#020617" />
          <stop offset="100%" stopColor="#1e293b" />
        </linearGradient>
        <linearGradient id="buildingGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>
        <linearGradient id="windowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#00d4ff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="trafficGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ef4444" stopOpacity="0" />
          <stop offset="50%" stopColor="#ef4444" stopOpacity="1" />
          <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="trafficGradientBlue" x1="100%" y1="0%" x2="0%" y2="0%">
          <stop offset="0%" stopColor="#00d4ff" stopOpacity="0" />
          <stop offset="50%" stopColor="#00d4ff" stopOpacity="1" />
          <stop offset="100%" stopColor="#00d4ff" stopOpacity="0" />
        </linearGradient>
        <filter id="glassBlur">
          <feGaussianBlur stdDeviation="2" />
        </filter>
        <filter id="neonGlow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      {/* --- SKY & ATMOSPHERE --- */}
      <rect width="100%" height="100%" fill="url(#skyGradient)" />
      
      {/* Neural Network Nodes in Sky */}
      <g opacity="0.3">
        {[...Array(20)].map((_, i) => (
          <circle key={i} cx={Math.random() * 800} cy={Math.random() * 600} r={Math.random() * 2 + 1} fill="#00d4ff">
            <animate attributeName="opacity" values="0.2;0.8;0.2" dur={`${Math.random() * 3 + 2}s`} repeatCount="indefinite" />
          </circle>
        ))}
        <path d="M100 100 L300 200 L500 150 L700 300" fill="none" stroke="#00d4ff" strokeWidth="0.5" opacity="0.2">
           <animate attributeName="stroke-dasharray" values="0,1000;1000,0" dur="10s" repeatCount="indefinite" />
        </path>
      </g>

      {/* --- CITY SKYLINE --- */}
      <g transform="translate(0, 400)">
        {/* Back Layer Buildings */}
        <path d="M0 600 L0 200 L50 200 L50 150 L100 150 L100 600 Z" fill="#1e293b" opacity="0.8" />
        <path d="M150 600 L150 300 L200 300 L200 250 L250 250 L250 600 Z" fill="#1e293b" opacity="0.7" />
        <path d="M600 600 L600 200 L650 200 L650 100 L750 100 L750 600 Z" fill="#1e293b" opacity="0.8" />
        
        {/* Front Layer Buildings */}
        <path d="M50 600 L50 350 L120 350 L120 600 Z" fill="url(#buildingGradient)" />
        <rect x="60" y="360" width="50" height="200" fill="url(#windowGradient)" opacity="0.1" />
        
        <path d="M250 600 L250 100 L350 100 L350 150 L400 150 L400 600 Z" fill="url(#buildingGradient)" />
        <rect x="260" y="110" width="80" height="400" fill="url(#windowGradient)" opacity="0.2" />
        
        <path d="M450 600 L450 250 L550 250 L550 600 Z" fill="url(#buildingGradient)" />
        <rect x="460" y="260" width="80" height="300" fill="url(#windowGradient)" opacity="0.15" />
        
        <path d="M700 600 L700 400 L800 400 L800 600 Z" fill="url(#buildingGradient)" />
      </g>

      {/* --- TRAFFIC --- */}
      <g transform="translate(0, 900)">
        {/* Road Lines */}
        <line x1="0" y1="0" x2="800" y2="0" stroke="#334155" strokeWidth="2" />
        <line x1="0" y1="20" x2="800" y2="20" stroke="#334155" strokeWidth="2" />
        
        {/* Moving Cars (Red Tail Lights) */}
        <rect x="-100" y="-5" width="100" height="4" fill="url(#trafficGradient)" opacity="0.8">
          <animate attributeName="x" from="-100" to="900" dur="4s" repeatCount="indefinite" />
        </rect>
        <rect x="-100" y="-5" width="100" height="4" fill="url(#trafficGradient)" opacity="0.8">
          <animate attributeName="x" from="-100" to="900" dur="5s" begin="2s" repeatCount="indefinite" />
        </rect>

        {/* Moving Cars (Blue Head Lights) */}
        <rect x="900" y="15" width="100" height="4" fill="url(#trafficGradientBlue)" opacity="0.8">
          <animate attributeName="x" from="900" to="-100" dur="3s" repeatCount="indefinite" />
        </rect>
      </g>

      {/* --- FLOATING WIDGETS (Glassmorphism) --- */}
      
      {/* 1. RISK PREDICTION (Top Right) */}
      <g transform="translate(480, 150)">
        <rect width="280" height="180" rx="15" fill="rgba(15, 23, 42, 0.6)" stroke="rgba(0, 212, 255, 0.3)" strokeWidth="1" />
        <text x="20" y="30" fill="#00d4ff" fontSize="14" fontWeight="bold" letterSpacing="1">RISK PREDICTION</text>
        {/* Graph */}
        <path d="M20 140 L260 140" stroke="#334155" strokeWidth="1" />
        <path d="M20 140 L20 50" stroke="#334155" strokeWidth="1" />
        <path d="M20 120 L60 110 L100 130 L140 80 L180 90 L220 60 L260 70" fill="none" stroke="#00d4ff" strokeWidth="2" filter="url(#neonGlow)">
           <animate attributeName="stroke-dasharray" from="0,300" to="300,0" dur="3s" fill="freeze" />
        </path>
        <circle cx="260" cy="70" r="4" fill="#fff">
          <animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite" />
        </circle>
      </g>

      {/* 2. SAFE ROUTES (Middle Left) */}
      <g transform="translate(40, 300)">
        <rect width="240" height="200" rx="15" fill="rgba(15, 23, 42, 0.6)" stroke="rgba(16, 185, 129, 0.3)" strokeWidth="1" />
        <text x="20" y="30" fill="#10b981" fontSize="14" fontWeight="bold" letterSpacing="1">SAFE ROUTES</text>
        {/* Map Grid */}
        <path d="M20 50 L220 50 M20 90 L220 90 M20 130 L220 130 M20 170 L220 170" stroke="#334155" strokeWidth="1" />
        <path d="M60 50 L60 170 M100 50 L100 170 M140 50 L140 170 M180 50 L180 170" stroke="#334155" strokeWidth="1" />
        {/* Route Path */}
        <path d="M60 170 L60 130 L100 130 L100 90 L140 90 L140 50" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round">
           <animate attributeName="stroke-dasharray" values="0,300;300,0" dur="4s" repeatCount="indefinite" />
        </path>
        <circle cx="140" cy="50" r="6" fill="#10b981" />
        <text x="155" y="55" fill="#fff" fontSize="10">DESTINATION</text>
      </g>

      {/* 3. INCIDENTS FEED (Bottom Right) */}
      <g transform="translate(500, 600)">
        <rect width="260" height="220" rx="15" fill="rgba(15, 23, 42, 0.6)" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="1" />
        <text x="20" y="30" fill="#ef4444" fontSize="14" fontWeight="bold" letterSpacing="1">LIVE INCIDENTS</text>
        
        <g transform="translate(20, 60)">
          <circle cx="10" cy="5" r="4" fill="#ef4444">
             <animate attributeName="opacity" values="1;0.2;1" dur="1s" repeatCount="indefinite" />
          </circle>
          <text x="25" y="10" fill="#fff" fontSize="12">Theft Reported - Sector 4</text>
          <text x="25" y="25" fill="#94a3b8" fontSize="10">2 mins ago</text>
        </g>
        
        <g transform="translate(20, 110)">
          <circle cx="10" cy="5" r="4" fill="#f59e0b" />
          <text x="25" y="10" fill="#fff" fontSize="12">Suspicious Activity</text>
          <text x="25" y="25" fill="#94a3b8" fontSize="10">15 mins ago</text>
        </g>
        
        <g transform="translate(20, 160)">
          <circle cx="10" cy="5" r="4" fill="#3b82f6" />
          <text x="25" y="10" fill="#fff" fontSize="12">Patrol Unit Deployed</text>
          <text x="25" y="25" fill="#94a3b8" fontSize="10">Now</text>
        </g>
      </g>

      {/* 4. EMERGENCY CONTACT (Bottom Left) */}
      <g transform="translate(60, 750)">
        <circle cx="40" cy="40" r="30" fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" strokeWidth="2">
           <animate attributeName="r" values="30;35;30" dur="1.5s" repeatCount="indefinite" />
           <animate attributeName="opacity" values="0.5;0.2;0.5" dur="1.5s" repeatCount="indefinite" />
        </circle>
        <circle cx="40" cy="40" r="20" fill="#ef4444" />
        <path d="M30 40 L35 45 L50 30" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <text x="85" y="45" fill="#fff" fontSize="16" fontWeight="bold">SOS READY</text>
      </g>

      {/* --- SCANNING BEAM --- */}
      <path d="M0 0 L800 0 L400 1000 Z" fill="url(#windowGradient)" opacity="0.05">
         <animateTransform attributeName="transform" type="rotate" from="-20 400 0" to="20 400 0" dur="8s" repeatCount="indefinite" />
      </path>

    </svg>
    <div className="character-title">
      SafeVision
    </div>
    <div className="character-subtitle">
      Advanced Urban Safety Network
    </div>
  </div>
));

const LoginModal = ({ isOpen, closeModal, onForgotPassword }) => {
  const { settings: sysSettings } = useSystemSettings();
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: "",
    firstName: "",
    lastName: "",
    password: "",
    confirmPassword: "",
    homeArea: "",
    phoneNumber: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [generatedUsername, setGeneratedUsername] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [animationStage, setAnimationStage] = useState("entering");
  const [isSwitching, setIsSwitching] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [pendingGoogleCredential, setPendingGoogleCredential] = useState(null);
  const [isGoogleLogin2FA, setIsGoogleLogin2FA] = useState(false);
  const usernameTimer = useRef(null);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showNotification, setNotification] = useState(null);
  const [rateLimitInfo, setRateLimitInfo] = useState(null); // { locked, retryAfter, message }
  const [admin2FASetup, setAdmin2FASetup] = useState(null); // { token, username, message }
  const rateLimitTimerRef = useRef(null);
  const notif = useNotification();

  // Email OTP states (mandatory 2FA for admin/superadmin)
  // Restore OTP state from sessionStorage if user navigated away (e.g., to check email)
  const savedOtpData = sessionStorage.getItem('pending_otp_data');
  const [requiresEmailOtp, setRequiresEmailOtp] = useState(!!savedOtpData);
  const [emailOtpCode, setEmailOtpCode] = useState('');
  const [pendingOtpData, setPendingOtpData] = useState(savedOtpData ? JSON.parse(savedOtpData) : null);
  const [otpCountdown, setOtpCountdown] = useState(() => {
    const savedExpiry = sessionStorage.getItem('otp_expiry_time');
    if (savedExpiry) {
      const remaining = Math.floor((parseInt(savedExpiry) - Date.now()) / 1000);
      return remaining > 0 ? remaining : 0;
    }
    return 0;
  });
  const [resendingOtp, setResendingOtp] = useState(false);
  const otpCountdownRef = useRef(null);

  // Force password change states (first-login for admin)
  const [requiresPasswordChange, setRequiresPasswordChange] = useState(false);
  const [pendingPasswordChangeToken, setPendingPasswordChangeToken] = useState(null);
  const [pendingPasswordChangeRole, setPendingPasswordChangeRole] = useState('admin');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordChangeErrors, setPasswordChangeErrors] = useState({});

  const { login, register, googleLogin, googleRegister, isAuthenticated, completeOtpLogin } = useAuth();
  const navigate = useNavigate();
  const formRef = useRef(null);
  const currentEmail = String(formData.email || '').trim().toLowerCase();
  const lockedEmail = String(rateLimitInfo?.email || '').trim().toLowerCase();
  const isRateLimitedForCurrentEmail = Boolean(rateLimitInfo?.locked && lockedEmail && lockedEmail === currentEmail);

  // Notifications handled globally via NotificationProvider

  // Determine if this is being used as a modal or page
  const isModal = isOpen !== undefined;
  const isPage = !isModal;

  // Global notifications are handled by NotificationProvider

  // Handle navigation after successful authentication
  useEffect(() => {
    if (isAuthenticated && isPage) {
      // FIXED: Respect the "from" state to preserve query parameters
      const fromPath = location.state?.from 
        ? `${location.state.from.pathname}${location.state.from.search}${location.state.from.hash}` 
        : '/dashboard';
      navigate(fromPath, { replace: true });
    }
  }, [isAuthenticated, isPage, navigate, location.state]);

  // Animation effects - Optimized to prevent unnecessary re-renders
  useEffect(() => {
    if (isOpen || isPage) {
      setAnimationStage("entering");
      const timer = setTimeout(() => setAnimationStage("entered"), 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen, isPage]);

  // Rate limit countdown timer
  useEffect(() => {
    if (isRateLimitedForCurrentEmail && rateLimitInfo.retryAfter > 0) {
      rateLimitTimerRef.current = setInterval(() => {
        setRateLimitInfo((prev) => {
          if (!prev || prev.retryAfter <= 1) {
            clearInterval(rateLimitTimerRef.current);
            return null; // Unlock
          }
          return { ...prev, retryAfter: prev.retryAfter - 1 };
        });
      }, 1000);
      return () => clearInterval(rateLimitTimerRef.current);
    }
  }, [isRateLimitedForCurrentEmail, rateLimitInfo?.retryAfter]);

  // OTP countdown timer (5 minutes)
  useEffect(() => {
    if (otpCountdown > 0) {
      otpCountdownRef.current = setInterval(() => {
        setOtpCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(otpCountdownRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(otpCountdownRef.current);
    }
  }, [otpCountdown > 0]);

  // Validation functions
  const validateEmail = useCallback((email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) return "Email is required";
    if (!emailRegex.test(email)) return "Please enter a valid email address";
    return "";
  }, []);

  const validatePassword = useCallback((password, isLogin = true) => {
    if (!password) return "Password is required";

    // For login, only check if it's not empty
    if (isLogin) return "";

    // For registration, check strength using system settings
    const minLen = sysSettings?.password_min_length ?? 8;
    if (password.length < minLen) return `Password must be at least ${minLen} characters`;
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password))
      return "Password must contain uppercase, lowercase, and numbers";

    return "";
  }, [sysSettings?.password_min_length]);

  const validateField = useCallback((name, value, isLogin, currentFormData) => {
    switch (name) {
      case "email":
        return validateEmail(value);
      case "password":
        return validatePassword(value, isLogin);
      case "confirmPassword":
        if (!isLogin && value !== currentFormData.password) return "Passwords do not match";
        return "";
      case "firstName":
      case "lastName":
        if (!isLogin && !value) return "This field is required";
        return "";
      default:
        return "";
    }
  }, [validateEmail, validatePassword]);

  const validateForm = useCallback(() => {
    const newErrors = {};

    Object.keys(formData).forEach(key => {
      if (isLogin && !["email", "password"].includes(key)) return;

      const error = validateField(key, formData[key], isLogin, formData);
      if (error) newErrors[key] = error;
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, isLogin, validateField]); // Keep dependencies as needed for validation

  // Check 2FA status for email
  const check2FAStatus = useCallback(async (email) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/auth/check-2fa-status?email=${encodeURIComponent(email)}`);
      if (!response.ok) {
        console.warn('Check 2FA status returned non-OK status:', response.status);
        setRequires2FA(false);
        return;
      }
      const data = await response.json();
      console.log('2FA status check result:', data);
      // Coerce to a real Boolean — backend may return tinyint/number 0/1 and
      // raw numbers leak as literal "0" through `{requires2FA && ...}` JSX.
      setRequires2FA(Boolean(data.enabled));
    } catch (error) {
      console.error('Error checking 2FA status:', error);
      setRequires2FA(false);
    }
  }, []);

  // Simplified input change handler - Optimized to prevent re-renders
  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;

    // Update form data
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));

    // Clear specific field error
    setErrors(prev => ({
      ...prev,
      [name]: "",
    }));

    // Check 2FA status when email changes
    if (name === "email" && value && isLogin) {
      check2FAStatus(value);
    }
  }, [isLogin, check2FAStatus]); // Add dependencies

  // Separate effect for username generation to avoid interfering with input
  useEffect(() => {
    if (!isLogin && (formData.firstName || formData.lastName)) {
      if (usernameTimer.current) clearTimeout(usernameTimer.current);

      usernameTimer.current = setTimeout(() => {
        if (formData.firstName && formData.lastName) {
          const base = `${formData.firstName}.${formData.lastName}`
            .toLowerCase()
            .replace(/\s+/g, "")
            .replace(/[^a-z0-9.]/g, "");
          const random = Math.floor(Math.random() * 900 + 100);
          const uname = `${base}${random}`;
          setGeneratedUsername(uname);
          // Keep username in formData so it is included in payloads
          setFormData(prev => ({ ...prev, username: uname }));
        }
      }, 300);
    }
  }, [formData.firstName, formData.lastName, isLogin]); // keep minimal deps

  const handleInputBlur = useCallback((e) => {
    const { name, value } = e.target;
    const error = validateField(name, value, isLogin, formData);
    if (error) {
      setErrors(prev => ({
        ...prev,
        [name]: error,
      }));
    }

    if (name === "password" && formData.confirmPassword) {
      const confirmError = validateField("confirmPassword", formData.confirmPassword, isLogin, formData);
      if (confirmError) {
        setErrors(prev => ({ ...prev, confirmPassword: confirmError }));
      }
    }
  }, [validateField, isLogin, formData]); // Keep formData dependency as it's needed for validation

  const handleTogglePassword = useCallback((fieldName) => {
    if (fieldName === "password") {
      setShowPassword(prev => !prev);
    } else if (fieldName === "confirmPassword") {
      setShowConfirmPassword(prev => !prev);
    }
  }, []); // No dependencies needed as it only uses setState functions

  const handleGoogleLogin = useCallback(async (response) => {
    console.log('🔐 LoginModal: Google login button clicked');
    setErrors({});
    setLoading(true);

    try {
      let result;

      if (isLogin) {
        // Login flow
        console.log('🔐 LoginModal: Attempting login flow with credential');
        result = await googleLogin(response.credential);
        
        console.log('🔐 LoginModal: Login result:', result);

        if (result.success) {
          console.log('✅ LoginModal: Login successful');
          notif.success('Google Login Successful', `Welcome back${result.username ? ', ' + result.username : ''}!`);
          toast.success(`Welcome back!`);
          // FIXED: Respect the redirect state
          const fromPath = location.state?.from 
            ? `${location.state.from.pathname}${location.state.from.search}${location.state.from.hash}` 
            : '/dashboard';
          navigate(fromPath, { replace: true });
          if (isModal) {
            closeModal();
          }
        } else if (result.requiresRegistration) {
          console.log('🔐 LoginModal: User requires registration (blocked)');
          // User needs to register but we are in Login mode - BLOCK access
          const errorMsg = "Account not found. Please Sign Up first.";
          setErrors({ general: errorMsg });
          notif.error('Login Failed', errorMsg);
          toast.error(errorMsg);
          // Do NOT switch to registration mode
        } else if (result.requires_verification) {
          console.log('🔐 LoginModal: User requires email verification');
          // User needs email verification
          const verificationMsg = result.message || 'Please verify your email address';
          notif.warning('Email Verification Required', verificationMsg);
          toast.info(verificationMsg);
          setErrors({ general: verificationMsg });
        } else if (result.requires_2fa) {
          console.log('🔐 LoginModal: User requires 2FA');
          // User needs 2FA
          const twoFAMsg = result.message || 'Please enter your 2FA code';
          notif.info('2FA Required', twoFAMsg);
          toast.info(twoFAMsg);
          setRequires2FA(true);
          setIsGoogleLogin2FA(true);
          setPendingGoogleCredential(response.credential);
          setErrors({});
        } else {
          console.error('🔐 LoginModal: Login failed with error:', result.error);
          const errorMsg = result.error || 'Google login failed';
          setErrors({ general: errorMsg });
          notif.error('Google Login Failed', errorMsg);
          toast.error(errorMsg);
          // Reset states on error
          setIsGoogleLogin2FA(false);
          setPendingGoogleCredential(null);
        }
      } else {
        // Registration flow
        console.log('🔐 LoginModal: Attempting registration flow with credential');
        const decodedToken = JSON.parse(atob(response.credential.split('.')[1]));

        const userData = {
          firstName: formData.firstName || decodedToken.given_name || '',
          lastName: formData.lastName || decodedToken.family_name || '',
          homeArea: formData.homeArea,
          phoneNumber: formData.phoneNumber || ''
        };

        result = await googleRegister(userData, response.credential);
        
        console.log('🔐 LoginModal: Registration result:', result);

        if (result.success) {
          console.log('✅ LoginModal: Registration successful');
          const successMsg = `Welcome to SafeVision${result.username ? ', ' + result.username : ''}! Please check your email to verify your account.`;
          notif.success('Google Signup Successful!', successMsg);
          toast.success(`🎉 Registration successful! Welcome to SafeVision`);
          // Always navigate to login after successful registration
          navigate('/login');
          if (isModal) {
            closeModal();
          }
        } else {
          console.error('🔐 LoginModal: Registration failed with error:', result.error);
          
          let errorMessage = result.error || 'Google registration failed';
          const lowerError = errorMessage.toLowerCase();
          if (lowerError.includes('already registered') || 
              lowerError.includes('already exists') || 
              lowerError.includes('email exists') || 
              lowerError.includes('duplicate')) {
             errorMessage = "Email is already registered. Please Sign In.";
          }
          
          setErrors({ general: errorMessage });
          notif.error('Google Signup Failed', errorMessage);
          toast.error(errorMessage);
        }
      }
    } catch (error) {
      console.error('🔐 LoginModal: Google auth error caught:', error);
      console.error('🔐 LoginModal: Error message:', error.message);
      const errorMsg = error.message || "Google authentication failed";
      notif.error('Google Authentication Error', errorMsg);
      toast.error("Google authentication failed");
      setErrors({ general: "Google authentication failed" });
    } finally {
      setLoading(false);
    }
  }, [googleLogin, googleRegister, isLogin, formData, isModal, closeModal, navigate, notif]);


  useEffect(() => {
    const initializeGoogleSignIn = () => {
      try {
        console.log('🔐 GoogleSignIn: Initializing Google Sign-In');
        console.log('🔐 GoogleSignIn: window.google available?', !!window.google);
        console.log('🔐 GoogleSignIn: window.google.accounts available?', !!window.google?.accounts);
        
        if (!window.google?.accounts?.id) {
          console.warn('⚠️ GoogleSignIn: Google Identity Services not available');
          toast.error("Google Identity Services not available");
          return;
        }

        const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '1062377219587-u12ic1km1lus47l8vl813mmib0p7cjsp.apps.googleusercontent.com';
        console.log('🔐 GoogleSignIn: Using client ID:', clientId ? clientId.substring(0, 20) + '...' : 'default');

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleLogin,
          auto_select: false,
          cancel_on_tap_outside: true,
          // Drives the wording of Google's auto-personalized button so the
          // register page says "Sign up as X" instead of "Sign in as X".
          context: isLogin ? 'signin' : 'signup',
        });
        
        console.log('✅ GoogleSignIn: Initialized successfully');
      
        const renderButton = () => {
          const buttonElement = document.getElementById('google-signin-button');
          if (buttonElement && window.google?.accounts?.id) {
            console.log('🔐 GoogleSignIn: Rendering button');
            buttonElement.innerHTML = '';
            
            window.google.accounts.id.renderButton(buttonElement, {
              theme: 'filled_black',
              size: 'large',
              text: isLogin ? 'signin_with' : 'signup_with',
              shape: 'pill',
              logo_alignment: 'left',
              // Google caps width at 400px and uses this same iframe for both
              // the regular "Sign in with Google" button AND the wider
              // personalized "Sign in as <name>" pill. Pick a value large
              // enough that the personalized variant doesn't clip the G logo.
              width: Math.min(400, Math.max(320, buttonElement.offsetWidth || 360)),
            });
            console.log('✅ GoogleSignIn: Button rendered successfully');
          } else {
            console.warn('⚠️ GoogleSignIn: Button element not found or Google not ready');
          }
        };
        renderButton();
      } catch (error) {
        console.error('❌ GoogleSignIn: Initialization failed:', error);
        toast.error("Google Sign-In initialization failed");
      }
    };
  
    const loadGoogleScript = () => {
      console.log('🔐 GoogleSignIn: Loading Google script');
      if (window.google && window.google.accounts) {
        console.log('✅ GoogleSignIn: Google already loaded, initializing');
        initializeGoogleSignIn();
      } else {
        const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
        if (existingScript) {
          console.log('🔐 GoogleSignIn: Removing existing script');
          existingScript.remove();
        }

        console.log('🔐 GoogleSignIn: Creating new script element');
        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onload = () => {
          console.log('✅ GoogleSignIn: Script loaded successfully');
          setTimeout(initializeGoogleSignIn, 1000);
        };
        script.onerror = () => {
          console.error('❌ GoogleSignIn: Failed to load Google Sign-In script');
          toast.error("Failed to load Google Sign-In script");
        };
        document.head.appendChild(script);
      }
    };

    if (isOpen || isPage) {
      console.log('🔐 GoogleSignIn: Modal/Page is open, loading script');
      loadGoogleScript();
    }

    return () => {
      const buttonElement = document.getElementById('google-signin-button');
      if (buttonElement) {
        buttonElement.innerHTML = '';
      }
    };
  }, [isLogin, handleGoogleLogin, isOpen, isPage]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();

    // Skip validation for Google 2FA - only need the 2FA code
    if (!isGoogleLogin2FA && !validateForm()) {
      notif.error('Validation Error', 'Please fill in all required fields correctly');
      return;
    }

    // Validate 2FA code if required for Google login
    if (isGoogleLogin2FA && !twoFactorCode) {
      setErrors({ twoFactorCode: '2FA code is required' });
      notif.error('2FA Required', 'Please enter your two-factor authentication code');
      return;
    }

    setErrors({});
    setLoading(true);

    try {
      if (isLogin) {
        let result;

        if (isGoogleLogin2FA && pendingGoogleCredential) {
          // Handle Google login with 2FA
          console.log('🔐 LoginModal: Submitting Google login with 2FA');
          result = await googleLogin(pendingGoogleCredential, twoFactorCode, rememberMe);
        } else {
          // Regular login
          result = await login(formData.email, formData.password, requires2FA ? twoFactorCode : null, rememberMe);
        }

        if (result.success) {
          console.log('✅ Login successful, showing notification');
          setRateLimitInfo(null);
          notif.success('Login Successful', `Welcome back, ${result.username || 'User'}!`);
          // FIXED: Respect the redirect state
          const fromPath = location.state?.from 
            ? `${location.state.from.pathname}${location.state.from.search}${location.state.from.hash}` 
            : '/dashboard';
          navigate(fromPath, { replace: true });
          if (isModal) {
            closeModal();
          }
          setIsGoogleLogin2FA(false);
          setPendingGoogleCredential(null);
        } else if (result.rate_limited) {
          // Account locked due to too many failed attempts
          console.log('🔒 Account rate limited');
          const retrySeconds = result.retryAfter || 1800;
          setRateLimitInfo({ locked: true, retryAfter: retrySeconds, message: result.error, email: currentEmail });
          setErrors({ general: result.error });
          notif.error('Account Locked', result.error || 'Too many failed attempts. Please try again later.');
        } else if (result.requires_email_otp) {
          // Mandatory email OTP for admin/superadmin
          console.log('🔐 Email OTP required for admin/superadmin');
          const otpData = {
            user_id: result.user_id,
            username: result.username,
            role: result.role,
            message: result.message,
          };
          setRequiresEmailOtp(true);
          setPendingOtpData(otpData);
          setOtpCountdown(300); // 5 minutes
          // Persist OTP state so it survives page refresh / navigation to email
          sessionStorage.setItem('pending_otp_data', JSON.stringify(otpData));
          sessionStorage.setItem('otp_expiry_time', String(Date.now() + 300 * 1000));
          setErrors({});
          notif.info('Verification Required', result.message || 'A verification code has been sent to your email.');
        } else if (result.requires_2fa_setup) {
          // Admin must set up 2FA before they can fully log in
          console.log('🔐 Admin 2FA setup required');
          setAdmin2FASetup({
            token: result.access_token,
            username: result.username,
            message: result.message,
          });
          notif.warning('2FA Setup Required', result.message || 'Admin accounts require two-factor authentication setup.');
        } else if (result.requires_2fa) {
          console.log('ℹ️ 2FA required, showing notification');
          setRequires2FA(true);
          setErrors({});
          notif.info('2FA Required', 'Please enter your two-factor authentication code');
        } else if (result.requires_verification) {
          console.log('⚠️ Email verification required, showing notification');
          setErrors({ general: result.error });
          notif.warning('Email Verification Required', 'Please verify your email address before logging in. Check your inbox for the verification link.');
        } else {
          console.log('❌ Login failed, showing notification. Error:', result.error);
          setErrors({ general: result.error });
          // Check if error message contains remaining attempts info
          if (result.error && result.error.includes('attempt(s) remaining')) {
            notif.warning('Login Failed', result.error);
          } else {
            notif.error('Login Failed', result.error || 'Invalid credentials');
          }
          setIsGoogleLogin2FA(false);
          setPendingGoogleCredential(null);
        }
      } else {
        if (formData.password !== formData.confirmPassword) {
          setErrors({ confirmPassword: "Passwords do not match" });
          notif.error('Password Mismatch', 'The passwords you entered do not match');
          setLoading(false);
          return;
        }

        const result = await register({
          first_name: formData.firstName,
          last_name: formData.lastName,
          email: formData.email,
          password: formData.password,
          home_area: formData.homeArea,
          phone_number: formData.phoneNumber,
          username: generatedUsername || undefined
        });

        if (result.success) {
          notif.success('Registration Successful!', `Welcome! Please check your email to verify your account.`);
          toast.success(`🎉 Registration successful!`, {
            position: "top-center",
            autoClose: 3000,
            theme: "colored",
          });

          if (isModal) {
            closeModal();
          } else {
            // Navigate to login page after successful registration
            navigate('/login');
          }
        } else {
          setErrors({ general: result.error });
          notif.error('Registration Failed', result.error || 'Unable to create account');
        }
      }
    } catch (error) {
      console.error('Auth error:', error);
      const errorMessage = error.message || "An unexpected error occurred";

      // Handle rate limiting errors thrown as exceptions
      if (error.status === 429) {
        const retrySeconds = error.retryAfter || 1800;
        setRateLimitInfo({ locked: true, retryAfter: retrySeconds, message: errorMessage, email: currentEmail });
        setErrors({ general: errorMessage });
        notif.error('Account Locked', errorMessage);
      } else if (errorMessage.includes('verify your email')) {
        notif.warning('Email Verification Required', 'Please verify your email address before logging in. Check your inbox for the verification link.');
      } else if (errorMessage.includes('Invalid credentials') || errorMessage.includes('Invalid email or password')) {
        notif.error('Invalid Credentials', 'The email or password you entered is incorrect');
      } else if (errorMessage.includes('attempt(s) remaining')) {
        notif.warning('Login Failed', errorMessage);
        setErrors({ general: errorMessage });
      } else {
        notif.error('Error', errorMessage);
      }

      if (!error.status || error.status !== 429) {
        toast.error(errorMessage);
        setErrors({ general: errorMessage });
      }
      // Reset Google 2FA states on error
      setIsGoogleLogin2FA(false);
      setPendingGoogleCredential(null);
    } finally {
      setLoading(false);
    }
  }, [validateForm, isLogin, formData, login, register, requires2FA, twoFactorCode, isModal, closeModal, isGoogleLogin2FA, pendingGoogleCredential, googleLogin, showNotification, navigate, rememberMe]);

  // --- OTP Verification Handler ---
  const handleVerifyOtp = useCallback(async () => {
    if (!emailOtpCode || emailOtpCode.length !== 6) {
      notif.error('Invalid Code', 'Please enter a valid 6-digit verification code');
      return;
    }
    setLoading(true);
    try {
      const data = await apiService.verifyLoginOtp(pendingOtpData.user_id, emailOtpCode);
      // Note: If `data.requires_password_change` is true the backend returns the access_token
      // and the dashboard surfaces a non-blocking change-password modal that supports "Remind Me Later".
      if (data.access_token) {
        // Login complete (works for both first-login & subsequent logins)
        const result = await completeOtpLogin(data.access_token, data.refresh_token, rememberMe);
        if (result.success) {
          setRequiresEmailOtp(false);
          setPendingOtpData(null);
          setEmailOtpCode('');
          setOtpCountdown(0);
          sessionStorage.removeItem('pending_otp_data');
          sessionStorage.removeItem('otp_expiry_time');
          // Surface a hint when this is a first login that still has the change-required flag,
          // so the dashboard popup is expected by the user.
          if (data.requires_password_change) {
            notif.warning('Password Change Recommended', 'For security, please change your temporary password from the Profile menu.');
          } else {
            notif.success('Login Successful', `Welcome back, ${pendingOtpData.username || 'Admin'}!`);
          }
          const fromPath = location.state?.from
            ? `${location.state.from.pathname}${location.state.from.search}${location.state.from.hash}`
            : '/dashboard';
          navigate(fromPath, { replace: true });
          if (isModal) closeModal();
        } else {
          notif.error('Login Failed', result.error || 'Failed to complete login');
        }
      }
    } catch (error) {
      notif.error('Verification Failed', error.message || 'Invalid or expired verification code');
    } finally {
      setLoading(false);
    }
  }, [emailOtpCode, pendingOtpData, completeOtpLogin, navigate, isModal, closeModal, notif, rememberMe]);

  // --- Resend OTP Handler ---
  const handleResendOtp = useCallback(async () => {
    if (resendingOtp) return;
    setResendingOtp(true);
    try {
      await apiService.resendLoginOtp(pendingOtpData.user_id);
      setOtpCountdown(300); // Reset to 5 minutes
      sessionStorage.setItem('otp_expiry_time', String(Date.now() + 300 * 1000));
      setEmailOtpCode('');
      notif.success('Code Resent', 'A new verification code has been sent to your email.');
    } catch (error) {
      notif.error('Resend Failed', error.message || 'Failed to resend verification code');
    } finally {
      setResendingOtp(false);
    }
  }, [pendingOtpData, resendingOtp, notif]);

  // --- Force Password Change Handler ---
  const handleForcePasswordChange = useCallback(async () => {
    const errors = {};
    const role = pendingPasswordChangeRole || 'admin';
    const minLen = role === 'superadmin' ? 12 : 10;

    if (!newPassword) {
      errors.newPassword = 'New password is required';
    } else if (newPassword.length < minLen) {
      errors.newPassword = `Password must be at least ${minLen} characters`;
    } else if (!/[A-Z]/.test(newPassword)) {
      errors.newPassword = 'Password must contain at least one uppercase letter';
    } else if (!/[a-z]/.test(newPassword)) {
      errors.newPassword = 'Password must contain at least one lowercase letter';
    } else if (!/[0-9]/.test(newPassword)) {
      errors.newPassword = 'Password must contain at least one number';
    } else if (role === 'superadmin' && !/[^A-Za-z0-9]/.test(newPassword)) {
      errors.newPassword = 'Password must contain at least one special character';
    }

    if (!confirmNewPassword) {
      errors.confirmNewPassword = 'Please confirm your new password';
    } else if (newPassword !== confirmNewPassword) {
      errors.confirmNewPassword = 'Passwords do not match';
    }

    if (Object.keys(errors).length > 0) {
      setPasswordChangeErrors(errors);
      return;
    }

    setPasswordChangeErrors({});
    setLoading(true);
    try {
      await apiService.forceChangePassword(pendingPasswordChangeToken, newPassword, confirmNewPassword);
      // After password change, complete login
      const result = await completeOtpLogin(pendingPasswordChangeToken, null, rememberMe);
      if (result.success) {
        setRequiresPasswordChange(false);
        setPendingPasswordChangeToken(null);
         setNewPassword('');
        setConfirmNewPassword('');
        notif.success('Password Changed', 'Your password has been updated. Welcome!');
        // FIXED: Respect the redirect state
        const fromPath = location.state?.from 
          ? `${location.state.from.pathname}${location.state.from.search}${location.state.from.hash}` 
          : '/dashboard';
        navigate(fromPath, { replace: true });
        if (isModal) closeModal();
      } else {
        notif.error('Login Failed', result.error || 'Failed to complete login after password change');
      }
    } catch (error) {
      notif.error('Password Change Failed', error.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  }, [newPassword, confirmNewPassword, pendingPasswordChangeToken, pendingPasswordChangeRole, completeOtpLogin, navigate, isModal, closeModal, notif, rememberMe]);

  // --- Cancel OTP / Go back handler ---
  const handleCancelOtp = useCallback(() => {
    setRequiresEmailOtp(false);
    setPendingOtpData(null);
    setEmailOtpCode('');
    setOtpCountdown(0);
    if (otpCountdownRef.current) clearInterval(otpCountdownRef.current);
    // Clear OTP persistence
    sessionStorage.removeItem('pending_otp_data');
    sessionStorage.removeItem('otp_expiry_time');
  }, []);

  const handleCancelPasswordChange = useCallback(() => {
    setRequiresPasswordChange(false);
    setPendingPasswordChangeToken(null);
    setNewPassword('');
    setConfirmNewPassword('');
    setPasswordChangeErrors({});
  }, []);

  const toggleMode = useCallback(() => {
    if (isSwitching) return;
    setIsSwitching(true);

    setAnimationStage("switching");

    setTimeout(() => {
      setIsLogin(prev => !prev);

      // Reset formData after mode switch
      setFormData({
        email: "",
        firstName: "",
        lastName: "",
        password: "",
        confirmPassword: "",
        homeArea: "",
        phoneNumber: ""
      });
      setErrors({});
      setGeneratedUsername("");
      setRequires2FA(false);
      setTwoFactorCode("");
      setPendingGoogleCredential(null);
      setIsGoogleLogin2FA(false);
      setAnimationStage("entered");
      setIsSwitching(false);
    }, 300); // match animation duration
  }, [isSwitching]);

  // Memoize the Content component to prevent re-renders that cause input focus loss
  // Must be defined before any early returns to maintain hook order
  const Content = useMemo(() => (
    <div className={`auth-container ${animationStage} ${isLogin ? 'login-mode' : 'register-mode'}`}>
      {/* Animated Background Elements */}
      <div className="auth-bg-elements">
        <div className="auth-floating-orb orb-1"></div>
        <div className="auth-floating-orb orb-2"></div>
        <div className="auth-floating-orb orb-3"></div>
      </div>

      {/* (close button moved out — see Modal/Page render below) */}

      {/* Two Column Layout */}
      <div className="auth-layout">
        {/* Left Side - Character */}
        <div className="auth-character-section">
          <SafeVisionCharacter isLogin={isLogin} />
        </div>

        {/* Right Side - Form */}
        <div className="auth-form-section">
          <div className="auth-header">
            {isModal && (
              <button
                type="button"
                className="modal-close-button"
                onClick={closeModal}
                aria-label="Close"
              >
                <i className="fas fa-times"></i>
              </button>
            )}
            <div className="auth-badge">
              <i className="fas fa-shield-alt"></i>
              <span>SafeVision {isLogin ? "Login" : "Register"}</span>
            </div>
            <h2 className="auth-title">
              {isLogin ? "Welcome Back" : "Join SafeVision"}
            </h2>
            <p className="auth-subtitle">
              {isLogin
                ? "Sign in to access your safety dashboard"
                : "Create your account to start enhancing urban safety"}
            </p>
          </div>

          {/* === EMAIL OTP VERIFICATION SCREEN === */}
          {requiresEmailOtp && pendingOtpData ? (
            <div className="otp-verification-container" style={{ padding: '20px 0' }}>
              <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                <i className="fas fa-envelope-open-text" style={{ fontSize: '48px', color: 'var(--accent-color, #3b82f6)', marginBottom: '12px', display: 'block' }}></i>
                <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary, #1a1a2e)' }}>Verify Your Identity</h3>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-secondary, #6b7280)' }}>
                  A 6-digit verification code has been sent to your email.
                  <br />Please enter it below to continue.
                </p>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label htmlFor="emailOtpCode" style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Verification Code</label>
                <input
                  type="text"
                  id="emailOtpCode"
                  value={emailOtpCode}
                  onChange={(e) => setEmailOtpCode(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                  placeholder="Enter 6-digit code"
                  maxLength="6"
                  disabled={loading}
                  style={{
                    width: '100%', padding: '12px 16px', fontSize: '20px', textAlign: 'center',
                    letterSpacing: '8px', fontWeight: 700, borderRadius: '8px',
                    border: '2px solid var(--border-color, #d1d5db)', outline: 'none',
                    background: 'var(--bg-secondary, #f9fafb)', color: 'var(--text-primary, #1a1a2e)',
                    boxSizing: 'border-box'
                  }}
                  autoFocus
                />
              </div>

              <div style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary, #6b7280)', marginBottom: '16px' }}>
                {otpCountdown > 0 ? (
                  <span><i className="fas fa-clock"></i> Code expires in {Math.floor(otpCountdown / 60)}:{(otpCountdown % 60).toString().padStart(2, '0')}</span>
                ) : (
                  <span style={{ color: '#ef4444' }}><i className="fas fa-exclamation-triangle"></i> Code expired</span>
                )}
                <span style={{ margin: '0 8px' }}>|</span>
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={resendingOtp}
                  style={{
                    background: 'none', border: 'none', color: 'var(--accent-color, #3b82f6)',
                    cursor: resendingOtp ? 'not-allowed' : 'pointer', textDecoration: 'underline',
                    fontSize: '13px', opacity: resendingOtp ? 0.5 : 1
                  }}
                >
                  {resendingOtp ? 'Resending...' : 'Resend Code'}
                </button>
              </div>

              <button
                type="button"
                onClick={handleVerifyOtp}
                disabled={loading || emailOtpCode.length !== 6}
                className="auth-button"
                style={{ width: '100%', marginBottom: '10px' }}
              >
                {loading ? (
                  <><div className="spinner"></div> Verifying...</>
                ) : (
                  <><i className="fas fa-check-circle"></i> Verify & Sign In</>
                )}
              </button>

              <button
                type="button"
                onClick={handleCancelOtp}
                style={{
                  width: '100%', padding: '10px', background: 'none', border: '1px solid var(--border-color, #d1d5db)',
                  borderRadius: '8px', color: 'var(--text-secondary, #6b7280)', cursor: 'pointer', fontSize: '14px'
                }}
              >
                <i className="fas fa-arrow-left"></i> Back to Login
              </button>
            </div>

          /* === FORCE PASSWORD CHANGE SCREEN === */
          ) : requiresPasswordChange && pendingPasswordChangeToken ? (
            <div className="force-password-change-container" style={{ padding: '20px 0' }}>
              <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                <i className="fas fa-key" style={{ fontSize: '48px', color: '#f59e0b', marginBottom: '12px', display: 'block' }}></i>
                <h3 style={{ margin: '0 0 8px 0', color: 'var(--text-primary, #1a1a2e)' }}>Change Your Password</h3>
                <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-secondary, #6b7280)' }}>
                  For security, you must set a new password before accessing the dashboard.
                  <br />
                  <strong>Minimum {pendingPasswordChangeRole === 'superadmin' ? '12' : '10'} characters</strong> with uppercase, lowercase, numbers{pendingPasswordChangeRole === 'superadmin' ? ', and symbols' : ''}.
                </p>
              </div>

              <div className="form-group" style={{ marginBottom: '14px' }}>
                <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  disabled={loading}
                  style={{
                    width: '100%', padding: '10px 14px', borderRadius: '8px',
                    border: `2px solid ${passwordChangeErrors.newPassword ? '#ef4444' : 'var(--border-color, #d1d5db)'}`,
                    background: 'var(--bg-secondary, #f9fafb)', color: 'var(--text-primary, #1a1a2e)',
                    boxSizing: 'border-box'
                  }}
                />
                {passwordChangeErrors.newPassword && (
                  <div style={{ color: '#ef4444', fontSize: '12px', marginTop: '4px' }}><i className="fas fa-exclamation-circle"></i> {passwordChangeErrors.newPassword}</div>
                )}
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontWeight: 600, marginBottom: '6px', display: 'block' }}>Confirm New Password</label>
                <input
                  type="password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={loading}
                  style={{
                    width: '100%', padding: '10px 14px', borderRadius: '8px',
                    border: `2px solid ${passwordChangeErrors.confirmNewPassword ? '#ef4444' : 'var(--border-color, #d1d5db)'}`,
                    background: 'var(--bg-secondary, #f9fafb)', color: 'var(--text-primary, #1a1a2e)',
                    boxSizing: 'border-box'
                  }}
                />
                {passwordChangeErrors.confirmNewPassword && (
                  <div style={{ color: '#ef4444', fontSize: '12px', marginTop: '4px' }}><i className="fas fa-exclamation-circle"></i> {passwordChangeErrors.confirmNewPassword}</div>
                )}
              </div>

              <button
                type="button"
                onClick={handleForcePasswordChange}
                disabled={loading || !newPassword || !confirmNewPassword}
                className="auth-button"
                style={{ width: '100%', marginBottom: '10px' }}
              >
                {loading ? (
                  <><div className="spinner"></div> Changing Password...</>
                ) : (
                  <><i className="fas fa-lock"></i> Set New Password & Continue</>
                )}
              </button>

              <button
                type="button"
                onClick={handleCancelPasswordChange}
                style={{
                  width: '100%', padding: '10px', background: 'none', border: '1px solid var(--border-color, #d1d5db)',
                  borderRadius: '8px', color: 'var(--text-secondary, #6b7280)', cursor: 'pointer', fontSize: '14px'
                }}
              >
                <i className="fas fa-arrow-left"></i> Cancel
              </button>
            </div>

          ) : (
          /* === NORMAL LOGIN/REGISTER FORM === */
          <form ref={formRef} onSubmit={handleSubmit} className="auth-form">
        <div className="form-fields-container">
          {isLogin ? (
            // Login Form
            <>
              {!isGoogleLogin2FA && commonFields.map(field => (
                <div key={field.id} className={`form-group ${errors[field.name] ? "error" : ""}`}>
                  <label htmlFor={field.id}>{field.label}</label>
                  <div className="input-with-icon">
                    <input
                      type={field.name === "password" ? (showPassword ? "text" : "password") : field.type}
                      id={field.id}
                      name={field.name}
                      value={formData[field.name]}
                      onChange={handleInputChange}
                      onBlur={handleInputBlur}
                      required={field.required}
                      disabled={loading}
                      placeholder={field.placeholder}
                      maxLength={field.maxLength}
                      className={errors[field.name] ? "input-error" : ""}
                    />
                    {field.name === "password" && (
                      <i
                        className={`fa ${showPassword ? "fa-eye-slash" : "fa-eye"} password-toggle-icon`}
                        onClick={() => handleTogglePassword(field.name)}
                      ></i>
                    )}
                  </div>
                  {errors[field.name] && <div className="field-error">{errors[field.name]}</div>}
                </div>
              ))}

              {isGoogleLogin2FA && (
                <div className="form-group" style={{ textAlign: 'center', padding: '10px 0' }}>
                  <p style={{ color: '#666', margin: 0 }}>
                    <i className="fas fa-lock" style={{ marginRight: '8px' }}></i>
                    Completing Google Sign-In with 2FA
                  </p>
                </div>
              )}

              {!isGoogleLogin2FA && (
                <div
                  className="login-options-row"
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    margin: '8px 0 4px',
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <label
                    htmlFor="rememberMe"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      userSelect: 'none',
                    }}
                  >
                    <input
                      type="checkbox"
                      id="rememberMe"
                      name="rememberMe"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      disabled={loading}
                      style={{ cursor: 'pointer' }}
                    />
                    Remember me
                  </label>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setShowForgotPassword(true)}
                    disabled={loading}
                  >
                    Forgot Password?
                  </button>
                </div>
              )}
            </>
          ) : (
            // Registration Form
            <>
              <div className="name-fields-row">
                {registerFields.slice(0, 2).map(field => (
                  <div key={field.id} className={`form-group compact ${errors[field.name] ? "error" : ""}`}>
                    <label htmlFor={field.id}>{field.label}</label>
                    <input
                      type={field.type}
                      id={field.id}
                      name={field.name}
                      value={formData[field.name]}
                      onChange={handleInputChange}
                      onBlur={handleInputBlur}
                      required={field.required}
                      disabled={loading}
                      placeholder={field.placeholder}
                      className={errors[field.name] ? "input-error" : ""}
                    />
                    {errors[field.name] && <div className="field-error">{errors[field.name]}</div>}
                  </div>
                ))}
              </div>


              {generatedUsername && (
                <div className="form-group username-display-group">
                  <label>Generated Username</label>
                  <div className="username-display">
                    <strong>{generatedUsername}</strong>
                    <small>(This will be your username)</small>
                  </div>
                </div>
              )}

              {commonFields.map(field => (
                <div key={field.id} className={`form-group ${errors[field.name] ? "error" : ""}`}>
                  <label htmlFor={field.id}>{field.label}</label>
                  <div className="input-with-icon">
                    <input
                      type={field.name === "password" ? (showPassword ? "text" : "password") : field.type}
                      id={field.id}
                      name={field.name}
                      value={formData[field.name]}
                      onChange={handleInputChange}
                      onBlur={handleInputBlur}
                      required={field.required}
                      disabled={loading}
                      placeholder={field.placeholder}
                      className={errors[field.name] ? "input-error" : ""}
                    />
                    {field.name === "password" && (
                      <i
                        className={`fa ${showPassword ? "fa-eye-slash" : "fa-eye"} password-toggle-icon`}
                        onClick={() => handleTogglePassword(field.name)}
                      ></i>
                    )}
                  </div>
                  {errors[field.name] && <div className="field-error">{errors[field.name]}</div>}
                </div>
              ))}

              {registerFields.slice(2).map(field => (
                <div key={field.id} className={`form-group ${errors[field.name] ? "error" : ""}`}>
                  <label htmlFor={field.id}>{field.label}</label>
                  <div className="input-with-icon">
                    <input
                      type={field.name === "confirmPassword" ? (showConfirmPassword ? "text" : "password") : field.type}
                      id={field.id}
                      name={field.name}
                      value={formData[field.name]}
                      onChange={handleInputChange}
                      onBlur={handleInputBlur}
                      required={field.required}
                      disabled={loading}
                      placeholder={field.placeholder}
                      className={errors[field.name] ? "input-error" : ""}
                    />
                    {field.name === "confirmPassword" && (
                      <i
                        className={`fa ${showConfirmPassword ? "fa-eye-slash" : "fa-eye"} password-toggle-icon`}
                        onClick={() => handleTogglePassword(field.name)}
                      ></i>
                    )}
                  </div>
                  {errors[field.name] && <div className="field-error">{errors[field.name]}</div>}
                </div>
              ))}

              
            </>
          )}

          {/* Home Area Field — registration only */}
          {!isLogin && (
            <div className="form-group">
              <small className="optional-text">Optional field, helps with area-specific alerts</small>
              <label htmlFor="homeArea">Home Area (Optional)</label>
              <input
                type="text"
                id="homeArea"
                name="homeArea"
                value={formData.homeArea}
                onChange={handleInputChange}
                disabled={loading}
                placeholder="Enter your home area (e.g., Gulberg, DHA)"
              />
            </div>
          )}

          {/* Phone Number Field */}
          {!isLogin && (
            <div className="form-group">
              <small className="optional-text">Optional field, used for emergency notifications</small>
              <label htmlFor="phoneNumber">Phone Number (Optional)</label>
              <input
                type="tel"
                id="phoneNumber"
                name="phoneNumber"
                value={formData.phoneNumber}
                onChange={handleInputChange}
                disabled={loading}
                placeholder="Enter your phone number (e.g., +92-300-1234567)"
              />
            </div>
          )}

          {/* 2FA Field */}
          {requires2FA && (
            <div className="form-group">
              <label htmlFor="twoFactorCode">
                Two-Factor Authentication Code
                {isGoogleLogin2FA && <small className="google-2fa-note"> (for Google Sign-In)</small>}
              </label>
              <div className="input-with-icon">
                <input
                  type="text"
                  id="twoFactorCode"
                  name="twoFactorCode"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="Enter your 2FA code"
                  maxLength="6"
                />
              </div>
            </div>
          )}
        </div>

        {/* Rate Limit Lockout Banner */}
        {isRateLimitedForCurrentEmail && (
          <div className="rate-limit-banner">
            <div className="rate-limit-icon">
              <i className="fas fa-lock"></i>
            </div>
            <div className="rate-limit-text">
              <strong>Account Temporarily Locked</strong>
              <p>{rateLimitInfo.message}</p>
              {rateLimitInfo.retryAfter > 0 && (
                <span className="rate-limit-timer">
                  <i className="fas fa-clock"></i>{' '}
                  Try again in {Math.floor(rateLimitInfo.retryAfter / 60)}:{(rateLimitInfo.retryAfter % 60).toString().padStart(2, '0')}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Admin 2FA Setup Required Banner */}
        {admin2FASetup && (
          <div className="admin-2fa-setup-banner">
            <div className="admin-2fa-icon">
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className="admin-2fa-text">
              <strong>Two-Factor Authentication Required</strong>
              <p>{admin2FASetup.message}</p>
              <button
                type="button"
                className="admin-2fa-setup-btn"
                onClick={() => {
                  // Navigate to 2FA setup with the temporary token
                  navigate('/dashboard', { state: { setup2FA: true, tempToken: admin2FASetup.token } });
                  if (isModal) closeModal();
                }}
              >
                <i className="fas fa-qrcode"></i> Set Up 2FA Now
              </button>
            </div>
          </div>
        )}

        {errors.general && !rateLimitInfo?.locked && (
          <div className="error-message general-error">
            <i className="fas fa-exclamation-triangle"></i>
            <span>{errors.general}</span>
          </div>
        )}

        <button
          type="submit"
          className={`auth-button ${loading ? 'loading' : ''}`}
          disabled={loading || isRateLimitedForCurrentEmail}
        >
          {loading ? (
            <>
              <div className="spinner"></div>
              {isLogin ? "Signing In..." : "Creating Account..."}
            </>
          ) : isRateLimitedForCurrentEmail ? (
            <>
              <i className="fas fa-lock"></i> Account Locked
            </>
          ) : (
            isLogin ? "Sign In" : "Create Account"
          )}
          </button>
          </form>
          )}

          {/* Google Sign-In - hide during OTP/password change screens */}
          {!requiresEmailOtp && !requiresPasswordChange && (
            <>
              <div className="google-signin-section">
                <div className="divider">
                  <span>or continue with</span>
                </div>
                <div id="google-signin-button" className="google-button-container"></div>
              </div>

              <div className="auth-toggle">
                <p>
                  {isLogin ? "Don't have an account?" : "Already have an account?"}
                  <button
                    type="button"
                    className="toggle-button"
                    onClick={toggleMode}
                    disabled={loading}
                  >
                    {isLogin ? "Create Account" : "Sign In"}
                  </button>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  ), [
    animationStage,
    isLogin,
    errors,
    formData,
    loading,
    showPassword,
    showConfirmPassword,
    generatedUsername,
    requires2FA,
    twoFactorCode,
    isGoogleLogin2FA,
    pendingGoogleCredential,
    rateLimitInfo,
    admin2FASetup,
    requiresEmailOtp,
    emailOtpCode,
    pendingOtpData,
    otpCountdown,
    resendingOtp,
    requiresPasswordChange,
    pendingPasswordChangeToken,
    pendingPasswordChangeRole,
    newPassword,
    confirmNewPassword,
    passwordChangeErrors,
    handleInputChange,
    handleInputBlur,
    handleTogglePassword,
    handleSubmit,
    handleVerifyOtp,
    handleResendOtp,
    handleForcePasswordChange,
    handleCancelOtp,
    handleCancelPasswordChange,
    onForgotPassword,
    toggleMode
    // Note: showNotification is intentionally NOT in dependencies to avoid closure issues
  ]);

  if (isModal && !isOpen) return null;

  // Render as modal
  if (isModal) {
    return (
      <>
        {!showForgotPassword && (
          <div
            className={`modal-overlay ${animationStage}`}
            onClick={() => {
              if (animationStage === "entered") closeModal();
            }}
          >
            {/* Persistent close button — sibling of .modal-content,
                anchored to viewport via position:fixed so nothing can clip it. */}
            <button
              type="button"
              className="auth-modal-close"
              onClick={(e) => { e.stopPropagation(); closeModal(); }}
              aria-label="Close"
            >
              <i className="fas fa-times"></i>
            </button>
            <div
              className={`modal-content ${animationStage}`}
              onClick={(e) => e.stopPropagation()}
              style={{ position: 'relative' }}
            >

              {Content}
            </div>
          </div>
        )}
        {/* Global NotificationContainer is mounted at app root */}
        <ForgotPasswordModal 
          show={showForgotPassword} 
          onHide={() => setShowForgotPassword(false)}
        />
      </>
    );
  }

  // Render as page
  return (
    <div className="login-page">
      {/* Persistent close button — always shown so users can return home
          even when login is rendered on the standalone /login page route. */}
      <button
        type="button"
        className="auth-modal-close"
        onClick={() => {
          if (typeof closeModal === 'function') closeModal();
          else if (typeof window !== 'undefined') window.location.href = '/';
        }}
        aria-label="Close"
      >
        <i className="fas fa-times"></i>
      </button>
      {Content}
      <ToastContainer />
      {/* Global NotificationContainer is mounted at app root */}
      <ForgotPasswordModal
        show={showForgotPassword}
        onHide={() => setShowForgotPassword(false)}
      />
    </div>
  );
};

export default LoginModal;
