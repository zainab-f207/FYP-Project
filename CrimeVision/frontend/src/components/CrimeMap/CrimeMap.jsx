// src/components/CrimeMap/CrimeMap.js
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
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

const CrimeMap = ({ showLoginModal, isAuthenticated }) => {
  const [crimes, setCrimes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(100);
  const [selectedCrimeType, setSelectedCrimeType] = useState('all');

  useEffect(() => {
    fetchCrimes();
  }, [limit, selectedCrimeType]);

  const fetchCrimes = async () => {
    try {
      setLoading(true);
      setError(null);

      const filters = {
        limit: limit,
        crime_type: selectedCrimeType !== 'all' ? selectedCrimeType : undefined
      };

      const data = await apiService.getCrimes(filters);
      setCrimes(data);
    } catch (err) {
      console.error("Error fetching crimes:", err);
      setError("Failed to load crime data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getFilteredCrimes = () => {
    return crimes.filter(crime => crime.coordinates && crime.coordinates.length === 2);
  };

  const filteredCrimes = getFilteredCrimes();

  // Create custom red marker icon
  const createRedIcon = (crimeCount = 1) => {
    const size = Math.min(20 + crimeCount * 2, 40); // Size based on crime count
    return L.divIcon({
      className: "crime-marker",
      html: `<div style="
        width: ${size}px;
        height: ${size}px;
        background: radial-gradient(circle, #ff4444, #cc0000);
        border: 3px solid #ffffff;
        border-radius: 50%;
        box-shadow: 0 2px 10px rgba(255, 68, 68, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${size > 25 ? '12px' : '10px'};
      ">${crimeCount > 1 ? crimeCount : ''}</div>`,
      iconSize: [size, size],
      iconAnchor: [size/2, size/2],
      popupAnchor: [0, -size/2]
    });
  };

  if (loading) {
    return (
      <section className="crime-map section-padding" id="map">
        <div className="section-title">
          <h2>Lahore Crime Overview</h2>
          <p>Loading crime data...</p>
        </div>
        <div style={{ padding: "40px", textAlign: "center", fontSize: "18px", color: "#374151" }}>
          🔄 Loading crime data...
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="crime-map section-padding" id="map">
        <div className="section-title">
          <h2>Lahore Crime Overview</h2>
          <p>Error loading crime data</p>
        </div>
        <div style={{ padding: "40px", textAlign: "center", color: "#dc2626" }}>
          <div style={{ fontSize: "18px", marginBottom: "15px" }}>❌ {error}</div>
          <button onClick={fetchCrimes} style={{ padding: "10px 20px", backgroundColor: "#dc2626", color: "white", border: "none", borderRadius: "6px", cursor: "pointer" }}>
            Try Again
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="crime-map section-padding" id="map">
      <div className="section-title">
        <h2>Lahore Crime Overview</h2>
        <p>View recent crime incidents across the city</p>
      </div>

      <div className="map-container">
        {/* Controls Panel */}
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
              <option value={1000}>1000 crimes</option>
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
              <option value="theft">Theft</option>
              <option value="robbery">Robbery</option>
              <option value="assault">Assault</option>
              <option value="burglary">Burglary</option>
              <option value="snatching">Snatching</option>
            </select>
          </div>

          <div className="stats">
            <div className="stat-item">
              <strong>Total:</strong> {filteredCrimes.length} crimes
            </div>
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

        {/* Map */}
        <div className="map-wrapper">
          <MapContainer
            center={[31.5204, 74.3587]}
            zoom={12}
            style={{ width: "100%", height: "500px" }}
            scrollWheelZoom={true}
            zoomControl={true}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />

            {/* Crime Markers */}
            {filteredCrimes.map((crime, index) => (
              <Marker
                key={`${crime.id}-${index}`}
                position={[crime.coordinates[0], crime.coordinates[1]]}
                icon={createRedIcon(1)}
              >
                <Popup>
                  <div className="crime-popup">
                    <h4 style={{ margin: "0 0 10px 0", color: "#dc2626" }}>
                      🚨 Crime Incident
                    </h4>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Type:</strong> {crime.type || crime.crime_type}
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Area:</strong> {crime.area}
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Date:</strong> {crime.date}
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Risk Level:</strong>
                      <span style={{
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        marginLeft: "5px",
                        backgroundColor: crime.risk_level === 'High' ? '#fee2e2' : crime.risk_level === 'Medium' ? '#fef3c7' : '#d1fae5',
                        color: crime.risk_level === 'High' ? '#dc2626' : crime.risk_level === 'Medium' ? '#d97706' : '#059669'
                      }}>
                        {crime.risk_level}
                      </span>
                    </div>

                    <div style={{ marginBottom: "8px" }}>
                      <strong>Location:</strong> {crime.coordinates[0].toFixed(4)}, {crime.coordinates[1].toFixed(4)}
                    </div>

                    <div style={{ fontSize: "11px", color: "#6b7280", marginTop: "10px", paddingTop: "8px", borderTop: "1px solid #e5e7eb" }}>
                      📍 Click map points for details
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>
    </section>
  );
};

export default CrimeMap;
