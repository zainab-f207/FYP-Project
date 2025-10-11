import React, { createContext, useState, useContext, useEffect } from 'react';
import apiService from '../services/apiService';

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
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on app start
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          // Verify token with backend via apiService so VITE_API_BASE_URL is respected
          const userData = await apiService.getCurrentUser(storedToken).catch(() => null);
          if (userData) {
            setUser(userData);
            setToken(storedToken);
          } else {
            localStorage.removeItem('token');
            setToken(null);
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('token');
          setToken(null);
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (username, password) => {
    try {
      try {
        const data = await apiService.login({ username, password });
        if (data && data.access_token) {
          localStorage.setItem('token', data.access_token);
          setToken(data.access_token);
          const userData = await apiService.getCurrentUser(data.access_token).catch(() => null);
          if (userData) setUser(userData);
          return { success: true };
        }
        return { success: false, error: 'Login failed' };
      } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: error.message || 'Network error' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error' };
    }
  };

  const register = async (firstName, lastName, email, password) => {
    try {
      try {
        const data = await apiService.register({
          first_name: firstName,
          last_name: lastName,
          email,
          password,
        });

        if (data && data.access_token) {
          localStorage.setItem('token', data.access_token);
          setToken(data.access_token);
          const userData = await apiService.getCurrentUser(data.access_token).catch(() => null);
          if (userData) setUser(userData);
          return { success: true, username: data.username, message: data.message || 'Registration successful' };
        }
        return { success: false, error: 'Registration failed' };
      } catch (error) {
        console.error('Registration error:', error);
        return { success: false, error: error.message || 'Network error' };
      }
    } catch (error) {
      console.error('Registration error:', error);
      return { success: false, error: 'Network error' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
