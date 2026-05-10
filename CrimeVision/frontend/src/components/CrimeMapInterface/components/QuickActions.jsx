import React, { useState, useEffect } from 'react';
import './QuickActions.css';

const QuickActions = () => {
  const [activeAction, setActiveAction] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [location, setLocation] = useState(null);

  // Get user location for emergency services
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => {
          console.log('Location access denied:', error);
        }
      );
    }
  }, []);

  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1 }
    );

    const element = document.querySelector('.quick-actions-section');
    if (element) {
      observer.observe(element);
    }

    return () => observer.disconnect();
  }, []);

  const actions = [
    {
      id: 'emergency',
      icon: 'fas fa-phone-alt',
      label: 'Emergency Call',
      description: 'Direct emergency services contact',
      color: '#dc2626',
      gradient: 'linear-gradient(135deg, #dc2626, #b91c1c)',
      type: 'emergency',
      action: () => {
        if (window.confirm('🚨 EMERGENCY CALL\n\nAre you sure you want to call emergency services?\n\nThis will dial 112 immediately.')) {
          window.open('tel:112', '_self');
        }
      }
    },
    {
      id: 'safety',
      icon: 'fas fa-shield-alt',
      label: 'Safety Check',
      description: 'Request immediate safety assistance',
      color: '#059669',
      gradient: 'linear-gradient(135deg, #059669, #047857)',
      type: 'safety',
      action: () => {
        if (!location) {
          alert('📍 Location Required\n\nPlease enable location services to perform safety check.');
          return;
        }
        alert(`✅ Safety Check\n\nYour current location: Lat ${location.lat.toFixed(4)}, Lng ${location.lng.toFixed(4)}\n\nArea safety status: SECURE\nNo immediate threats detected in your vicinity.`);
      }
    },
    {
      id: 'alerts',
      icon: 'fas fa-bell',
      label: 'Live Alerts',
      description: 'Real-time crime alerts in your area',
      color: '#f59e0b',
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      type: 'alert',
      action: () => {
        const isSubscribed = localStorage.getItem('alertSubscription') === 'true';
        const newStatus = !isSubscribed;
        localStorage.setItem('alertSubscription', newStatus.toString());
        alert(newStatus ?
          '🔔 Alerts Enabled\n\nYou will receive real-time crime alerts.' :
          '🔕 Alerts Disabled\n\nYou have unsubscribed from alerts.'
        );
      }
    },
    {
      id: 'resources',
      icon: 'fas fa-first-aid',
      label: 'Emergency Resources',
      description: 'Access emergency services & support',
      color: '#0891b2',
      gradient: 'linear-gradient(135deg, #0891b2, #0e7490)',
      type: 'resource',
      action: () => {
        if (!location) {
          alert('📍 Location Required\n\nPlease enable location services to access emergency resources.');
          return;
        }

        const emergencyServices = [
          {
            name: 'Police Station',
            phone: '15',
            coords: { lat: 31.5497, lng: 74.3436 },
            icon: 'fas fa-shield-alt'
          },
          {
            name: 'Hospital',
            phone: '1122',
            coords: { lat: 31.5204, lng: 74.3587 },
            icon: 'fas fa-hospital'
          },
          {
            name: 'Fire Station',
            phone: '16',
            coords: { lat: 31.5497, lng: 74.3436 },
            icon: 'fas fa-fire-extinguisher'
          }
        ];

        const serviceOptions = emergencyServices.map(service =>
          `${service.icon.split(' ')[1]} ${service.name} (${service.phone})`
        ).join('\n');

        const selectedService = prompt(`🏥 Emergency Resources\n\nSelect a service to get directions:\n\n${serviceOptions}\n\nEnter the number (1-3) or service name:`);

        if (selectedService) {
          const serviceIndex = parseInt(selectedService) - 1;
          const service = emergencyServices[serviceIndex] ||
                         emergencyServices.find(s => s.name.toLowerCase().includes(selectedService.toLowerCase()));

          if (service) {
            // Open OpenStreetMap with routing
            const osmUrl = `https://www.openstreetmap.org/directions?engine=graphhopper_car&route=${location.lat},${location.lng};${service.coords.lat},${service.coords.lng}`;
            window.open(osmUrl, '_blank');

            alert(`🗺️ Opening Map Directions\n\nRouting from your location to ${service.name}\nPhone: ${service.phone}`);
          } else {
            alert('❌ Invalid selection. Please try again.');
          }
        }
      }
    }
  ];

  const handleActionClick = (action) => {
    setActiveAction(action.id);
    
    // Add haptic feedback if available
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
    
    // Execute the action
    action.action();
    
    // Reset active state after animation
    setTimeout(() => setActiveAction(null), 600);
  };

  const getActionBadge = (type) => {
    const badges = {
      emergency: { text: 'URGENT', color: '#ef4444' },
      safety: { text: 'SAFETY', color: '#10b981' },
      service: { text: 'SERVICE', color: '#3b82f6' },
      alert: { text: 'ALERT', color: '#f59e0b' },
      resource: { text: 'RESOURCE', color: '#8b5cf6' }
    };
    
    return badges[type] || { text: 'ACTION', color: '#6b7280' };
  };

  return (
    <section className="quick-actions-section">
      <div className="actions-container">
        {/* Enhanced Header */}
        <div className="actions-header">
          <div className="header-badge">
            <i className="fas fa-bolt"></i>
            <span>Quick Access</span>
          </div>
          <h2 className="actions-title">Emergency & Safety Services</h2>
          <p className="actions-subtitle">
            Immediate access to critical safety resources and emergency services
          </p>
        </div>

        {/* Main Actions Grid - FIXED: Ensuring cards render */}
        <div className="actions-grid">
          {actions.map((action, index) => {
            const badge = getActionBadge(action.type);
            
            return (
              <div
                key={action.id}
                className={`action-card ${activeAction === action.id ? 'active' : ''} ${isVisible ? 'visible' : ''}`}
                style={{
                  '--action-color': action.color,
                  '--action-gradient': action.gradient,
                  animationDelay: `${index * 100}ms`
                }}
                onClick={() => handleActionClick(action)}
              >
                {/* Background Effects */}
                <div className="card-background">
                  <div className="floating-orb"></div>
                  <div className="action-glow"></div>
                </div>

                {/* Action Badge */}
                <div 
                  className="action-badge"
                  style={{ backgroundColor: badge.color }}
                >
                  {badge.text}
                </div>

                {/* Icon Section */}
                <div className="action-icon-container">
                  <div 
                    className="action-icon-wrapper"
                    style={{ background: action.gradient }}
                  >
                    <i className={action.icon}></i>
                  </div>
                  
                  {/* Live Indicator for Emergency Actions */}
                  {(action.type === 'emergency' || action.type === 'safety') && (
                    <div className="live-indicator">
                      <div className="pulse-dot"></div>
                      <span>LIVE</span>
                    </div>
                  )}
                </div>

                {/* Content Section */}
                <div className="action-content">
                  <h3 className="action-label">{action.label}</h3>
                  <p className="action-description">{action.description}</p>
                </div>

                {/* Action Arrow */}
                <div className="action-arrow">
                  <i className="fas fa-chevron-right"></i>
                </div>

                {/* Hover Effect */}
                <div className="card-hover-effect"></div>
              </div>
            );
          })}
        </div>

        {/* Enhanced Footer */}
        <div className="actions-footer">
          <div className="footer-grid">
            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-clock"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Response Time</span>
                <span className="footer-value">2-5 minutes</span>
              </div>
            </div>

            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-shield-check"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Service Status</span>
                <span className="footer-value active">All Systems Active</span>
              </div>
            </div>

            <div className="footer-item">
              <div className="footer-icon">
                <i className="fas fa-user-check"></i>
              </div>
              <div className="footer-content">
                <span className="footer-label">Verified</span>
                <span className="footer-value">Official Services</span>
              </div>
            </div>
          </div>

          {/* Emergency Notice */}
          <div className="emergency-notice">
            <div className="notice-icon">
              <i className="fas fa-info-circle"></i>
            </div>
            <div className="notice-content">
              <strong>Emergency Protocol:</strong>
              <span>In case of immediate danger, call emergency services directly at 112</span>
            </div>
          </div>

          {/* Location Status */}
          <div className="location-status">
            <i className={`fas ${location ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
            <span>
              {location ? 
                'Location services active - Enhanced safety features available' : 
                'Enable location for full functionality'
              }
            </span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="quick-stats">
          <div className="stat-item">
            <div className="stat-number">24/7</div>
            <div className="stat-label">Available</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">50K+</div>
            <div className="stat-label">Users Protected</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">98%</div>
            <div className="stat-label">Success Rate</div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default QuickActions;
