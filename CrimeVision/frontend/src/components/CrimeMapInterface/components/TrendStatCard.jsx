import React from 'react';
import AnimatedCounter from './AnimatedCounter';

const TrendStatCard = ({ icon, label, value, caption, color = '#00d4ff' }) => {
  return (
    <div className="trend-stat-card">
      <div className="stat-icon" style={{ color }}>
        <i className={`fas ${icon}`}></i>
      </div>
      <div className="stat-content">
        <div className="stat-value">
          <AnimatedCounter value={value} />
        </div>
        <div className="stat-label">{label}</div>
        {caption && <div className="stat-caption">{caption}</div>}
      </div>
    </div>
  );
};

export default TrendStatCard;
