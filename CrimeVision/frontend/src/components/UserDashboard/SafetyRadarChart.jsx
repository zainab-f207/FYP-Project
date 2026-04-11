import React, { useEffect, useState } from 'react';
import styles from './SafetyRadarChart.module.css';

const SafetyRadarChart = ({ userArea, stats }) => {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const safetyScore = typeof stats?.safety_score === 'number' ? Math.round(stats.safety_score) : 0;
  
  const breakdown = stats?.breakdown || {
    violent: 0,
    property: 0,
    personal: 0,
    day: 0,
    night: 0
  };
  
  // Enhanced zones with icons and colors
  const zones = [
    { 
      name: 'Overall', 
      icon: 'fa-shield-alt',
      value: Math.round(safetyScore),
      color: safetyScore >= 70 ? '#10b981' : safetyScore >= 40 ? '#f59e0b' : '#ef4444',
      angle: 0 
    },
    { 
      name: 'Violent', 
      icon: 'fa-bolt',
      value: Math.round(breakdown.violent ?? 0),
      color: (breakdown.violent ?? 0) >= 70 ? '#10b981' : (breakdown.violent ?? 0) >= 40 ? '#f59e0b' : '#ef4444',
      angle: 60 
    },
    { 
      name: 'Property', 
      icon: 'fa-home',
      value: Math.round(breakdown.property ?? 0),
      color: (breakdown.property ?? 0) >= 70 ? '#10b981' : (breakdown.property ?? 0) >= 40 ? '#f59e0b' : '#ef4444',
      angle: 120 
    },
    { 
      name: 'Personal', 
      icon: 'fa-user-shield',
      value: Math.round(breakdown.personal ?? 0),
      color: (breakdown.personal ?? 0) >= 70 ? '#10b981' : (breakdown.personal ?? 0) >= 40 ? '#f59e0b' : '#ef4444',
      angle: 180 
    },
    { 
      name: 'Daytime', 
      icon: 'fa-sun',
      value: Math.round(breakdown.day ?? 0),
      color: (breakdown.day ?? 0) >= 70 ? '#10b981' : (breakdown.day ?? 0) >= 40 ? '#f59e0b' : '#ef4444',
      angle: 240 
    },
    { 
      name: 'Nighttime', 
      icon: 'fa-moon',
      value: Math.round(breakdown.night ?? 0),
      color: (breakdown.night ?? 0) >= 70 ? '#10b981' : (breakdown.night ?? 0) >= 40 ? '#f59e0b' : '#ef4444',
      angle: 300 
    }
  ];

  const centerX = 150;
  const centerY = 150;
  const maxRadius = 100;

  const getPoint = (angle, value) => {
    const radius = (value / 100) * maxRadius;
    const radian = (angle - 90) * (Math.PI / 180);
    return {
      x: centerX + radius * Math.cos(radian),
      y: centerY + radius * Math.sin(radian)
    };
  };

  const radarPath = zones.map((zone, index) => {
    const point = getPoint(zone.angle, zone.value);
    return `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`;
  }).join(' ') + ' Z';

  const gridLevels = [25, 50, 75, 100];

  return (
    <div className={styles.radarContainer}>
      <svg viewBox="0 0 300 300" className={styles.radarSvg}>
        <defs>
          <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.1" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Grid Circles */}
        {gridLevels.map((level, index) => (
          <circle
            key={`grid-${level}`}
            cx={centerX}
            cy={centerY}
            r={(level / 100) * maxRadius}
            className={styles.gridCircle}
            style={{ animationDelay: `${index * 100}ms` }}
          />
        ))}

        {/* Axes and Icons */}
        {zones.map((zone, index) => {
          const point = getPoint(zone.angle, 100);
          const iconPoint = getPoint(zone.angle, 125);
          return (
            <g key={`axis-group-${index}`}>
              <line
                x1={centerX}
                y1={centerY}
                x2={point.x}
                y2={point.y}
                className={styles.radarAxis}
              />
              <foreignObject 
                x={iconPoint.x - 15} 
                y={iconPoint.y - 15} 
                width="30" 
                height="30"
                className={styles.iconObject}
              >
                <div className={styles.axisIconWrapper} title={zone.name}>
                  <i className={`fas ${zone.icon}`} style={{ color: zone.color }}></i>
                </div>
              </foreignObject>
            </g>
          );
        })}

        {/* Radar Area */}
        <path
          d={radarPath}
          className={`${styles.radarArea} ${animated ? styles.animated : ''}`}
          fill="url(#radarGradient)"
          filter="url(#glow)"
        />

        {/* Data Points */}
        {zones.map((zone, index) => {
          const point = getPoint(zone.angle, zone.value);
          return (
            <g key={`point-${index}`}>
              <circle
                cx={point.x}
                cy={point.y}
                r="4"
                className={styles.dataPoint}
                style={{ fill: zone.color, animationDelay: `${index * 100}ms` }}
              />
            </g>
          );
        })}

        {/* Center Score Circle */}
        <circle cx={centerX} cy={centerY} r="35" fill="rgba(15, 23, 42, 0.8)" stroke="#00d4ff" strokeWidth="2" />
      </svg>

      {/* Central Stats Overlay */}
      <div className={styles.centerStats}>
        <div className={styles.statValue}>{Math.round(safetyScore)}%</div>
        <div className={styles.statLabel}>SAFETY</div>
      </div>
    </div>
  );
};

export default SafetyRadarChart;
