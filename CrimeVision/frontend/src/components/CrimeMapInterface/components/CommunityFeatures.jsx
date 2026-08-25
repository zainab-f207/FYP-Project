import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import apiService from '../../../services/apiService';
import EmergencyContacts from './EmergencyContacts';
import './CommunityFeatures.css';

const CommunityFeatures = () => {
  const { user, token } = useAuth();
  const [activeFeature, setActiveFeature] = useState('watch');
  const [isVisible, setIsVisible] = useState(false);
  const [communityStats, setCommunityStats] = useState({
    totalMembers: 0,
    activeToday: 0,
    alertsThisWeek: 0,
    resourcesAvailable: 0,
    connectionsMade: 0,
    incidentsReported: 0
  });
  const [userLocation, setUserLocation] = useState(null);
  const [joinModal, setJoinModal] = useState({ isOpen: false, feature: null });
  const [reportModal, setReportModal] = useState({ isOpen: false, feature: null });
  const [alertHistoryModal, setAlertHistoryModal] = useState({ isOpen: false });
  const [activityModal, setActivityModal] = useState({ isOpen: false });
  const [neighborsModal, setNeighborsModal] = useState({ isOpen: false });
  const [groupsModal, setGroupsModal] = useState({ isOpen: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [userStatuses, setUserStatuses] = useState({
    watch: { isJoined: false, isActive: false },
    alerts: { isSubscribed: false, alertCount: 0 },
    resources: { hasDownloaded: false, lastAccess: null },
    network: { connectionsCount: 0, isConnected: false }
  });

  // Simulate real-time data updates (only for activeToday, since alerts system is not yet implemented)
  useEffect(() => {
    const interval = setInterval(() => {
      setCommunityStats(prev => ({
        ...prev,
        activeToday: Math.floor(800 + Math.random() * 100)
      }));
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Get user location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
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

  // Fetch community stats and user statuses on mount
  useEffect(() => {
    const fetchCommunityStats = async () => {
      try {
        setLoading(true);
        const stats = await apiService.getCommunityStats();
        setCommunityStats(prev => ({
          ...prev,
          totalMembers: stats.total_members || prev.totalMembers,
          activeToday: stats.active_today || prev.activeToday,
          alertsThisWeek: stats.alerts_this_week || prev.alertsThisWeek,
          resourcesAvailable: stats.resources_available || prev.resourcesAvailable,
          connectionsMade: stats.connections_made || prev.connectionsMade,
          incidentsReported: stats.incidents_reported || prev.incidentsReported
        }));
      } catch (error) {
        console.error('Error fetching community stats:', error);
        setError('Failed to load community stats');
      } finally {
        setLoading(false);
      }
    };

    const fetchUserStatuses = async () => {
      if (!user || !token) return;

      try {
        const [watchStatus, alertsStatus, resourcesStatus, networkStatus] = await Promise.all([
          apiService.getUserCommunityStatus('watch'),
          apiService.getUserAlertStatus(),
          apiService.getUserResourceStatus(),
          apiService.getUserNetworkStatus()
        ]);

        setUserStatuses({
          watch: {
            isJoined: watchStatus.is_joined || false,
            isActive: watchStatus.is_active || false
          },
          alerts: {
            isSubscribed: alertsStatus.is_subscribed || false,
            alertCount: alertsStatus.alert_count || 0
          },
          resources: {
            hasDownloaded: resourcesStatus.has_downloaded || false,
            lastAccess: resourcesStatus.last_access
          },
          network: {
            connectionsCount: networkStatus.connections_count || 0,
            isConnected: networkStatus.is_connected || false
          }
        });
      } catch (error) {
        console.error('Error fetching user statuses:', error);
      }
    };

    fetchCommunityStats();
    fetchUserStatuses();
  }, [user, token]);

  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.2 }
    );

    const element = document.querySelector('.community-features-section');
    if (element) observer.observe(element);

    return () => observer.disconnect();
  }, []);

  const features = [
    {
      id: 'watch',
      icon: 'fas fa-eye',
      title: 'Neighborhood Watch',
      description: 'Connect with local community members for mutual safety support and real-time monitoring',
      stats: `${communityStats.totalMembers.toLocaleString()} active members`,
      color: '#10b981',
      gradient: 'linear-gradient(135deg, #10b981, #059669)',
      actions: userStatuses.watch.isJoined ? ['Leave Group', 'Report Incident', 'View Activity'] : ['Join Group', 'Report Incident', 'View Activity'],
      liveData: `${communityStats.activeToday} active today`,
      status: userStatuses.watch.isJoined ? (userStatuses.watch.isActive ? 'Active Member' : 'Member') : 'Not Joined',
      features: ['Real-time Monitoring', 'Incident Reporting', 'Community Chat', 'Patrol Coordination'],
      benefits: [
        '24/7 neighborhood surveillance',
        'Instant incident alerts',
        'Coordinated safety patrols',
        'Verified community members'
      ]
    },
    {
      id: 'alerts',
      icon: 'fas fa-bell',
      title: 'Community Alerts',
      description: 'Receive real-time notifications about safety concerns and incidents in your immediate area',
      stats: `${communityStats.alertsThisWeek} alerts this week`,
      color: '#f59e0b',
      gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      actions: userStatuses.alerts.isSubscribed ? ['Unsubscribe', 'Alert History', 'Customize'] : ['Subscribe', 'Alert History', 'Customize'],
      liveData: `${userStatuses.alerts.alertCount} alerts received`,
      status: userStatuses.alerts.isSubscribed ? 'Subscribed' : 'Not Subscribed',
      features: ['Push Notifications', 'Location-based Alerts', 'Custom Filters', 'Emergency Broadcasts'],
      benefits: [
        'Instant safety notifications',
        'Customizable alert zones',
        'Historical incident data',
        'Emergency broadcast system'
      ]
    },
    {
      id: 'emergency',
      icon: 'fas fa-phone-alt',
      title: 'Emergency Contacts',
      description: 'Quick access to emergency services, police, fire brigade, and medical assistance with one-tap calling',
      stats: '6 emergency services',
      color: '#ef4444',
      gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
      actions: ['Call Emergency', 'View Services', 'Share Location'],
      liveData: '24/7 available',
      status: 'Always Active',
      features: ['One-Tap Calling', 'Location Sharing', 'Emergency SMS', 'Service Tracking'],
      benefits: [
        'Instant emergency access',
        'GPS location sharing',
        'Real-time response tracking',
        'Multi-language support'
      ]
    },
    {
      id: 'resources',
      icon: 'fas fa-shield-alt',
      title: 'Safety Resources',
      description: 'Access comprehensive guides, emergency protocols, and safety tools for personal and community protection',
      stats: `${communityStats.resourcesAvailable} resources available`,
      color: '#3b82f6',
      gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
      actions: userStatuses.resources.hasDownloaded ? ['Browse', 'Download Again', 'Contribute'] : ['Browse', 'Download', 'Contribute'],
      liveData: userStatuses.resources.lastAccess ? `Last accessed ${new Date(userStatuses.resources.lastAccess).toLocaleDateString()}` : 'Updated daily',
      status: userStatuses.resources.hasDownloaded ? 'Downloaded' : 'Not Downloaded',
      features: ['Safety Guides', 'Emergency Protocols', 'Training Materials', 'Toolkits'],
      benefits: [
        'Expert safety guidelines',
        'Emergency procedure manuals',
        'Training resources',
        'Printable safety materials'
      ]
    },
    {
      id: 'network',
      icon: 'fas fa-users',
      title: 'Safety Network',
      description: 'Build trusted connections with neighbors, local authorities, and emergency services',
      stats: `${communityStats.connectionsMade.toLocaleString()} connections`,
      color: '#8b5cf6',
      gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
      actions: userStatuses.network.isConnected ? ['Find Neighbors', 'Disconnect', 'Groups'] : ['Find Neighbors', 'Connect', 'Groups'],
      liveData: `${userStatuses.network.connectionsCount} connections made`,
      status: userStatuses.network.isConnected ? 'Connected' : 'Not Connected',
      features: ['Trusted Contacts', 'Group Creation', 'Authority Links', 'Emergency Contacts'],
      benefits: [
        'Verified neighbor network',
        'Direct authority communication',
        'Emergency contact sharing',
        'Community group management'
      ]
    }
  ];

  const handleAction = async (featureId, action) => {
    if (!user || !token) {
      alert('Please log in to access community features.');
      return;
    }

    const feature = features.find(f => f.id === featureId);

    try {
      setLoading(true);
      switch (action) {
        case 'Join Group':
          setJoinModal({ isOpen: true, feature });
          break;
        case 'Report Incident':
          setReportModal({ isOpen: true, feature });
          break;
        case 'View Activity':
          setActivityModal({ isOpen: true });
          break;
        case 'Subscribe':
          await apiService.subscribeToAlerts(token, { area: user?.home_area || 'all', alert_radius: 5 });
          setUserStatuses(prev => ({
            ...prev,
            alerts: { ...prev.alerts, isSubscribed: true }
          }));
          alert(`🔔 Subscribed to ${feature.title} alerts`);
          break;
        case 'Unsubscribe':
          await apiService.unsubscribeFromAlerts(token);
          setUserStatuses(prev => ({
            ...prev,
            alerts: { ...prev.alerts, isSubscribed: false }
          }));
          alert(`🔕 Unsubscribed from ${feature.title}`);
          break;
        case 'Alert History':
          setAlertHistoryModal({ isOpen: true });
          break;
        case 'Customize':
          alert(`⚙️ ${feature.title} Settings\n\nCustomizing your alert preferences...`);
          break;
        case 'Browse':
          // Open resources modal or navigate to resources page
          alert(`📚 Opening Safety Resources\n\nBrowsing available safety guides and materials...`);
          break;
        case 'Download':
          await apiService.downloadResource('safety-guide');
          setUserStatuses(prev => ({
            ...prev,
            resources: { ...prev.resources, hasDownloaded: true, lastAccess: new Date() }
          }));
          alert(`📥 Resource Downloaded\n\nSafety guide downloaded successfully.`);
          break;
        case 'Download Again':
          await apiService.downloadResource('safety-guide');
          alert(`📥 Resource Downloaded Again\n\nLatest safety guide downloaded.`);
          break;
        case 'Contribute':
          alert(`🤝 Contribute to ${feature.title}\n\nOpening resource contribution form...`);
          break;
        case 'Find Neighbors':
          setNeighborsModal({ isOpen: true });
          break;
        case 'Connect':
          await apiService.sendConnectionRequest({ user_id: user.id, target_user_id: 'neighbor_id' });
          setUserStatuses(prev => ({
            ...prev,
            network: { ...prev.network, isConnected: true, connectionsCount: prev.network.connectionsCount + 1 }
          }));
          alert(`🔗 Connection Request Sent\n\nYour connection request has been sent.`);
          break;
        case 'Disconnect':
          await apiService.disconnectFromNetwork();
          setUserStatuses(prev => ({
            ...prev,
            network: { ...prev.network, isConnected: false }
          }));
          alert(`🔌 Disconnected from Safety Network`);
          break;
        case 'Groups':
          setGroupsModal({ isOpen: true });
          break;
        case 'Leave Group':
          await apiService.leaveCommunityGroup(featureId);
          setUserStatuses(prev => ({
            ...prev,
            watch: { ...prev.watch, isJoined: false, isActive: false }
          }));
          alert(`👋 Left ${feature.title}`);
          break;
        default:
          console.log(`Action: ${action} for feature: ${featureId}`);
      }
    } catch (error) {
      console.error('Error performing action:', error);
      setError(`Failed to ${action.toLowerCase()}. Please try again.`);
      alert(`❌ Error\n\nFailed to ${action.toLowerCase()}. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinCommunity = async (feature) => {
    if (!user || !token) {
      alert('Please log in to join the community.');
      setJoinModal({ isOpen: false, feature: null });
      return;
    }

    try {
      setLoading(true);
      await apiService.joinCommunityGroup(feature.id);
      alert(`✅ Successfully joined ${feature.title}!\n\nYou now have access to:\n• ${feature.features.join('\n• ')}`);
      // Update user status after joining
      setUserStatuses(prev => ({
        ...prev,
        watch: { isJoined: true, isActive: true }
      }));
      // Refresh community stats after joining
      const stats = await apiService.getCommunityStats();
      setCommunityStats(prev => ({
        ...prev,
        totalMembers: stats.total_members || prev.totalMembers,
      }));
    } catch (error) {
      console.error('Error joining community:', error);
      alert('❌ Failed to join community. Please try again.');
    } finally {
      setLoading(false);
      setJoinModal({ isOpen: false, feature: null });
    }
  };

  const getActiveFeature = () => features.find(f => f.id === activeFeature);

  return (
    <section className="community-features-section">
      <div className="features-container">
        {/* Enhanced Header */}
        <div className="features-header">
          <div className="header-badge">
            <i className="fas fa-users"></i>
            <span>Community Network</span>
          </div>
          <h2 className="features-title">Community Safety Ecosystem</h2>
          <p className="features-subtitle">
            Collaborative safety features that connect neighbors, share alerts, and build stronger, safer communities together
          </p>
        </div>

        {/* Live Community Stats */}
        <div className="community-stats">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">
                <i className="fas fa-user-friends"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{communityStats.totalMembers.toLocaleString()}</div>
                <div className="stat-label">Total Members</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <i className="fas fa-bell"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{communityStats.alertsThisWeek}</div>
                <div className="stat-label">Weekly Alerts</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <i className="fas fa-shield-alt"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">{communityStats.connectionsMade.toLocaleString()}</div>
                <div className="stat-label">Connections</div>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <i className="fas fa-chart-line"></i>
              </div>
              <div className="stat-content">
                <div className="stat-number">98%</div>
                <div className="stat-label">Response Rate</div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Features Grid */}
        <div className="features-grid">
          {features.map((feature, index) => (
            <div
              key={feature.id}
              className={`feature-card ${activeFeature === feature.id ? 'active' : ''} ${isVisible ? 'visible' : ''}`}
              onClick={() => setActiveFeature(feature.id)}
              style={{
                '--feature-color': feature.color,
                '--feature-gradient': feature.gradient,
                animationDelay: `${index * 150}ms`
              }}
            >
              {/* Background Effects */}
              <div className="card-background">
                <div className="floating-orb"></div>
                <div className="feature-glow"></div>
              </div>

              {/* Live Indicator */}
              <div className="live-indicator">
                <div className="pulse-dot"></div>
                <span>LIVE</span>
              </div>

              {/* Icon Section */}
              <div className="feature-icon-container">
                <div 
                  className="feature-icon-wrapper"
                  style={{ background: feature.gradient }}
                >
                  <i className={feature.icon}></i>
                </div>
              </div>

              {/* Content Section */}
              <div className="feature-content">
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
                
                {/* Live Data */}
                <div className="feature-live-data">
                  <i className="fas fa-circle"></i>
                  <span>{feature.liveData}</span>
                </div>

                {/* Status Badge */}
                <div className="feature-status">
                  <span className={`status-badge ${feature.status.toLowerCase().replace(' ', '-')}`}>
                    {feature.status}
                  </span>
                </div>

                {/* Stats */}
                <div className="feature-stats">
                  {feature.stats}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="feature-actions">
                {feature.actions.slice(0, 2).map((action, actionIndex) => (
                  <button
                    key={actionIndex}
                    className="action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(feature.id, action);
                    }}
                  >
                    {action}
                  </button>
                ))}
              </div>

              {/* Hover Effect */}
              <div className="card-hover-effect"></div>
            </div>
          ))}
        </div>

        {/* Active Feature Details */}
        <div className="feature-details-panel">
          {getActiveFeature() && (
            <div className="active-feature-details">
              <div className="details-header">
                <div className="feature-highlight">
                  <div 
                    className="highlight-icon"
                    style={{ background: getActiveFeature().gradient }}
                  >
                    <i className={getActiveFeature().icon}></i>
                  </div>
                  <div className="highlight-content">
                    <h3>{getActiveFeature().title}</h3>
                    <p>{getActiveFeature().description}</p>
                    <div className="highlight-stats">
                      <span className="stat-value">{getActiveFeature().stats}</span>
                      <span className="stat-badge">{getActiveFeature().liveData}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="details-content">
                <div className="features-list">
                  <h4>Key Features</h4>
                  <div className="features-grid-mini">
                    {getActiveFeature().features.map((featureItem, idx) => (
                      <div key={idx} className="feature-item">
                        <i className="fas fa-check"></i>
                        <span>{featureItem}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="benefits-section">
                  <h4>Community Benefits</h4>
                  <ul className="benefits-list">
                    {getActiveFeature().benefits.map((benefit, idx) => (
                      <li key={idx}>
                        <i className="fas fa-star"></i>
                        {benefit}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="action-section">
                  <h4>Get Started</h4>
                  <div className="action-buttons">
                    {getActiveFeature().actions.map((action, idx) => (
                      <button
                        key={idx}
                        className="primary-action-btn"
                        onClick={() => handleAction(getActiveFeature().id, action)}
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Community Impact */}
        <div className="community-impact">
          <div className="impact-header">
            <h3>Community Impact</h3>
            <p>Real results from our safety network</p>
          </div>
          <div className="impact-stats">
            <div className="impact-item">
              <div className="impact-number">47%</div>
              <div className="impact-label">Reduction in local crime</div>
            </div>
            <div className="impact-item">
              <div className="impact-number">89%</div>
              <div className="impact-label">Faster emergency response</div>
            </div>
            <div className="impact-item">
              <div className="impact-number">92%</div>
              <div className="impact-label">Member satisfaction rate</div>
            </div>
          </div>
        </div>
      </div>

      {/* Join Modal */}
      {joinModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Join {joinModal.feature?.title}</h3>
              <button onClick={() => setJoinModal({ isOpen: false, feature: null })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <div className="feature-preview">
                <div
                  className="preview-icon"
                  style={{ background: joinModal.feature?.gradient }}
                >
                  <i className={joinModal.feature?.icon}></i>
                </div>
                <h4>You'll get access to:</h4>
                <ul>
                  {joinModal.feature?.features.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  ))}
                </ul>
              </div>
              <div className="modal-actions">
                <button
                  className="join-btn"
                  onClick={() => handleJoinCommunity(joinModal.feature)}
                >
                  Join Community
                </button>
                <button
                  className="cancel-btn"
                  onClick={() => setJoinModal({ isOpen: false, feature: null })}
                >
                  Maybe Later
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Report Incident Modal */}
      {reportModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Report Incident</h3>
              <button onClick={() => setReportModal({ isOpen: false, feature: null })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <form onSubmit={async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const incidentData = {
                  type: formData.get('incident-type'),
                  description: formData.get('description'),
                  location: userLocation,
                  severity: formData.get('severity'),
                  user_id: user.id
                };

                try {
                  await apiService.reportIncident(incidentData);
                  alert('🚨 Incident Report Submitted\n\nYour report has been submitted and is being reviewed.');
                  setReportModal({ isOpen: false, feature: null });
                } catch (error) {
                  alert('❌ Failed to submit report. Please try again.');
                }
              }}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
                    Incident Type
                  </label>
                  <select
                    name="incident-type"
                    required
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      background: 'rgba(255, 255, 255, 0.1)',
                      color: '#e2e8f0'
                    }}
                  >
                    <option value="suspicious-activity">Suspicious Activity</option>
                    <option value="theft">Theft</option>
                    <option value="vandalism">Vandalism</option>
                    <option value="assault">Assault</option>
                    <option value="emergency">Emergency</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
                    Severity
                  </label>
                  <select
                    name="severity"
                    required
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      background: 'rgba(255, 255, 255, 0.1)',
                      color: '#e2e8f0'
                    }}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
                    Description
                  </label>
                  <textarea
                    name="description"
                    required
                    placeholder="Describe the incident in detail..."
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      background: 'rgba(255, 255, 255, 0.1)',
                      color: '#e2e8f0',
                      minHeight: '100px',
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div className="modal-actions">
                  <button
                    type="submit"
                    className="join-btn"
                  >
                    Submit Report
                  </button>
                  <button
                    type="button"
                    className="cancel-btn"
                    onClick={() => setReportModal({ isOpen: false, feature: null })}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Alert History Modal */}
      {alertHistoryModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Alert History</h3>
              <button onClick={() => setAlertHistoryModal({ isOpen: false })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {/* Mock alert history data */}
                {[
                  { id: 1, type: 'Suspicious Activity', time: '2 hours ago', location: 'Main Street', status: 'Active' },
                  { id: 2, type: 'Traffic Incident', time: '1 day ago', location: 'Elm Avenue', status: 'Resolved' },
                  { id: 3, type: 'Weather Alert', time: '3 days ago', location: 'Downtown', status: 'Resolved' },
                  { id: 4, type: 'Community Event', time: '1 week ago', location: 'City Park', status: 'Resolved' }
                ].map(alert => (
                  <div key={alert.id} style={{
                    padding: '1rem',
                    marginBottom: '0.5rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h4 style={{ color: '#e2e8f0', margin: '0 0 0.25rem 0' }}>{alert.type}</h4>
                        <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.9rem' }}>
                          {alert.location} • {alert.time}
                        </p>
                      </div>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '20px',
                        fontSize: '0.7rem',
                        fontWeight: '600',
                        background: alert.status === 'Active' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: alert.status === 'Active' ? '#ef4444' : '#10b981'
                      }}>
                        {alert.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setAlertHistoryModal({ isOpen: false })}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Activity Modal */}
      {activityModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Community Activity</h3>
              <button onClick={() => setActivityModal({ isOpen: false })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {/* Mock activity data */}
                {[
                  { id: 1, type: 'New Member', user: 'John D.', time: '30 min ago', action: 'joined Neighborhood Watch' },
                  { id: 2, type: 'Incident Report', user: 'Sarah M.', time: '2 hours ago', action: 'reported suspicious activity' },
                  { id: 3, type: 'Alert Sent', user: 'System', time: '4 hours ago', action: 'sent community alert' },
                  { id: 4, type: 'Resource Download', user: 'Mike R.', time: '6 hours ago', action: 'downloaded safety guide' },
                  { id: 5, type: 'Connection Made', user: 'Lisa K.', time: '1 day ago', action: 'connected with 3 neighbors' }
                ].map(activity => (
                  <div key={activity.id} style={{
                    padding: '1rem',
                    marginBottom: '0.5rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontSize: '0.8rem',
                        fontWeight: '600'
                      }}>
                        {activity.user.charAt(0)}
                      </div>
                      <div style={{ flex: 1 }}>
                        <p style={{ color: '#e2e8f0', margin: '0 0 0.25rem 0', fontSize: '0.9rem' }}>
                          <strong>{activity.user}</strong> {activity.action}
                        </p>
                        <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.8rem' }}>
                          {activity.time}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setActivityModal({ isOpen: false })}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Neighbors Modal */}
      {neighborsModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Find Neighbors</h3>
              <button onClick={() => setNeighborsModal({ isOpen: false })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder="Search by name or location..."
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: '#e2e8f0',
                    marginBottom: '1rem'
                  }}
                />
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {/* Mock neighbors data */}
                {[
                  { id: 1, name: 'John Doe', distance: '0.2 miles', status: 'Verified', mutual: 3 },
                  { id: 2, name: 'Sarah Smith', distance: '0.5 miles', status: 'Verified', mutual: 2 },
                  { id: 3, name: 'Mike Johnson', distance: '0.8 miles', status: 'Verified', mutual: 1 },
                  { id: 4, name: 'Lisa Brown', distance: '1.2 miles', status: 'Pending', mutual: 0 }
                ].map(neighbor => (
                  <div key={neighbor.id} style={{
                    padding: '1rem',
                    marginBottom: '0.5rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <h4 style={{ color: '#e2e8f0', margin: '0 0 0.25rem 0' }}>{neighbor.name}</h4>
                      <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.9rem' }}>
                        {neighbor.distance} away • {neighbor.mutual} mutual connections
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '12px',
                        fontSize: '0.7rem',
                        background: neighbor.status === 'Verified' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: neighbor.status === 'Verified' ? '#10b981' : '#f59e0b'
                      }}>
                        {neighbor.status}
                      </span>
                      <button
                        style={{
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          border: '1px solid rgba(59, 130, 246, 0.3)',
                          background: 'rgba(59, 130, 246, 0.1)',
                          color: '#3b82f6',
                          cursor: 'pointer'
                        }}
                        onClick={() => alert(`Connection request sent to ${neighbor.name}`)}
                      >
                        Connect
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setNeighborsModal({ isOpen: false })}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Groups Modal */}
      {groupsModal.isOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Community Groups</h3>
              <button onClick={() => setGroupsModal({ isOpen: false })}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '1rem' }}>
                <button
                  style={{
                    padding: '0.75rem 1.5rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    background: 'rgba(16, 185, 129, 0.1)',
                    color: '#10b981',
                    cursor: 'pointer',
                    marginBottom: '1rem'
                  }}
                  onClick={() => alert('Create new group functionality would open here')}
                >
                  + Create New Group
                </button>
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {/* Mock groups data */}
                {[
                  { id: 1, name: 'Downtown Safety Patrol', members: 45, type: 'Patrol', status: 'Active' },
                  { id: 2, name: 'Neighborhood Watch Group A', members: 32, type: 'Watch', status: 'Active' },
                  { id: 3, name: 'Emergency Response Team', members: 28, type: 'Emergency', status: 'Active' },
                  { id: 4, name: 'Youth Safety Program', members: 15, type: 'Education', status: 'Active' }
                ].map(group => (
                  <div key={group.id} style={{
                    padding: '1rem',
                    marginBottom: '0.5rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <h4 style={{ color: '#e2e8f0', margin: '0 0 0.25rem 0' }}>{group.name}</h4>
                      <p style={{ color: '#94a3b8', margin: 0, fontSize: '0.9rem' }}>
                        {group.members} members • {group.type}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '12px',
                        fontSize: '0.7rem',
                        background: 'rgba(16, 185, 129, 0.2)',
                        color: '#10b981'
                      }}>
                        {group.status}
                      </span>
                      <button
                        style={{
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          border: '1px solid rgba(59, 130, 246, 0.3)',
                          background: 'rgba(59, 130, 246, 0.1)',
                          color: '#3b82f6',
                          cursor: 'pointer'
                        }}
                        onClick={() => alert(`Joining ${group.name}...`)}
                      >
                        Join
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setGroupsModal({ isOpen: false })}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default CommunityFeatures;
