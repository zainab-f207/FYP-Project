import React, { createContext, useState, useContext, useEffect } from 'react';
import { apiService } from '../services/apiService';

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

  useEffect(() => {
    // Check if user is logged in on app start
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token');
      
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Verify the token is still valid before setting it
        const userData = await apiService.getCurrentUser(storedToken);
        setUser(userData);
        setToken(storedToken);
      } catch (error) {
        console.log('Auth check failed - removing invalid token:', error.message);
        // Remove invalid token from storage
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (username, password) => {
    try {
      const data = await apiService.login({ username, password });
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);

      // Get user info with the new valid token
      const userData = await apiService.getCurrentUser(data.access_token);
      setUser(userData);

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
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);

      // Get user info with the new valid token
      const userDataResponse = await apiService.getCurrentUser(data.access_token);
      setUser(userDataResponse);

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
  };

  // Function to check if token is still valid (can be called periodically)
  const validateToken = async () => {
    if (!token) return false;
    
    try {
      await apiService.getCurrentUser(token);
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
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    validateToken,
    updateProfile,
    isAuthenticated: !!token && !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
