import React, { createContext, useState, useContext, useEffect } from 'react';
import { apiService } from '../services/apiService_updated';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null); // Don't initialize with localStorage
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState(null);
  const [permissions, setPermissions] = useState([]);

  useEffect(() => {
    // Check if user is logged in on app start
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token');

      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Try to verify the token is still valid
        const userData = await apiService.getCurrentUser(storedToken);
        setUser(userData);
        setToken(storedToken);
        setRole(userData.role || 'user');
        setPermissions(userData.permissions || []);
      } catch (error) {
        console.log('Auth check failed - keeping token for offline use:', error.message);
        // Don't remove token immediately - allow offline use
        // Only remove if explicitly logged out or login fails
        setToken(storedToken);
        setRole('user'); // Default role
        setPermissions([]);
        // Don't set user data to avoid showing stale info
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email, password, twoFactorCode = null) => {
    try {
      const data = await apiService.login({ email, password, two_factor_code: twoFactorCode });
      if (data.requires_2fa) {
        return { success: false, requires_2fa: true, message: data.message };
      }
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);

      // Get user info with the new valid token
      const userData = await apiService.getCurrentUser(data.access_token);
      setUser(userData);
      setRole(userData.role || 'user');
      setPermissions(userData.permissions || []);

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Login failed'
      };
    }
  };

  const register = async (firstName, lastName, email, password, homeArea = '') => {
    try {
      const userData = {
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        home_area: homeArea || null
      };

      const data = await apiService.register(userData);

      // Backend currently sends a message and username but does not auto-issue access tokens
      // Only store a token and fetch user info if the backend returned an access_token
      if (data && data.access_token) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);

        // Get user info with the new valid token
        const userDataResponse = await apiService.getCurrentUser(data.access_token);
        setUser(userDataResponse);
        setRole(userDataResponse.role || 'user');
        setPermissions(userDataResponse.permissions || []);
      }

      return {
        success: true,
        username: data.username,
        message: data.message || 'Registration successful'
      };
    } catch (error) {
      console.error('Registration error:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || error.message || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setRole(null);
    setPermissions([]);
  };

  // Function to check if token is still valid (can be called periodically)
  const validateToken = async () => {
    if (!token) return false;
    
    try {
      const userData = await apiService.getCurrentUser(token);
      setUser(userData);
      setRole(userData.role || 'user');
      setPermissions(userData.permissions || []);
      return true;
    } catch (error) {
      console.log('Token validation failed:', error.message);
      logout(); // Auto-logout if token is invalid
      return false;
    }
  };

  const updateProfile = async (profileData) => {
    if (!token) throw new Error('Not authenticated');
    await apiService.updateProfile(profileData, token);
    const updatedUser = await apiService.getCurrentUser(token);
    setUser(updatedUser);
    setRole(updatedUser.role || 'user');
    setPermissions(updatedUser.permissions || []);
  };

  const value = {
    user,
    setUser,
    token,
    role,
    permissions,
    loading,
    login,
    register,
    logout,
    validateToken,
    updateProfile,
    isAuthenticated: !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
