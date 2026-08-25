// TokenValidator.jsx
// Silently watches the JWT expiry and refreshes the token BEFORE it lapses,
// so API calls never hit a 401 mid-session.
import { useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';

/** Decode a JWT payload without verifying the signature (client-side only). */
const getTokenExpiry = (token) => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp ? payload.exp * 1000 : null; // convert seconds to ms
  } catch {
    return null;
  }
};

const REFRESH_BEFORE_EXPIRY_MS = 3 * 60 * 1000; // refresh when 3 minutes remain
const CHECK_INTERVAL_MS = 60 * 1000;             // check every 60 seconds

export const TokenValidator = () => {
  const { token, isAuthenticated, refreshAuthToken } = useAuth();
  const tokenRef = useRef(token);

  // Keep ref in sync so the interval always reads the latest token
  useEffect(() => { tokenRef.current = token; }, [token]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const check = async () => {
      const currentToken = tokenRef.current;
      if (!currentToken) return;

      const expiresAt = getTokenExpiry(currentToken);
      if (!expiresAt) return;

      const remainingMs = expiresAt - Date.now();

      if (remainingMs <= REFRESH_BEFORE_EXPIRY_MS) {
        // Token expires in less than 3 minutes (or already expired) - silently refresh
        await refreshAuthToken();
      }
    };

    // Run once immediately on mount, then every minute
    check();
    const interval = setInterval(check, CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isAuthenticated, refreshAuthToken]);

  return null;
};
