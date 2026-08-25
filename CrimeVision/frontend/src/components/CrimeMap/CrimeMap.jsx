import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiService } from "../../services/apiService";
import { ppcSimpleLabel } from '../../utils/ppcUtils';
import { SYSTEM_SETTINGS_DEFAULTS, useSystemSettings } from '../../contexts/SystemSettingsContext';
import './CrimeMap2.css';

// Fix for default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Google Maps style icons
const createGoogleMapsIcon = (color = '#ea4335', size = 'normal') => {
  const baseSizes = {
    small: [20, 34],
    normal: [30, 48],
    large: [40, 64]
  };

  const [bw, bh] = baseSizes[size] || baseSizes.normal;
  const width = Math.round(bw * 1.02); // +2%
  const height = Math.round(bh * 1.02); // +2%

  return L.divIcon({
    className: 'google-maps-marker',
    html: `
      <div style="position: relative; width: ${width}px; height: ${height}px; color: ${color};">
        <div class="marker-blink" style="position:absolute; top: 12px; left: 50%; width: 10px; height: 10px; margin-left: -5px; border-radius: 50%; background: currentColor; opacity: 0.6;"></div>
        <svg width="${width}" height="${height}" viewBox="0 0 30 48" fill="none">
          <path d="M15 47C7 47 1 41 1 33C1 25 15 1 15 1C15 1 29 25 29 33C29 41 23 47 15 47Z" fill="${color}" stroke="#ffffff" stroke-width="2"/>
          <circle cx="15" cy="21" r="4" fill="#ffffff"/>
        </svg>
      </div>
    `,
    iconSize: [width, height],
    iconAnchor: [width/2, height],
    popupAnchor: [0, -height]
  });
};

// Risk level color mapping
const riskColors = {
  'High': '#ea4335',    // Google Maps red
  'Medium': '#fbbc04',  // Google Maps yellow
  'Low': '#34a853',     // Google Maps green
  'Unknown': '#6b7280'  // Neutral gray for unknown
};

const riskRank = {
  Low: 1,
  Moderate: 2,
  Medium: 2,
  High: 3,
  Critical: 4,
};

const actionLabel = (level) => {
  if (level === 'Critical') return 'Avoid';
  if (level === 'High') return 'Warning';
  if (level === 'Moderate') return 'Caution';
  return 'Safe';
};

const normalizeVisibilityThreshold = (value) => {
  const v = String(value || SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold).toLowerCase();
  if (v === 'critical') return 'Critical';
  if (v === 'high') return 'High';
  if (v === 'medium') return 'Moderate';
  return 'Low';
};

const normalizeRiskLevel = (value) => {
  const v = String(value || '').toLowerCase();
  if (v.includes('critical') || v.includes('avoid')) return 'Critical';
  if (v.includes('high') || v.includes('warning')) return 'High';
  if (v.includes('moderate') || v.includes('medium') || v.includes('caution')) return 'Moderate';
  if (v.includes('low') || v.includes('safe')) return 'Low';
  return 'Low';
};

// Component to handle map view changes based on prediction data
const MapController = ({ predictionData, crimes }) => {
  const map = useMap();

  useEffect(() => {
    if (predictionData && predictionData.area && crimes.length > 0) {
      // Find crimes in the predicted area to center the map
      const areaCrimes = crimes.filter(crime =>
        crime.area && crime.area.toLowerCase().includes(predictionData.area.toLowerCase())
      );

      if (areaCrimes.length > 0) {
        // Use the first crime's coordinates to center the map
        const firstCrime = areaCrimes[0];
        let position;
        if (firstCrime.coordinates && Array.isArray(firstCrime.coordinates) && firstCrime.coordinates.length === 2) {
          position = [firstCrime.coordinates[0], firstCrime.coordinates[1]];
        } else if (firstCrime.latitude && firstCrime.longitude) {
          position = [firstCrime.latitude, firstCrime.longitude];
        }

        if (position) {
          map.setView(position, 14, {
            animate: true,
            duration: 1.5
          });
        }
      }
    }
  }, [predictionData, crimes, map]);

  return null;
};

const FitBounds = ({ points, paddingPx, maxZoom }) => {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const latLngs = points.map(([lat, lng]) => L.latLng(lat, lng));
    const bounds = L.latLngBounds(latLngs);

    try {
      const safePadding = Number.isFinite(Number(paddingPx)) ? Number(paddingPx) : 20;
      const safeMaxZoom = Number.isFinite(Number(maxZoom)) ? Number(maxZoom) : 14;
      map.fitBounds(bounds, { padding: [safePadding, safePadding], maxZoom: safeMaxZoom, animate: true, duration: 1.0 });
    } catch (e) {
      // no-op
    }
  }, [points, map, paddingPx, maxZoom]);

  return null;
};

const CrimeMap = ({ showLoginModal, isAuthenticated, predictionData, hideControls = false, filteredCrimes }) => {
  const { settings: systemSettings } = useSystemSettings();
  const [crimes, setCrimes] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
  const [selectedCrimeType, setSelectedCrimeType] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [mapStyle, setMapStyle] = useState(systemSettings?.map_default_style || SYSTEM_SETTINGS_DEFAULTS.map_default_style);
  const [mapProvider, setMapProvider] = useState(systemSettings?.map_provider_default || SYSTEM_SETTINGS_DEFAULTS.map_provider_default);
  const [fallbackTriggered, setFallbackTriggered] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [settingsSyncedAt, setSettingsSyncedAt] = useState(() => new Date());
  const limitTouchedRef = useRef(false);
  const mapStyleTouchedRef = useRef(false);
  const mapProviderTouchedRef = useRef(false);

  // Track global theme changes (supports both body class and data-theme attribute)
  useEffect(() => {
    const updateTheme = () => {
      const dark = document.body.classList.contains('dark-mode') || document.body.getAttribute('data-theme') === 'dark';
      setIsDarkMode(dark);
    };
    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.body, { attributes: true, attributeFilter: ['class', 'data-theme'] });
    return () => observer.disconnect();
  }, []);

  // Handle automatic fallback from MapTiler to OSM on error
  const handleTileError = () => {
    if (mapProvider === 'maptiler' && !fallbackTriggered) {
      console.log('MapTiler tiles failed, falling back to OSM');
      setFallbackTriggered(true);
      setMapProvider('osm');
    }
  };

  // MapTiler configuration
  const MAPTILER_API_KEY = String(systemSettings?.maptiler_api_key || SYSTEM_SETTINGS_DEFAULTS.maptiler_api_key || '');

  // Unified tile config generator for MapTiler and OSM sources
  const getTileConfig = (provider, style, isDark) => {
    if (provider === 'maptiler') {
      const maptilerBase = 'https://api.maptiler.com/maps';
      const urls = {
        streets: `${maptilerBase}/${isDark ? 'streets-v2-dark' : 'streets-v2'}/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
        dark: `${maptilerBase}/streets-v2-dark/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
        satellite: `${maptilerBase}/satellite/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
        hybrid: `${maptilerBase}/hybrid/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
        basic: `${maptilerBase}/${isDark ? 'basic-v2-dark' : 'basic-v2'}/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
        outdoor: `${maptilerBase}/outdoor/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
      };
      return {
        url: urls[style] || urls.streets,
        attribution: '&copy; <a href="https://www.maptiler.com/">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      };
    } else {
      // OpenStreetMap tiles from CrimeMapInterface_real_insights
      const osmUrls = {
        streets: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        basic: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        hybrid: 'https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}',
        outdoor: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
      };

      const attributions = {
        streets: '&copy; OpenStreetMap contributors',
        basic: '&copy; OpenStreetMap contributors',
        satellite: 'Tiles &copy; Esri',
        hybrid: 'Tiles &copy; Esri',
        outdoor: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
      };

      return {
        url: osmUrls[style] || osmUrls.streets,
        attribution: attributions[style] || attributions.streets,
        overlayUrl: style === 'hybrid' ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}' : null,
        overlayAttribution: style === 'hybrid' ? 'Labels &copy; Esri' : null
      };
    }
  };

  useEffect(() => {
    const configuredLimit = Number(systemSettings?.map_default_record_limit ?? SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
    if (!limitTouchedRef.current && Number.isFinite(configuredLimit) && configuredLimit >= 0 && configuredLimit !== limit) {
      setLimit(configuredLimit);
    }
  }, [systemSettings?.map_default_record_limit]);

  useEffect(() => {
    const configuredStyle = String(systemSettings?.map_default_style || SYSTEM_SETTINGS_DEFAULTS.map_default_style);
    if (!mapStyleTouchedRef.current && configuredStyle) {
      setMapStyle(configuredStyle);
    }
  }, [systemSettings?.map_default_style]);

  useEffect(() => {
    const maptilerEnabled = Boolean(systemSettings?.maptiler_enabled ?? SYSTEM_SETTINGS_DEFAULTS.maptiler_enabled);
    const configuredProvider = String(systemSettings?.map_provider_default || SYSTEM_SETTINGS_DEFAULTS.map_provider_default);
    if (!maptilerEnabled) {
      setMapProvider('osm');
      return;
    }
    if (!mapProviderTouchedRef.current && (configuredProvider === 'maptiler' || configuredProvider === 'osm')) {
      setMapProvider(configuredProvider);
    }
  }, [systemSettings?.map_provider_default, systemSettings?.maptiler_enabled]);

  useEffect(() => {
    setSettingsSyncedAt(new Date());
  }, [systemSettings]);

  useEffect(() => {
    // Fetch crime types from database
    fetchCrimeTypes();

    if (!predictionData) {
      fetchCrimes();
    } else {
      fetchPredictionCrimes();
    }
  }, [limit, selectedCrimeType, predictionData, systemSettings?.data_retention_days]);

  const fetchCrimeTypes = async () => {
    try {
      const response = await apiService.getCrimeTypes();
      const crimeTypesData = response.crime_types || [];
      setCrimeTypes(crimeTypesData);
    } catch (err) {
      console.error("Error fetching crime types:", err);
    }
  };

  const fetchCrimes = async () => {
    try {
      setLoading(true);
      setError(null);

      const filters = {
        limit: limit === 0 ? undefined : limit,
        crime_type: selectedCrimeType !== 'all' ? selectedCrimeType : undefined
      };

      const retentionDays = Number(systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days);
      if (retentionDays > 0) {
        const start = new Date();
        start.setDate(start.getDate() - retentionDays);
        filters.start_date = start.toISOString().slice(0, 10);
      }

      const data = await apiService.getCrimes(filters);
      setCrimes(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Error fetching crimes:", err);
      setError("Failed to load crime data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const fetchPredictionCrimes = async () => {
    try {
      setLoading(true);
      setError(null);

      const filters = {
        limit: 100,
        crime_type: predictionData.crimeType
      };

      const data = await apiService.getCrimesByArea(predictionData.area, filters);

      const allCrimes = Array.isArray(data) ? data : [];

      const relevantCrimes = allCrimes
        .map(crime => ({
          ...crime,
          relevanceScore: calculateRelevanceScore(crime, predictionData)
        }))
        .sort((a, b) => b.relevanceScore - a.relevanceScore)
        .slice(0, 50);

      setCrimes(relevantCrimes);
    } catch (err) {
      console.error("Error fetching prediction crimes:", err);
      setError("Failed to load prediction-related reports.");
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get risk level
  const getRiskLevel = (crime) => {
    if (crime.risk_level) {
      return crime.risk_level;
    }
    return 'Unknown';
  };

  // Calculate relevance score for crimes based on prediction
  const calculateRelevanceScore = (crime, prediction) => {
    let score = 0;

    // Exact crime type match gets highest score
    if (crime.crime_type?.toLowerCase() === prediction.crimeType?.toLowerCase()) {
      score += 50;
    }

    // Partial crime type match
    else if (crime.crime_type?.toLowerCase().includes(prediction.crimeType?.toLowerCase()) ||
             prediction.crimeType?.toLowerCase().includes(crime.crime_type?.toLowerCase())) {
      score += 25;
    }

    // Risk level alignment with prediction
    const crimeRiskLevel = getRiskLevel(crime);
    if (crimeRiskLevel === prediction.riskLevel) {
      score += 30;
    }
    else if ((crimeRiskLevel === 'High' && prediction.riskLevel === 'Medium') ||
             (crimeRiskLevel === 'Medium' && prediction.riskLevel === 'High')) {
      score += 15;
    }

    // Recency bonus (crimes from last 30 days get higher score)
    if (crime.date) {
      const crimeDate = new Date(crime.date);
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      if (crimeDate >= thirtyDaysAgo) {
        score += 20;
      }
      else if (crimeDate >= new Date(thirtyDaysAgo.getFullYear(), thirtyDaysAgo.getMonth() - 3, thirtyDaysAgo.getDate())) {
        score += 10;
      }
    }

    // Area name similarity bonus
    if (crime.area && prediction.area) {
      const crimeArea = crime.area.toLowerCase();
      const predictionArea = prediction.area.toLowerCase();

      if (crimeArea.includes(predictionArea) || predictionArea.includes(crimeArea)) {
        score += 15;
      }
    }

    return score;
  };

  const getFilteredCrimes = () => {
    const threshold = normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold);
    const thresholdRank = riskRank[threshold] || 1;

    const filtered = crimes.filter(crime => {
      if (selectedCrimeType !== 'all' && String(crime.crime_type || '').toLowerCase() !== String(selectedCrimeType).toLowerCase()) {
        return false;
      }

      let lat, lng;

      // Check coordinates array format first
      if (crime.coordinates && Array.isArray(crime.coordinates) && crime.coordinates.length === 2) {
        lat = crime.coordinates[0];
        lng = crime.coordinates[1];
      }
      // Check separate lat/lng fields
      else if (crime.latitude !== undefined && crime.longitude !== undefined) {
        lat = crime.latitude;
        lng = crime.longitude;
      }
      else {
        return false;
      }

      // Validate that coordinates are valid numbers
      const isValidLat = lat !== null && !isNaN(lat) && isFinite(lat) &&
                         lat >= -90 && lat <= 90;
      const isValidLng = lng !== null && !isNaN(lng) && isFinite(lng) &&
                         lng >= -180 && lng <= 180;

      if (!isValidLat || !isValidLng) {
        console.warn(`Filtering out crime ${crime.id} - invalid coordinates: lat=${lat}, lng=${lng}`);
        return false;
      }

      const normalizedRisk = normalizeRiskLevel(crime.risk_level);
      if ((riskRank[normalizedRisk] || 1) < thresholdRank) {
        return false;
      }

      if (riskFilter !== 'all' && normalizedRisk !== riskFilter) {
        return false;
      }

      const crimeDate = String(crime.date || '').slice(0, 10);
      if (dateRange.start && crimeDate && crimeDate < dateRange.start) {
        return false;
      }
      if (dateRange.end && crimeDate && crimeDate > dateRange.end) {
        return false;
      }

      return true;
    });

    return filtered;
  };

  // Use prop filteredCrimes if provided, otherwise use local filtering
  const displayCrimes = filteredCrimes || getFilteredCrimes();

  const markerPositions = displayCrimes.map((crime) => {
    let lat, lng;
    if (crime.coordinates && Array.isArray(crime.coordinates) && crime.coordinates.length === 2) {
      lat = crime.coordinates[0];
      lng = crime.coordinates[1];
    } else if (crime.latitude !== undefined && crime.longitude !== undefined) {
      lat = crime.latitude;
      lng = crime.longitude;
    } else {
      return null;
    }

    const isValid = lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng) && isFinite(lat) && isFinite(lng);
    return isValid ? [lat, lng] : null;
  }).filter(Boolean);

  // Create Google Maps style marker icon based on risk level
  const createRiskIcon = (riskLevel, isPrediction = false, relevanceScore = 0) => {
    const color = riskColors[riskLevel] || riskColors['Medium'];
    const size = isPrediction ? 'large' : 'normal';

    return createGoogleMapsIcon(color, size);
  };

  if (loading) {
    return (
      <div className="crime-map-container">
        <div style={{ padding: "40px", textAlign: "center", fontSize: "18px", color: "#374151" }}>
          🔄 Loading crime data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="crime-map-container">
        <div style={{ padding: "40px", textAlign: "center", color: "#dc2626" }}>
          <div style={{ fontSize: "18px", marginBottom: "15px" }}>❌ {error}</div>
          <button onClick={predictionData ? fetchPredictionCrimes : fetchCrimes} style={{ padding: "10px 20px", backgroundColor: "#dc2626", color: "white", border: "none", borderRadius: "6px", cursor: "pointer" }}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const formatAreaName = (name) => {
    if (!name) return 'Unknown Area';
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const tileConfig = getTileConfig(mapProvider, mapStyle, isDarkMode);
  const minZoom = Number(systemSettings?.map_min_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_min_zoom);
  const maxZoom = Number(systemSettings?.map_max_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_max_zoom);
  const baseZoom = Number(systemSettings?.default_map_zoom ?? SYSTEM_SETTINGS_DEFAULTS.default_map_zoom);
  const requestedZoom = predictionData ? baseZoom + 2 : baseZoom + 1;
  const mapZoom = Math.max(minZoom, Math.min(maxZoom, requestedZoom));
  const mapBounds = [[
    Number(systemSettings?.map_bounds_south ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_south),
    Number(systemSettings?.map_bounds_west ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_west),
  ], [
    Number(systemSettings?.map_bounds_north ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_north),
    Number(systemSettings?.map_bounds_east ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_east),
  ]];
  const mapBoundsViscosity = Number(systemSettings?.map_bounds_viscosity ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_viscosity);
  const fitBoundsPaddingPx = Number(systemSettings?.map_fitbounds_padding_px ?? SYSTEM_SETTINGS_DEFAULTS.map_fitbounds_padding_px);
  const fitBoundsMaxZoom = Number(systemSettings?.map_fitbounds_max_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_fitbounds_max_zoom);

  return (
    <div className="crime-map-container">
      
      {/* Controls Panel - Only show if not in prediction mode and not hidden */}
      {!hideControls && !predictionData && (
        <div className="map-controls">
          <div className="control-group">
            <label htmlFor="limit-select">Show Reports:</label>
            <select
              id="limit-select"
              value={limit}
              onChange={(e) => {
                limitTouchedRef.current = true;
                setLimit(parseInt(e.target.value, 10));
              }}
              className="limit-selector"
            >
              <option value={500}>500 reports</option>
              <option value={1000}>1,000 reports</option>
              <option value={2000}>2,000 reports</option>
              <option value={5000}>5,000 reports</option>
              <option value={200}>200 reports</option>
              <option value={100}>100 reports</option>
              <option value={50}>50 reports</option>
              <option value={0}>All records</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="crime-type-select">Report Type:</label>
            <select
              id="crime-type-select"
              value={selectedCrimeType}
              onChange={(e) => setSelectedCrimeType(e.target.value)}
              className="crime-type-selector"
            >
              <option value="all">All Types</option>
              {crimeTypes.map((crimeType, index) => (
                <option key={index} value={crimeType}>
                  {crimeType.charAt(0).toUpperCase() + crimeType.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="risk-select">Risk Level:</label>
            <select
              id="risk-select"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="crime-type-selector"
            >
              <option value="all">All Levels</option>
              <option value="Critical">Avoid</option>
              <option value="High">Warning</option>
              <option value="Moderate">Caution</option>
              <option value="Low">Safe</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="from-date">From:</label>
            <input
              id="from-date"
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="crime-type-selector"
            />
          </div>

          <div className="control-group">
            <label htmlFor="to-date">To:</label>
            <input
              id="to-date"
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="crime-type-selector"
            />
          </div>

          <div className="stats">
            <div className="stat-item">
              <strong>Total:</strong> {displayCrimes.length} reports
            </div>
            <div className="stat-item">
              <strong>Visibility:</strong> {normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold)}+
            </div>
            {selectedCrimeType !== 'all' && (
              <div className="stat-item">
                <strong>Type:</strong> {selectedCrimeType}
              </div>
            )}
          </div>

          {!isAuthenticated && (
            <div className="login-prompt">
              <h5>🔒 Advanced Features</h5>
              <p>Login for heatmap analysis and detailed insights</p>
              <button onClick={showLoginModal} className="login-button">
                Login for Advanced View
              </button>
            </div>
          )}
        </div>
      )}

      {/* Map Title - Only show when in UserDashboard with prediction data */}
      {predictionData && (
        <div style={{
          textAlign: 'center',
          marginBottom: '15px',
          padding: '10px',
          backgroundColor: '#f8fafc',
          borderRadius: '8px'
        }}>
          <h4 style={{ margin: '0 0 5px 0', color: '#374151' }}>
            Reports Visualization for {formatAreaName(predictionData.area)}
          </h4>
          <p style={{ margin: 0, color: '#6b7280', fontSize: '14px' }}>
            Showing {predictionData.crimeType} reports with {predictionData.riskLevel.toLowerCase()} risk prediction
            {displayCrimes.length > 0 && ` • ${displayCrimes.length} reports found`}
          </p>
        </div>
      )}

      {/* Map Source & Style Selector */}
      <div className="map-style-selector">
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label>Source:</label>
            <select
              value={mapProvider}
              onChange={(e) => {
                mapProviderTouchedRef.current = true;
                setMapProvider(e.target.value);
              }}
              className="style-select"
            >
              {(systemSettings?.maptiler_enabled ?? SYSTEM_SETTINGS_DEFAULTS.maptiler_enabled) && (
                <option value="maptiler">MapTiler</option>
              )}
              <option value="osm">OpenStreetMap</option>
            </select>
          </div>
          <div>
            <label>Map Style:</label>
            <select
              value={mapStyle}
              onChange={(e) => {
                mapStyleTouchedRef.current = true;
                setMapStyle(e.target.value);
              }}
              className="style-select"
            >
              <option value="streets">Streets</option>
              <option value="dark">Dark</option>
              <option value="satellite">Satellite</option>
              <option value="hybrid">Hybrid</option>
              <option value="basic">Basic</option>
              <option value="outdoor">Outdoor</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applied Settings Snapshot */}
      <div
        style={{
          margin: '10px 0 14px',
          padding: '10px 12px',
          borderRadius: '10px',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          background: 'linear-gradient(135deg, rgba(30,41,59,0.7), rgba(15,23,42,0.7))',
          display: 'flex',
          gap: '8px',
          flexWrap: 'wrap',
          alignItems: 'center'
        }}
      >
        <span style={{ fontSize: '0.75rem', color: '#93c5fd', fontWeight: 700, letterSpacing: '0.3px' }}>
          Applied from System Settings
        </span>
        <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>
          Last synced: {settingsSyncedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
        <span style={{ padding: '4px 9px', borderRadius: '999px', background: 'rgba(59,130,246,0.18)', color: '#bfdbfe', fontSize: '0.75rem', fontWeight: 600 }}>
          Records: {Number(systemSettings?.map_default_record_limit ?? limit).toLocaleString()}
        </span>
        <span style={{ padding: '4px 9px', borderRadius: '999px', background: 'rgba(34,197,94,0.16)', color: '#bbf7d0', fontSize: '0.75rem', fontWeight: 600 }}>
          Visibility: {normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold)}+
        </span>
        <span style={{ padding: '4px 9px', borderRadius: '999px', background: 'rgba(245,158,11,0.16)', color: '#fde68a', fontSize: '0.75rem', fontWeight: 600 }}>
          Lookback: {Number(systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days)} days
        </span>
        <span style={{ padding: '4px 9px', borderRadius: '999px', background: 'rgba(168,85,247,0.16)', color: '#e9d5ff', fontSize: '0.75rem', fontWeight: 600 }}>
          Heatmap: r{Number(systemSettings?.heatmap_radius ?? SYSTEM_SETTINGS_DEFAULTS.heatmap_radius)} • i{Number(systemSettings?.heatmap_intensity ?? SYSTEM_SETTINGS_DEFAULTS.heatmap_intensity)}
        </span>
      </div>

      {/* Map */}
      <div className="map-wrapper">
        <MapContainer
          center={[
            Number(systemSettings?.map_default_center_lat ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lat),
            Number(systemSettings?.map_default_center_lng ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lng),
          ]}
          zoom={mapZoom}
          minZoom={minZoom}
          maxZoom={maxZoom}
          maxBounds={mapBounds}
          maxBoundsViscosity={mapBoundsViscosity}
          style={{ width: "100%", height: "70vh" }}
          scrollWheelZoom={false}
          zoomControl={true}
          doubleClickZoom={false}
          boxZoom={false}
          keyboard={false}
        >
          {/* Base Tile Layer (auto-switches light/dark based on theme) */}
          <TileLayer
            key={tileConfig.url}
            url={tileConfig.url}
            attribution={tileConfig.attribution}
            eventHandlers={{
              tileerror: handleTileError
            }}
          />

          {/* Optional labels overlay for hybrid when using OSM sources */}
          {tileConfig.overlayUrl && (
            <TileLayer
              key={tileConfig.overlayUrl}
              url={tileConfig.overlayUrl}
              attribution={tileConfig.overlayAttribution}
              zIndex={1000}
            />
          )}

          {/* Map Controller for prediction data */}
          <MapController predictionData={predictionData} crimes={crimes} />
          {!predictionData && markerPositions.length > 0 && (
            <FitBounds points={markerPositions} paddingPx={fitBoundsPaddingPx} maxZoom={fitBoundsMaxZoom} />
          )}

          {/* Crime Markers */}
          {displayCrimes.map((crime, index) => {
            // Handle both coordinate formats
            let position;
            if (crime.coordinates && Array.isArray(crime.coordinates) && crime.coordinates.length === 2) {
              position = [crime.coordinates[0], crime.coordinates[1]];
            } else if (crime.latitude && crime.longitude) {
              position = [crime.latitude, crime.longitude];
            } else {
              return null; // Skip if no valid coordinates
            }

            return (
              <Marker
                key={`${crime.id || index}-${position[0]}-${position[1]}`}
                position={position}
                icon={createRiskIcon(getRiskLevel(crime), false, crime.relevanceScore || 0)}
              >
                <Popup>
                  <div className="crime-popup">
                    <h4 style={{ margin: "0 0 10px 0", color: "#0f172a" }}>
                      📍 Area Report
                    </h4>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Report Type:</strong> {crime.crime_type || 'Unknown'}
                      {crime.crime_type && ppcSimpleLabel(crime.crime_type) !== crime.crime_type && (
                        <span style={{ color: '#6b7280', fontSize: '0.85em', marginLeft: 4 }}>({ppcSimpleLabel(crime.crime_type)})</span>
                      )}
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Area:</strong> {formatAreaName(crime.area)}
                      {crime.area_translit && crime.area_translit !== crime.area && (
                        <span style={{ color: '#6b7280', fontStyle: 'italic', display: 'block', fontSize: '0.82em', marginTop: 1 }}>{crime.area_translit}</span>
                      )}
                      {crime.area_urdu && (
                        <span style={{ fontFamily: "'Noto Nastaliq Urdu', serif", direction: 'rtl', display: 'block', fontSize: '0.85em', marginTop: 2 }}>{crime.area_urdu}</span>
                      )}
                    </div>

                    {crime.date && (
                      <div style={{ marginBottom: "8px" }}>
                        <strong>Reported:</strong> {new Date(crime.date).toLocaleString()}
                      </div>
                    )}

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Risk Level:</strong>
                      <span style={{
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        marginLeft: "5px",
                        backgroundColor: getRiskLevel(crime) === 'High' ? '#fee2e2' : getRiskLevel(crime) === 'Medium' ? '#fef3c7' : getRiskLevel(crime) === 'Low' ? '#d1fae5' : '#e5e7eb',
                        color: getRiskLevel(crime) === 'High' ? '#dc2626' : getRiskLevel(crime) === 'Medium' ? '#d97706' : getRiskLevel(crime) === 'Low' ? '#059669' : '#374151'
                      }}>
                        {actionLabel(normalizeRiskLevel(getRiskLevel(crime)))}
                      </span>
                    </div>

                    {crime.description && (
                      <div style={{ marginBottom: "8px" }}>
                        <strong>Description:</strong> {crime.description}
                      </div>
                    )}

                    {predictionData && crime.relevanceScore > 0 && (
                      <div style={{
                        marginTop: "10px",
                        padding: "8px",
                        backgroundColor: "#f0f9ff",
                        borderRadius: "4px",
                        borderLeft: "4px solid #0ea5e9"
                      }}>
                        <small>
                          <strong>📊 Relevance Score:</strong>
                          <span className="relevance-score">
                            {crime.relevanceScore}/100
                          </span>
                          <br />
                          <strong>Relevance:</strong> {
                            crime.relevanceScore >= 80 ? 'High' :
                            crime.relevanceScore >= 50 ? 'Medium' : 'Low'
                          }
                        </small>
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};

export default CrimeMap;
