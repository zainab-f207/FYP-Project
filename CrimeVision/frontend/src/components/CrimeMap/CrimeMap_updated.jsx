import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiService } from "../../services/apiService";
import './CrimeMap.css';

// Fix for default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

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

const CrimeMap = ({ showLoginModal, isAuthenticated, predictionData, hideControls = false }) => {
  const [crimes, setCrimes] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(50);
  const [selectedCrimeType, setSelectedCrimeType] = useState('all');

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
        limit: limit,
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

      // Enhanced filtering for prediction relevance
      const filters = {
        limit: 100, // Increased limit for better relevance
        crime_type: predictionData.crimeType
      };

      // Use the new getCrimesByArea function for area-specific filtering
      const data = await apiService.getCrimesByArea(predictionData.area, filters);

      // Filter and prioritize crimes based on prediction relevance
      const allCrimes = Array.isArray(data) ? data : [];

      // Sort crimes by relevance to prediction
      const relevantCrimes = allCrimes
        .map(crime => ({
          ...crime,
          relevanceScore: calculateRelevanceScore(crime, predictionData)
        }))
        .sort((a, b) => b.relevanceScore - a.relevanceScore)
        .slice(0, 50); // Take top 50 most relevant

      setCrimes(relevantCrimes);
    } catch (err) {
      console.error("Error fetching prediction crimes:", err);
      // Fallback to general crimes
      fetchCrimes();
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get risk level (moved up to avoid hoisting issues)
  const getRiskLevel = (crime) => {
    // Use the actual risk_level from the database if available
    if (crime.risk_level && ['High', 'Medium', 'Low'].includes(crime.risk_level)) {
      return crime.risk_level;
    }

    // Fallback to crime type-based mapping if database risk_level is not available
    // Using dynamic crime type detection instead of hardcoded lists
    const crimeType = crime.crime_type?.toLowerCase() || '';

    // High risk crimes typically involve violence or serious threats
    const highRiskKeywords = ['murder', 'rape', 'assault', 'robbery', 'kidnapping', 'terrorism', 'homicide'];
    const mediumRiskKeywords = ['theft', 'burglary', 'vandalism', 'drug', 'fraud', 'snatching', 'arson'];

    if (highRiskKeywords.some(keyword => crimeType.includes(keyword))) return 'High';
    if (mediumRiskKeywords.some(keyword => crimeType.includes(keyword))) return 'Medium';
    return 'Low';
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
    // Handle both coordinate formats: separate lat/lng fields or coordinates array
    // Add additional validation to ensure coordinates are valid numbers
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

    console.log('Total crimes:', crimes.length);
    console.log('Filtered crimes (with valid coordinates):', filtered.length);
    console.log('Sample crime data:', crimes.slice(0, 3));
    console.log('Crimes without valid coordinates:', crimes.filter(crime => {
      let lat, lng;

      if (crime.coordinates && Array.isArray(crime.coordinates) && crime.coordinates.length === 2) {
        lat = crime.coordinates[0];
        lng = crime.coordinates[1];
      } else if (crime.latitude !== undefined && crime.longitude !== undefined) {
        lat = crime.latitude;
        lng = crime.longitude;
      } else {
        return true;
      }

      const isValidLat = lat !== null && !isNaN(lat) && isFinite(lat) &&
                         lat >= -90 && lat <= 90;
      const isValidLng = lng !== null && !isNaN(lng) && isFinite(lng) &&
                         lng >= -180 && lng <= 180;

      return !isValidLat || !isValidLng;
    }).length);

    return filtered;
  };

  const filteredCrimes = getFilteredCrimes();

  // Create custom marker icon based on risk level
  const createRiskIcon = (riskLevel, isPrediction = false, relevanceScore = 0) => {
    const colors = {
      'High': { primary: '#dc2626', secondary: '#fecaca' },
      'Medium': { primary: '#f59e0b', secondary: '#fef3c7' },
      'Low': { primary: '#22c55e', secondary: '#d1fae5' }
    };

    const color = colors[riskLevel] || colors['Medium'];
    const size = isPrediction ? 60 : 35; // Made prediction marker larger

    // Determine relevance indicator color
    let relevanceClass = 'relevance-low';
    if (relevanceScore >= 80) relevanceClass = 'relevance-high';
    else if (relevanceScore >= 50) relevanceClass = 'relevance-medium';

    return L.divIcon({
      className: isPrediction ? "prediction-marker prediction-marker-enhanced" : "crime-marker",
      html: `<div style="
        width: ${size}px;
        height: ${size}px;
        background: radial-gradient(circle, ${color.primary}, ${color.primary}dd);
        border: 4px solid #ffffff;
        border-radius: 50%;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4), 0 0 20px ${color.primary}66;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${size > 25 ? '14px' : '10px'};
        position: relative;
        z-index: 1000;
        ${isPrediction ? 'animation: pulse-glow 2s infinite;' : ''}
      ">
        ${isPrediction ? '⚠️' : ''}
        ${isPrediction ? `<div style="
          position: absolute;
          top: -8px;
          right: -8px;
          background: ${color.primary};
          color: white;
          border-radius: 50%;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          font-weight: bold;
          border: 2px solid white;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        ">${filteredCrimes.length}</div>` : ''}
        ${!isPrediction && relevanceScore > 0 ? `<div class="${relevanceClass} relevance-indicator">
          ${relevanceScore >= 80 ? '●' : relevanceScore >= 50 ? '●' : '●'}
        </div>` : ''}
      </div>`,
      iconSize: [size, size],
      iconAnchor: [size/2, size/2],
      popupAnchor: [0, -size/2]
    });
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



  return (
    <div className="crime-map-container">
      {/* Controls Panel - Only show if not in prediction mode and not hidden */}
      {!hideControls && !predictionData && (
        <div className="map-controls">
          <div className="control-group">
            <label htmlFor="limit-select">Show Crimes:</label>
            <select
              id="limit-select"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="limit-selector"
            >
              <option value={50}>50 crimes</option>
              <option value={100}>100 crimes</option>
              <option value={200}>200 crimes</option>
              <option value={500}>500 crimes</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="crime-type-select">Crime Type:</label>
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
              <strong>Total:</strong> {filteredCrimes.length} crimes
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
            Crime Risk Visualization for {formatAreaName(predictionData.area)}
          </h4>
          <p style={{ margin: 0, color: '#6b7280', fontSize: '14px' }}>
            Showing {predictionData.crimeType} incidents with {predictionData.riskLevel.toLowerCase()} risk prediction
            {filteredCrimes.length > 0 && ` • ${filteredCrimes.length} incidents found`}
          </p>
        </div>
      )}

      {/* Map */}
      <div className="map-wrapper">
        <MapContainer
          center={[31.5204, 74.3587]} // Default Lahore coordinates
          zoom={predictionData ? 13 : 11}
          style={{ width: "100%", height: "400px" }}
          scrollWheelZoom={true}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png?lang=en"
            attribution='&copy; OpenStreetMap contributors'
          />

          {/* Map Controller for prediction data */}
          <MapController predictionData={predictionData} crimes={crimes} />

          {/* Prediction Marker */}
          {predictionData && filteredCrimes.length > 0 && (() => {
            // Handle both coordinate formats for prediction marker
            let position;
            const firstCrime = filteredCrimes[0];
            if (firstCrime.coordinates && Array.isArray(firstCrime.coordinates) && firstCrime.coordinates.length === 2) {
              position = [firstCrime.coordinates[0], firstCrime.coordinates[1]];
            } else if (firstCrime.latitude && firstCrime.longitude) {
              position = [firstCrime.latitude, firstCrime.longitude];
            } else {
              return null; // Skip if no valid coordinates
            }

            return (
              <Marker
                position={position}
                icon={createRiskIcon(predictionData.riskLevel, true)}
              >
              <Popup>
                <div className="prediction-popup">
                  <h4 style={{ margin: "0 0 10px 0", color: predictionData.riskLevel === 'High' ? '#dc2626' : predictionData.riskLevel === 'Medium' ? '#f59e0b' : '#22c55e' }}>
                    🎯 Risk Prediction
                  </h4>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Area:</strong> {formatAreaName(predictionData.area)}
                  </div>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Crime Type:</strong> {predictionData.crimeType}
                  </div>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Risk Level:</strong>
                    <span style={{
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      marginLeft: "5px",
                      backgroundColor: predictionData.riskLevel === 'High' ? '#fee2e2' : predictionData.riskLevel === 'Medium' ? '#fef3c7' : '#d1fae5',
                      color: predictionData.riskLevel === 'High' ? '#dc2626' : predictionData.riskLevel === 'Medium' ? '#d97706' : '#059669'
                    }}>
                      {predictionData.riskLevel} Risk ({predictionData.riskPercentage}%)
                    </span>
                  </div>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Date:</strong> {new Date(predictionData.date).toLocaleDateString()}
                  </div>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Confidence:</strong> {Math.round((predictionData.confidence || 0.8) * 100)}%
                  </div>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Incidents Found:</strong> {filteredCrimes.length}
                  </div>
                </div>
              </Popup>
            </Marker>
            );
          })()}

          {/* Crime Markers */}
          {filteredCrimes.map((crime, index) => {
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
                    <h4 style={{ margin: "0 0 10px 0", color: "#dc2626" }}>
                      🚨 Crime Incident
                    </h4>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Type:</strong> {crime.crime_type || 'Unknown'}
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Area:</strong> {formatAreaName(crime.area)}
                    </div>

                    {crime.date && (
                      <div style={{ marginBottom: "8px" }}>
                        <strong>Date:</strong> {new Date(crime.date).toLocaleDateString()}
                      </div>
                    )}

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Risk Level:</strong>
                      <span style={{
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        marginLeft: "5px",
                        backgroundColor: getRiskLevel(crime) === 'High' ? '#fee2e2' : getRiskLevel(crime) === 'Medium' ? '#fef3c7' : '#d1fae5',
                        color: getRiskLevel(crime) === 'High' ? '#dc2626' : getRiskLevel(crime) === 'Medium' ? '#d97706' : '#059669'
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