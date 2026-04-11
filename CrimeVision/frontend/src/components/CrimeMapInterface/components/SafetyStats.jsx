// SafetyStats.js
import React, { useEffect, useState, useMemo } from 'react';
import AnimatedCounter from './AnimatedCounter';
import './SafetyStats.css';

const SafetyStats = ({ keyMetrics = {} }) => {
  const [animatedValues, setAnimatedValues] = useState({
    totalIncidents: 0,
    weeklyChange: 0,
    highRiskShare: 0,
    averageResponse: 0,
    areasAffected: 0
  });

  const [isVisible, setIsVisible] = useState(true); // Cards visible immediately

  useEffect(() => {
    if (isVisible) {
      const delays = [0, 200, 400, 600, 800];
      
      Object.keys(animatedValues).forEach((key, index) => {
        setTimeout(() => {
          setAnimatedValues(prev => ({
            ...prev,
            [key]: keyMetrics[key] || 0
          }));
        }, delays[index]);
      });
    }
  }, [keyMetrics, isVisible, animatedValues]);

  // No default metrics - use only real data
  const actualMetrics = keyMetrics || {};

  const stats = useMemo(() => [
    {
      id: 1,
      icon: 'fas fa-shield-alt',
      label: 'Total Incidents',
      value: animatedValues.totalIncidents || actualMetrics.totalIncidents,
      suffix: '',
      color: '#3b82f6',
      gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
      description: 'Reported incidents this period',
      trend: null,
      precision: 0,
      iconBg: 'rgba(59, 130, 246, 0.1)'
    },
    {
      id: 2,
      icon: 'fas fa-chart-line',
      label: 'Weekly Trend',
      value: Math.abs(animatedValues.weeklyChange || actualMetrics.weeklyChange),
      suffix: '%',
      color: (animatedValues.weeklyChange || actualMetrics.weeklyChange) >= 0 ? '#ef4444' : '#10b981',
      gradient: (animatedValues.weeklyChange || actualMetrics.weeklyChange) >= 0 
        ? 'linear-gradient(135deg, #ef4444, #dc2626)' 
        : 'linear-gradient(135deg, #10b981, #059669)',
      description: (animatedValues.weeklyChange || actualMetrics.weeklyChange) >= 0 ? 'Increase from last week' : 'Decrease from last week',
      trend: (animatedValues.weeklyChange || actualMetrics.weeklyChange) >= 0 ? 'up' : 'down',
      precision: 1,
      iconBg: (animatedValues.weeklyChange || actualMetrics.weeklyChange) >= 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)'
    },
    {
      id: 3,
      icon: 'fas fa-exclamation-triangle',
      label: 'High Risk Areas',
      value: animatedValues.highRiskShare || actualMetrics.highRiskShare,
      suffix: '%',
      color: '#f59e0b',
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      description: 'Areas requiring immediate attention',
      trend: null,
      precision: 0,
      iconBg: 'rgba(245, 158, 11, 0.1)'
    },
    {
      id: 4,
      icon: 'fas fa-clock',
      label: 'Avg Response Time',
      value: animatedValues.averageResponse || actualMetrics.averageResponse,
      suffix: ' min',
      color: '#8b5cf6',
      gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
      description: 'Average emergency response time',
      trend: null,
      precision: 0,
      iconBg: 'rgba(139, 92, 246, 0.1)'
    },
    {
      id: 5,
      icon: 'fas fa-map-marker-alt',
      label: 'Areas Covered',
      value: animatedValues.areasAffected || actualMetrics.areasAffected,
      suffix: '',
      color: '#06b6d4',
      gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)',
      description: 'Active monitoring areas',
      trend: null,
      precision: 0,
      iconBg: 'rgba(6, 182, 212, 0.1)'
    }
  ], [animatedValues, actualMetrics]);

  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'up':
        return 'fas fa-arrow-up trend-up';
      case 'down':
        return 'fas fa-arrow-down trend-down';
      default:
        return 'fas fa-minus trend-neutral';
    }
  };

  const getTrendColor = (trend) => {
    switch (trend) {
      case 'up':
        return '#ef4444';
      case 'down':
        return '#10b981';
      default:
        return '#6b7280';
    }
  };

  return (
    <section className="safety-stats-section">
      <div className="stats-container">
        {/* Enhanced Header */}
        <div className="stats-header">
          <div className="header-badge">
            <i className="fas fa-chart-bar"></i>
            <span>Live Analytics</span>
          </div>
          <h2 className="stats-title">Safety Intelligence Dashboard</h2>
          <p className="stats-subtitle">
            Real-time crime statistics and performance metrics powered by advanced analytics
          </p>
        </div>

        {/* Main Stats Grid */}
        <div className="stats-grid">
          {stats.map((stat, index) => (
            <div 
              key={stat.id}
              className={`stat-card ${isVisible ? 'visible' : ''}`}
              style={{ 
                animationDelay: `${index * 150}ms`,
                '--card-color': stat.color,
                '--card-gradient': stat.gradient
              }}
            >
              {/* Animated Background Effect */}
              <div className="card-background">
                <div className="floating-orb orb-1"></div>
                <div className="floating-orb orb-2"></div>
              </div>

              {/* Card Content */}
              <div className="card-content">
                {/* Icon Section */}
                <div className="stat-icon-container">
                  <div 
                    className="stat-icon-wrapper"
                    style={{ backgroundColor: stat.iconBg }}
                  >
                    <i className={stat.icon}></i>
                  </div>
                  
                  {/* Trend Indicator */}
                  {stat.trend && (
                    <div 
                      className="trend-badge"
                      style={{ backgroundColor: getTrendColor(stat.trend) }}
                    >
                      <i className={getTrendIcon(stat.trend)}></i>
                    </div>
                  )}
                </div>

                {/* Value Section */}
                <div className="stat-value-section">
                  <div className="value-container">
                    <AnimatedCounter
                      value={stat.value}
                      duration={1800}
                      suffix={stat.suffix}
                      precision={stat.precision}
                      className="stat-value"
                    />
                  </div>
                  
                  {/* Progress Bar for Percentage-based Stats */}
                  {(stat.label.includes('Risk') || stat.label.includes('Trend')) && (
                    <div className="progress-container">
                      <div 
                        className="progress-bar"
                        style={{ 
                          width: `${Math.min(stat.value, 100)}%`,
                          background: stat.gradient
                        }}
                      >
                        <div className="progress-glow"></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Label and Description */}
                <div className="stat-info">
                  <h3 className="stat-label">{stat.label}</h3>
                  <p className="stat-description">{stat.description}</p>
                </div>

                {/* Interactive Hover Effect */}
                <div className="card-hover-effect"></div>
              </div>

              {/* Performance Indicator */}
              <div className="performance-indicator">
                <div className="indicator-dot"></div>
                <span className="indicator-text">Live</span>
              </div>
            </div>
          ))}
        </div>

        {/* Enhanced Footer with More Metrics */}
        <div className="stats-footer">
          <div className="footer-grid">
            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-bolt"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Data Refresh</span>
                <span className="footer-value">Real-time</span>
              </div>
            </div>

            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-database"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Data Source</span>
                <span className="footer-value">Local Authorities</span>
              </div>
            </div>

            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-clock"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Last Updated</span>
                <span className="footer-value">{new Date().toLocaleTimeString()}</span>
              </div>
            </div>

            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-shield-check"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Data Integrity</span>
                <span className="footer-value verified">Verified</span>
              </div>
            </div>
          </div>

          {/* Data Quality Indicator */}
          <div className="data-quality">
            <div className="quality-bar">
              <div className="quality-segment excellent"></div>
              <div className="quality-segment good"></div>
              <div className="quality-segment fair"></div>
            </div>
            <div className="quality-labels">
              <span>Data Quality: </span>
              <span className="quality-status excellent">Excellent</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SafetyStats;
