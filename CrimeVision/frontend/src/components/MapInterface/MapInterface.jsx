// src/components/MapInterface/MapInterface.js
import React, { useState, useRef, useEffect } from 'react';
import './MapInterface.css';

const MapInterface = () => {
  const [activeMode, setActiveMode] = useState('heatmap');
  const [controlsVisible, setControlsVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('trends');
  const [filters, setFilters] = useState({
    theft: true,
    burglary: true,
    assault: true,
    vehicle: false,
    street: true
  });
  const [tooltip, setTooltip] = useState({ visible: false, content: '', x: 0, y: 0 });

  // Visualization modes
  const visualizationModes = [
    { id: 'heatmap', label: 'Heat Map', icon: 'fas fa-fire' },
    { id: 'cluster', label: 'Clusters', icon: 'fas fa-circle-nodes' },
    { id: 'timeline', label: 'Timeline', icon: 'fas fa-timeline' },
    { id: 'compare', label: 'Compare', icon: 'fas fa-layer-group' }
  ];

  // Incident types for filtering
  const incidentTypes = [
    { id: 'theft', label: 'Theft & Robbery' },
    { id: 'burglary', label: 'Burglary' },
    { id: 'assault', label: 'Assault' },
    { id: 'vehicle', label: 'Vehicle Theft' },
    { id: 'street', label: 'Street Crime' }
  ];

  // Time periods
  const timePeriods = [
    { id: '24h', label: 'Last 24 Hours' },
    { id: '7d', label: 'Last 7 Days' },
    { id: '30d', label: 'Last 30 Days' },
    { id: 'custom', label: 'Custom Range' }
  ];

  // Generate random map points
  const generateMapPoints = () => {
    const points = [];
    const pointCount = 50;
    
    for (let i = 0; i < pointCount; i++) {
      points.push({
        id: i,
        x: Math.random() * 80 + 10,
        y: Math.random() * 80 + 10,
        type: ['theft', 'burglary', 'assault', 'vehicle', 'street'][Math.floor(Math.random() * 5)],
        intensity: Math.random()
      });
    }
    
    return points;
  };

  const [mapPoints, setMapPoints] = useState([]);

  useEffect(() => {
    setMapPoints(generateMapPoints());
  }, []);

  // Handle filter toggle
  const toggleFilter = (filterId) => {
    setFilters(prev => ({
      ...prev,
      [filterId]: !prev[filterId]
    }));
  };

  // Handle mode change with animation
  const handleModeChange = (modeId) => {
    setActiveMode(modeId);
    // Add any mode-specific animations or data updates here
  };

  // Show tooltip
  const showTooltip = (event, content) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltip({
      visible: true,
      content,
      x: rect.left + rect.width / 2,
      y: rect.top - 10
    });
  };

  // Hide tooltip
  const hideTooltip = () => {
    setTooltip({ ...tooltip, visible: false });
  };

  // Export functionality
  const handleExport = (type) => {
    // Simulate export functionality
    alert(`Exporting ${type} report...`);
  };

  return (
    <section className="map-interface-section" id="maps">
      <div className="map-container">
        {/* Section Header */}
        <div className="map-header">
          <div className="map-badge">
            <i className="fas fa-map-marked-alt"></i>
            <span>Interactive Platform</span>
          </div>
          <h2 className="map-title">Live Incident Visualization</h2>
          <p className="map-subtitle">
            Explore real-time incident data across Lahore with advanced spatial analysis 
            and interactive visualization tools
          </p>
        </div>

        {/* Main Map Interface */}
        <div className="map-interface">
          {/* Map Visualization */}
          <div className="map-visualization">
            {/* Animated Grid Background */}
            <div className="map-grid"></div>
            
            {/* Heatmap Overlay */}
            {activeMode === 'heatmap' && <div className="heatmap-overlay"></div>}
            
            {/* Map Points */}
            {mapPoints.map(point => (
              <div
                key={point.id}
                className={`map-point ${point.intensity > 0.7 ? 'hotspot' : point.intensity > 0.4 ? 'cluster' : ''}`}
                style={{
                  left: `${point.x}%`,
                  top: `${point.y}%`,
                  animationDelay: `${point.id * 0.1}s`
                }}
                onMouseEnter={(e) => showTooltip(e, `Incident: ${point.type.toUpperCase()}\nIntensity: ${Math.round(point.intensity * 100)}%`)}
                onMouseLeave={hideTooltip}
              />
            ))}
          </div>

          {/* Control Panel */}
          <div className={`map-controls ${controlsVisible ? 'active' : ''}`}>
            <div className="control-header">
              <h3 className="control-title">Map Controls</h3>
              <button className="close-controls" onClick={() => setControlsVisible(false)}>
                <i className="fas fa-times"></i>
              </button>
            </div>

            {/* Visualization Modes */}
            <div className="visualization-modes">
              {visualizationModes.map(mode => (
                <button
                  key={mode.id}
                  className={`mode-btn ${activeMode === mode.id ? 'active' : ''}`}
                  onClick={() => handleModeChange(mode.id)}
                >
                  <i className={`${mode.icon} mode-icon`}></i>
                  <span className="mode-label">{mode.label}</span>
                </button>
              ))}
            </div>

            {/* Incident Type Filters */}
            <div className="filter-section">
              <h4 className="filter-title">Incident Types</h4>
              <div className="filter-group">
                {incidentTypes.map(type => (
                  <div
                    key={type.id}
                    className={`filter-option ${filters[type.id] ? 'active' : ''}`}
                    onClick={() => toggleFilter(type.id)}
                  >
                    <div className="filter-checkbox"></div>
                    <span className="filter-label">{type.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Time Period Filters */}
            <div className="filter-section">
              <h4 className="filter-title">Time Period</h4>
              <div className="filter-group">
                {timePeriods.map(period => (
                  <div
                    key={period.id}
                    className="filter-option"
                    onClick={() => {/* Handle time period change */}}
                  >
                    <div className="filter-checkbox"></div>
                    <span className="filter-label">{period.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Floating Action Button */}
          <button 
            className="map-fab"
            onClick={() => setControlsVisible(!controlsVisible)}
          >
            <i className="fas fa-sliders-h"></i>
          </button>

          {/* Data Panel */}
          <div className="data-panel">
            <div className="panel-tabs">
              <button 
                className={`panel-tab ${activeTab === 'trends' ? 'active' : ''}`}
                onClick={() => setActiveTab('trends')}
              >
                <i className="fas fa-chart-line"></i>
                Trends
              </button>
              <button 
                className={`panel-tab ${activeTab === 'analytics' ? 'active' : ''}`}
                onClick={() => setActiveTab('analytics')}
              >
                <i className="fas fa-chart-bar"></i>
                Analytics
              </button>
              <button 
                className={`panel-tab ${activeTab === 'insights' ? 'active' : ''}`}
                onClick={() => setActiveTab('insights')}
              >
                <i className="fas fa-lightbulb"></i>
                Insights
              </button>
            </div>

            <div className="chart-container">
              <div className="chart-placeholder">
                {activeTab === 'trends' && 'Incident Trends Over Time'}
                {activeTab === 'analytics' && 'Spatial Analysis Results'}
                {activeTab === 'insights' && 'AI-Generated Insights'}
              </div>
            </div>

            <div className="export-controls">
              <button 
                className="export-btn"
                onClick={() => handleExport('data')}
              >
                <i className="fas fa-download"></i>
                Export Data
              </button>
              <button 
                className="export-btn primary"
                onClick={() => handleExport('report')}
              >
                <i className="fas fa-file-pdf"></i>
                Generate Report
              </button>
            </div>
          </div>

          {/* Tooltip */}
          <div 
            className={`map-tooltip ${tooltip.visible ? 'visible' : ''}`}
            style={{
              left: `${tooltip.x}px`,
              top: `${tooltip.y}px`,
              transform: 'translate(-50%, -100%)'
            }}
          >
            <div className="tooltip-title">Incident Details</div>
            <div className="tooltip-content">{tooltip.content}</div>
          </div>
        </div>

        {/* Features Showcase */}
        <div className="map-features">
          <div className="features-grid">
            <div className="feature-item">
              <div className="feature-icon">
                <i className="fas fa-bolt"></i>
              </div>
              <h4>Real-time Updates</h4>
              <p>Live data streaming with instant incident updates and notifications</p>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <i className="fas fa-robot"></i>
              </div>
              <h4>AI-Powered Insights</h4>
              <p>Machine learning algorithms detect patterns and predict hotspots</p>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <i className="fas fa-mobile-alt"></i>
              </div>
              <h4>Mobile Optimized</h4>
              <p>Fully responsive design optimized for all devices and screen sizes</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default MapInterface;
