import React from 'react';

export const DashboardIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="dashboardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
        <stop offset="50%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#ffc107", stopOpacity:1}} />
      </linearGradient>
    </defs>
    <rect x="3" y="3" width="7" height="7" rx="1" fill="url(#dashboardGrad)" opacity="0.8"/>
    <rect x="14" y="3" width="7" height="7" rx="1" fill="url(#dashboardGrad)" opacity="0.6"/>
    <rect x="3" y="14" width="7" height="7" rx="1" fill="url(#dashboardGrad)" opacity="0.7"/>
    <rect x="14" y="14" width="7" height="7" rx="1" fill="url(#dashboardGrad)" opacity="0.9"/>
    <circle cx="6.5" cy="6.5" r="1.5" fill="#fff" opacity="0.9"/>
    <circle cx="17.5" cy="6.5" r="1.5" fill="#fff" opacity="0.7"/>
    <path d="m4 16 2 2 4-4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M15 17h5m-5-2h6m-6 4h4" stroke="#fff" strokeWidth="1" strokeLinecap="round"/>
  </svg>
);

export const UsersIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="usersGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
      </linearGradient>
      <filter id="glow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge> 
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <circle cx="12" cy="8" r="3" fill="url(#usersGrad)" filter="url(#glow)"/>
    <path d="M16 14c0-2.21-1.79-4-4-4s-4 1.79-4 4v6h8v-6z" fill="url(#usersGrad)" opacity="0.8"/>
    <circle cx="6" cy="9" r="2" fill="url(#usersGrad)" opacity="0.7"/>
    <circle cx="18" cy="9" r="2" fill="url(#usersGrad)" opacity="0.7"/>
    <path d="M8 20v-2c0-1.5-.8-2.8-2-3.5" stroke="url(#usersGrad)" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
    <path d="M16 20v-2c0-1.5.8-2.8 2-3.5" stroke="url(#usersGrad)" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
    <circle cx="12" cy="8" r="1" fill="#fff" opacity="0.9"/>
  </svg>
);

export const AdminIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="adminGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#ffc107", stopOpacity:1}} />
        <stop offset="50%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
      </linearGradient>
      <filter id="shadow">
        <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.3"/>
      </filter>
    </defs>
    <circle cx="12" cy="8" r="3" fill="url(#adminGrad)" filter="url(#shadow)"/>
    <path d="M12 14c-4 0-6 2-6 4v4h12v-4c0-2-2-4-6-4z" fill="url(#adminGrad)" opacity="0.9"/>
    <rect x="10" y="3" width="4" height="2" rx="1" fill="url(#adminGrad)" opacity="0.8"/>
    <path d="m9 10 2-1 2 1" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" opacity="0.9"/>
    <circle cx="12" cy="8" r="1" fill="#fff" opacity="0.9"/>
    <path d="M16 18h4m-2-2v4" stroke="url(#adminGrad)" strokeWidth="2" strokeLinecap="round" opacity="0.7"/>
  </svg>
);

export const AnalyticsIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="analyticsGrad" x1="0%" y1="100%" x2="100%" y2="0%">
        <stop offset="0%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
        <stop offset="50%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#ffc107", stopOpacity:1}} />
      </linearGradient>
    </defs>
    <rect x="3" y="12" width="3" height="9" fill="url(#analyticsGrad)" opacity="0.8" rx="1"/>
    <rect x="7" y="8" width="3" height="13" fill="url(#analyticsGrad)" opacity="0.9" rx="1"/>
    <rect x="11" y="4" width="3" height="17" fill="url(#analyticsGrad)" rx="1"/>
    <rect x="15" y="10" width="3" height="11" fill="url(#analyticsGrad)" opacity="0.85" rx="1"/>
    <rect x="19" y="6" width="3" height="15" fill="url(#analyticsGrad)" opacity="0.7" rx="1"/>
    <path d="m3 3 3 3 4-4 4 4 4-2 3-1" stroke="url(#analyticsGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.9"/>
    <circle cx="6" cy="6" r="1.5" fill="#fff" opacity="0.9"/>
    <circle cx="10" cy="2" r="1.5" fill="#fff" opacity="0.9"/>
    <circle cx="14" cy="6" r="1.5" fill="#fff" opacity="0.9"/>
    <circle cx="18" cy="4" r="1.5" fill="#fff" opacity="0.9"/>
  </svg>
);

export const SecurityIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="securityGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#dc2626", stopOpacity:1}} />
        <stop offset="50%" style={{stopColor:"#ffc107", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
      </linearGradient>
      <filter id="securityGlow">
        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
        <feMerge> 
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" 
          fill="url(#securityGrad)" filter="url(#securityGlow)" opacity="0.9"/>
    <path d="M12 7L8 11l-2-2" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="12" cy="12" r="6" stroke="#fff" strokeWidth="1.5" opacity="0.6" fill="none"/>
    <circle cx="12" cy="12" r="2" fill="#fff" opacity="0.8"/>
    <path d="M12 2v4M12 16v6M7 7l-2-2M17 7l2-2" stroke="#fff" strokeWidth="1" opacity="0.5"/>
  </svg>
);

export const SystemIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="systemGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
      </linearGradient>
    </defs>
    <rect x="2" y="4" width="20" height="16" rx="3" fill="url(#systemGrad)" opacity="0.9"/>
    <rect x="4" y="6" width="16" height="1" fill="#fff" opacity="0.8"/>
    <circle cx="6" cy="9" r="1" fill="#ffc107"/>
    <circle cx="9" cy="9" r="1" fill="#dc2626"/>
    <circle cx="12" cy="9" r="1" fill="#22c55e"/>
    <rect x="6" y="12" width="8" height="1" fill="#fff" opacity="0.6"/>
    <rect x="6" y="15" width="6" height="1" fill="#fff" opacity="0.4"/>
    <rect x="15" y="12" width="3" height="6" fill="#00a6a6" opacity="0.7" rx="1"/>
    <path d="M4 20h16l-2 2H6l-2-2z" fill="url(#systemGrad)" opacity="0.6"/>
  </svg>
);

export const CrownIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="crownGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#ffc107", stopOpacity:1}} />
        <stop offset="50%" style={{stopColor:"#ffd700", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#ffab00", stopOpacity:1}} />
      </linearGradient>
      <filter id="crownGlow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge> 
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <path d="M5 16L3 7l5.5 7L12 4l3.5 10L21 7l-2 9H5z" fill="url(#crownGrad)" filter="url(#crownGlow)"/>
    <rect x="4" y="16" width="16" height="2" rx="1" fill="url(#crownGrad)" opacity="0.8"/>
    <circle cx="5" cy="7" r="1.5" fill="#dc2626" opacity="0.9"/>
    <circle cx="12" cy="4" r="1.5" fill="#dc2626" opacity="0.9"/>
    <circle cx="19" cy="7" r="1.5" fill="#dc2626" opacity="0.9"/>
    <path d="M8 13h8M9 11h6" stroke="#fff" strokeWidth="0.8" opacity="0.7"/>
  </svg>
);

export const SettingsIcon = ({ size = 24, className = "", color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <defs>
      <linearGradient id="settingsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:"#00a6a6", stopOpacity:1}} />
        <stop offset="100%" style={{stopColor:"#1a3a5f", stopOpacity:1}} />
      </linearGradient>
    </defs>
    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" fill="url(#settingsGrad)" opacity="0.9"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" 
          stroke="url(#settingsGrad)" strokeWidth="1.5" fill="none" opacity="0.8"/>
    <circle cx="12" cy="12" r="1" fill="#fff" opacity="0.9"/>
    <animateTransform 
      attributeName="transform" 
      attributeType="XML" 
      type="rotate" 
      from="0 12 12" 
      to="360 12 12" 
      dur="10s" 
      repeatCount="indefinite"/>
  </svg>
);
