import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { apiService } from '../services/apiService_updated';
import locationTrackingService from '../services/LocationTrackingService';

const AuthContext = createContext();

// Get API_BASE_URL from the apiService or define it here
const API_BASE_URL = apiService.API_BASE_URL || 'http://localhost:8000';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  const [browserNotificationsEnabled, setBrowserNotificationsEnabled] = useState(
    'Notification' in window && Notification.permission === 'granted'
  );

  // Location tracking state
  const [locationTrackingEnabled, setLocationTrackingEnabled] = useState(false);
  const [locationPermission, setLocationPermission] = useState('prompt'); // 'granted', 'denied', 'prompt'
  const [currentLocation, setCurrentLocation] = useState(null);
  const [locationTrackingStatus, setLocationTrackingStatus] = useState({
    isTracking: false,
    lastUpdate: null,
    error: null
  });

  // Risk alert state
  const [riskAlerts, setRiskAlerts] = useState([]);
  const [lastRiskCheck, setLastRiskCheck] = useState(null);

  // Token storage keys
  const TOKEN_KEY = 'SafeVision_token';
  const REFRESH_TOKEN_KEY = 'SafeVision_refresh_token';
  const USER_KEY = 'SafeVision_user';

  // Clear all auth data
  const clearAuthData = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);

    if (locationTrackingService) {
      locationTrackingService.stopTracking();
      setLocationTrackingEnabled(false);
      setLocationTrackingStatus({ isTracking: false, lastUpdate: null, error: null });
    }
  }, []);

  // Save auth data
  const saveAuthData = useCallback((newToken, newRefreshToken, userData, rememberMe = false) => {
    const storage = rememberMe ? localStorage : sessionStorage;

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);

    storage.setItem(TOKEN_KEY, newToken);
    storage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
    storage.setItem(USER_KEY, JSON.stringify(userData));

    setToken(newToken);
    setRefreshToken(newRefreshToken);
    setUser(userData);
  }, []);

  const updateUser = useCallback((userData) => {
    setUser(userData);

    const storage = localStorage.getItem(TOKEN_KEY) ? localStorage : sessionStorage;
    storage.setItem(USER_KEY, JSON.stringify(userData));
  }, []);

  // Refresh token function
  const refreshAuthToken = useCallback(async () => {
    try {
      const currentRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY);

      if (!currentRefreshToken) {
        return false;
      }

      const response = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: currentRefreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();

      if (data.access_token) {
        const userData = await apiService.getCurrentUser(data.access_token);
        const storage = localStorage.getItem(REFRESH_TOKEN_KEY) ? localStorage : sessionStorage;
        saveAuthData(data.access_token, currentRefreshToken, userData, storage === localStorage);
        return true;
      }

      return false;
    } catch (error) {
      // Silently fail — callers handle the false return value
      return false;
    }
  }, [saveAuthData]);

  // Initialize auth state from storage
  const initializeAuth = useCallback(async () => {
    try {
      setLoading(true);

      let storedToken = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
      let storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY);
      let storedUser = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);

      if (!storedToken || !storedUser) {
        setLoading(false);
        setInitialized(true);
        return;
      }

      try {
        const userData = await apiService.getCurrentUser(storedToken);

        if (userData && userData.username) {
          setToken(storedToken);
          setRefreshToken(storedRefreshToken);
          setUser(userData);
        } else {
          const refreshSuccess = await refreshAuthToken();
          if (!refreshSuccess) {
            clearAuthData();
          }
        }
      } catch (error) {
        const refreshSuccess = await refreshAuthToken();

        if (!refreshSuccess) {
          if (error.message.includes('Network') || error.message.includes('Failed to fetch')) {
            try {
              const cachedUser = JSON.parse(storedUser);
              if (cachedUser && cachedUser.username) {
                setToken(storedToken);
                setRefreshToken(storedRefreshToken);
                setUser(cachedUser);
              } else {
                clearAuthData();
              }
            } catch {
              clearAuthData();
            }
          } else {
            clearAuthData();
          }
        }
      }
    } catch (error) {
      // Non-critical init error — leave auth data intact
    } finally {
      setLoading(false);
      setInitialized(true);
    }
  }, [clearAuthData, refreshAuthToken]);

  // Auto-initialize auth on mount
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  // Initialize location tracking service when user is authenticated
  useEffect(() => {
    if (user && token && initialized) {
      console.log('📍 Initializing location tracking service...');

      // Initialize location tracking service
      locationTrackingService.initialize(token, {
        onLocationUpdate: (locationData) => {
          console.log('📍 Location updated:', locationData);
          setCurrentLocation(locationData.position);
          setLocationTrackingStatus(prev => ({
            ...prev,
            lastUpdate: new Date(),
            error: null
          }));

          // Check for high-risk areas and trigger alerts
          checkRiskAlerts(locationData);
        },
        onError: (error) => {
          console.error('📍 Location tracking error:', error);
          setLocationTrackingStatus(prev => ({
            ...prev,
            error: error.message
          }));
        },
        onPermissionChange: (permission) => {
          console.log('📍 Location permission changed:', permission);
          setLocationPermission(permission);
        }
      });

      // Enhanced permission monitoring with real-time updates
      if (navigator.permissions) {
        navigator.permissions.query({ name: 'geolocation' }).then(result => {
          setLocationPermission(result.state);

          // Listen for permission changes
          result.onchange = () => {
            console.log('📍 Permission state changed to:', result.state);
            setLocationPermission(result.state);

            // Provide user feedback based on permission state
            if (result.state === 'denied') {
              console.warn('📍 Location permission denied - user will need to enable manually');
            } else if (result.state === 'granted') {
              console.log('📍 Location permission granted - tracking can proceed');
            }
          };
        }).catch((error) => {
          console.warn('📍 Permission query not supported:', error);
          setLocationPermission('unknown');
        });
      }
    }
  }, [user, token, initialized]);

  useEffect(() => {
    if (user && token) {
      // Check browser notification permission
      if ('Notification' in window) {
        setBrowserNotificationsEnabled(Notification.permission === 'granted');
      }
    }
  }, [user, token]);

  // Location tracking functions
  const startLocationTracking = useCallback(async () => {
    if (!token) {
      throw new Error('Authentication required for location tracking');
    }

    try {
      console.log('📍 Starting location tracking...');
      const result = await locationTrackingService.startTracking();

      if (result.success) {
        setLocationTrackingEnabled(true);
        setLocationTrackingStatus(prev => ({
          ...prev,
          isTracking: true,
          error: null
        }));

        console.log('📍 Location tracking started successfully');
        return { success: true };
      }
    } catch (error) {
      console.error('📍 Failed to start location tracking:', error);
      setLocationTrackingStatus(prev => ({
        ...prev,
        error: error.message
      }));
      throw error;
    }
  }, [token]);

  const stopLocationTracking = useCallback(() => {
    console.log('📍 Stopping location tracking...');
    locationTrackingService.stopTracking();

    setLocationTrackingEnabled(false);
    setLocationTrackingStatus(prev => ({
      ...prev,
      isTracking: false,
      error: null
    }));

    console.log('📍 Location tracking stopped');
  }, []);

  const requestLocationPermission = useCallback(async () => {
    try {
      await locationTrackingService.requestPermission();
      return { success: true };
    } catch (error) {
      console.error('📍 Location permission request failed:', error);
      throw error;
    }
  }, []);

  const getLocationHistory = useCallback(async (days = 7) => {
    try {
      return await locationTrackingService.getLocationHistory(days);
    } catch (error) {
      console.error('📍 Failed to get location history:', error);
      throw error;
    }
  }, []);

  const clearLocationHistory = useCallback(async (daysToKeep = null) => {
    try {
      return await locationTrackingService.clearLocationHistory(daysToKeep);
    } catch (error) {
      console.error('📍 Failed to clear location history:', error);
      throw error;
    }
  }, []);

  const updateLocationPreferences = useCallback(async (preferences) => {
    try {
      return await locationTrackingService.updateTrackingPreferences(preferences);
    } catch (error) {
      console.error('📍 Failed to update location preferences:', error);
      throw error;
    }
  }, []);

  const googleLogin = async (credential, twoFactorCode = null, rememberMe = true) => {
    try {
      console.log('🔐 AuthContext: Starting Google login...');
      const result = await apiService.googleLogin(credential, twoFactorCode);

      console.log('🔐 AuthContext: Google login result:', result);

      if (result.access_token) {
        console.log('🔐 AuthContext: Access token received, fetching user data...');
        // Fetch user data with the new token (same as regular login)
        const userData = await apiService.getCurrentUser(result.access_token);

        console.log('🔐 AuthContext: User data fetched:', userData);
        // Save auth data properly using the context's saveAuthData function
        const refreshToken = result.refresh_token || result.access_token; // Fallback if no refresh token
        saveAuthData(result.access_token, refreshToken, userData, rememberMe);
        return {
          success: true,
          isNewUser: result.is_new_user
        };
      } else if (result.requires_2fa) {
        console.log('🔐 AuthContext: 2FA required, passing through to LoginModal');
        return {
          requires_2fa: true,
          message: result.message,
          user_info: result.user_info
        };
      } else if (result.requiresRegistration) {
        console.log('🔐 AuthContext: Registration required');
        return {
          requiresRegistration: true,
          user_info: result.user_info
        };
      } else if (result.requires_verification) {
        console.log('🔐 AuthContext: Email verification required');
        return {
          requires_verification: true,
          message: result.message
        };
      } else {
        console.warn('🔐 AuthContext: No access token in result:', result);
        return { success: false, error: result.detail || result.error || 'Google login failed' };
      }
    } catch (error) {
      console.error('🔐 AuthContext: Google login catch block - error:', error);
      console.error('🔐 AuthContext: Error message:', error.message);
      console.error('🔐 AuthContext: Error response:', error.response);
      
      const errorMessage = error.response?.data?.detail || error.message || 'Google login failed';

      // Handle specific cases
      if (errorMessage.includes("User not found") || 
          errorMessage.includes("does not exist") || 
          errorMessage.includes("not registered") ||
          errorMessage.includes("account not found")) {
        console.log('🔐 AuthContext: User not found - requires registration');
        return {
          success: false,
          requiresRegistration: true,
          error: errorMessage
        };
      }

      console.log('🔐 AuthContext: Returning error:', errorMessage);
      return { success: false, error: errorMessage };
    }
  };
  
  const googleRegister = async (userData, credential, twoFactorCode = null) => {
    try {
      // Perform registration via API but DO NOT auto-login
      const result = await apiService.googleRegister(userData, credential, twoFactorCode);

      // Many backends may return tokens upon successful registration. We intentionally ignore
      // any access/refresh tokens here to enforce the flow: register -> then login explicitly.
      if (result && (result.success || result.message || result.user || result.id)) {
        return {
          success: true,
          isNewUser: true,
          message: result.message || 'Registration successful. Please sign in with Google to continue.'
        };
      }

      // If response includes tokens (some backends do), still enforce login-first policy
      if (result && (result.access_token || result.refresh_token)) {
        return {
          success: true,
          isNewUser: true,
          message: 'Registration successful. Please sign in with Google to continue.'
        };
      }

      return { success: false, error: result?.detail || 'Google registration failed' };
    } catch (error) {
      // Normalize known duplicate/exists errors from different backends
      const raw = error?.response?.data?.detail || error?.message || '';
      const lower = String(raw).toLowerCase();
      let normalized = raw;
      if (lower.includes('already registered') || lower.includes('already exists') || lower.includes('email exists') || lower.includes('duplicate')) {
        normalized = 'Email is already registered. Please Sign In.';
      }
      return {
        success: false,
        error: normalized || 'Google registration failed'
      };
    }
  };

  // Login function
  const login = async (email, password, twoFactorCode = null, rememberMe = false) => {
    try {
      setLoading(true);
      console.log('🔐 Attempting login...');

      const credentials = { email, password };
      if (twoFactorCode) {
        credentials.two_factor_code = twoFactorCode;
      }

      const data = await apiService.login(credentials);

      if (data.requires_2fa) {
        setLoading(false);
        return { success: false, requires_2fa: true, message: data.message };
      }

      // Admin must set up 2FA before full login
      if (data.requires_2fa_setup) {
        setLoading(false);
        return {
          success: false,
          requires_2fa_setup: true,
          access_token: data.access_token,
          username: data.username,
          message: data.message,
        };
      }

      // Mandatory email OTP for admin/superadmin
      if (data.requires_email_otp) {
        setLoading(false);
        return {
          success: false,
          requires_email_otp: true,
          user_id: data.user_id,
          username: data.username,
          role: data.role,
          message: data.message,
        };
      }

      if (data.access_token) {
        console.log('✅ Login successful, fetching user data...');
        const userData = await apiService.getCurrentUser(data.access_token);

        // Save auth data (handle both cases where refresh token might or might not be present)
        const refreshToken = data.refresh_token || data.access_token; // Fallback if no refresh token
        saveAuthData(data.access_token, refreshToken, userData, rememberMe);

        setLoading(false);
        return { success: true, user: userData };
      }

      throw new Error('No access token received');
    } catch (error) {
      console.error('❌ Login error:', error);
      setLoading(false);

      const errorMessage = error.response?.data?.detail || error.message || 'Login failed';
      const isVerificationError = errorMessage.includes('verify your email') ||
                                  errorMessage.includes('email verification') ||
                                  errorMessage.includes('Please verify');

      // Pass through rate limiting info
      if (error.status === 429) {
        return {
          success: false,
          error: errorMessage,
          rate_limited: true,
          retryAfter: error.retryAfter,
        };
      }

      return {
        success: false,
        error: errorMessage,
        requires_verification: isVerificationError
      };
    }
  };

  // Complete login after OTP verification (for admin/superadmin)
  const completeOtpLogin = useCallback(async (accessToken, refreshTokenValue, rememberMe = false) => {
    try {
      setLoading(true);
      console.log('🔐 Completing OTP login, fetching user data...');
      const userData = await apiService.getCurrentUser(accessToken);
      const rToken = refreshTokenValue || accessToken;
      saveAuthData(accessToken, rToken, userData, rememberMe);
      setLoading(false);
      return { success: true, user: userData };
    } catch (error) {
      console.error('❌ Complete OTP login error:', error);
      setLoading(false);
      return { success: false, error: error.message || 'Failed to complete login' };
    }
  }, [saveAuthData]);

  // Logout function
  const logout = useCallback(async () => {
    console.log('🚪 Logging out...');
    try {
      // Read token from state or storage in case state is stale
      const currentToken = token || localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
      if (currentToken) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${currentToken}`,
          },
        }).catch((e) => {
          console.warn('Logout API call failed (continuing to clear local state):', e?.message || e);
        });
      } else {
        console.warn('No token available for logout API call; clearing local state.');
      }
    } catch (e) {
      console.warn('Unexpected error during logout request:', e?.message || e);
    } finally {
      clearAuthData();

      setTimeout(() => {
        window.location.href = '/logout';
      }, 100);
    }
  }, [clearAuthData, token]);

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      console.log('📝 Attempting registration...');

      // Call backend registration endpoint
      const data = await apiService.register(userData);

      // Successful registration – we should have an access token
      if (data && data.access_token) {
        console.log('✅ Registration successful, fetching user data...');
        const userInfo = await apiService.getCurrentUser(data.access_token);

        // Save auth data (fallback to session storage for new users)
        const refreshToken = data.refresh_token || data.access_token;
        saveAuthData(data.access_token, refreshToken, userInfo, false);

        setLoading(false);
        return {
          success: true,
          user: userInfo,
          username: userInfo.username || data.username,
          message: data.message,
        };
      }

      // If we reach here the backend didn’t return a token
      // It might be that email verification is required, so we shouldn't throw an error if success is true but no token
      if (data && (data.success || data.message)) {
         setLoading(false);
         return {
             success: true,
             message: data.message || "Registration successful. Please verify your email."
         };
      }

      throw new Error('No access token received from registration response');
    } catch (error) {
      console.error('❌ Registration error:', error);
      setLoading(false);
      return {
        success: false,
        error: error.message || 'Registration failed',
      };
    }
  };

  // Validate current token
  const validateToken = async () => {
    if (!token) return false;

    try {
      const userData = await apiService.getCurrentUser(token);
      if (userData && userData.username) {
        return true;
      }
      return false;
    } catch (error) {
      // Silently try refresh on any failure
      const refreshSuccess = await refreshAuthToken();
      return refreshSuccess;
    }
  };

  // Risk alert checking function
  const checkRiskAlerts = useCallback(async (locationData) => {
    if (!token) return;

    try {
      // Throttle risk checks to avoid excessive API calls
      const now = Date.now();
      if (lastRiskCheck && (now - lastRiskCheck) < 30000) { // 30 seconds minimum
        return;
      }
      setLastRiskCheck(now);

      console.log('🚨 Checking for risk alerts at location:', locationData.position);

      const response = await fetch('/api/location/risk-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          latitude: locationData.position.latitude,
          longitude: locationData.position.longitude,
          accuracy: locationData.accuracy,
          timestamp: locationData.timestamp
        })
      });

      if (!response.ok) {
        console.warn('🚨 Risk check failed:', response.status);
        return;
      }

      const riskData = await response.json();

      if (riskData.alerts && riskData.alerts.length > 0) {
        console.warn('🚨 Risk alerts detected:', riskData.alerts);

        // Add new alerts to state
        setRiskAlerts(prev => {
          const newAlerts = riskData.alerts.filter(alert =>
            !prev.some(existing => existing.id === alert.id)
          );
          return [...prev, ...newAlerts];
        });

        // Trigger browser notifications for high-risk alerts
        riskData.alerts.forEach(alert => {
          if (alert.severity === 'high' || alert.severity === 'critical') {
            // Use browser notification API if available
            if ('Notification' in window && Notification.permission === 'granted') {
              new Notification('🚨 Crime Risk Alert', {
                body: alert.message,
                icon: '/favicon.ico',
                tag: `risk-alert-${alert.id}`
              });
            }

            // Could also trigger push notifications here
            console.error('🚨 HIGH RISK ALERT:', alert.message);
          }
        });
      }

    } catch (error) {
      console.error('🚨 Error checking risk alerts:', error);
    }
  }, [token, lastRiskCheck]);

  const value = {
    user,
    token,
    loading,
    login,
    register,
    googleLogin,
    googleRegister,
    logout,
    validateToken,
    clearAuthData,
    refreshAuthToken,
    initialized,
    isAuthenticated: !!token && !!user,
    completeOtpLogin,
    // Expose these functions for profile updates
    updateUser,
    setUser, // Direct access if needed
    // Location tracking
    locationTrackingEnabled,
    locationPermission,
    currentLocation,
    locationTrackingStatus,
    startLocationTracking,
    stopLocationTracking,
    requestLocationPermission,
    getLocationHistory,
    clearLocationHistory,
    updateLocationPreferences,
    setLocationTrackingEnabled,
    // Risk alerts
    riskAlerts,
    setRiskAlerts,
    checkRiskAlerts,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext };
