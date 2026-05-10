import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { useAuth } from '../../contexts/AuthContext_updated';

const decodeJwtExp = (jwt) => {
  if (!jwt || typeof jwt !== 'string') return null;
  const parts = jwt.split('.');
  if (parts.length !== 3) return null;
  try {
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padding = '='.repeat((4 - (padded.length % 4)) % 4);
    const payload = JSON.parse(atob(padded + padding));
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch (_e) {
    return null;
  }
};

const formatRemaining = (seconds) => {
  if (seconds <= 0) return '0:00';
  const days = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (days > 0) return `${days}d ${h}h`;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${m}:${String(s).padStart(2, '0')}`;
};

const SessionTimer = ({ warnSeconds, criticalSeconds, compact }) => {
  const { token, refreshAuthToken, logout } = useAuth();
  const expSeconds = useMemo(() => decodeJwtExp(token), [token]);
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));

  useEffect(() => {
    const id = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  if (!expSeconds) return null;

  const remaining = expSeconds - now;
  const expired = remaining <= 0;
  const critical = !expired && remaining <= criticalSeconds;
  const warn = !expired && !critical && remaining <= warnSeconds;

  const palette = expired
    ? { bg: 'rgba(239,68,68,0.18)', fg: '#fca5a5', border: 'rgba(239,68,68,0.4)' }
    : critical
      ? { bg: 'rgba(239,68,68,0.16)', fg: '#fca5a5', border: 'rgba(239,68,68,0.35)' }
      : warn
        ? { bg: 'rgba(251,191,36,0.15)', fg: '#fbbf24', border: 'rgba(251,191,36,0.35)' }
        : { bg: 'rgba(45,127,184,0.14)', fg: '#93c5fd', border: 'rgba(45,127,184,0.3)' };

  const handleExtend = async () => {
    try {
      const ok = await refreshAuthToken?.();
      if (!ok) {
        logout?.();
      }
    } catch (_e) {
      // refreshAuthToken handles its own errors silently
    }
  };

  const titleText = expired
    ? 'Your session has expired — you will be signed out on the next request'
    : `Session expires in ${formatRemaining(remaining)}. Click to extend.`;

  return (
    <button
      type="button"
      onClick={handleExtend}
      title={titleText}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: compact ? '4px 10px' : '6px 12px',
        background: palette.bg,
        color: palette.fg,
        border: `1px solid ${palette.border}`,
        borderRadius: 999,
        fontSize: compact ? 11 : 12,
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
      }}
    >
      <i
        className={expired ? 'fas fa-circle-exclamation' : 'far fa-clock'}
        style={{ fontSize: compact ? 11 : 12 }}
      />
      <span>
        {expired ? 'Session expired' : `Session: ${formatRemaining(remaining)}`}
      </span>
    </button>
  );
};

SessionTimer.propTypes = {
  warnSeconds: PropTypes.number,
  criticalSeconds: PropTypes.number,
  compact: PropTypes.bool,
};

SessionTimer.defaultProps = {
  warnSeconds: 5 * 60,
  criticalSeconds: 60,
  compact: false,
};

export default SessionTimer;
