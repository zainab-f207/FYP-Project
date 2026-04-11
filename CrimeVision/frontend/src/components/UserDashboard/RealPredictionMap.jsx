// src/components/PredictionMapView/RealPredictionMap.jsx
import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';
import styles from './RealPredictionMap.module.css';

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom prediction markers with your theme colors
const createPredictionIcon = (riskLevel, isHotspot = false) => {
  const colors = {
    High: '#ef4444',    // red-500
    Medium: '#f59e0b',  // amber-500
    Low: '#10b981',     // emerald-500
    Unknown: '#6b7280'  // gray-500
  };

  const color = colors[riskLevel] || colors.Unknown;
  const size = isHotspot ? 40 : 30;
  
  return L.divIcon({
    className: `prediction-marker ${isHotspot ? 'hotspot' : ''}`,
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${isHotspot ? '14px' : '12px'};
      ">
        ${isHotspot ? '🔥' : '📊'}
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2]
  });
};

// Real heatmap layer using leaflet.heat
const HeatLayer = ({ points }) => {
  const map = useMap();
  useEffect(() => {
    if (!points?.length) return;
    const heat = L.heatLayer(points, { radius: 22, blur: 18, maxZoom: 17, max: 1.0 });
    heat.addTo(map);
    return () => heat.remove();
  }, [points, map]);
  return null;
};

// Risk area circles with gradient effects
const RiskArea = ({ center, riskLevel, radius }) => {
  const colors = {
    High: '#ef4444',
    Medium: '#f59e0b',
    Low: '#10b981'
  };

  return (
    <Circle
      center={center}
      radius={radius}
      pathOptions={{
        fillColor: colors[riskLevel],
        fillOpacity: 0.1,
        color: colors[riskLevel],
        opacity: 0.6,
        weight: 2
      }}
    >
      <Tooltip permanent direction="center" className={styles.riskTooltip}>
        {riskLevel} Risk Zone
      </Tooltip>
    </Circle>
  );
};

// Map controller for handling view changes
const MapController = ({ prediction, crimes, areaDetails }) => {
  const map = useMap();

  useEffect(() => {
    if (prediction?.coordinates) {
      // Handle both object and array formats for coordinates
      let lat, lng;
      if (Array.isArray(prediction.coordinates)) {
        [lat, lng] = prediction.coordinates;
      } else if (prediction.coordinates.lat && prediction.coordinates.lng) {
        lat = prediction.coordinates.lat;
        lng = prediction.coordinates.lng;
      }
      
      if (lat && lng) {
        map.setView([lat, lng], 14, {
          animate: true,
          duration: 1.5
        });
      }
    }
  }, [prediction, map]);

  return null;
};

// Heatmap layer simulation (since real heatmap requires more complex setup)
const PredictionHeatmap = ({ crimes, prediction }) => {
  const map = useMap();
  
  useEffect(() => {
    // Simulate heatmap by clustering crimes
    if (crimes.length > 0) {
      const group = new L.FeatureGroup();
      
      crimes.forEach(crime => {
        let position;
        
        // Handle different coordinate formats
        if (crime.coordinates && Array.isArray(crime.coordinates)) {
          position = crime.coordinates;
        } else if (crime.coordinates && crime.coordinates.lat && crime.coordinates.lng) {
          position = [crime.coordinates.lat, crime.coordinates.lng];
        } else if (crime.latitude && crime.longitude) {
          position = [crime.latitude, crime.longitude];
        }
        
        if (position && position.length === 2 && position[0] && position[1]) {
          const circle = L.circle(position, {
            radius: 100,
            fillColor: '#ff0000',
            fillOpacity: 0.2,
            color: '#ff0000',
            opacity: 0.4,
            weight: 1
          });
          group.addLayer(circle);
        }
      });
      
      if (group.getLayers().length > 0) {
        map.addLayer(group);
      }
      
      return () => {
        if (map.hasLayer(group)) {
          map.removeLayer(group);
        }
      };
    }
  }, [crimes, map]);

  return null;
};

const PERIOD_H_BOUNDS = { Morning:[6,11], Afternoon:[12,17], Evening:[18,23], Night:[0,5] };

const getCrimeRecencyColor = (dateStr) => {
  if (!dateStr) return '#94a3b8';
  const months = (Date.now() - new Date(dateStr)) / (1000 * 60 * 60 * 24 * 30);
  if (months <= 6)  return '#dc2626'; // red  — last 6 months
  if (months <= 12) return '#f97316'; // orange — last year
  return '#eab308';                   // yellow — older
};

// Deterministic coordinate jitter — spreads stacked area-centroid markers so all are visible
const getJitter = (id, i, axis) => {
  const seed = id ? Number(id) : (i + 1) * 997;
  const n = Math.abs((seed * (axis === 0 ? 127 : 311) + 49297) % 10000) / 10000;
  return (n - 0.5) * 0.005; // ±0.0025° ≈ ±275 m at Lahore's latitude
};

const RealPredictionMap = ({ prediction, areaDetails, crimes }) => {
  const [mapReady, setMapReady] = useState(false);
  const [filteredCrimes, setFilteredCrimes] = useState([]);
  const [mapStyle, setMapStyle] = useState('streets');
  const [crimeTypeFilter, setCrimeTypeFilter] = useState('all');
  const [hourFrom, setHourFrom] = useState(0);
  const [hourTo, setHourTo]   = useState(23);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const mapRef = useRef();

  // Auto-set time filter from prediction period
  useEffect(() => {
    if (prediction?.timePeriod) {
      const [f, t] = PERIOD_H_BOUNDS[prediction.timePeriod] || [0, 23];
      setHourFrom(f); setHourTo(t);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getCrimeHour = (t) => {
    if (!t) return -1;
    try {
      const s = t.trim();
      if (s.includes('AM') || s.includes('PM')) {
        const [tp, ampm] = s.split(' ');
        const h = parseInt(tp.split(':')[0], 10);
        return ampm === 'PM' ? (h === 12 ? 12 : h + 12) : (h === 12 ? 0 : h);
      }
      return parseInt(s.split(':')[0], 10);
    } catch { return -1; }
  };

  const fmtHour = (h) => {
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 || 12;
    return `${h12}:00 ${ampm}`;
  };

  // Get coordinates in a safe way
  const getCoordinates = () => {
    if (!prediction?.coordinates) return null;
    
    if (Array.isArray(prediction.coordinates)) {
      return prediction.coordinates;
    } else if (prediction.coordinates.lat && prediction.coordinates.lng) {
      return [prediction.coordinates.lat, prediction.coordinates.lng];
    }
    
    return null;
  };

  // Filter and enhance crimes with prediction context
  useEffect(() => {
    if (crimes && prediction) {
      const enhancedCrimes = crimes
        .filter(crime => {
          const isSameArea = crime.area?.toLowerCase().includes(prediction.area.toLowerCase()) ||
                             prediction.area.toLowerCase().includes(crime.area?.toLowerCase() || '');
          if (!isSameArea) return false;
          if (crimeTypeFilter === 'selected' && prediction.crimeType) {
            const ct = (crime.crime_type || '').toLowerCase();
            const pt = prediction.crimeType.toLowerCase();
            return ct.includes(pt) || pt.includes(ct);
          }
          return true;
        })
        .map(crime => ({
          ...crime,
          relevanceScore: calculateRelevance(crime, prediction),
          isHotspot: calculateRelevance(crime, prediction) > 70
        }))
        .sort((a, b) => b.relevanceScore - a.relevanceScore);

      setFilteredCrimes(enhancedCrimes);
    }
  }, [crimes, prediction, crimeTypeFilter]);

  const calculateRelevance = (crime, prediction) => {
    let score = 0;

    // Crime type match (40 points max)
    if (crime.crime_type?.toLowerCase() === prediction.crimeType?.toLowerCase()) {
      score += 40;
    } else if (crime.crime_type?.toLowerCase().includes(prediction.crimeType?.toLowerCase()) ||
               prediction.crimeType?.toLowerCase().includes(crime.crime_type?.toLowerCase())) {
      score += 20;
    }

    // Area match (30 points max)
    if (crime.area?.toLowerCase() === prediction.area?.toLowerCase()) {
      score += 30;
    } else if (crime.area?.toLowerCase().includes(prediction.area?.toLowerCase()) ||
               prediction.area?.toLowerCase().includes(crime.area?.toLowerCase())) {
      score += 15;
    }

    // Temporal relevance (20 points max)
    if (crime.date) {
      const crimeDate = new Date(crime.date);
      const predictionDate = new Date(prediction.date);
      const timeDiff = Math.abs(predictionDate - crimeDate);
      const daysDiff = timeDiff / (1000 * 60 * 60 * 24);
      
      if (daysDiff <= 30) score += 20;
      else if (daysDiff <= 90) score += 10;
      else if (daysDiff <= 180) score += 5;
    }

    // Risk level alignment (10 points max)
    const crimeRisk = crime.risk_level || 'Medium';
    if (crimeRisk === prediction.riskLevel) {
      score += 10;
    }

    return Math.min(score, 100);
  };

  const getTileUrl = (style) => {
    const baseUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const styles = {
      streets: baseUrl,
      satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    };
    return styles[style] || styles.streets;
  };

  const formatAreaName = (name) => {
    if (!name) return 'Unknown Area';
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const coordinates = getCoordinates();

  if (!coordinates) {
    return (
      <div className={styles.mapFallback}>
        <div className={styles.fallbackContent}>
          <i className="fas fa-map-marked-alt"></i>
          <h3>Map Unavailable</h3>
          <p>No geographic data available for {formatAreaName(prediction?.area)}</p>
        </div>
      </div>
    );
  }

  const [lat, lng] = coordinates;

  const timeFilteredCrimes = filteredCrimes.filter(c => {
    const h = getCrimeHour(c.crime_time);
    return h === -1 || (h >= hourFrom && h <= hourTo);
  });

  const heatPoints = timeFilteredCrimes
    .filter(c => c.latitude && c.longitude)
    .map(c => {
      const months = c.date
        ? (Date.now() - new Date(c.date.split(' ')[0])) / (1000 * 60 * 60 * 24 * 30)
        : 999;
      const intensity = months <= 6 ? 1.0 : months <= 12 ? 0.6 : 0.3;
      return [c.latitude, c.longitude, intensity];
    });

  return (
    <div className={styles.realPredictionMap}>
      {/* ── Prediction Summary Panel ── */}
      <div className={styles.predSummaryPanel}>
        <div className={styles.predSummaryLeft}>
          <div className={styles.predSummaryArea}><i className="fas fa-map-marker-alt"></i> {formatAreaName(prediction.area)}</div>
          <div className={styles.predSummaryCrime}><i className="fas fa-shield-alt"></i> {prediction.crimeType}</div>
          <div className={styles.predSummaryDate}>
            <i className="fas fa-calendar"></i> {new Date(prediction.date + 'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}
            {prediction.time && <> · <i className="fas fa-clock"></i> {(() => { const [h,m] = prediction.time.split(':').map(Number); return `${h%12||12}:${String(m||0).padStart(2,'0')} ${h>=12?'PM':'AM'}`; })()}</>}
          </div>
        </div>
        <div className={styles.predSummaryRight}>
          <div className={styles.predSummaryRisk} data-risk={prediction.riskLevel}>
            <span className={styles.predSummaryPct}>{prediction.riskPercentage}%</span>
            <span className={styles.predSummaryLevel}>{prediction.riskLevel} Risk</span>
          </div>
          {prediction.timePeriod && (
            <div className={styles.predSummaryPeriod}>
              {({'Morning':'🌅','Afternoon':'☀️','Evening':'🌆','Night':'🌙'})[prediction.timePeriod]} {prediction.timePeriod}
              {' '}· map filtered to this period
            </div>
          )}
        </div>
      </div>

      {/* Map Controls */}
      <div className={styles.mapControls}>
        <div className={styles.controlGroup}>
          <label>Map Style:</label>
          <select 
            value={mapStyle} 
            onChange={(e) => setMapStyle(e.target.value)}
            className={styles.styleSelect}
          >
            <option value="streets">Streets</option>
            <option value="satellite">Satellite</option>
            <option value="dark">Dark</option>
          </select>
        </div>

        {/* Time filter sliders */}
        <div className={styles.timeSliderWrap}>
          <span className={styles.sliderLabelTitle}>
            <i className="fas fa-clock"></i> Filter by Hour
          </span>
          <div className={styles.sliderRow}>
            <span className={styles.sliderLabel}>From</span>
            <input type="range" min={0} max={23} value={hourFrom} className={styles.timeSlider}
              onChange={e => { const v = +e.target.value; setHourFrom(Math.min(v, hourTo)); }} />
            <span className={styles.sliderValue}>{fmtHour(hourFrom)}</span>
          </div>
          <div className={styles.sliderRow}>
            <span className={styles.sliderLabel}>To</span>
            <input type="range" min={0} max={23} value={hourTo} className={styles.timeSlider}
              onChange={e => { const v = +e.target.value; setHourTo(Math.max(v, hourFrom)); }} />
            <span className={styles.sliderValue}>{fmtHour(hourTo)}</span>
          </div>
        </div>

        <div className={styles.predictionInfo}>
          <div className={styles.riskBadge} data-risk={prediction.riskLevel}>
            {prediction.riskLevel} Risk Area
          </div>
          <div className={styles.stats}>
            {timeFilteredCrimes.length}/{filteredCrimes.length} incidents shown
          </div>
          <div className={styles.mapViewToggle}>
            <button
              className={`${styles.toggleBtn} ${!showHeatmap ? styles.toggleBtnActive : ''}`}
              onClick={() => setShowHeatmap(false)}
            >
              <i className="fas fa-map-pin"></i> Markers
            </button>
            <button
              className={`${styles.toggleBtn} ${showHeatmap ? styles.toggleBtnActive : ''}`}
              onClick={() => setShowHeatmap(true)}
            >
              <i className="fas fa-fire"></i> Heatmap
            </button>
          </div>
          <div className={styles.mapViewToggle}>
            <button
              className={`${styles.toggleBtn} ${crimeTypeFilter === 'selected' ? styles.toggleBtnActive : ''}`}
              onClick={() => setCrimeTypeFilter('selected')}
              title={prediction.crimeType || 'Selected crime type'}
            >
              <i className="fas fa-filter"></i> {prediction.crimeType ? prediction.crimeType.slice(0,18) + (prediction.crimeType.length > 18 ? '…' : '') : 'This Type'}
            </button>
            <button
              className={`${styles.toggleBtn} ${crimeTypeFilter === 'all' ? styles.toggleBtnActive : ''}`}
              onClick={() => setCrimeTypeFilter('all')}
            >
              <i className="fas fa-layer-group"></i> All Crimes
            </button>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <div className={styles.mapContainer}>
        <MapContainer
          center={[lat, lng]}
          zoom={14}
          style={{ height: '600px', width: '100%' }}
          zoomControl={true}
          ref={mapRef}
          whenReady={() => setMapReady(true)}
        >
          <TileLayer
            url={getTileUrl(mapStyle)}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />

          <MapController 
            prediction={prediction} 
            crimes={filteredCrimes}
            areaDetails={areaDetails}
          />

          {/* Prediction Risk Zone */}
          <RiskArea 
            center={[lat, lng]}
            riskLevel={prediction.riskLevel}
            radius={500} // 500 meter radius
          />

          {/* Prediction Center Marker */}
          <Marker
            position={[lat, lng]}
            icon={createPredictionIcon(prediction.riskLevel, true)}
          >
            <Popup>
              <div className={styles.predictionPopup}>
                <h4>🎯 AI Risk Prediction</h4>
                <div className={styles.popupContent}>
                  <div className={styles.popupItem}>
                    <strong>Area:</strong> {formatAreaName(prediction.area)}
                  </div>
                  <div className={styles.popupItem}>
                    <strong>Crime Type:</strong> {prediction.crimeType}
                  </div>
                  <div className={styles.popupItem}>
                    <strong>Risk Level:</strong> 
                    <span className={styles.riskLevel} data-risk={prediction.riskLevel}>
                      {prediction.riskLevel}
                    </span>
                  </div>
                  <div className={styles.popupItem}>
                    <strong>Probability:</strong> {prediction.riskPercentage}%
                  </div>
                  <div className={styles.popupItem}>
                    <strong>Confidence:</strong> {Math.round(prediction.confidence * 100)}%
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>

          {/* Historical Crime Markers (recency-colored, jittered) */}
          {!showHeatmap && timeFilteredCrimes.map((crime, index) => {
            let position;
            if (crime.coordinates && Array.isArray(crime.coordinates)) {
              position = crime.coordinates;
            } else if (crime.coordinates?.lat && crime.coordinates?.lng) {
              position = [crime.coordinates.lat, crime.coordinates.lng];
            } else if (crime.latitude && crime.longitude) {
              position = [crime.latitude, crime.longitude];
            }
            if (!position || position.length !== 2 || !position[0] || !position[1]) return null;

            const color        = getCrimeRecencyColor(crime.date);
            const mths         = crime.date ? (Date.now() - new Date(crime.date)) / (1000*60*60*24*30) : 999;
            const recencyLabel = mths <= 6 ? 'Last 6 months' : mths <= 12 ? 'Last 12 months' : 'Older than 1 year';
            const locationStr  = crime.area_translit || (crime.area ? formatAreaName(crime.area) : 'Unknown Location');
            const jLat = position[0] + getJitter(crime.id, index, 0);
            const jLng = position[1] + getJitter(crime.id, index, 1);
            const crimeIcon = L.divIcon({
              html: `<div style="background:${color};width:16px;height:16px;border-radius:50%;border:2.5px solid rgba(255,255,255,0.95);box-shadow:0 2px 8px rgba(0,0,0,.6),0 0 0 3px ${color}44"></div>`,
              className: '', iconSize: [16, 16], iconAnchor: [8, 8],
            });
            return (
              <Marker key={`crime-${crime.id || index}`} position={[jLat, jLng]} icon={crimeIcon}>
                <Popup className="crime-fir-popup">
                  <div style={{ fontFamily: "'Segoe UI', Arial, sans-serif", minWidth: 230, maxWidth: 280, overflow: 'hidden' }}>
                    <div style={{ background: color, padding: '9px 13px 8px', color: '#fff' }}>
                      <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.35 }}>{crime.crime_type || 'FIR Record'}</div>
                      <div style={{ fontSize: 10, opacity: 0.82, marginTop: 2 }}>Historical Crime Record</div>
                    </div>
                    <div style={{ padding: '10px 13px 12px', background: '#fff' }}>
                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>📍 Location</div>
                        <div style={{ fontSize: 12.5, color: '#111827', fontWeight: 600, lineHeight: 1.4 }}>{locationStr}</div>
                      </div>
                      {crime.date && (
                        <div style={{ fontSize: 12, color: '#374151', marginBottom: 9, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ color: '#6b7280' }}>📅</span>
                          <span>{crime.date.split(' ')[0]}</span>
                          {crime.crime_time && <><span style={{ color: '#e5e7eb', margin: '0 3px' }}>|</span><span style={{ color: '#6b7280' }}>🕐</span><span>{crime.crime_time}</span></>}
                        </div>
                      )}
                      <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontSize: 10.5, fontWeight: 700, background: color + '18', color: color, border: `1px solid ${color}55` }}>{recencyLabel}</span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Real Heatmap (leaflet.heat) */}
          {showHeatmap && <HeatLayer points={heatPoints} />}
        </MapContainer>
      </div>

      {/* Map Legend */}
      <div className={styles.mapLegend}>
        <div className={styles.legendTitle}>Map Legend</div>
        <div className={styles.legendItems}>
          <div className={styles.legendItem}>
            <div className={`${styles.legendMarker} ${styles.hotspot}`}></div>
            <span>Prediction Zone</span>
          </div>
          {!showHeatmap && (
            <>
              <div className={styles.legendItem}>
                <div className={styles.legendMarker} style={{background:'#dc2626'}}></div>
                <span>Last 6 months</span>
              </div>
              <div className={styles.legendItem}>
                <div className={styles.legendMarker} style={{background:'#f97316'}}></div>
                <span>Last 12 months</span>
              </div>
              <div className={styles.legendItem}>
                <div className={styles.legendMarker} style={{background:'#eab308'}}></div>
                <span>Older than 1 year</span>
              </div>
            </>
          )}
          <div className={styles.legendItem}>
            <div className={styles.riskZone}></div>
            <span>Risk Zone (500 m)</span>
          </div>
          {showHeatmap && (
            <div className={styles.legendItem} style={{ marginLeft: 'auto', fontWeight: 600, color: '#f59e0b' }}>
              <i className="fas fa-fire" style={{ marginRight: 4 }}></i>
              Heatmap: crime density
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RealPredictionMap;
