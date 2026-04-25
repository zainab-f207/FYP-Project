import React from 'react';
import logoSrc from '../../../../../branding/safevision/concept9.svg';

/**
 * Shared SafeVision brand mark.
 * Used across Header (home), UserDashboard, AdminDashboard, SuperAdminDashboard
 * so the brand is consistent everywhere.
 *
 * Props:
 *   size      — pixel width/height of the logo (default 36)
 *   className — extra class to attach
 */
const SafeVisionLogo = ({ size = 36, className = '', alt = 'SafeVision' }) => (
  <img
    src={logoSrc}
    alt={alt}
    className={className}
    width={size}
    height={size}
    style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
    draggable={false}
  />
);

export default SafeVisionLogo;