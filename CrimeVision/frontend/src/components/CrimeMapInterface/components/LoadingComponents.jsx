import React from 'react';
import './LoadingComponents.css';

// Modern animated loading spinner
export const LoadingSpinner = ({ size = 'medium', className = '' }) => {
  const sizeClasses = {
    small: 'loading-spinner-sm',
    medium: 'loading-spinner-md',
    large: 'loading-spinner-lg',
    xlarge: 'loading-spinner-xl'
  };

  return (
    <div className={`loading-spinner ${sizeClasses[size]} ${className}`}>
      <div className="spinner-ring">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>
    </div>
  );
};

// Skeleton loading for dashboard cards
export const SkeletonCard = ({ height = '120px', className = '' }) => {
  return (
    <div className={`skeleton-card ${className}`} style={{ height }}>
      <div className="skeleton-pulse"></div>
    </div>
  );
};

// Pulse loading for lists
export const SkeletonList = ({ items = 3, className = '' }) => {
  return (
    <div className={`skeleton-list ${className}`}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="skeleton-list-item">
          <div className="skeleton-avatar"></div>
          <div className="skeleton-content">
            <div className="skeleton-line skeleton-line--medium"></div>
            <div className="skeleton-line skeleton-line--short"></div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Modern loading overlay with blur effect
export const LoadingOverlay = ({ message = 'Loading...', show = true }) => {
  if (!show) return null;

  return (
    <div className="loading-overlay">
      <div className="loading-overlay__backdrop"></div>
      <div className="loading-overlay__content">
        <div className="neon-loader">
          <div className="neon-loader__circle"></div>
          <div className="neon-loader__circle"></div>
          <div className="neon-loader__circle"></div>
        </div>
        <p className="loading-overlay__message">{message}</p>
      </div>
    </div>
  );
};

// Shimmer loading effect for cards
export const ShimmerCard = ({ className = '' }) => {
  return (
    <div className={`shimmer-card ${className}`}>
      <div className="shimmer-card__header">
        <div className="shimmer shimmer--circle"></div>
        <div className="shimmer shimmer--title"></div>
      </div>
      <div className="shimmer-card__content">
        <div className="shimmer shimmer--line"></div>
        <div className="shimmer shimmer--line shimmer--short"></div>
        <div className="shimmer shimmer--line shimmer--medium"></div>
      </div>
    </div>
  );
};

// Progress bar with gradient
export const ProgressBar = ({ progress = 0, label = '', className = '' }) => {
  return (
    <div className={`progress-bar-container ${className}`}>
      {label && <span className="progress-bar-label">{label}</span>}
      <div className="progress-bar-track">
        <div 
          className="progress-bar-fill"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        ></div>
      </div>
    </div>
  );
};
