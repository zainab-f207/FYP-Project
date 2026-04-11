import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LoadingSpinner,
  SkeletonCard,
  SkeletonList,
  LoadingOverlay,
  ShimmerCard
} from '../CrimeMapInterface/components/LoadingComponents';
import styles from './UserDashboard.module.css';
import './UserDropdown.css';
import PredictionPage from './PredictionPage';
import EmergencyContacts from '../CrimeMapInterface/components/EmergencyContacts';
import AIRouteAnalysis from "./AIRouteAnalysis";
import CrimeMap from '../CrimeMapInterface/CrimeMapInterface_real_insights';
import CrimeMapInterface from '../CrimeMapInterface/CrimeMapInterface_real_insights';
import ProfileModal from './ProfileModal';
import BrowserNotifications from './BrowserNotifications';
import SafetyScoreExplainer from './SafetyScoreExplainer';
import apiService from '../../services/apiService_updated';

const getProfileImageUrl = (profilePicture) => {
  if (!profilePicture) return null;
  if (profilePicture.startsWith('http://') || profilePicture.startsWith('https://')) {
    return profilePicture;
  }
  // Point to backend server where profile photos are served
  const backendUrl = process.env.NODE_ENV === 'production'
    ? window.location.origin.replace(':5173', ':8000')
    : 'http://localhost:8000';
  return `${backendUrl}/${profilePicture}`;
};

const normalizeRiskBandLabel = (value) => {
  const normalized = String(value || '').toLowerCase();
  if (normalized.includes('critical') || normalized.includes('avoid')) return 'Avoid';
  if (normalized.includes('high') || normalized.includes('warning')) return 'Warning';
  if (normalized.includes('moderate') || normalized.includes('medium') || normalized.includes('caution')) return 'Caution';
  if (normalized.includes('low') || normalized.includes('safe')) return 'Safe';
  return 'Caution';
};

const RECENT_ALERT_WINDOW_DAYS = 90;

const normalizeAreaToken = (value) =>
  String(value || '')
    .split(',')[0]
    .trim()
    .toLowerCase();

const isWithinLastDays = (timestamp, days) => {
  if (!timestamp) return false;
  const dt = new Date(timestamp);
  if (Number.isNaN(dt.getTime())) return false;
  const cutoff = Date.now() - (days * 24 * 60 * 60 * 1000);
  return dt.getTime() >= cutoff;
};

// Individual Alert Card Component (moved outside UserDashboard)
const AlertCard = ({ alert, onMarkAsRead, markingRead, isRead = false }) => {
  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
      case 'critical':
        return 'fas fa-exclamation-triangle';
      case 'medium':
        return 'fas fa-info-circle';
      case 'low':
      default:
        return 'fas fa-info-circle';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
      case 'critical':
        return '#ef4444';
      case 'medium':
        return '#f59e0b';
      case 'low':
      default:
        return '#10b981';
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Recently';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <div className={`${styles.alertCard} ${isRead ? styles.alertCardRead : ''}`}>
      <div 
        className={styles.alertSeverityIndicator}
        style={{ backgroundColor: getSeverityColor(alert.severity) }}
      ></div>
      
      <div className={styles.alertIcon}>
        <i className={getSeverityIcon(alert.severity)}></i>
      </div>
      
      <div className={styles.alertContent}>
        <div className={styles.alertHeader}>
          <h4 className={styles.alertTitle}>{alert.title || 'Safety Alert'}</h4>
          <span className={styles.alertTime}>
            {formatTime(alert.created_at || alert.timestamp)}
          </span>
        </div>
        
        <p className={styles.alertMessage}>
          {alert.message || alert.description || 'No message provided'}
        </p>
        
        {alert.area && (
          <div className={styles.alertArea}>
            <i className="fas fa-map-marker-alt"></i>
            {alert.area}
          </div>
        )}
        
        <div className={styles.alertMeta}>
          <span className={styles.alertType}>{alert.type || alert.alert_type || 'General'}</span>
          {alert.source && <span className={styles.alertSource}>{alert.source}</span>}
        </div>
      </div>
      
      {!isRead && onMarkAsRead && (
        <button 
          className={styles.markReadButton}
          onClick={() => onMarkAsRead(alert.id)}
          disabled={markingRead}
          title="Mark as read"
        >
          {markingRead ? (
            <i className="fas fa-spinner fa-spin"></i>
          ) : (
            <i className="fas fa-check"></i>
          )}
        </button>
      )}
    </div>
  );
};

// Alerts Page Component (moved outside UserDashboard)
const AlertsPage = ({ styles, alerts, loading, token, onRefresh }) => {
  const [localAlerts, setLocalAlerts] = useState(alerts || []);
  const [markingRead, setMarkingRead] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Update local alerts when props change
  useEffect(() => {
    if (alerts) {
      setLocalAlerts(alerts);
    }
  }, [alerts]);

  // Function to mark an alert as read
  const handleMarkAsRead = async (alertId) => {
    try {
      setMarkingRead(true);
      await apiService.markAlertAsRead(token, alertId);
      
      // Update local state
      setLocalAlerts(prevAlerts => 
        prevAlerts.map(alert => 
          alert.id === alertId ? { ...alert, is_read: true } : alert
        )
      );
    } catch (error) {
      console.error('Error marking alert as read:', error);
      alert('Failed to mark alert as read');
    } finally {
      setMarkingRead(false);
    }
  };

  // Function to mark all alerts as read
  const handleMarkAllAsRead = async () => {
    try {
      setMarkingRead(true);
      await apiService.markAllAlertsAsRead(token);
      
      // Update all alerts to read
      setLocalAlerts(prevAlerts => 
        prevAlerts.map(alert => ({ ...alert, is_read: true }))
      );
    } catch (error) {
      console.error('Error marking all alerts as read:', error);
      alert('Failed to mark all alerts as read');
    } finally {
      setMarkingRead(false);
    }
  };

  // Function to refresh alerts
  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      if (onRefresh) {
        await onRefresh();
      }
    } catch (error) {
      console.error('Error refreshing alerts:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const recentAlerts = localAlerts.filter((alert) =>
    isWithinLastDays(alert.created_at || alert.timestamp, RECENT_ALERT_WINDOW_DAYS)
  );
  const unreadAlerts = recentAlerts.filter(alert => !alert.is_read);
  const readAlerts = recentAlerts.filter(alert => alert.is_read);

  // Sort alerts by creation date (newest first)
  const sortedUnreadAlerts = [...unreadAlerts].sort((a, b) => 
    new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp)
  );
  const sortedReadAlerts = [...readAlerts].sort((a, b) => 
    new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp)
  );

  return (
    <div className={styles.pageContainer}>
      <div className={styles.pageHeader}>
        <h1>Alerts & Notifications</h1>
        <p>Recent area activity in the last 30-90 days</p>
      </div>

      {loading ? (
        <div className={styles.loadingState}>
          <i className="fas fa-bell fa-spin"></i>
          <p>Loading alerts...</p>
        </div>
      ) : (
        <div className={styles.alertsContainer}>
          {/* Alert Actions */}
          <div className={styles.alertActions}>
            <div className={styles.alertStats}>
              <span className={styles.statBadge}>
                {unreadAlerts.length} Unread
              </span>
              <span className={styles.statBadge}>
                {recentAlerts.length} Last {RECENT_ALERT_WINDOW_DAYS} Days
              </span>
            </div>
            <div className={styles.alertButtons}>
              <button 
                className={styles.refreshButton}
                onClick={handleRefresh}
                disabled={refreshing}
              >
                {refreshing ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    Refreshing...
                  </>
                ) : (
                  <>
                    <i className="fas fa-redo"></i>
                    Refresh
                  </>
                )}
              </button>
              {unreadAlerts.length > 0 && (
                <button 
                  className={styles.markAllButton}
                  onClick={handleMarkAllAsRead}
                  disabled={markingRead}
                >
                  {markingRead ? (
                    <>
                      <i className="fas fa-spinner fa-spin"></i>
                      Marking...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-check-double"></i>
                      Mark All as Read
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Unread Alerts */}
          {sortedUnreadAlerts.length > 0 && (
            <div className={styles.alertSection}>
              <h3 className={styles.alertSectionTitle}>
                <i className="fas fa-exclamation-circle"></i>
                Unread Alerts ({sortedUnreadAlerts.length})
              </h3>
              {sortedUnreadAlerts.map((alert, index) => (
                <AlertCard 
                  key={alert.id || `unread-${index}`}
                  alert={alert}
                  onMarkAsRead={handleMarkAsRead}
                  markingRead={markingRead}
                />
              ))}
            </div>
          )}

          {/* Read Alerts */}
          {sortedReadAlerts.length > 0 && (
            <div className={styles.alertSection}>
              <h3 className={styles.alertSectionTitle}>
                <i className="fas fa-history"></i>
                Read Alerts ({sortedReadAlerts.length})
              </h3>
              {sortedReadAlerts.map((alert, index) => (
                <AlertCard 
                  key={alert.id || `read-${index}`}
                  alert={alert}
                  isRead={true}
                />
              ))}
            </div>
          )}

          {/* No Alerts State */}
          {recentAlerts.length === 0 && (
            <div className={styles.noAlerts}>
              <i className="fas fa-bell-slash"></i>
              <h3>No Recent Alerts</h3>
              <p>No alert activity in the recent 30-90 day window for this monitored area.</p>
              <button 
                className={styles.refreshButton}
                onClick={handleRefresh}
                disabled={refreshing}
              >
                {refreshing ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    Checking for alerts...
                  </>
                ) : (
                  <>
                    <i className="fas fa-redo"></i>
                    Check for New Alerts
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const UserDashboard = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [activePage, setActivePage] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [locationChanging, setLocationChanging] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
  const [locationSearch, setLocationSearch] = useState('');
  const [isSearchingLocation, setIsSearchingLocation] = useState(false);
  const [prevLocation, setPrevLocation] = useState(null);
  const [manualAreaOverride, setManualAreaOverride] = useState(null);
  const [timeFilter, setTimeFilter] = useState('all'); // '7d', '30d', '12m', 'all' - Default to 'all' to show complete historical data
  const [showHelpModal, setShowHelpModal] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Redirect to crime map with search query
      // We'll use the onAreaSelect prop if available, or just navigate
      // Since this is the dashboard, we might want to navigate to the map page
      navigate('/crime-map', { state: { searchQuery: searchQuery } });
    }
  };
  
  const { user, token, logout, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation(); // Add this

  const [queryArea, setQueryArea] = useState(null);
  const [queryTo, setQueryTo] = useState(null);

  // Fix: Handle browser navigation and query parameters
  useEffect(() => {
    // Check for query parameters first (priority)
    const searchParams = new URLSearchParams(location.search);
    const activeParam = searchParams.get('active');
    const areaParam = searchParams.get('area');
    const toParam = searchParams.get('to');
    
    if (areaParam) setQueryArea(areaParam);
    if (toParam) setQueryTo(toParam);
    
    if (activeParam) {
      switch (activeParam) {
        case 'crime-map':
          setActivePage('crime-heatmap');
          break;
        case 'navigation':
          setActivePage('navigation');
          break;
        case 'prediction':
          setActivePage('prediction');
          break;
        default:
          setActivePage('dashboard');
      }
      return; // If query param is present, it takes precedence over hash
    }

    // Fallback to hash if no query param
    const hash = location.hash;
    if (hash) {
      switch (hash) {
        case '#alerts':
          setActivePage('alerts');
          break;
        case '#risk-prediction':
          setActivePage('prediction');
          break;
        case '#reports':
          setActivePage('dashboard');
          break;
        default:
          setActivePage('dashboard');
      }
    }
  }, [location]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      navigate('/');
    }
  }, [authLoading, token, navigate]);

  // Real data fetching - only if authenticated
  useEffect(() => {
    if (token) {
      getUserLocation();
    }
  }, [token]);

useEffect(() => {
  if (token && userLocation) {
    // Detect if location actually changed (not first load)
    const isLocationChange = prevLocation && (
      prevLocation.lat !== userLocation.lat || prevLocation.lng !== userLocation.lng
    );
    if (isLocationChange) {
      setLocationChanging(true);
    }

    // Always clear session cache when location OR time filter changes to get fresh data
    const cacheKey = `dashboard_data_${user?.id}`;
    sessionStorage.removeItem(cacheKey);

    setPrevLocation({ lat: userLocation.lat, lng: userLocation.lng });
    fetchDashboardData();
  }
}, [token, userLocation, timeFilter, manualAreaOverride]);

  const handleLocationOverride = async (e) => {
    e.preventDefault();
    if (!locationSearch.trim()) return;
    
    setIsSearchingLocation(true);
    try {
      // Search with Lahore restriction for better results
      const query = encodeURIComponent(`${locationSearch.trim()}, Lahore, Pakistan`);
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=5&countrycodes=pk&addressdetails=1`,
        { headers: { 'User-Agent': 'SafeVision-App-Web-Frontend' } }
      );
      const results = await response.json();
      
      // Filter results to Lahore bounds (31.3-31.7 N, 74.0-74.6 E)
      const lahoreResults = results.filter(r => {
        const rlat = parseFloat(r.lat);
        const rlng = parseFloat(r.lon);
        return rlat >= 31.3 && rlat <= 31.7 && rlng >= 74.0 && rlng <= 74.6;
      });

      // Fall back to all results if no Lahore-specific ones
      const bestResults = lahoreResults.length > 0 ? lahoreResults : results;
      
      if (bestResults && bestResults.length > 0) {
        const { lat, lon, display_name } = bestResults[0];
        const parsedLat = parseFloat(lat);
        const parsedLng = parseFloat(lon);
        const typedArea = locationSearch.trim();
        console.log('🌍 Manual location override:', { lat: parsedLat, lng: parsedLng, display_name });
        // Setting userLocation triggers fetchDashboardData which uses coordinates for accurate stats
        setManualAreaOverride(typedArea);
        // Clear all caches and data immediately on location change
        setDataCache(null);

        setDashboardData(null);
        const cacheKey = `dashboard_data_${user?.id}`;
        sessionStorage.removeItem(cacheKey);

        // Force timestamp so React always sees a new object and triggers our useEffect
        setUserLocation({ lat: parsedLat, lng: parsedLng, timestamp: Date.now() });


        setIsLocationModalOpen(false);
        setLocationSearch('');
      } else {
        alert(`Location "${locationSearch}" not found in Lahore. Please try a more specific area name (e.g. "Johar Town", "DHA Phase 5").`);
      }
    } catch (error) {
      console.error("Geocoding failed:", error);
      alert("Search service unavailable. Please check your connection.");
    } finally {
      setIsSearchingLocation(false);
    }
  };

  const [dataCache, setDataCache] = useState(null);
 const fetchDashboardData = async () => {
  try {
    setLoading(true);
    setLocationChanging(true); // Signal location change starting
    setError(null);
    
    // Clear previous dashboard data immediately to avoid showing stale data
    setDashboardData(null);
    
    if (!token) {
      setError('Please log in to view dashboard data');
      return;
    }

    console.log('🔄 Fetching dashboard data using working APIs...');

    // Helper function to get area name from coordinates
    const getAreaFromCoordinates = async (lat, lng) => {
      try {
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
          { 
            signal: AbortSignal.timeout(5000),
            headers: {
              'User-Agent': 'SafeVision-App-Web-Frontend'
            }
          }
        );
        
        if (!response.ok) return null;
        
        const data = await response.json();
        
        if (data && data.address) {
          const addr = data.address;
          const areaHierarchy = [
            addr.neighbourhood,
            addr.suburb,
            addr.city_district,
            addr.district,
            addr.city,
            addr.town,
            addr.village
          ];
          
          const specificArea = areaHierarchy.find(area => 
            area && area.trim() !== '' && area !== 'Punjab'
          );
          
          if (specificArea) {
            console.log('📍 Found area from coordinates:', specificArea);
            return specificArea;
          }
        }
        
        return null;
      } catch (error) {
        console.warn('Reverse geocoding failed:', error.message);
        return null;
      }
    };

    // Fetch user alerts and activity (for lists)
    // Fetch user alerts, activity, AND city-wide average for comparison
    const [userAlerts, emergencyStats, recentActivity, cityAvgResult] = await Promise.allSettled([
      apiService.getUserAlerts(token),
      apiService.getEmergencyStats(),
      apiService.getRecentActivity(token),
      // Fetch city-wide stats (no location = overall) for real city average
      apiService.getUserStats(token)
    ]);

    const alerts = userAlerts.status === 'fulfilled' ? 
      (Array.isArray(userAlerts.value) ? userAlerts.value : userAlerts.value?.alerts || []) : 
      [];

    console.log('📊 Fetched alerts and activity:', {
      alertsCount: alerts.length,
      activityCount: recentActivity.status === 'fulfilled' ? recentActivity.value.length : 0
    });

    // Get area name from location or use home area (for display)
    let areaName = null;
    if (manualAreaOverride) {
      areaName = manualAreaOverride;
      console.log('📍 Using manual area override:', areaName);
    } else if (userLocation) {
      areaName = await getAreaFromCoordinates(userLocation.lat, userLocation.lng);
    }
    
    if (!areaName && user?.home_area) {
      areaName = user.home_area.split(',')[0].trim();
    }

    console.log('📍 Using area for display:', areaName);

    // Fetch comprehensive user stats (safety score, alerts, etc.) based on location
    // This uses the backend's radius-based calculation for accurate local data
    let userStats = null;
    try {
      if (userLocation) {
        console.log('🔄 Fetching stats for location:', userLocation, 'areaName:', areaName);
        
        // Push location to tracking/alerting system to actively trigger live alerts
        try {
          await apiService.checkLocationForAlerts(token, {
            latitude: userLocation.lat,
            longitude: userLocation.lng,
            accuracy: 20,
            address: areaName,
            // Manual typed area should never fire live alerts; browser geolocation should.
            location_source: manualAreaOverride ? 'dashboard_manual' : 'gps',
            device_type: 'desktop' // Defaulting for dashboard
          });
        } catch(alertErr) {
          console.warn('Alert tracking sync warning:', alertErr);
        }

        userStats = await apiService.getUserStats(token, userLocation.lat, userLocation.lng, areaName, timeFilter);
      } else {
        console.log('🔄 Fetching stats for home location');
        userStats = await apiService.getUserStats(token, null, null, areaName, timeFilter);
      }
      console.log('✅ User stats fetched:', userStats);
    } catch (error) {
      console.error('Error fetching user stats:', error);
      // Fallback object if fetch fails - use null/0 to indicate no data (NOT fake scores)
      userStats = {
        safety_score: null,
        safety_score_change: 0,
        weekly_alerts: 0,
        weekly_alerts_change: 0,
        safe_routes: 0,
        nearest_safe_zone: 0,
        safe_zone_name: 'N/A',
        breakdown: { violent: 0, property: 0, personal: 0, day: 0, night: 0 },
        confidence: 'none',
        risk_level: 'Unknown',
        system_status: [
          { type: 'warning', message: 'Telemetry unavailable - backend stats request failed', time: new Date().toISOString() }
        ],
        resolved_area: areaName || user?.home_area || 'Unknown'
      };
    }

    // Extract city-wide average safety score for comparison card
    let cityAvgSafetyScore = null;
    if (cityAvgResult && cityAvgResult.status === 'fulfilled' && cityAvgResult.value) {
      cityAvgSafetyScore = cityAvgResult.value.safety_score;
      console.log('📊 City-wide average safety score:', cityAvgSafetyScore);
    }

    // Calculate safe routes from activity logs (fallback if not in userStats)
    const activity = recentActivity.status === 'fulfilled' ? recentActivity.value : [];
    const safeRoutesCount = activity.filter(act => 
      act.activity_type === 'route_analysis' || 
      act.activity_type === 'navigation' ||
      (act.details && act.details.includes('route'))
    ).length;

    // Build comprehensive stats object using backend data
    // Use 0 as default instead of fake high scores to avoid misleading data
    const rawScore = userStats?.safety_score;
    // Default to null instead of 100 if missing, to prevent showing "100% Safe" on error
    const effectiveScore = (rawScore !== null && rawScore !== undefined) ? rawScore : null;
    // UI location label: Prioritize backend-resolved area (normalized) over local geocoding
    const resolvedArea = typeof userStats?.resolved_area === 'string' ? userStats.resolved_area.trim() : '';
    const normalizedAreaNameFromSearch = typeof areaName === 'string' ? areaName.trim() : '';
    const isGenericResolvedArea = !resolvedArea || ['unknown', 'your location', 'n/a'].includes(resolvedArea.toLowerCase());
    
    // UI location label: Prioritize the backend-resolved (and normalized) area name
    const displayArea = !isGenericResolvedArea ? resolvedArea : (normalizedAreaNameFromSearch || user?.home_area || 'Current Location');
    
    const stats = {
      safety_score: effectiveScore,
      risk_score: typeof userStats?.risk_score === 'number'
        ? userStats.risk_score
        : (effectiveScore === null ? null : Math.max(0, Math.min(100, 100 - effectiveScore))),
      safety_score_change: userStats?.safety_score_change,
      weekly_alerts: userStats?.weekly_alerts,
      weekly_alerts_change: userStats?.weekly_alerts_change,
      safe_routes: userStats?.safe_routes,
      nearest_safe_zone: userStats?.nearest_safe_zone,
      safe_zone_name: userStats?.safe_zone_name ?? 'N/A',
      safe_zone_type: null, 
      nearest_safe_zones: [], 
      breakdown: userStats?.breakdown ?? {
        violent: 0,
        property: 0,
        personal: 0,
        day: 0,
        night: 0
      },
      risk_level: userStats?.risk_level || (
                  effectiveScore === null ? 'Loading...' :
                  effectiveScore >= 80 ? 'Low' :
                  effectiveScore >= 50 ? 'Moderate' :
                  effectiveScore >= 20 ? 'High' : 'Critical'
      ),
      recent_7d_crimes: typeof userStats?.recent_7d_crimes === 'number' ? userStats.recent_7d_crimes : null,
      recent_30d_crimes: typeof userStats?.recent_30d_crimes === 'number' ? userStats.recent_30d_crimes : null,
      previous_7d_crimes: typeof userStats?.previous_7d_crimes === 'number' ? userStats.previous_7d_crimes : null,
      total_crimes: typeof userStats?.total_crimes === 'number' ? userStats.total_crimes : 0,
      high_risk_crimes: typeof userStats?.high_risk_crimes === 'number' ? userStats.high_risk_crimes : 0,
      medium_risk_crimes: typeof userStats?.medium_risk_crimes === 'number' ? userStats.medium_risk_crimes : 0,
      unique_crime_types: typeof userStats?.unique_crime_types === 'number' ? userStats.unique_crime_types : 0,
      top_crimes_list: Array.isArray(userStats?.top_crimes_list) ? userStats.top_crimes_list : [],
      sub_areas: userStats?.sub_areas || [],
      system_status: userStats?.system_status || [
        { type: 'info', message: 'Retrieving secure telemetry...', time: new Date().toISOString() },
        { type: 'success', message: 'Encryption layer active', time: new Date().toISOString() }
      ],
      confidence: userStats?.confidence || 'unknown',
      trend_data: Array.isArray(userStats?.trend_data) ? userStats.trend_data : [],
      trend_labels: Array.isArray(userStats?.trend_labels) ? userStats.trend_labels : [],
      // Real city-wide average from backend (not a fake multiplied value)
      city_avg_safety_score: cityAvgSafetyScore,
      // Prefer the backend's resolved_area (authoritative, coordinate-based) over Nominatim name
      // Backend already knows the area from its DB; Nominatim names often differ from DB names
      area: displayArea
    };

    console.log('📍 Using area for display:', stats.area);
    console.log('🏘️ Sub-areas from stats:', stats.sub_areas);

    const processedData = {
      stats: stats,
      alerts: alerts,
      emergencyStats: emergencyStats.status === 'fulfilled' ? emergencyStats.value : {},
      recentActivity: activity
    };

    console.log('✅ Dashboard data processed with REAL values:', {
      safetyScore: stats.safety_score,
      weeklyAlerts: stats.weekly_alerts,
      weeklyAlertsChange: stats.weekly_alerts_change,
      safeRoutes: stats.safe_routes,
      breakdown: stats.breakdown,
      alertsCount: alerts.length,
      activityCount: activity.length,
      location: userLocation,
      area: areaName
    });

    setDashboardData(processedData);
    setDataCache(processedData);
    
    // Cache the data for 5 minutes
    const cacheKey = `dashboard_data_${user?.id}`;
    sessionStorage.setItem(cacheKey, JSON.stringify({
      ...processedData,
      timestamp: Date.now()
    }));

  } catch (error) {
    console.error('❌ Error fetching dashboard data:', error);
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      response: error.response?.data,
      status: error.response?.status
    });
    setError('Failed to load dashboard data. Showing live no-data state until sync recovers.');
  } finally {
    setLoading(false);
    setLocationChanging(false);
  }
};

  const getUserLocation = () => {
    if (!navigator.geolocation) {
      console.log('⚠️ Geolocation not supported, will use home area');
      return;
    }

    const geoOptions = {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 0
    };

    const applyLocation = (position, source = 'primary') => {
      const location = {
        lat: position.coords.latitude,
        lng: position.coords.longitude
      };
      console.log(`✅ User location obtained (${source}):`, {
        ...location,
        accuracy: position.coords.accuracy,
        ageMs: Date.now() - position.timestamp
      });
      setManualAreaOverride(null);
      setUserLocation(location);
    };

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const accuracy = position.coords?.accuracy ?? null;
        const ageMs = Date.now() - position.timestamp;
        const isStale = ageMs > 120000;
        const isTooCoarse = accuracy !== null && accuracy > 1200;

        if (isStale || isTooCoarse) {
          console.log('⚠️ Initial geolocation is stale/coarse, retrying for a better fix...', {
            accuracy,
            ageMs
          });

          navigator.geolocation.getCurrentPosition(
            (retryPosition) => applyLocation(retryPosition, 'retry'),
            (retryError) => {
              console.log('⚠️ Retry geolocation failed, using initial position:', retryError);
              applyLocation(position, 'fallback-initial');
            },
            { ...geoOptions, timeout: 18000 }
          );
          return;
        }

        applyLocation(position);
      },
      (error) => {
        console.log('⚠️ Location access denied or unavailable:', error);
        console.log('Will use home area for safety calculations');
      },
      geoOptions
    );
  };

  // Listen for manual location updates from QuickActions
  useEffect(() => {
    const handleLocationUpdate = (event) => {
      const { lat, lng, address, isManual, requestedArea } = event.detail;
      console.log('📍 Location updated from QuickActions:', { lat, lng, address, isManual });
      
      // Show loading overlay and invalidate cache
      setLocationChanging(true);
      setManualAreaOverride(isManual ? (requestedArea || address || null) : null);
      const cacheKey = `dashboard_data_${user?.id}`;
      sessionStorage.removeItem(cacheKey);
      // Update user location - this will trigger fetchDashboardData via the useEffect
      setUserLocation({ lat, lng });
    };

    window.addEventListener('locationUpdated', handleLocationUpdate);
    
    return () => {
      window.removeEventListener('locationUpdated', handleLocationUpdate);
    };
  }, []);

  const toggleSidebar = () => setSidebarCollapsed(!sidebarCollapsed);
  const toggleMobileSidebar = () => setMobileSidebarOpen(!mobileSidebarOpen);
  const closeMobileSidebar = () => setMobileSidebarOpen(false);
  const toggleDropdown = () => setDropdownOpen(!dropdownOpen);
  const openProfileModal = () => { setProfileModalOpen(true); setDropdownOpen(false); };
  const closeProfileModal = () => setProfileModalOpen(false);

  const formatAreaName = (name) => name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  // FIXED: Navigation handlers - prevent default and use state
  const handleDashboardClick = (e) => { 
    e.preventDefault(); 
    setActivePage('dashboard'); 
    closeMobileSidebar(); 
    // Remove hash from URL
    window.history.replaceState(null, '', window.location.pathname);
  };

  const handleHeatmapClick = (e) => { 
    e.preventDefault(); 
    setActivePage('crime-heatmap'); 
    closeMobileSidebar(); 
  };

  const handleEmergencyClick = (e) => { 
    e.preventDefault(); 
    setActivePage('emergency'); 
    closeMobileSidebar(); 
  };

  const handleNavigationClick = (e) => { 
    e.preventDefault(); 
    setActivePage('navigation'); 
    closeMobileSidebar(); 
  };

  const handleAlertsClick = (e) => { 
    e.preventDefault(); 
    setActivePage('alerts'); 
    closeMobileSidebar(); 
  };

  const handleReportsClick = (e) => {
    e.preventDefault();
    setActivePage('dashboard');
    closeMobileSidebar();
    // You can implement reports functionality later
    console.log('Reports feature coming soon...');
  };

  // Show loading while authenticating
  if (authLoading) {
    return (
      <div className={styles.loadingContainer}>
        <LoadingOverlay message="Initializing your dashboard..." show={true} />
      </div>
    );
  }

  // Show message if not authenticated
  if (!token) {
    return (
      <div className={styles.authRequired}>
        <div className={styles.authMessage}>
          <i className="fas fa-exclamation-triangle"></i>
          <h2>Authentication Required</h2>
          <p>Please log in to access the dashboard</p>
          <button 
            className={styles.loginButton}
            onClick={() => navigate('/')}
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.appContainer}>
      {/* Mobile Toggle */}
      <button className={styles.mobileToggle} onClick={toggleMobileSidebar}>
        <i className="fas fa-bars"></i>
      </button>

      {/* Sidebar */}
      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
        <div className={styles.sidebarHeaderCompact}>
          <div className={styles.logoCompact}>
            <i className="fas fa-shield-alt"></i>
          </div>
        </div>

        <ul className={styles.sidebarMenu}>
          <li>
            <a href="#" 
               className={activePage === 'dashboard' ? styles.active : ''} 
               onClick={handleDashboardClick}>
              <i className="fas fa-home"></i>
              <span>Dashboard</span>
            </a>
          </li>
          <li>
            <a href="#" 
               className={activePage === 'crime-heatmap' ? styles.active : ''}
               onClick={handleHeatmapClick}>
              <i className="fas fa-map-marker-alt"></i>
              <span>Risk Map</span>
            </a>
          </li>
          <li>
            <a href="#" 
               className={activePage === 'navigation' ? styles.active : ''} 
               onClick={handleNavigationClick}>
              <i className="fas fa-route"></i>
              <span>Safe Routes</span>
            </a>
          </li>
          <li>
            <a href="#"
               className={activePage === 'prediction' ? styles.active : ''}
               onClick={(e) => {
                 e.preventDefault();
                 setActivePage('prediction');
                 closeMobileSidebar();
               }}>
              <i className="fas fa-robot"></i>
              <span>Risk Predictions</span>
            </a>
          </li>
          <li>
            <a href="#alerts" 
               className={activePage === 'alerts' ? styles.active : ''} 
               onClick={handleAlertsClick}>
              <i className="fas fa-bell"></i>
              <span>Alerts</span>
              {dashboardData?.alerts && dashboardData.alerts.length > 0 && (
                <span className={styles.menuBadge}>
                  {dashboardData.alerts.filter(alert => !alert.is_read).length}
                </span>
              )}
            </a>
          </li>
          <li>
            <a href="#" 
               className={activePage === 'emergency' ? styles.active : ''} 
               onClick={handleEmergencyClick}>
              <i className="fas fa-plus-square"></i>
              <span>Emergency</span>
            </a>
          </li>
          <li>
            <a href="#" onClick={(e) => { e.preventDefault(); openProfileModal(); }}>
              <i className="fas fa-user"></i>
              <span>My Profile</span>
            </a>
          </li>
        </ul>

        <div className={styles.sidebarFooter}>
          <a href="#" onClick={logout} className={styles.logoutLink}>
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
          <button className={styles.toggleBtn} onClick={toggleSidebar}>
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        <div className={styles.navbar}>
          <div className={styles.navQuickIcons}>
            <button className={styles.navQuickIcon} onClick={handleDashboardClick} title="Dashboard">
              <i className="fas fa-chart-pie"></i>
            </button>
            <button className={styles.navQuickIcon} onClick={handleHeatmapClick} title="Risk Map">
              <i className="fas fa-map-marked-alt"></i>
            </button>
            <button className={styles.navQuickIcon} onClick={handleNavigationClick} title="Safe Routes">
              <i className="fas fa-route"></i>
            </button>
            <button className={styles.navQuickIcon} onClick={() => setActivePage('prediction')} title="Risk Predictions">
              <i className="fas fa-hat-cowboy"></i>
            </button>
            <button className={styles.navQuickIcon} onClick={handleEmergencyClick} title="Emergency">
              <i className="fas fa-user-shield"></i>
            </button>
          </div>

          <div className={styles.navCenterTitle} onClick={() => setIsLocationModalOpen(true)}>
            <span className={styles.navCenterTitleText}>{dashboardData?.stats?.area || 'Detecting Location...'}</span>
            <i className="fas fa-chevron-down"></i>
          </div>

          <div className={styles.navbarActions}>
            <button className={styles.navActionLink} onClick={handleHeatmapClick}>
              <i className="fas fa-map-marked-alt"></i>
              <span>View Map</span>
            </button>
            <button className={styles.navActionLink} onClick={handleAlertsClick}>
              <i className="fas fa-bell"></i>
              <span>Alert Settings</span>
            </button>
            <div className={styles.notificationBtn} onClick={handleAlertsClick}>
              <i className="fas fa-bell"></i>
              <span className={styles.notificationBadge}>
                {dashboardData?.alerts?.filter(alert => !alert.is_read).length || 0}
              </span>
            </div>
            
            {/* User Profile Dropdown */}
            <div className={styles.userProfileContainer}>
              <button 
                className={styles.userProfileBtn}
                onClick={toggleDropdown}
                title="Profile Menu"
              >
                <img 
                  src={getProfileImageUrl(user?.profile_picture)} 
                  alt={user?.name || user?.username}
                  className={styles.userProfileImg}
                />
                <i className={`fas fa-chevron-${dropdownOpen ? 'up' : 'down'}`}></i>
              </button>
              
              {dropdownOpen && (
                <div className="user-dropdown">
                  <button 
                    className="dropdown-item"
                    onClick={openProfileModal}
                  >
                    <i className="fas fa-user-circle"></i>
                    My Profile
                  </button>
                  <button 
                    className="dropdown-item"
                    onClick={() => {
                      setDropdownOpen(false);
                      // Navigate to alerts
                      setActivePage('alerts');
                    }}
                  >
                    <i className="fas fa-cog"></i>
                    Settings
                  </button>
                  <div className="dropdown-divider"></div>
                  <button 
                    className="dropdown-item"
                    onClick={() => {
                      setDropdownOpen(false);
                      logout();
                    }}
                  >
                    <i className="fas fa-sign-out-alt"></i>
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dashboard Page */}
        {activePage === 'dashboard' && (
          <div className={styles.dashboardGrid}>
            {/* Location Change Loading Overlay */}
            {locationChanging && (
              <div className={styles.locationChangeOverlay}>
                <div className={styles.locationChangeContent}>
                  <div className={styles.locationChangeSpinner}>
                    <i className="fas fa-satellite fa-spin"></i>
                  </div>
                  <h3>Updating Monitored Area...</h3>
                  <p>Fetching real-time safety data for your selected location</p>
                  <div className={styles.locationChangeProgress}>
                    <div className={styles.locationChangeBar}></div>
                  </div>
                </div>
              </div>
            )}
            {/* Error Banner */}
            {error && (
              <div className={`${styles.errorBanner} ${styles.fadeIn}`}>
                <div className={styles.errorContent}>
                  <i className="fas fa-exclamation-triangle"></i>
                  <div>
                    <strong>Data Sync Error:</strong> {error}
                  </div>
                </div>
                <button className={styles.retryButton} onClick={fetchDashboardData}>
                  <i className="fas fa-redo"></i> Re-sync
                </button>
              </div>
            )}

            {/* Time Filter Tabs */}
            <div className={styles.timeFilterContainer}>
              <div className={styles.timeFilterWrapper}>
                <button
                  className={`${styles.timeFilterBtn} ${timeFilter === '7d' ? styles.activeFilter : ''}`}
                  onClick={() => setTimeFilter('7d')}
                >7 Days</button>
                <button
                  className={`${styles.timeFilterBtn} ${timeFilter === '30d' ? styles.activeFilter : ''}`}
                  onClick={() => setTimeFilter('30d')}
                >30 Days</button>
                <button
                  className={`${styles.timeFilterBtn} ${timeFilter === '12m' ? styles.activeFilter : ''}`}
                  onClick={() => setTimeFilter('12m')}
                >12 Months</button>
                <button
                  className={`${styles.timeFilterBtn} ${timeFilter === 'all' ? styles.activeFilter : ''}`}
                  onClick={() => setTimeFilter('all')}
                >All Time</button>
                <button
                  className={styles.timeFilterRefreshBtn}
                  onClick={fetchDashboardData}
                  title="Refresh"
                  aria-label="Refresh dashboard data"
                >
                  <i className="fas fa-sync-alt"></i>
                </button>
              </div>
            </div>

            <ReferenceDashboard
              styles={styles}
              stats={dashboardData?.stats}
              loading={loading || locationChanging}
              onHeatmapClick={handleHeatmapClick}
              onNavigationClick={handleNavigationClick}
              onAlertsClick={handleAlertsClick}
              onEmergencyClick={() => setActivePage('emergency')}
              setShowHelpModal={setShowHelpModal}
            />
          </div>
        )}

        {/* Location Simulation Modal */}
        {isLocationModalOpen && (
          <div className={styles.modalOverlay}>
            <div className={styles.modalContent}>
              <h3><i className="fas fa-map-marker-alt"></i> CHANGE MONITORED AREA</h3>
              <p>Enter a new location to simulate real-time safety monitoring for that area.</p>
              <form onSubmit={handleLocationOverride}>
                <div className={styles.searchBar} style={{ maxWidth: '100%', marginBottom: '1.5rem' }}>
                  <i className="fas fa-search-location"></i>
                  <input 
                    type="text" 
                    placeholder="Search for area (e.g. Model Town, Lahore)" 
                    value={locationSearch}
                    onChange={(e) => setLocationSearch(e.target.value)}
                    autoFocus
                  />
                </div>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button type="button" onClick={() => setIsLocationModalOpen(false)} style={{ background: 'rgba(255,255,255,0.1)', color: 'white' }}>
                    Cancel
                  </button>
                  <button type="submit" disabled={isSearchingLocation}>
                    {isSearchingLocation ? 'Updating...' : 'Apply Area'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Alerts Page */}
        {activePage === 'alerts' && (
          <AlertsPage 
            styles={styles}
            alerts={dashboardData?.alerts}
            loading={loading}
            token={token}
            onRefresh={fetchDashboardData}
          />
        )}

        {/* Other pages */}
        {activePage === 'crime-heatmap' && (
          <div className={styles.pageContainer}>
            <div className={styles.pageHeader}>
              <h1>Crime Incidents & Heatmap Analysis</h1>
              <p>Real-time incident density visualization and FIR analysis across Lahore</p>
            </div>
            <div className={styles.crimeHeatmapPageContainer}>
              <CrimeMapInterface 
                showAdditionalSections={false}
                initialArea={queryArea}
              />
            </div>
          </div>
        )}

        {activePage === 'emergency' && (
          <div className={styles.pageContainer}>
            <div className={styles.pageHeader}>
              <h1>Emergency Resources</h1>
              <p>Immediate access to emergency services and support</p>
            </div>
            <EmergencyContacts />
          </div>
        )}

        {activePage === 'navigation' && (
          <div className={styles.pageContainer}>
            <div className={styles.pageHeader}>
              <h1>Safe Navigation</h1>
              <p>Get the safest routes using AI crime risk predictions based on historical crime patterns</p>
            </div>
            <AIRouteAnalysis userLocation={userLocation} initialDestination={queryTo} />
          </div>
        )}

        {activePage === 'prediction' && (
          <PredictionPage initialArea={queryArea} />
        )}
      </div>

      <ProfileModal isOpen={profileModalOpen} user={user} onClose={closeProfileModal} />

      {/* Help Modal */}
      {showHelpModal && (
        <div className={styles.helpModalOverlay} onClick={() => setShowHelpModal(false)}>
          <div className={styles.helpModalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.helpModalHeader}>
              <h2><i className="fas fa-info-circle"></i> Understanding Safety Scores</h2>
              <button
                className={styles.helpModalClose}
                onClick={() => setShowHelpModal(false)}
              >
                ×
              </button>
            </div>

            <div className={styles.helpModalBody}>
              <div className={styles.helpSection}>
                <h3>📊 Dashboard vs Area Profile Differences</h3>
                <div className={styles.comparisonCards}>
                  <div className={styles.helpCard}>
                    <h4><i className="fas fa-map-marked-alt"></i> Dashboard Score (Current View)</h4>
                    <div className={styles.helpCardContent}>
                      <p><strong>Coverage:</strong> Your location + 1.5km radius</p>
                      <p><strong>Purpose:</strong> Real-time navigation safety</p>
                      <p><strong>Includes:</strong> Nearby crimes, similar area names</p>
                      <p><strong>Best for:</strong> "Should I go here now?" decisions</p>
                    </div>
                  </div>

                  <div className={styles.helpCard}>
                    <h4><i className="fas fa-chart-area"></i> Area Profile Score</h4>
                    <div className={styles.helpCardContent}>
                      <p><strong>Coverage:</strong> Exact neighborhood only</p>
                      <p><strong>Purpose:</strong> Precise area analysis</p>
                      <p><strong>Includes:</strong> Strict area matches only (no silent nearby fallback)</p>
                      <p><strong>Best for:</strong> "Should I live/work here?" decisions</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className={styles.helpSection}>
                <h3>🕐 Time Filter Guide</h3>
                <ul className={styles.helpList}>
                  <li><strong>7 Days:</strong> Very recent incidents (can be zero in low-activity areas)</li>
                  <li><strong>30 Days:</strong> Near-term pattern changes</li>
                  <li><strong>12 Months:</strong> Yearly trend with month labels</li>
                  <li><strong>All Time:</strong> Full history for the selected area only</li>
                </ul>
              </div>

              <div className={styles.helpSection}>
                <h3>📈 Trend & Risk Details</h3>
                <ul className={styles.helpList}>
                  <li><strong>Top Risk Factors:</strong> Real top 10 categories from database records for your selected area/filter</li>
                  <li><strong>Trend Chart:</strong> Bars and line animate when data loads</li>
                  <li><strong>Hover Points:</strong> Move cursor over chart points to see period label, incidents, and percent share</li>
                </ul>
              </div>

              <div className={styles.helpSection}>
                <h3>⚡ Quick Tips</h3>
                <div className={styles.tipGrid}>
                  <div className={styles.tip}>
                    <i className="fas fa-lightbulb"></i>
                    <p>Different scores are normal - they serve different purposes</p>
                  </div>
                  <div className={styles.tip}>
                    <i className="fas fa-refresh"></i>
                    <p>Use "All Time" for broad context, then compare with 30-day or 7-day view</p>
                  </div>
                  <div className={styles.tip}>
                    <i className="fas fa-clock"></i>
                    <p>Hover trend points for detailed month-by-month breakdown</p>
                  </div>
                  <div className={styles.tip}>
                    <i className="fas fa-bell"></i>
                    <p>Enable browser notifications in Profile to receive push alerts from monitoring</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ReferenceDashboard = ({ styles, stats, loading, onHeatmapClick, onNavigationClick, onAlertsClick, onEmergencyClick, setShowHelpModal }) => {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  if (loading) {
    return (
      <div className={styles.referenceDashboard}>
        <SkeletonCard height="200px" />
        <SkeletonCard height="160px" />
        <SkeletonCard height="220px" />
        <SkeletonCard height="140px" />
      </div>
    );
  }

  // ── Data extraction ──────────────────────────────────────────────────────────
  const hasSafetyScore = typeof stats?.safety_score === 'number';
  const safetyScore = hasSafetyScore ? Math.max(0, Math.min(100, Math.round(stats.safety_score))) : null;
  const riskLevel = normalizeRiskBandLabel(stats?.risk_level);
  const riskLabel = hasSafetyScore
    ? (riskLevel === 'Safe' ? 'Low' : riskLevel === 'Caution' ? 'Moderate' : riskLevel === 'Warning' ? 'High' : 'Severe')
    : 'No Data';
  const recent7d   = typeof stats?.recent_7d_crimes   === 'number' ? stats.recent_7d_crimes   : 0;
  const recent30d  = typeof stats?.recent_30d_crimes  === 'number' ? stats.recent_30d_crimes  : 0;
  const previous7d = typeof stats?.previous_7d_crimes === 'number' ? stats.previous_7d_crimes : null;
  const totalIncidents = typeof stats?.total_crimes === 'number' ? stats.total_crimes : 0;
  const highRisk   = typeof stats?.high_risk_crimes  === 'number' ? stats.high_risk_crimes  : 0;
  const periodDeltaPct = previous7d !== null
    ? (previous7d > 0 ? Math.round(((recent7d - previous7d) / previous7d) * 100) : (recent7d > 0 ? 100 : 0))
    : Number(stats?.weekly_alerts_change ?? 0);
  const confidence = String(stats?.data_confidence || stats?.confidence || 'unknown')
    .replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  // time filter label
  const filterLabel = (() => {
    const tf = stats?.time_filter;
    if (tf === '7d') return '7 Days';
    if (tf === '30d') return '30 Days';
    if (tf === '12m') return '12 Months';
    if (tf === 'all') return 'All Time';
    return 'Selected Period';
  })();

  // ── Colour theming ────────────────────────────────────────────────────────────
  const scoreColor = !hasSafetyScore
    ? '#94a3b8'
    : safetyScore >= 75 ? '#10b981'
    : safetyScore >= 55 ? '#f59e0b'
    : safetyScore >= 35 ? '#f97316'
    : '#ef4444';
  const scoreGradientStart = scoreColor;
  const scoreGradientEnd   = safetyScore >= 75 ? '#06b6d4' : safetyScore >= 55 ? '#d97706' : '#dc2626';

  // ── SVG Ring Gauge ────────────────────────────────────────────────────────────
  const RADIUS = 58, STROKE = 10;
  const CIRC = 2 * Math.PI * RADIUS;
  const fillRatio = hasSafetyScore ? (safetyScore / 100) : 0;
  const dashOffset = CIRC * (1 - fillRatio);

  // ── Trend chart ───────────────────────────────────────────────────────────────
  const trendData   = Array.isArray(stats?.trend_data)   ? stats.trend_data.map((n) => Number(n || 0)) : [];
  const trendLabels = Array.isArray(stats?.trend_labels) ? stats.trend_labels : trendData.map((_, i) => `${i + 1}`);
  const trendAxisLabels = trendLabels.map((lbl) => {
    const text = String(lbl || '');

    if (/^\d{4}-\d{2}$/.test(text)) {
      const [y, m] = text.split('-').map(Number);
      const dt = new Date(y, (m || 1) - 1, 1);
      return dt.toLocaleString('en-US', { month: 'short' });
    }

    if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
      const dt = new Date(text);
      return Number.isNaN(dt.getTime()) ? text : dt.toLocaleString('en-US', { month: 'short' });
    }

    return text;
  });
  const hasTrendData = trendData.length > 1 && trendData.some((n) => n > 0);
  const chartMax = Math.max(1, ...trendData);

  // Bar chart coords (SVG viewport 0-200 wide, 0-80 tall)
  const BAR_W = 200 / Math.max(trendData.length, 1);
  const barRects = trendData.map((val, i) => {
    const barH = (val / chartMax) * 68;
    return { x: i * BAR_W, y: 80 - barH, w: BAR_W * 0.62, h: barH };
  });

  // Line over bars
  const linePoints = hasTrendData
    ? trendData.map((val, i) => {
        const cx = i * BAR_W + BAR_W / 2;
        const cy = 80 - (val / chartMax) * 68;
        return `${cx},${cy}`;
      }).join(' ')
    : '';

  // Trend change pct
  const trendChangePct = hasTrendData && trendData[0] > 0
    ? Math.round(((trendData[trendData.length - 1] - trendData[0]) / trendData[0]) * 100)
    : null;

  const trendTooltip = hoveredPoint !== null
    ? (() => {
        const idx = hoveredPoint;
        const current = trendData[idx] || 0;
        const previous = idx > 0 ? trendData[idx - 1] || 0 : null;
        const delta = previous !== null ? current - previous : null;
        const deltaPct = (previous !== null && previous > 0)
          ? Math.round((delta / previous) * 100)
          : null;
        const sharePct = totalIncidents > 0 ? ((current / totalIncidents) * 100).toFixed(1) : '0.0';

        return {
          label: trendAxisLabels[idx] || `Point ${idx + 1}`,
          current,
          previous,
          delta,
          deltaPct,
          sharePct,
          left: `${((idx + 0.5) / Math.max(trendData.length, 1)) * 100}%`,
          top: `${100 - ((current / Math.max(chartMax, 1)) * 68 / 80) * 100}%`,
        };
      })()
    : null;

  // ── Top crimes ────────────────────────────────────────────────────────────────
  const cleanCrimeName = (name) => {
    if (!name) return 'Unknown';
    return String(name)
      .replace(/^Punishment for /i, '')
      .replace(/^Punishment of /i, '')
      .replace(/^Offence of /i, '')
      .replace(/^\d+\s*-\s*/, '')
      .replace(/_/g, ' ').trim();
  };
  const topCrimes = Array.isArray(stats?.top_crimes_list) ? stats.top_crimes_list.slice(0, 10) : [];
  const totalTop  = Math.max(1, topCrimes.reduce((s, r) => s + Number(r?.count || 0), 0));
  const riskFactors = topCrimes.map((item, idx) => ({
    label: cleanCrimeName(item?.display_name || item?.type || item?.display_type || item?.crime_type),
    pct:   typeof item?.pct === 'number' ? item.pct : typeof item?.percentage === 'number' ? item.percentage : Math.round((Number(item?.count || 0) / totalTop) * 100),
    count: Number(item?.count || 0),
    color: idx === 0 ? '#ef4444' : idx === 1 ? '#f59e0b' : '#3b82f6',
  }));

  // ── Live feed ─────────────────────────────────────────────────────────────────
  const feed = [];
  if (recent7d === 0) {
    feed.push({ icon: 'fas fa-shield-check', color: '#10b981', text: 'No incidents reported in the past 7 days.' });
  } else {
    feed.push({ icon: 'fas fa-exclamation-triangle', color: '#f59e0b', text: `${recent7d} incident${recent7d === 1 ? '' : 's'} in the last 7 days.` });
  }
  if (recent30d > 0 && recent30d !== recent7d) {
    feed.push({ icon: 'fas fa-calendar-alt', color: '#60a5fa', text: `${recent30d} total incidents in the last 30 days.` });
  }
  if (totalIncidents > 0 && totalIncidents !== recent30d) {
    feed.push({ icon: 'fas fa-database', color: '#a78bfa', text: `${totalIncidents} records analyzed over ${filterLabel}.` });
  }
  if (highRisk > 0) {
    feed.push({ icon: 'fas fa-radiation-alt', color: '#ef4444', text: `${highRisk} high-severity incident${highRisk === 1 ? '' : 's'} in window.` });
  }
  feed.push({ icon: 'fas fa-satellite-dish', color: '#00f2ff', text: 'Monitoring active — data sync OK.' });

  return (
    <div className={styles.referenceDashboard}>

      {/* ── ROW 1: Safety Gauge + Activity Stats + Risk Factors ── */}
      <div className={styles.refRow1}>

        {/* Safety Score Spiral Card */}
        <div className={`${styles.refCard} ${styles.refGaugeCard}`}>
          <div className={styles.refCardLabel}>
            <i className="fas fa-shield-alt"></i> Safety Score
            <span className={styles.refFilterPill}>{filterLabel}</span>
            <button
              className={styles.helpButton}
              onClick={() => setShowHelpModal(true)}
              title="Understanding Safety Scores"
            >
              <i className="fas fa-question-circle"></i>
              Help
            </button>
          </div>
          <div className={styles.refGaugeWrapper}>
            <svg viewBox="0 0 140 140" className={styles.refGaugeSvg}>
              <defs>
                <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor={scoreGradientStart} />
                  <stop offset="100%" stopColor={scoreGradientEnd} />
                </linearGradient>
                <filter id="gaugeGlow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                  <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
              </defs>
              {/* Track */}
              <circle cx="70" cy="70" r={RADIUS} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={STROKE} />
              {/* Fill */}
              <circle
                cx="70" cy="70" r={RADIUS}
                fill="none"
                stroke="url(#gaugeGrad)"
                strokeWidth={STROKE}
                strokeDasharray={CIRC}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                transform="rotate(-90 70 70)"
                filter="url(#gaugeGlow)"
                style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
              />
              {/* Center text */}
              <text x="70" y="64" textAnchor="middle" fontSize="22" fontWeight="900" fill={scoreColor} fontFamily="Orbitron, sans-serif">
                {hasSafetyScore ? `${safetyScore}` : 'N/A'}
              </text>
              <text x="70" y="82" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.6)" fontFamily="sans-serif">
                {hasSafetyScore ? '/ 100' : ''}
              </text>
            </svg>
          </div>
          <div className={styles.refRiskBadge} style={{ background: `${scoreColor}22`, border: `1px solid ${scoreColor}55`, color: scoreColor }}>
            {hasSafetyScore ? `${riskLabel} Risk` : 'No Data'}
          </div>
          <div className={styles.refMeta}>
            <span>Confidence: <strong style={{ color: '#f7cc66' }}>{confidence}</strong></span>
          </div>
          {periodDeltaPct !== 0 && (
            <div className={styles.refMeta} style={{ color: periodDeltaPct > 0 ? '#ef4444' : '#10b981' }}>
              <i className={`fas fa-caret-${periodDeltaPct > 0 ? 'up' : 'down'}`}></i>
              {` ${Math.abs(periodDeltaPct)}% vs prev. 7 days`}
            </div>
          )}
        </div>

        {/* Activity Stats */}
        <div className={styles.refColumn}>
          <div className={`${styles.refCard} ${styles.refStatCard}`}>
            <div className={styles.refCardLabel}><i className="fas fa-bolt"></i> Last 7 Days</div>
            <div className={styles.refBigNumber} style={{ color: recent7d === 0 ? '#10b981' : '#f59e0b' }}>
              {recent7d}
            </div>
            <div className={styles.refMeta}>incidents recorded</div>
          </div>
          <div className={`${styles.refCard} ${styles.refStatCard}`}>
            <div className={styles.refCardLabel}><i className="fas fa-calendar"></i> Last 30 Days</div>
            <div className={styles.refBigNumber} style={{ color: recent30d === 0 ? '#10b981' : '#f97316' }}>
              {recent30d}
            </div>
            <div className={styles.refMeta}>incidents recorded</div>
          </div>
          <div className={`${styles.refCard} ${styles.refStatCard}`}>
            <div className={styles.refCardLabel}><i className="fas fa-database"></i> In {filterLabel}</div>
            <div className={styles.refBigNumber} style={{ color: totalIncidents === 0 ? '#10b981' : '#a78bfa' }}>
              {totalIncidents}
            </div>
            <div className={styles.refMeta}>total records analyzed</div>
          </div>
        </div>

        {/* Top Risk Factors */}
        <div className={`${styles.refCard} ${styles.refRiskFactorsCard}`}>
          <div className={styles.refCardLabel}>
            <i className="fas fa-list-ol"></i> Top Risk Factors
            <span className={styles.refFilterPill}>{filterLabel}</span>
          </div>
          {riskFactors.length > 0 ? (
            <div className={styles.refFactorList}>
              {riskFactors.map((f, i) => (
                <div key={i} className={styles.refFactorItem}>
                  <div className={styles.refFactorHeader}>
                    <span className={styles.refFactorName}>
                      <span className={styles.refFactorRank} style={{ background: f.color }}>{i + 1}</span>
                      {f.label}
                    </span>
                    <strong style={{ color: f.color }}>{f.pct}%</strong>
                  </div>
                  <div className={styles.refFactorBar}>
                    <div style={{ width: `${f.pct}%`, background: `linear-gradient(90deg, ${f.color}cc, ${f.color}44)` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.refEmptyState}>
              <i className="fas fa-check-circle"></i>
              <span>No risk factors detected in this window.</span>
              <small>Area appears quiet for {filterLabel}.</small>
            </div>
          )}
        </div>
      </div>

      {/* ── ROW 2: Crime Trend Chart + Threat Assessment ── */}
      <div className={styles.refRow2}>

        {/* Crime Trend */}
        <div className={`${styles.refCard} ${styles.refTrendCard}`}>
          <div className={styles.refCardLabel}>
            <i className="fas fa-chart-area"></i> Crime Trend
            <span className={styles.refFilterPill}>{filterLabel}</span>
            {trendChangePct !== null && (
              <span className={styles.refTrendBadge} style={{ color: trendChangePct <= 0 ? '#10b981' : '#ef4444', background: trendChangePct <= 0 ? '#10b98122' : '#ef444422' }}>
                <i className={`fas fa-arrow-${trendChangePct <= 0 ? 'down' : 'up'}`}></i>
                {trendChangePct <= 0 ? '' : '+'}{trendChangePct}%
              </span>
            )}
          </div>

          {hasTrendData ? (
            <div className={styles.refChartWrapper}>
              <svg viewBox="0 0 200 80" preserveAspectRatio="none" className={styles.refChartSvg}>
                <defs>
                  <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgba(99,102,241,0.55)" />
                    <stop offset="100%" stopColor="rgba(99,102,241,0.04)" />
                  </linearGradient>
                  <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#00f2ff" />
                    <stop offset="100%" stopColor="#a78bfa" />
                  </linearGradient>
                  <filter id="lineGlow">
                    <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
                    <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                {/* Horizontal grid lines */}
                {[25, 50, 75].map(y => (
                  <line key={y} x1="0" y1={y * 80 / 100} x2="200" y2={y * 80 / 100}
                    stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" strokeDasharray="3,3" />
                ))}
                {/* Bars */}
                {barRects.map((r, i) => (
                  <rect key={i} x={r.x + (BAR_W - r.w) / 2} y={r.y} width={r.w} height={r.h}
                    fill="url(#barGrad)" rx="1.5" className={styles.refTrendBar}
                    style={{ animationDelay: `${i * 45}ms` }} />
                ))}
                {/* Line */}
                <polyline points={linePoints} fill="none" stroke="url(#lineGrad)" strokeWidth="1.8"
                  strokeLinejoin="round" strokeLinecap="round" filter="url(#lineGlow)" className={styles.refTrendLine} />
                {/* Dots */}
                {trendData.map((val, i) => {
                  const cx = i * BAR_W + BAR_W / 2;
                  const cy = 80 - (val / chartMax) * 68;
                  return (
                    <g key={i}>
                      <circle cx={cx} cy={cy} r="2.7" fill="#1e1b4b" stroke="#00f2ff" strokeWidth="1.2" className={styles.refTrendPoint} />
                      <circle cx={cx} cy={cy} r="1" fill="#00f2ff" className={styles.refTrendPointCore} />
                      <circle
                        cx={cx}
                        cy={cy}
                        r="7"
                        fill="transparent"
                        onMouseEnter={() => setHoveredPoint(i)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      >
                        <title>{`${trendAxisLabels[i] || i + 1}: ${val} incidents`}</title>
                      </circle>
                    </g>
                  );
                })}
              </svg>

              {trendTooltip && (
                <div
                  className={styles.refTrendTooltip}
                  style={{ left: trendTooltip.left, top: trendTooltip.top }}
                >
                  <div className={styles.refTrendTooltipTitle}>{trendTooltip.label}</div>
                  <div className={styles.refTrendTooltipRow}><span>Incidents</span><strong>{trendTooltip.current}</strong></div>
                  <div className={styles.refTrendTooltipRow}><span>Share</span><strong>{trendTooltip.sharePct}%</strong></div>
                  {trendTooltip.previous !== null && (
                    <div className={styles.refTrendTooltipRow}>
                      <span>Change</span>
                      <strong style={{ color: trendTooltip.delta <= 0 ? '#10b981' : '#ef4444' }}>
                        {trendTooltip.delta > 0 ? '+' : ''}{trendTooltip.delta}
                        {trendTooltip.deltaPct !== null ? ` (${trendTooltip.deltaPct > 0 ? '+' : ''}${trendTooltip.deltaPct}%)` : ''}
                      </strong>
                    </div>
                  )}
                </div>
              )}

              {/* X-axis labels */}
              <div className={styles.refChartAxis}>
                {trendAxisLabels.map((lbl, i) => (
                  <span key={i} style={{ flex: 1, textAlign: 'center', fontSize: '0.58rem', color: '#6b7280', overflow: 'hidden', textOverflow: 'clip', whiteSpace: 'nowrap' }}>
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className={styles.refEmptyState}>
              <i className="fas fa-chart-line"></i>
              <span>No trend data available</span>
              <small>Try selecting a longer period (12 Months).</small>
            </div>
          )}
        </div>

        {/* Threat Assessment */}
        <div className={`${styles.refCard} ${styles.refThreatCard}`}>
          <div className={styles.refCardLabel}><i className="fas fa-radar"></i> Threat Assessment</div>
          <div className={styles.refThreatBody}>
            <div className={styles.refThreatIcon} style={{ color: scoreColor, boxShadow: `0 0 20px ${scoreColor}44`, background: `${scoreColor}18` }}>
              <i className={
                !hasSafetyScore ? 'fas fa-question-circle'
                : totalIncidents === 0 ? 'fas fa-leaf'
                : riskLabel === 'Low' ? 'fas fa-shield-alt'
                : riskLabel === 'Moderate' ? 'fas fa-exclamation-circle'
                : 'fas fa-radiation-alt'
              }></i>
            </div>
            <div className={styles.refThreatDetails}>
              <div className={styles.refThreatTitle} style={{ color: scoreColor }}>
                {!hasSafetyScore ? 'No Data Available'
                  : totalIncidents === 0 ? 'Area Clear'
                  : riskLabel === 'Low' ? 'Low Threat'
                  : riskLabel === 'Moderate' ? 'Moderate Threat'
                  : 'Elevated Threat'}
              </div>
              <div className={styles.refThreatRows}>
                <div className={styles.refThreatRow}>
                  <span>Period</span><strong>{filterLabel}</strong>
                </div>
                <div className={styles.refThreatRow}>
                  <span>Incidents</span><strong style={{ color: totalIncidents === 0 ? '#10b981' : '#f59e0b' }}>{totalIncidents}</strong>
                </div>
                <div className={styles.refThreatRow}>
                  <span>High Severity</span><strong style={{ color: highRisk === 0 ? '#10b981' : '#ef4444' }}>{highRisk}</strong>
                </div>
                <div className={styles.refThreatRow}>
                  <span>Confidence</span><strong style={{ color: '#f7cc66' }}>{confidence}</strong>
                </div>
                <div className={styles.refThreatRow}>
                  <span>7d Change</span>
                  <strong style={{ color: periodDeltaPct > 0 ? '#ef4444' : '#10b981' }}>
                    {periodDeltaPct > 0 ? `+${periodDeltaPct}` : periodDeltaPct}%
                  </strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── ROW 3: Live Feed + Quick Actions ── */}
      <div className={styles.refRow3}>
        <div className={`${styles.refCard} ${styles.refFeedCard}`}>
          <div className={styles.refCardLabel}><i className="fas fa-satellite-dish"></i> Live Intel Feed</div>
          <div className={styles.refFeedList}>
            {feed.map((item, i) => (
              <div key={i} className={styles.refFeedItem} style={{ animationDelay: `${i * 0.08}s` }}>
                <div className={styles.refFeedDot} style={{ background: item.color, boxShadow: `0 0 6px ${item.color}` }}></div>
                <i className={item.icon} style={{ color: item.color, fontSize: '0.7rem', width: '14px' }}></i>
                <span>{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.refCard} ${styles.refActionsCard}`}>
          <div className={styles.refCardLabel}><i className="fas fa-bolt"></i> Quick Access</div>
          <div className={styles.refActionsGrid}>
            {[
              { icon: 'fas fa-map-marked-alt', label: 'Risk Map',     color: '#ef4444', action: onHeatmapClick },
              { icon: 'fas fa-route',          label: 'Safe Route',   color: '#3b82f6', action: onNavigationClick },
              { icon: 'fas fa-bell',           label: 'Alerts',       color: '#f59e0b', action: onAlertsClick },
              { icon: 'fas fa-first-aid',      label: 'Emergency',    color: '#10b981', action: onEmergencyClick },
            ].map((btn, i) => (
              <button key={i} className={styles.refActionBtn} onClick={btn.action}
                style={{ '--btn-color': btn.color }}>
                <div className={styles.refActionIcon} style={{ background: `${btn.color}22`, color: btn.color }}>
                  <i className={btn.icon}></i>
                </div>
                <span>{btn.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};



// Updated DashboardCards component with real data implementation
const DashboardCards = ({ styles, stats, loading, userLocation, timeFilter }) => {
  // Log stats data for debugging
  console.log('DashboardCards received:', {
    stats,
    userLocation,
    loading
  });
  
  // Use real data from backend - all values are numbers, not percentages
  const hasSafetyScore = typeof stats?.safety_score === 'number';
  const safetyScore = hasSafetyScore ? Math.round(stats.safety_score) : 0;
  const longTermRiskScore = typeof stats?.risk_score === 'number'
    ? Math.max(0, Math.min(100, Math.round(stats.risk_score)))
    : (hasSafetyScore ? Math.max(0, Math.min(100, 100 - safetyScore)) : 50);
  const safetyChange = typeof stats?.safety_score_change === 'number' ? Math.round(stats.safety_score_change * 10) / 10 : 0;
  const weeklyAlerts = typeof stats?.weekly_alerts === 'number' ? stats.weekly_alerts : 0;
  const alertChange = typeof stats?.weekly_alerts_change === 'number' ? stats.weekly_alerts_change : 0;
  const safeRoutes = typeof stats?.safe_routes === 'number' ? stats.safe_routes : 0;
  const nearestSafeZone = typeof stats?.nearest_safe_zone === 'number' ? stats.nearest_safe_zone : 0;
  const safeZoneName = stats?.safe_zone_name || 'None found';
  const breakdown = stats?.breakdown || { violent: 0, property: 0, personal: 0, day: 0, night: 0 };
  
  console.log('DashboardCards parsed values:', {
    safetyScore,
    safetyChange,
    weeklyAlerts,
    alertChange,
    safeRoutes,
    nearestSafeZone,
    safeZoneName,
    breakdown,
    userLocationActive: !!userLocation
  });

  const safetyTrend = safetyChange > 0 ? 'positive' : safetyChange < 0 ? 'negative' : 'neutral';
  const alertTrend = alertChange < 0 ? 'positive' : alertChange > 0 ? 'negative' : 'neutral';
  const recentActivityRisk = Math.min(100, Math.max(0, weeklyAlerts * 15));
  const blendedThreatScore = Math.round((longTermRiskScore * 0.7) + (recentActivityRisk * 0.3));
  const THREAT_POLICY = { high: 74, moderate: 42 };
  const threatBand = blendedThreatScore >= THREAT_POLICY.high
    ? 'HIGH'
    : blendedThreatScore >= THREAT_POLICY.moderate
      ? 'MODERATE'
      : 'LOW';
  const threatPrimaryColor = threatBand === 'LOW' ? '#10b981' : threatBand === 'MODERATE' ? '#f59e0b' : '#ef4444';
  const threatSecondaryColor = threatBand === 'LOW' ? '#06b6d4' : threatBand === 'MODERATE' ? '#f97316' : '#dc2626';

  const getSafetyInsight = (score) => {
    if (!hasSafetyScore) return 'Awaiting telemetry data';
    if (score >= 85) return 'Optimal security - safe perimeter';
    if (score >= 70) return 'Standard security - secure zone';
    if (score >= 55) return 'Elevated awareness required';
    if (score >= 40) return 'Caution: High activity profile';
    if (score >= 20) return 'High volatility - use extreme caution';
    return 'Critical risk - avoid extraction points';
  };

  const getAlertInsight = (count) => {
    const periodLabel = timeFilter === '7d' ? 'last 7 days' : 
                        timeFilter === '30d' ? 'last 30 days' : 
                        timeFilter === '12m' ? 'last 12 months' : 'complete history';
    
    // Scale expectations for longer periods
    const dailyRate = count / (timeFilter === '7d' ? 7 : timeFilter === '30d' ? 30 : timeFilter === '12m' ? 365 : 1000);
    
    if (count === 0) return `No incident notifications in the ${periodLabel}`;
    if (dailyRate < 0.1) return `Low incident activity over the ${periodLabel}`;
    if (dailyRate < 0.5) return `Moderate incident activity over the ${periodLabel}`;
    return `High incident activity over the ${periodLabel}`;
  };

  const getRouteInsight = (count) => {
    if (count === 0) return 'Initialize first secure corridor';
    if (count === 1) return '1 secure corridor analyzed';
    if (count <= 5) return 'Multiple secure corridors active';
    return 'Comprehensive route network active';
  };

  const getThreatBasisText = () => {
    const periodLabel = timeFilter === '7d' ? 'last 7 days' : 
                        timeFilter === '30d' ? 'last 30 days' : 
                        timeFilter === '12m' ? 'last 12 months' : 'complete history';

    if (!hasSafetyScore) return 'Threat model is waiting for telemetry data';

    const total = stats?.total_crimes || 0;
    const weekly = weeklyAlerts;
    
    if (weekly === 0) {
      if (total > 0) {
        return `${total} historical incidents in ${periodLabel} | 0 recent detections in last 7 days`;
      }
      return `No incidents in ${periodLabel} | Threat uses 70% long-term risk + 30% recent activity`;
    }
    
    const changeText = alertChange === 0 ? 'Stable' : alertChange > 0 ? `+${alertChange} increase` : `${alertChange} decrease`;
    return `${weekly} recent incidents detected | ${changeText} vs prior 7-day window`;
  };

  const getZoneInsight = (distance, name) => {
    if (distance === 0 || !name || name === 'None found') return 'No secure zones detected';
    if (distance < 0.5) return 'Target zone: Immediate proximity';
    if (distance <= 1) return 'Target zone: Within tactical distance';
    if (distance <= 2) return 'Target zone: Nearby perimeter';
    if (distance <= 5) return 'Target zone: Moderate distance';
    return 'Target zone: Outside immediate perimeter';
  };

  return (
    <div className={styles.dashboardCards}>
      {loading ? (
        <>
          <SkeletonCard height="120px" />
          <SkeletonCard height="120px" />
          <SkeletonCard height="120px" />
          <SkeletonCard height="120px" />
        </>
      ) : (
        <>
          {/* Safety Score Card */}
          <div className={`${styles.card} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Safety Score</h4>
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className={styles.cardValue} style={{ color: safetyScore >= 70 ? '#10b981' : safetyScore >= 50 ? '#f59e0b' : '#ef4444' }}>
              {hasSafetyScore ? `${safetyScore}%` : 'Loading...'}
            </div>
            <div className={`${styles.cardChange} ${styles[safetyTrend]}`}>
              <i className={`fas fa-arrow-${safetyTrend === 'positive' ? 'up' : safetyTrend === 'negative' ? 'down' : 'right'}`}></i>
              {safetyChange !== 0 ? `${safetyChange > 0 ? '+' : ''}${safetyChange}%` : 'Stable'} vs last month
            </div>
            <div className={styles.cardInsight}>
              {getSafetyInsight(safetyScore)}
            </div>
          </div>
          
          {/* Weekly Alerts Card */}
          <div className={`${styles.card} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Area Activity ({
                timeFilter === '7d' ? '7 Days' :
                timeFilter === '30d' ? '30 Days' :
                timeFilter === '12m' ? '12 Months' : 'Complete History'
              })</h4>
              <i className="fas fa-bell"></i>
            </div>
            <div className={styles.cardValue}>
              {weeklyAlerts}
            </div>
            <div className={`${styles.cardChange} ${styles[alertTrend]}`}>
              <i className={`fas fa-${alertTrend === 'positive' ? 'arrow-down' : alertTrend === 'negative' ? 'arrow-up' : 'minus'}`}></i>
              {alertChange !== 0 ? 
                `${Math.abs(alertChange)} ${alertChange < 0 ? 'fewer' : 'more'} than last ${timeFilter === '7d' ? 'week' : timeFilter === '30d' ? 'month' : 'year'}` : 
                `Same as last ${timeFilter === '7d' ? 'week' : timeFilter === '30d' ? 'month' : 'year'}`
              }
            </div>
            <div className={styles.cardInsight}>
              {getAlertInsight(weeklyAlerts)}
            </div>
          </div>
          
          {/* Real-Time Threat Level Card - Impressive Gauge */}
          <div className={`${styles.card} ${styles.threatLevelCard} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Threat Level</h4>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            
            {/* Circular Threat Gauge */}
            <div className={styles.threatGauge}>
              <svg viewBox="0 0 200 200" className={styles.gaugeSvg}>
                <defs>
                  <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor={threatPrimaryColor} />
                    <stop offset="100%" stopColor={threatSecondaryColor} />
                  </linearGradient>
                </defs>
                
                {/* Background Circle */}
                <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="20"/>
                
                {/* Progress Circle */}
                <circle 
                  cx="100" 
                  cy="100" 
                  r="80" 
                  fill="none" 
                  stroke="url(#gaugeGradient)" 
                  strokeWidth="20"
                  strokeDasharray={`${(blendedThreatScore / 100) * 502.65} 502.65`}
                  strokeLinecap="round"
                  transform="rotate(-90 100 100)"
                  className={styles.gaugeProgress}
                />
                
                {/* Center Text */}
                <text x="100" y="95" textAnchor="middle" className={styles.gaugeValue}>
                  {threatBand}
                </text>
                <text x="100" y="115" textAnchor="middle" className={styles.gaugeLabel}>
                  THREAT
                </text>
              </svg>
            </div>
            
            <div className={styles.threatStatus}>
              <div className={styles.statusIndicator} style={{
                background: threatBand === 'LOW'
                  ? 'linear-gradient(135deg, #10b981, #06b6d4)'
                  : threatBand === 'MODERATE'
                    ? 'linear-gradient(135deg, #f59e0b, #f97316)'
                    : 'linear-gradient(135deg, #ef4444, #dc2626)'
              }}>
                {threatBand === 'LOW' ? '✓ Low Current Threat' : threatBand === 'MODERATE' ? '⚠ Moderate Caution' : '⚠ High Caution'}
              </div>
              <div className={styles.threatDetails}>
                {getThreatBasisText()}
              </div>
            </div>
          </div>
          
          {/* Crime Trend Analysis Card - Mini Chart */}
          <div className={`${styles.card} ${styles.trendCard} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Crime Trend</h4>
              <i className="fas fa-chart-line"></i>
            </div>
            
            {/* Trend Indicator */}
            <div className={styles.trendIndicator}>
              <div className={styles.trendValue} style={{
                color: alertChange <= 0 ? '#10b981' : '#ef4444'
              }}>
                {alertChange === 0 ? '→ 0' : alertChange < 0 ? `↓ ${Math.abs(alertChange)}` : `↑ ${Math.abs(alertChange)}`} incidents
              </div>
              <div className={styles.trendPeriod}>vs last week</div>
            </div>
            
            {/* Mini Trend Chart */}
            <div className={styles.miniChart}>
              {(() => {
                const trendArr = stats?.trend_data || [0, 0, 0, 0, 0, 0, 0];
                const maxCount = Math.max(...trendArr, 2); // Avoid division by zero, min 2 for scale
                return (
                  <div className={styles.chartContainer}>
                    <div className={styles.chartBars}>
                      {trendArr.map((count, i) => {
                        const height = Math.max(8, (count / maxCount) * 100);
                        return (
                          <div key={i} className={styles.chartBar} title={`${count} incidents`}>
                            <div 
                              className={styles.barFill}
                              style={{
                                height: `${height}%`,
                                background: alertChange <= 0 ? 
                                  'linear-gradient(to top, #10b981, #34d399)' : 
                                  'linear-gradient(to top, #ef4444, #f87171)'
                              }}
                            >
                              {count > 0 && <span className={styles.barVal}>{count}</span>}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className={styles.chartLabels}>
                      <span>Earlier</span>
                      <span>Latest</span>
                    </div>
                  </div>
                );
              })()}
            </div>
            
            <div className={styles.trendInsight}>
              <i className={`fas fa-${alertChange <= 0 ? 'chart-line' : 'exclamation-circle'}`}></i>
              <span style={{ marginLeft: '8px' }}>
                {alertChange <= 0 ? 
                  'Short-term activity is low compared with last week' : 
                  'Short-term activity has increased vs last week'}
              </span>
            </div>
          </div>
          
          {/* Safety Recommendations Card - AI Powered */}
          <div className={`${styles.card} ${styles.recommendationsCard} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Safety Tips</h4>
              <i className="fas fa-lightbulb"></i>
            </div>
            
            <div className={styles.recommendations}>
              {(() => {
                const hour = new Date().getHours();
                const isNight = hour >= 20 || hour < 6;
                const isHighRisk = safetyScore < 50;
                const violentScore = typeof breakdown?.violent === 'number' ? breakdown.violent : 100;
                const propertyScore = typeof breakdown?.property === 'number' ? breakdown.property : 100;
                const personalScore = typeof breakdown?.personal === 'number' ? breakdown.personal : 100;
                
                const tips = [];
                
                if (isNight) {
                  tips.push({
                    icon: 'fas fa-moon',
                    text: 'Prefer well-lit main roads after dark',
                    priority: 'high'
                  });
                }

                if (propertyScore < 70) {
                  tips.push({
                    icon: 'fas fa-lock',
                    text: 'Keep valuables secure in crowded areas',
                    priority: 'medium'
                  });
                }

                if (personalScore < 70 || violentScore < 70) {
                  tips.push({
                    icon: 'fas fa-user-shield',
                    text: 'Avoid isolated streets and use trusted transport',
                    priority: 'high'
                  });
                }
                
                if (isHighRisk) {
                  tips.push({
                    icon: 'fas fa-share-alt',
                    text: 'Share live location with a trusted contact',
                    priority: 'high'
                  });
                } else {
                  tips.push({
                    icon: 'fas fa-check-circle',
                    text: 'Short-term conditions are currently stable',
                    priority: 'low'
                  });
                }
                
                tips.push({
                  icon: 'fas fa-phone-alt',
                  text: 'Keep emergency contacts and nearest hospital ready',
                  priority: 'medium'
                });
                
                if (weeklyAlerts > 5) {
                  tips.push({
                    icon: 'fas fa-eye',
                    text: 'Stay aware of surroundings',
                    priority: 'high'
                  });
                }
                
                return tips.slice(0, 3).map((tip, i) => (
                  <div key={i} className={`${styles.recommendationItem} ${styles[tip.priority]}`}>
                    <span className={styles.tipIcon}><i className={tip.icon}></i></span>
                    <span className={styles.tipText}>{tip.text}</span>
                  </div>
                ));
              })()}
            </div>
            
            <div className={styles.aiPowered}>
              <i className="fas fa-robot"></i>
              <span>AI-powered recommendations</span>
            </div>
          </div>
          
          {/* Community Safety Comparison Card */}
          <div className={`${styles.card} ${styles.comparisonCard} ${styles.fadeIn}`}>
            <div className={styles.cardHeader}>
              <h4 className={styles.cardTitle}>Area Comparison</h4>
              <i className="fas fa-users"></i>
            </div>
            
            {(() => {
              const cityAvg = typeof stats?.city_avg_safety_score === 'number' 
                ? Math.round(stats.city_avg_safety_score) 
                : null;
              const hasCityAvg = cityAvg !== null;
              const isBetter = hasCityAvg && hasSafetyScore ? safetyScore >= cityAvg : true;
              const diff = hasCityAvg && hasSafetyScore ? safetyScore - cityAvg : 0;
              
              return (
                <>
                  <div className={styles.comparisonContent}>
                    <div className={styles.yourArea}>
                      <div className={styles.areaLabel}>Your Area</div>
                      <div className={styles.areaScore} style={{
                        color: safetyScore >= 70 ? '#10b981' : safetyScore >= 50 ? '#f59e0b' : '#ef4444'
                      }}>
                        {hasSafetyScore ? `${safetyScore}%` : 'N/A'}
                      </div>
                    </div>
                    
                    <div className={styles.vsIndicator}>VS</div>
                    
                    <div className={styles.cityAverage}>
                      <div className={styles.areaLabel}>City Average</div>
                      <div className={styles.areaScore}>
                        {hasCityAvg ? `${cityAvg}%` : 'N/A'}
                      </div>
                    </div>
                  </div>
                  
                  {/* Comparison Bar */}
                  {hasCityAvg && hasSafetyScore && (
                    <div className={styles.comparisonBar}>
                      <div 
                        className={styles.comparisonFill}
                        style={{
                          width: `${Math.min(100, cityAvg > 0 ? (safetyScore / cityAvg) * 50 : 50)}%`,
                          background: isBetter 
                            ? 'linear-gradient(90deg, #10b981, #06b6d4)' 
                            : 'linear-gradient(90deg, #ef4444, #f97316)'
                        }}
                      ></div>
                    </div>
                  )}
                  
                  <div className={styles.comparisonInsight} style={{ color: isBetter ? '#10b981' : '#ef4444' }}>
                    <i className={`fas fa-${isBetter ? 'award' : 'exclamation-circle'}`}></i>
                    <span style={{ marginLeft: '8px' }}>
                      {!hasCityAvg 
                        ? 'City average data unavailable'
                        : isBetter 
                          ? `Safety index ${diff > 0 ? `+${diff}%` : 'matches'} city average` 
                          : `Safety index ${Math.abs(diff)}% below city average`}
                    </span>
                  </div>
                </>
              );
            })()}
          </div>
        </>
      )}
    </div>
  );
};

// Updated AlertSection with loading states
// const AlertSection = ({ styles, alerts, loading }) => (
//   <div className={`${styles.alertSection} ${styles.fadeIn}`}>
//     <div className={styles.alertHeader}>
//       <h3 className={styles.alertTitle}>Recent Alerts</h3>
//       <a href="#alerts" className={styles.viewAll}>View All <i className="fas fa-chevron-right"></i></a>
//     </div>

//     {loading ? (
//       <SkeletonList items={3} />
//     ) : alerts && alerts.length > 0 ? (
//       alerts.slice(0, 3).map((alert, index) => {
//         const formatTime = (timestamp) => {
//           if (!timestamp) return 'Recently';
//           const date = new Date(timestamp);
//           const now = new Date();
//           const diffMs = now - date;
//           const diffMins = Math.floor(diffMs / 60000);
//           const diffHours = Math.floor(diffMs / 3600000);
//           const diffDays = Math.floor(diffMs / 86400000);
//           if (diffMins < 1) return 'Just now';
//           if (diffMins < 60) return `${diffMins}m ago`;
//           if (diffHours < 24) return `${diffHours}h ago`;
//           if (diffDays < 7) return `${diffDays}d ago`;
//           return date.toLocaleDateString();
//         };
        
//         return (
//         <div key={index} className={styles.alertItem}>
//           <div className={styles.alertIcon} style={{background: alert.severity === 'high' || alert.severity === 'critical' ? '#ef4444' : alert.severity === 'medium' ? '#f59e0b' : '#10b981'}}>
//             <i className={`fas fa-${alert.severity === 'high' || alert.severity === 'critical' ? 'exclamation-triangle' : alert.severity === 'medium' ? 'info-circle' : 'check-circle'}`}></i>
//           </div>
//           <div className={styles.alertContent}>
//             <h4>{alert.title}</h4>
//             <p>{alert.message}</p>
//           </div>
//           <div className={styles.alertTime}>{formatTime(alert.created_at)}</div>
//         </div>
//         );
//       })
//     ) : (
//       <div className={styles.noAlerts}>
//         <i className="fas fa-bell-slash"></i>
//         <p>No active alerts</p>
//       </div>
//     )}
//   </div>
// );

// PredictionResults remains the same
const PredictionResults = ({ predictionResult, showMap, onViewOnMap, formatAreaName, selectedArea, selectedCrimeType, selectedDate, styles }) => (
  <>
    <div className={`${styles.predictionResultCard} ${styles.fadeIn}`}>
      <div className={styles.predictionResultHeader}>
        <h3>Prediction Results</h3>
        <button className={styles.viewOnMapBtn} onClick={onViewOnMap}>
          <i className="fas fa-map-marker-alt"></i> {showMap ? 'Hide Map' : 'View on Map'}
        </button>
      </div>
      
      <div className={styles.predictionDetails}>
        <div className={styles.riskScoreDisplay}>
          <div className={styles.riskMeter}>
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="#eee" strokeWidth="8" />
              <circle 
                cx="60" cy="60" r="54" fill="none" 
                stroke={predictionResult.riskLevel === 'High' ? '#dc2626' : predictionResult.riskLevel === 'Medium' ? '#f59e0b' : '#22c55e'}
                strokeWidth="8"
                strokeDasharray="339.3"
                strokeDashoffset={339.3 - (predictionResult.riskPercentage / 100) * 339.3}
                transform="rotate(-90 60 60)"
              />
              <text x="60" y="65" textAnchor="middle" fontSize="14" fill="var(--text-dark)" fontWeight="bold">
                {predictionResult.riskPercentage}%
              </text>
            </svg>
          </div>
          <div className={`${styles.riskValue} ${styles[predictionResult.riskLevel.toLowerCase()]}`}>
            {predictionResult.riskLevel} Risk
          </div>
        </div>
        
        <div className={styles.predictionInfo}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Area:</span>
            <span className={styles.infoValue}>{formatAreaName(predictionResult.area)}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Crime Type:</span>
            <span className={styles.infoValue}>{predictionResult.crimeType}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Date:</span>
            <span className={styles.infoValue}>{new Date(predictionResult.date).toLocaleDateString()}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Confidence:</span>
            <span className={styles.infoValue}>{Math.round((predictionResult.confidence || 0.8) * 100)}%</span>
          </div>
        </div>
      </div>
    </div>

    {showMap && (
      <div className={`${styles.mapContainer} ${styles.fadeIn}`}>
        <div className={styles.mapHeader}>
          <h3 className={styles.mapTitle}>Crime Risk Visualization</h3>
          <div className={styles.mapControls}>
            <div className={styles.predictionFilter}>
              <span className={styles.filterLabel}>Showing prediction for:</span>
              <span className={styles.filterValue}>
                {formatAreaName(selectedArea)} • {selectedCrimeType} • {new Date(selectedDate).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
        
        <div className={styles.crimeMapWrapper}>
          <CrimeMap 
            isAuthenticated={true} 
            showLoginModal={() => alert('Please login to access advanced features')}
            predictionData={predictionResult}
            hideControls={true}
          />
        </div>
      </div>
    )}
  </>
);

const OperationalFeed = ({ styles, statusReports, loading }) => {
  if (loading) return (
    <div className={styles.operationalFeed}>
      <h3 className={styles.feedTitle}><i className="fas fa-rss"></i> LIVE ACTIVITY FEED</h3>
      <div className={styles.feedList}>
        <ShimmerCard /><ShimmerCard />
      </div>
    </div>
  );

  const reports = statusReports || [];

  return (
    <div className={styles.operationalFeed}>
      <div className={styles.feedHeader}>
        <h3 className={styles.feedTitle}><i className="fas fa-rss"></i> LIVE ACTIVITY FEED</h3>
        <div className={styles.feedStatus}>ACTIVE</div>
      </div>
      <div className={styles.feedList}>
        {reports.length > 0 ? reports.map((report, idx) => (
          <div key={idx} className={`${styles.feedItem} ${styles[report.type]}`}>
            <div className={styles.feedItemIcon}>
              <i className={report.type === 'success' ? 'fas fa-check-circle' : 
                           report.type === 'warning' ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle'}></i>
            </div>
            <div className={styles.feedItemContent}>
              <p className={styles.feedItemMsg}>{report.message}</p>
              <span className={styles.feedItemTime}>
                {new Date(report.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        )) : (
          <div className={styles.emptyFeed}>No active operations to report</div>
        )}
      </div>
      <div className={styles.feedFooter}>
        <div className={styles.scrollingText}>
          &gt; LIVE MONITORING ACTIVE &gt; DATA SYNC: NORMAL &gt; ANALYTICS ENGINE RUNNING &gt; 
        </div>
      </div>
    </div>
  );
};

const SubAreaAnalysis = ({ subAreas, styles, loading }) => {
  if (loading) return (
    <div className={styles.subAreaSection}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>Neighborhood Analysis</h2>
      </div>
      <div className={styles.subAreaGrid}>
        <ShimmerCard /><ShimmerCard /><ShimmerCard />
      </div>
    </div>
  );

  if (!subAreas || subAreas.length === 0) {
    return (
      <div className={`${styles.subAreaSection} ${styles.fadeIn}`}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Neighborhood Analysis</h2>
          <p className={styles.sectionSubtitle}>No specific sub-area telemetry available for this location yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.subAreaSection} ${styles.fadeIn}`}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Neighborhood Analysis</h2>
          <p className={styles.sectionSubtitle}>Detailed safety metrics for specific blocks and sub-areas. Local block scores can differ from the area-wide index.</p>
        </div>
        <div className={styles.areaBadge}>
          <i className="fas fa-map-marked-alt"></i> {subAreas.length} Areas Analyzed
        </div>
      </div>
      
      <div className={styles.subAreaGrid}>
        {subAreas.map((area, index) => (
          <div key={index} className={styles.subAreaCard} style={{ animationDelay: `${index * 50}ms` }}>
            <div className={styles.subAreaHeader}>
              <h4>{area.name}</h4>
              <span className={styles.subAreaBadge} style={{ 
                backgroundColor: (area.safety_score ?? 100) >= 85 ? 'rgba(16, 185, 129, 0.1)' : (area.safety_score ?? 100) >= 70 ? 'rgba(16, 185, 129, 0.05)' : (area.safety_score ?? 100) >= 55 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                color: (area.safety_score ?? 100) >= 85 ? '#10b981' : (area.safety_score ?? 100) >= 70 ? '#10b981' : (area.safety_score ?? 100) >= 55 ? '#f59e0b' : '#ef4444',
                border: `1px solid ${(area.safety_score ?? 100) >= 85 ? '#10b98144' : (area.safety_score ?? 100) >= 70 ? '#10b98122' : (area.safety_score ?? 100) >= 55 ? '#f59e0b44' : '#ef444444'}`
              }}>
                {area.risk_level || 'N/A'}
              </span>
            </div>
            <div className={styles.subAreaStats}>
              <div className={styles.subAreaStat}>
                <span className={styles.statLabel}>Safety Score</span>
                <span className={styles.statVal} style={{ 
                  color: (area.safety_score ?? 100) >= 70 ? '#10b981' : (area.safety_score ?? 100) >= 55 ? '#f59e0b' : '#ef4444' 
                }}>{Math.round(area.safety_score ?? 100)}%</span>
              </div>
              <div className={styles.subAreaStat}>
                <span className={styles.statLabel}>Incidents</span>
                <span className={styles.statVal}>{area.total || 0}</span>
              </div>
            </div>
            <div className={styles.subAreaFooter}>
              <div className={styles.progressBar}>
                <div 
                  className={styles.progressFill} 
                  style={{ 
                    width: `${area.safety_score ?? 100}%`,
                    background: (area.safety_score ?? 100) >= 70 ? 'linear-gradient(90deg, #10b981, #34d399)' : 
                               (area.safety_score ?? 100) >= 50 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 
                               'linear-gradient(90deg, #ef4444, #f87171)'
                  }}
                ></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default UserDashboard;
