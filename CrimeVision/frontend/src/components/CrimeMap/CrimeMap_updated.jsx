import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiService } from "../../services/apiService_updated";
import { ppcSimpleLabel } from '../../utils/ppcUtils';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
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

const FitBounds = ({ points }) => {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const latLngs = points.map(([lat, lng]) => L.latLng(lat, lng));
    const bounds = L.latLngBounds(latLngs);

    try {
      map.fitBounds(bounds, { padding: [20, 20], maxZoom: 14, animate: true, duration: 1.0 });
    } catch (e) {
      // no-op
    }
  }, [points, map]);

  return null;
};

const CrimeMap = ({ showLoginModal, isAuthenticated, predictionData, hideControls = false, filteredCrimes }) => {
  const { settings: systemSettings } = useSystemSettings();
  const [crimes, setCrimes] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(1000);
  const [selectedCrimeType, setSelectedCrimeType] = useState('all');
  const [mapStyle, setMapStyle] = useState('streets'); // Default to streets style
  const [mapProvider, setMapProvider] = useState('maptiler'); // 'maptiler' or 'osm'
  const [fallbackTriggered, setFallbackTriggered] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

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
  const MAPTILER_API_KEY = 'JKSv1djb3YWDL4sjZtTB'; // Replace with your MapTiler API key

  // Unified tile config generator for MapTiler and OSM sources
  const getTileConfig = (provider, style, isDark) => {
    if (provider === 'maptiler') {
      const maptilerBase = 'https://api.maptiler.com/maps';
      const urls = {
        streets: `${maptilerBase}/${isDark ? 'streets-v2-dark' : 'streets-v2'}/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`,
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
    // Fetch crime types from database
    fetchCrimeTypes();

    if (!predictionData) {
      fetchCrimes();
    } else {
      fetchPredictionCrimes();
    }
  }, [limit, selectedCrimeType, predictionData]);

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
        limit: limit === 1000 ? undefined : limit,
        crime_type: selectedCrimeType !== 'all' ? selectedCrimeType : undefined
      };

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
    const filtered = crimes.filter(crime => {
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
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="limit-selector"
            >
              <option value={1000}>All reports</option>
              <option value={500}>500 reports</option>
              <option value={200}>200 reports</option>
              <option value={100}>100 reports</option>
              <option value={50}>50 reports</option>
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

          <div className="stats">
            <div className="stat-item">
              <strong>Total:</strong> {displayCrimes.length} reports
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
              onChange={(e) => setMapProvider(e.target.value)}
              className="style-select"
            >
              <option value="maptiler">MapTiler</option>
              <option value="osm">OpenStreetMap</option>
            </select>
          </div>
          <div>
            <label>Map Style:</label>
            <select
              value={mapStyle}
              onChange={(e) => setMapStyle(e.target.value)}
              className="style-select"
            >
              <option value="streets">Streets</option>
              <option value="satellite">Satellite</option>
              <option value="hybrid">Hybrid</option>
              <option value="basic">Basic</option>
              <option value="outdoor">Outdoor</option>
            </select>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="map-wrapper">
        <MapContainer
          center={[31.5204, 74.3587]} // Lahore coordinates
          zoom={predictionData ? (systemSettings?.default_map_zoom || 12) + 2 : (systemSettings?.default_map_zoom || 12) + 1}
          minZoom={11}
          maxBounds={[[31.30, 74.15], [31.75, 74.60]]}
          maxBoundsViscosity={1.0}
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
            <FitBounds points={markerPositions} />
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
                        {getRiskLevel(crime)}
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
