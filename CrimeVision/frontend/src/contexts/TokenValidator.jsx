// TokenValidator.jsx
import { useEffect } from 'react';
import { useAuth } from './AuthContext_updated';

export const TokenValidator = () => {
  const { validateToken, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      // Validate token every 5 minutes
      const interval = setInterval(() => {
        validateToken();
      }, 5 * 60 * 1000); // 5 minutes

      return () => clearInterval(interval);
    }
  }, [isAuthenticated, validateToken]);

  return null;
};