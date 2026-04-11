// src/components/AdvancedCrimeHeatmap.jsx
import { useState, useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import HeatmapLayer from "./HeatMapLayer";
import axios from "axios";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useAuth } from "../contexts/AuthContext_updated";
import { apiService } from "../services/apiService_updated";
import { useSystemSettings } from "../contexts/SystemSettingsContext";

// Fix for default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Calculate crime hotspots with real data
function calculateHotspots(crimes, gridSize = 0.005) {
  const grid = {};

  crimes.forEach(crime => {
    if (!crime.coordinates) return;

    const lat = Math.floor(crime.coordinates[0] / gridSize) * gridSize;
    const lng = Math.floor(crime.coordinates[1] / gridSize) * gridSize;
    const key = `${lat},${lng}`;

    if (!grid[key]) {
      grid[key] = {
        count: 0,
        crimes: [],
        center: [lat + gridSize/2, lng + gridSize/2],
        bounds: [
          [lat, lng],
          [lat + gridSize, lng + gridSize]
        ]
      };
    }
    grid[key].count++;
    grid[key].crimes.push(crime);
  });

  // Get top 20 hotspots
  return Object.values(grid)
    .filter(cell => cell.count > 1) // Only areas with multiple crimes
    .sort((a, b) => b.count - a.count)
    .slice(0, 20);
}

export default function CrimeHeatmap({ isAuthenticated, showLoginModal }) {
  const [crimes, setCrimes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRiskLevel, setSelectedRiskLevel] = useState("all");
  const [bandwidth, setBandwidth] = useState(1.0);
  const [hotspots, setHotspots] = useState([]);
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);
  const [showHotspots, setShowHotspots] = useState(true);

  const { isAuthenticated: authStatus } = useAuth();
  const { settings: systemSettings } = useSystemSettings();

  const fetchCrimes = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getCrimes({ limit: 5000 });
      setCrimes(data);
      setHotspots(calculateHotspots(data));
    } catch (err) {
      console.error("Error fetching crimes:", err);
      setError("Failed to load crime data. Make sure the backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus) {
      fetchCrimes();
    } else {
      setLoading(false);
    }
  }, [authStatus]);

  const getFilteredCrimes = () => {
    return crimes.filter((crime) => {
      if (!crime.coordinates) return false;
      if (selectedRiskLevel === "all") return true;
      return crime.risk_level?.toLowerCase() === selectedRiskLevel.toLowerCase();
    });
  };

  const filteredCrimes = getFilteredCrimes();
  const filteredHotspots = hotspots.filter(hotspot =>
    selectedRiskLevel === "all" ||
    hotspot.crimes.some(crime => crime.risk_level?.toLowerCase() === selectedRiskLevel.toLowerCase())
  );

  // Show login prompt if not authenticated
  if (!authStatus) {
    return (
      <div style={{
        padding: "60px 40px",
        textAlign: "center",
        backgroundColor: "#f8fafc",
        borderRadius: "16px",
        margin: "20px 0",
        border: "2px solid #e2e8f0",
        boxShadow: "0 10px 40px rgba(0,0,0,0.1)"
      }}>
        <div style={{
          fontSize: "48px",
          marginBottom: "20px",
          opacity: "0.6"
        }}>
          🔒
        </div>
        <h3 style={{
          margin: "0 0 16px 0",
          color: "#374151",
          fontSize: "24px"
        }}>
          Crime Data Access Restricted
        </h3>
        <p style={{
          margin: "0 0 24px 0",
          color: "#6b7280",
          fontSize: "16px",
          lineHeight: "1.6"
        }}>
          Sign in to view detailed crime mapping, heatmaps, and risk analysis for different areas.
          Access to real-time crime data helps you make informed safety decisions.
        </p>
        <button
          onClick={showLoginModal}
          style={{
            padding: "14px 28px",
            background: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
            color: "white",
            border: "none",
            borderRadius: "8px",
            fontSize: "16px",
            fontWeight: "600",
            cursor: "pointer",
            transition: "all 0.2s ease"
          }}
          onMouseOver={(e) => {
            e.target.style.background = "linear-gradient(135deg, #2563eb, #1e40af)";
            e.target.style.transform = "translateY(-1px)";
          }}
          onMouseOut={(e) => {
            e.target.style.background = "linear-gradient(135deg, #3b82f6, #1d4ed8)";
            e.target.style.transform = "translateY(0)";
          }}
        >
          Sign In to View Crime Data
        </button>

        <div style={{
          marginTop: "24px",
          padding: "16px",
          backgroundColor: "#eff6ff",
          borderRadius: "8px",
          border: "1px solid #bfdbfe"
        }}>
          <h4 style={{
            margin: "0 0 12px 0",
            color: "#1e40af",
            fontSize: "16px"
          }}>
            🔍 What you'll get access to:
          </h4>
          <ul style={{
            margin: "0",
            paddingLeft: "20px",
            color: "#3730a3",
            textAlign: "left"
          }}>
            <li>Real-time crime heatmaps</li>
            <li>Interactive crime markers</li>
            <li>Risk level analysis</li>
            <li>Historical crime data</li>
            <li>Area-specific safety insights</li>
          </ul>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center", fontSize: "18px", color: "#374151", backgroundColor: "#f8fafc", borderRadius: "12px", margin: "20px" }}>
        <div style={{ marginBottom: "20px" }}>🔄 Loading crime data...</div>
        <div style={{ fontSize: "14px", color: "#6b7280" }}>Performing spatial analysis...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#dc2626", backgroundColor: "#fef2f2", borderRadius: "12px", margin: "20px" }}>
        <div style={{ fontSize: "18px", marginBottom: "15px" }}>❌ {error}</div>
        <button onClick={fetchCrimes} style={{ padding: "10px 20px", backgroundColor: "#dc2626", color: "white", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "14px" }}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "80vh", position: "relative", backgroundColor: "#f8fafc", borderRadius: "16px", overflow: "hidden", boxShadow: "0 10px 40px rgba(0,0,0,0.1)", margin: "20px 0", border: "2px solid #e2e8f0" }}>

      {/* Collapsible Control Panel */}
      <div style={{ position: "absolute", top: "20px", left: "20px", zIndex: 1000, background: "white", padding: isPanelCollapsed ? "10px" : "20px", borderRadius: "12px", boxShadow: "0 4px 20px rgba(0,0,0,0.15)", maxWidth: isPanelCollapsed ? "60px" : "300px", transition: "all 0.3s ease" }}>

        {!isPanelCollapsed ? (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
              <h4 style={{ margin: 0, color: "#1f2937", fontSize: "16px" }}>📊 Crime Heatmap</h4>
              <button onClick={() => setIsPanelCollapsed(true)} style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#6b7280" }}>×</button>
            </div>

            {/* Bandwidth Control */}
            <div style={{ marginBottom: "15px" }}>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: "500", color: "#374151" }}>
                Heat Intensity: {bandwidth} km
              </label>
              <input
                type="range"
                min="0.5"
                max="3.0"
                step="0.1"
                value={bandwidth}
                onChange={(e) => setBandwidth(parseFloat(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>

            {/* Risk Level Filter */}
            <div style={{ marginBottom: "15px" }}>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: "500", color: "#374151" }}>
                Risk Level:
              </label>
              <select
                value={selectedRiskLevel}
                onChange={(e) => setSelectedRiskLevel(e.target.value)}
                style={{ width: "100%", padding: "8px", border: "1px solid #d1d5db", borderRadius: "6px", fontSize: "14px" }}
              >
                <option value="all">All Risks</option>
                <option value="low">Low Risk</option>
                <option value="medium">Medium Risk</option>
                <option value="high">High Risk</option>
              </select>
            </div>

            {/* Hotspots Toggle */}
            <div style={{ marginBottom: "15px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={showHotspots}
                  onChange={(e) => setShowHotspots(e.target.checked)}
                  style={{ cursor: "pointer" }}
                />
                <span style={{ fontSize: "14px" }}>Show Hotspots</span>
              </label>
            </div>

            {/* Statistics */}
            <div style={{ padding: "12px", backgroundColor: "#f1f5f9", borderRadius: "8px", fontSize: "13px", marginBottom: "15px" }}>
              <div style={{ marginBottom: "6px" }}><strong>Total Crimes:</strong> {crimes.length}</div>
              <div style={{ marginBottom: "6px" }}><strong>Filtered:</strong> {filteredCrimes.length}</div>
              <div style={{ marginBottom: "6px" }}><strong>Hotspots:</strong> {filteredHotspots.length}</div>
              <div style={{ color: "#6366f1", fontWeight: "bold", fontSize: "12px" }}>HEATMAP ANALYSIS</div>
            </div>

            {/* Legend */}
            <div style={{ padding: "10px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #e5e7eb" }}>
              <h5 style={{ margin: "0 0 8px 0", fontSize: "12px", color: "#374151" }}>Heat Intensity</h5>
              <div style={{ background: "linear-gradient(90deg, blue, cyan, lime, yellow, orange, red)", height: "15px", borderRadius: "3px", marginBottom: "6px" }}></div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#6b7280" }}>
                <span>Low</span>
                <span>High</span>
              </div>
            </div>
          </>
        ) : (
          <button onClick={() => setIsPanelCollapsed(false)} style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: "#3b82f6", width: "40px", height: "40px" }}>⚙️</button>
        )}
      </div>

      {/* Map */}
      <MapContainer
        center={[31.5204, 74.3587]}
        zoom={systemSettings?.default_map_zoom || 12}
        style={{ width: "100%", height: "100%" }}
        scrollWheelZoom={true}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />

        {/* Heatmap Layer */}
        <HeatmapLayer
          points={filteredCrimes.map((c) => ({
            lat: c.coordinates[0],
            lng: c.coordinates[1],
            intensity: 1,
          }))}
          radius={bandwidth * 25}
          blur={bandwidth * 15}
        />

        {/* Hotspot markers with accurate crime data */}
        {showHotspots && filteredHotspots.map((hotspot, i) => (
          <Marker
            key={i}
            position={hotspot.center}
            icon={L.divIcon({
              className: "hotspot-icon",
              html: `<div style="width:${Math.min(8 + hotspot.count, 20)}px;height:${Math.min(8 + hotspot.count, 20)}px;background:rgba(255,0,0,0.7);border-radius:50%;border:2px solid white;box-shadow:0 0 10px rgba(255,0,0,0.5);"></div>`,
            })}
          >
            <Popup>
              <div style={{ padding: "15px", minWidth: "250px", maxWidth: "300px" }}>
                <h4 style={{ margin: "0 0 12px 0", color: "#dc2626", borderBottom: "2px solid #e5e7eb", paddingBottom: "8px" }}>
                  🔥 Crime Hotspot
                </h4>

                <div style={{ marginBottom: "12px" }}>
                  <strong>Total Crimes:</strong> {hotspot.count} incidents<br/>
                  <strong>Area:</strong> ~500m radius<br/>
                  <strong>Location:</strong> {hotspot.center[0].toFixed(4)}, {hotspot.center[1].toFixed(4)}
                </div>

                <div style={{ backgroundColor: "#f8fafc", padding: "10px", borderRadius: "6px", marginBottom: "10px" }}>
                  <strong>Crime Types:</strong>
                  <div style={{ marginTop: "8px" }}>
                    {Array.from(new Set(hotspot.crimes.map(c => c.type))).slice(0, 5).map((type, i) => (
                      <span key={i} style={{
                        display: "inline-block",
                        backgroundColor: "#e5e7eb",
                        padding: "4px 8px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        margin: "2px",
                        color: "#374151"
                      }}>
                        {type}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ fontSize: "11px", color: "#6b7280" }}>
                  📍 Based on {hotspot.count} crime reports in this area
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
