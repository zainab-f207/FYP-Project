import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiService } from '../services/apiService';

const TOKEN_KEY       = 'SafeVision_token';
const REFRESH_KEY     = 'SafeVision_refresh_token';
const USER_KEY        = 'SafeVision_user';

/**
 * AutoLoginPage — handles magic-link email deep-links.
 *
 * Flow:
 *   1. Backend /api/auth/email-link validates the one-time JWT and
 *      redirects to /autologin?access_token=<JWT>&next=<path>
 *   2. This page stores the token in localStorage (persistent, 30-day session)
 *      and fetches user data just like a normal login.
 *   3. Navigates to <next> (e.g. /dashboard?tab=map&area=...)
 *   4. On any error it falls to /login.
 */
export default function AutoLoginPage() {
  const [searchParams] = useSearchParams();
  const navigate        = useNavigate();
  const [status, setStatus] = useState('Verifying your link…');
  const [error,  setError]  = useState('');

  useEffect(() => {
    const doAutoLogin = async () => {
      const accessToken = searchParams.get('access_token');
      const nextPath    = searchParams.get('next') || '/dashboard';

      if (!accessToken) {
        setError('Invalid or missing link token.');
        setTimeout(() => navigate('/login?error=invalid_link', { replace: true }), 2000);
        return;
      }

      try {
        setStatus('Authenticating…');
        const userData = await apiService.getCurrentUser(accessToken);

        if (!userData?.username) {
          throw new Error('Could not load user data');
        }

        // Persist — use localStorage for email links (30-day session same as "Remember me")
        localStorage.setItem(TOKEN_KEY,   accessToken);
        localStorage.setItem(REFRESH_KEY, accessToken);
        localStorage.setItem(USER_KEY,    JSON.stringify(userData));

        setStatus('Opening your dashboard…');
        // Small delay so browser can process the storage write
        setTimeout(() => {
          window.location.href = nextPath;   // hard nav so AuthContext re-initialises
        }, 300);

      } catch (err) {
        console.error('AutoLogin failed:', err);
        setError('This link has expired or is no longer valid.');
        setTimeout(() => navigate('/login?error=expired_link', { replace: true }), 2500);
      }
    };

    doAutoLogin();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f172a 100%)',
      color: '#e2e8f0',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    }}>
      <div style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '20px',
        padding: '48px 56px',
        textAlign: 'center',
        maxWidth: '420px',
        width: '90%',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
      }}>
        {/* Logo mark */}
        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>
          {error ? '⚠️' : '🛡️'}
        </div>

        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px', color: '#f1f5f9' }}>
          SafeVision
        </h1>

        {error ? (
          <>
            <p style={{ color: '#f87171', marginBottom: '8px', fontSize: '0.95rem' }}>{error}</p>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Redirecting to login…</p>
          </>
        ) : (
          <>
            {/* Spinner */}
            <div style={{
              width: '48px', height: '48px',
              border: '4px solid rgba(99,102,241,0.3)',
              borderTop: '4px solid #6366f1',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '20px auto',
            }} />
            <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>{status}</p>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
