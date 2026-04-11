import React, { useState, useEffect, useContext } from 'react';
import './PatrolRequest.css';
import { AuthContext } from '../../../contexts/AuthContext_updated';
import apiService from '../../../services/apiService_updated';

const PatrolRequest = () => {
  const { user, token } = useContext(AuthContext);
  const [isVisible, setIsVisible] = useState(false);
  const [location, setLocation] = useState(null);
  const [isRequesting, setIsRequesting] = useState(false);
  const [requestStatus, setRequestStatus] = useState(null);
  const [requestHistory, setRequestHistory] = useState([]);
  const [formData, setFormData] = useState({
    urgency: 'medium',
    description: '',
    location_details: ''
  });

  // Get user location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            address: 'Current Location' // Would be reverse geocoded in production
          });
        },
        (error) => {
          console.log('Location access denied:', error);
          setLocation({
            lat: 31.5204,
            lng: 74.3587,
            address: 'Lahore, Pakistan'
          });
        }
      );
    }
  }, []);

  // Load request history
  useEffect(() => {
    const loadHistory = async () => {
      if (!token) return;

      try {
        const history = await apiService.getPatrolRequests(token);
        setRequestHistory(history.slice(0, 5)); // Show last 5 requests
      } catch (error) {
        console.error('Failed to load patrol request history:', error);
      }
    };

    loadHistory();
  }, [token]);

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

    const element = document.querySelector('.patrol-request-section');
    if (element) {
      observer.observe(element);
    }

    return () => observer.disconnect();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();

    if (!user || !token) {
      alert('🔐 Authentication Required\n\nPlease log in to request patrol assistance.');
      return;
    }

    if (!location) {
      alert('📍 Location Required\n\nPlease enable location services to request patrol.');
      return;
    }

    if (isRequesting) {
      alert('⏳ Request in Progress\n\nPlease wait while we process your request.');
      return;
    }

    setIsRequesting(true);

    try {
      const requestData = {
        ...formData,
        location: {
          latitude: location.lat,
          longitude: location.lng,
          address: location.address
        },
        timestamp: new Date().toISOString()
      };

      const response = await apiService.requestPatrol(token, requestData);

      setRequestStatus({
        type: 'success',
        message: `🚓 Patrol Request Submitted Successfully\n\nRequest ID: ${response.id || 'N/A'}\nEstimated response time: 8-12 minutes\n\nPolice will be dispatched to your location.`,
        requestId: response.id
      });

      // Reset form
      setFormData({
        urgency: 'medium',
        description: '',
        location_details: ''
      });

      // Refresh history
      const history = await apiService.getPatrolRequests(token);
      setRequestHistory(history.slice(0, 5));

    } catch (error) {
      console.error('Patrol request failed:', error);
      setRequestStatus({
        type: 'error',
        message: `❌ Patrol Request Failed\n\n${error.message || 'Unable to submit patrol request. Please try again.'}`
      });
    } finally {
      setIsRequesting(false);
    }
  };

  const getUrgencyColor = (urgency) => {
    const colors = {
      low: '#10b981',
      medium: '#f59e0b',
      high: '#ef4444',
      critical: '#7c2d12'
    };
    return colors[urgency] || colors.medium;
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#f59e0b',
      accepted: '#3b82f6',
      dispatched: '#8b5cf6',
      completed: '#10b981',
      cancelled: '#6b7280'
    };
    return colors[status] || colors.pending;
  };

  return (
    <section className="patrol-request-section">
      <div className="patrol-container">
        {/* Header */}
        <div className="patrol-header">
          <div className="header-badge">
            <i className="fas fa-car"></i>
            <span>Patrol Services</span>
          </div>
          <h2 className="patrol-title">Request Police Patrol</h2>
          <p className="patrol-subtitle">
            Request immediate police presence in your area for enhanced safety and security
          </p>
        </div>

        <div className="patrol-content">
          {/* Request Form */}
          <div className="request-form-card">
            <div className="form-header">
              <h3>Submit Patrol Request</h3>
              <div className="form-status">
                <i className={`fas ${location ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
                <span>{location ? 'Location detected' : 'Location required'}</span>
              </div>
            </div>

            <form onSubmit={handleSubmitRequest} className="patrol-form">
              {/* Urgency Level */}
              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-exclamation-triangle"></i>
                  Urgency Level
                </label>
                <select
                  name="urgency"
                  value={formData.urgency}
                  onChange={handleInputChange}
                  className="form-select"
                  style={{ borderColor: getUrgencyColor(formData.urgency) }}
                >
                  <option value="low">Low - General patrol request</option>
                  <option value="medium">Medium - Increased presence needed</option>
                  <option value="high">High - Suspicious activity</option>
                  <option value="critical">Critical - Immediate threat</option>
                </select>
              </div>

              {/* Description */}
              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-comment"></i>
                  Description
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Describe the situation and why you need police patrol..."
                  className="form-textarea"
                  rows="4"
                  required
                />
              </div>

              {/* Location Details */}
              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-map-marker-alt"></i>
                  Additional Location Details
                </label>
                <input
                  type="text"
                  name="location_details"
                  value={formData.location_details}
                  onChange={handleInputChange}
                  placeholder="Specific address, landmarks, or directions..."
                  className="form-input"
                />
              </div>

              {/* Location Display */}
              {location && (
                <div className="location-display">
                  <div className="location-icon">
                    <i className="fas fa-location-arrow"></i>
                  </div>
                  <div className="location-info">
                    <div className="location-address">{location.address}</div>
                    <div className="location-coords">
                      {location.lat.toFixed(6)}, {location.lng.toFixed(6)}
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                className={`submit-btn ${isRequesting ? 'loading' : ''}`}
                disabled={isRequesting || !location}
              >
                {isRequesting ? (
                  <>
                    <div className="spinner"></div>
                    Submitting Request...
                  </>
                ) : (
                  <>
                    <i className="fas fa-paper-plane"></i>
                    Request Patrol
                  </>
                )}
              </button>
            </form>

            {/* Status Message */}
            {requestStatus && (
              <div className={`status-message ${requestStatus.type}`}>
                <div className="status-icon">
                  <i className={`fas ${requestStatus.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}`}></i>
                </div>
                <div className="status-content">
                  <pre>{requestStatus.message}</pre>
                </div>
                <button
                  className="status-close"
                  onClick={() => setRequestStatus(null)}
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
            )}
          </div>

          {/* Request History */}
          <div className="request-history-card">
            <div className="history-header">
              <h3>Recent Requests</h3>
              <div className="history-count">
                <i className="fas fa-history"></i>
                <span>{requestHistory.length} requests</span>
              </div>
            </div>

            <div className="history-list">
              {requestHistory.length > 0 ? (
                requestHistory.map((request) => (
                  <div key={request.id} className="history-item">
                    <div className="history-icon">
                      <i className="fas fa-car"></i>
                    </div>
                    <div className="history-content">
                      <div className="history-title">
                        Patrol Request #{request.id}
                      </div>
                      <div className="history-meta">
                        <span className="history-date">
                          {new Date(request.timestamp).toLocaleDateString()}
                        </span>
                        <span
                          className="history-status"
                          style={{ backgroundColor: getStatusColor(request.status) }}
                        >
                          {request.status || 'pending'}
                        </span>
                      </div>
                      {request.description && (
                        <div className="history-description">
                          {request.description.length > 50
                            ? `${request.description.substring(0, 50)}...`
                            : request.description
                          }
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-history">
                  <i className="fas fa-inbox"></i>
                  <p>No patrol requests yet</p>
                  <span>Submit your first request above</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="patrol-footer">
          <div className="footer-info">
            <div className="info-item">
              <div className="info-icon">
                <i className="fas fa-clock"></i>
              </div>
              <div className="info-content">
                <span className="info-label">Response Time</span>
                <span className="info-value">8-12 minutes</span>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <i className="fas fa-shield-alt"></i>
              </div>
              <div className="info-content">
                <span className="info-label">Service</span>
                <span className="info-value">24/7 Available</span>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <i className="fas fa-map-marker-alt"></i>
              </div>
              <div className="info-content">
                <span className="info-label">Coverage</span>
                <span className="info-value">Lahore Division</span>
              </div>
            </div>
          </div>

          <div className="emergency-notice">
            <div className="notice-icon">
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <div className="notice-content">
              <strong>Emergency Situations:</strong>
              <span>For immediate danger, call emergency services at 112 directly</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PatrolRequest;
