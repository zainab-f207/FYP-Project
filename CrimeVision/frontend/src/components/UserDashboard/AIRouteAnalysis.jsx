// AI Route Analysis & Comparison System - COMPLETE VERSION
// Features: Manual placement, draggable markers, multiple routes, popups

import React, { useState, useEffect, useRef } from "react";
import styles from "./AIRouteAnalysis.module.css";
import AIRouteMap from "./AIRouteMap";
import apiService from "../../services/apiService";

const AIRouteAnalysis = ({ userLocation, initialDestination = null }) => {
  const [startLocation, setStartLocation] = useState("");
  const [destination, setDestination] = useState("");
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [startPosition, setStartPosition] = useState(null);
  const [destPosition, setDestPosition] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("");
  const [routeError, setRouteError] = useState(null); // { type: 'error'|'warning', title, message }
  const [placementMode, setPlacementMode] = useState(null); // 'start' or 'destination'
  const [travelDate, setTravelDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [travelTime, setTravelTime] = useState(() => {
    const now = new Date();
    return `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  });
  // Per-card expansion state so "+N more" can toggle to show every chip
  const [expandedAreas, setExpandedAreas] = useState({});
  const [expandedCrimes, setExpandedCrimes] = useState({});

  const toggleExpanded = (which, key) => (e) => {
    // Don't bubble to the card's onClick (that selects the route)
    e.stopPropagation();
    const setter = which === 'areas' ? setExpandedAreas : setExpandedCrimes;
    setter(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Initialize start location from user location
  useEffect(() => {
    if (userLocation?.lat && userLocation?.lng) {
      setStartPosition(userLocation);
      reverseGeocode(userLocation.lat, userLocation.lng).then((addr) => {
        setStartLocation(addr);
      });
    }
  }, [userLocation]);

  // Handle initialDestination selection from dashboard/email links
  useEffect(() => {
    if (initialDestination) {
      const destName = initialDestination.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      setDestination(destName);
      setAutoAnalyze(true);
      console.log(`✅ Pre-populated destination: ${destName}`);
    }
  }, [initialDestination]);

  // Special effect to auto-analyze when both positions are geocoded
  useEffect(() => {
    if (autoAnalyze && startPosition && destPosition && !loading && !isGeocoding) {
      console.log("⚡ Triggering auto-analysis of route...");
      analyzeRoutes();
      setAutoAnalyze(false);
    }
  }, [autoAnalyze, startPosition, destPosition, loading, isGeocoding]);

  const reverseGeocode = async (lat, lng) => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&accept-language=en`
      );
      const data = await res.json();
      return data.display_name || "Selected Location";
    } catch {
      return "Selected Location";
    }
  };

  const geocodeLocation = async (location) => {
    // Bias Nominatim to the Lahore bounding box. Without this, ambiguous names
    // like "Askari 4" or "DHA Phase 4" resolve to Karachi first, which yields
    // 1000+ km routes that exhaust the public OSRM 25-second timeout.
    // viewbox = lon_min, lat_max, lon_max, lat_min  (left, top, right, bottom)
    const LAHORE_VIEWBOX = "74.05,31.80,74.70,31.30";
    try {
      const params = new URLSearchParams({
        format: "json",
        q: location,
        countrycodes: "pk",
        viewbox: LAHORE_VIEWBOX,
        bounded: "1",
        limit: "1",
        "accept-language": "en",
      });
      let res = await fetch(`https://nominatim.openstreetmap.org/search?${params}`);
      let data = await res.json();
      if (!data?.length) {
        // Fallback: relax the bounding box but still prefer Lahore via viewbox
        // (without `bounded=1`) so we get a Lahore hit if available, otherwise
        // any Pakistan match — better than failing outright.
        const relaxed = new URLSearchParams({
          format: "json",
          q: location,
          countrycodes: "pk",
          viewbox: LAHORE_VIEWBOX,
          limit: "1",
          "accept-language": "en",
        });
        res = await fetch(`https://nominatim.openstreetmap.org/search?${relaxed}`);
        data = await res.json();
      }
      return data?.[0]
        ? { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) }
        : null;
    } catch (error) {
      console.error("Geocoding error:", error);
      return null;
    }
  };

  // Auto-geocode when user types
  useEffect(() => {
    if (startLocation && startLocation.length > 3 && !startLocation.includes("Selected Location")) {
      setIsGeocoding(true);
      const timer = setTimeout(() => {
        geocodeLocation(startLocation).then((coords) => {
          if (coords) setStartPosition(coords);
          setIsGeocoding(false);
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [startLocation]);

  useEffect(() => {
    if (destination && destination.length > 3) {
      setIsGeocoding(true);
      const timer = setTimeout(() => {
        geocodeLocation(destination).then((coords) => {
          if (coords) setDestPosition(coords);
          setIsGeocoding(false);
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [destination]);

  // Handle map click for manual placement
  const handleMapClick = async (lat, lng) => {
    setIsGeocoding(true);
    if (placementMode === 'start') {
      setStartPosition({ lat, lng });
      const address = await reverseGeocode(lat, lng);
      setStartLocation(address);
      setPlacementMode(null);
    } else if (placementMode === 'destination') {
      setDestPosition({ lat, lng });
      const address = await reverseGeocode(lat, lng);
      setDestination(address);
      setPlacementMode(null);
    }
    setIsGeocoding(false);
  };

  // Handle marker drag
  const handleMarkerDrag = async (type, lat, lng) => {
    setIsGeocoding(true);
    if (type === 'start') {
      setStartPosition({ lat, lng });
      const address = await reverseGeocode(lat, lng);
      setStartLocation(address);
    } else if (type === 'destination') {
      setDestPosition({ lat, lng });
      const address = await reverseGeocode(lat, lng);
      setDestination(address);
    }
    setIsGeocoding(false);
  };

  const analyzeRoutes = async () => {
    // Clear previous routes and errors immediately
    setRoutes([]);
    setSelectedRoute(null);
    setRouteError(null);

    if (!startPosition || !destPosition) {
      setRouteError({
        type: 'warning',
        title: 'Locations required',
        message: 'Please select both a start location and a destination before analysing routes. You can type an address or click 📍 on the map.',
      });
      return;
    }

    setLoading(true);
    setLoadingStatus("Calculating multiple route options...");
    
    try {
      setLoadingStatus("Analyzing routes with AI...");
      
      const baseUrl = apiService.API_BASE_URL || 'http://localhost:8000';
      const params = new URLSearchParams({
        start_lat: startPosition.lat,
        start_lng: startPosition.lng,
        end_lat: destPosition.lat,
        end_lng: destPosition.lng,
        ...(travelDate && { date: travelDate }),
        ...(travelTime && { time: travelTime }),
        ...(startLocation && { start_name: startLocation }),
        ...(destination   && { end_name:   destination   }),
      });
      const response = await fetch(
        `${baseUrl}/api/crimes/compare-routes?${params}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      );

      const is503 = response.status === 503;
      const is500 = response.status === 500;
      if (!response.ok) {
        throw Object.assign(new Error(`Failed to analyze routes: ${response.status}`), { status: response.status });
      }

      const data = await response.json();
      
      console.log("✅ Route analysis complete:", data);
      
      setRoutes(data.routes || []);
      setSelectedRoute(data.recommendation);
      setLoadingStatus("");
      
    } catch (error) {
      console.error("❌ Error analyzing routes:", error);
      const is500 = error.message?.includes('500') || error.status === 500;
      const is503 = error.message?.includes('503') || error.status === 503;
      setRouteError({
        type: 'error',
        title: is503
          ? 'Routing service unavailable'
          : is500
          ? 'Server error — analysis failed'
          : 'Could not analyse routes',
        message: is503
          ? 'The routing service (OSRM) is taking too long to respond. This is a temporary issue with the external service. Please wait a few seconds and try again.'
          : is500
          ? 'The AI route analysis service returned an internal error. This usually happens when the geocoding service is temporarily unavailable. Please wait a few seconds and try again.'
          : error.message || 'An unexpected error occurred. Please check your connection and try again.',
      });
      setLoadingStatus("");
    } finally {
      setLoading(false);
    }
  };

  const getRouteColor = (label) => {
    const l = label?.toLowerCase() || '';
    if (l === 'safest')       return '#22c55e'; // Green
    if (l === 'fastest')      return '#3b82f6'; // Blue
    if (l === 'shortest')     return '#f59e0b'; // Amber
    if (l === 'balanced')     return '#a855f7'; // Purple
    if (l === 'fastest_alt')  return '#60a5fa'; // Light blue
    if (l === 'shortest_alt') return '#fcd34d'; // Light amber
    return '#64748b';                           // Slate-gray for alternative
  };

  const getRouteBestFor = (route) => {
    const l = route.label?.toLowerCase() || '';
    if (l === 'safest') {
      const extras = route.secondary_labels || [];
      if (extras.includes('fastest') && extras.includes('shortest'))
        return 'Best overall — lowest risk, shortest distance & fastest time';
      if (extras.includes('fastest'))
        return 'Lowest crime risk & fastest travel time';
      if (extras.includes('shortest'))
        return 'Lowest crime risk & shortest distance';
      return 'Optimised for lowest predicted crime risk';
    }
    if (l === 'fastest')      return 'Fastest travel time among all route options';
    if (l === 'shortest')     return 'Shortest total distance among all route options';
    if (l === 'fastest_alt')  return 'Fastest time among alternative routes';
    if (l === 'shortest_alt') return 'Shortest distance among alternative routes';
    if (l === 'alternative') return route.alt_via ? `Via ${route.alt_via} — alternative path` : 'Alternative route';
    return 'Alternative route';
  };

  const getRouteIcon = (label) => {
    const l = label?.toLowerCase() || '';
    if (l === 'safest')       return '🛡️';
    if (l === 'fastest')      return '⚡';
    if (l === 'shortest')     return '🛣️';
    if (l === 'fastest_alt')  return '⚡';
    if (l === 'shortest_alt') return '🛣️';
    if (l === 'alternative')  return '🔀';
    return '🗺️';
  };

  const getSafetyBadge = (score) => {
    if (score >= 80) return { text: 'Very Safe', color: '#10b981', icon: '✅' };
    if (score >= 60) return { text: 'Safe', color: '#3b82f6', icon: '✓' };
    if (score >= 40) return { text: 'Moderate', color: '#f59e0b', icon: '⚠️' };
    return { text: 'Risky', color: '#ef4444', icon: '⚠️' };
  };

  const formatTravelDateTime = () => {
    if (!travelDate || !travelTime) return '';
    try {
      const dt = new Date(`${travelDate}T${travelTime}:00`);
      return dt.toLocaleString('en-PK', {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: 'numeric', minute: '2-digit',
      });
    } catch {
      return `${travelDate} ${travelTime}`;
    }
  };

  return (
    <div className={styles.aiRouteAnalysis}>
      {/* Input Section */}
      <div className={styles.inputSection}>
        <h2>🤖 AI-Powered Route Analysis</h2>
        <p className={styles.subtitle}>
          Compare routes with AI-based safety predictions using historical crime patterns • Click map to set markers
        </p>

        <div className={styles.inputGroup}>
          <div className={styles.inputWithIcon}>
            <i className="fas fa-location-arrow"></i>
            <input
              type="text"
              placeholder="Start location (or click map)"
              value={startLocation}
              onChange={(e) => setStartLocation(e.target.value)}
              className={styles.input}
            />
            <button
              className={styles.mapPlaceBtn}
              onClick={() => setPlacementMode(placementMode === 'start' ? null : 'start')}
              title="Click map to set start location"
            >
              {placementMode === 'start' ? '✓' : '📍'}
            </button>
          </div>
          <div className={styles.inputWithIcon}>
            <i className="fas fa-flag"></i>
            <input
              type="text"
              placeholder="Destination (or click map)"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className={styles.input}
            />
            <button
              className={styles.mapPlaceBtn}
              onClick={() => setPlacementMode(placementMode === 'destination' ? null : 'destination')}
              title="Click map to set destination"
            >
              {placementMode === 'destination' ? '✓' : '🏁'}
            </button>
          </div>
        </div>

        {placementMode && (
          <div className={styles.placementHint}>
            <i className="fas fa-hand-pointer"></i>
            Click on the map to set {placementMode === 'start' ? 'start' : 'destination'} location
          </div>
        )}

        {/* Travel date & time */}
        <div className={styles.travelTimeRow}>
          <div className={styles.timeField}>
            <i className="fas fa-calendar-alt"></i>
            <label>Date</label>
            <input
              type="date"
              value={travelDate}
              onChange={e => setTravelDate(e.target.value)}
              className={styles.timeInput}
            />
          </div>
          <div className={styles.timeField}>
            <i className="fas fa-clock"></i>
            <label>Departure</label>
            <input
              type="time"
              value={travelTime}
              onChange={e => setTravelTime(e.target.value)}
              className={styles.timeInput}
            />
          </div>
          {travelTime && (() => {
            const h = parseInt(travelTime.split(':')[0]);
            if (h >= 20 || h < 6) return <span className={styles.nightBadge}>🌙 Night travel — historical patterns show higher incident rates after hours</span>;
            if (h >= 17) return <span className={styles.eveningBadge}>🌆 Evening — moderately elevated crime patterns at dusk</span>;
            return <span className={styles.dayBadge}>☀️ Daytime — standard risk assessment</span>;
          })()}
        </div>

        <button
          className={`${styles.analyzeBtn} ${loading || isGeocoding ? styles.loading : ''}`}
          onClick={analyzeRoutes}
          disabled={loading || isGeocoding || !startPosition || !destPosition}
        >
          {loading ? (
            <>
              <div className={styles.spinner}></div>
              {loadingStatus || "Analyzing..."}
            </>
          ) : isGeocoding ? (
            <>
              <div className={styles.spinner}></div>
              Locating...
            </>
          ) : (
            <>
              <i className="fas fa-brain"></i> Analyze Routes with AI
            </>
          )}
        </button>
      </div>

      {/* Error / warning alert card */}
      {routeError && (
        <div className={`${styles.alert} ${styles[routeError.type === 'warning' ? 'medium' : 'high']}`}>
          <div className={styles.alertItem}>
            <strong>
              {routeError.type === 'warning' ? '⚠️' : '❌'} {routeError.title}
            </strong>
            <p>{routeError.message}</p>
            <small>
              <button
                onClick={() => setRouteError(null)}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', textDecoration: 'underline', padding: 0, fontSize: 'inherit' }}
              >
                Dismiss
              </button>
            </small>
          </div>
        </div>
      )}

      {/* Map Display - Always visible for manual placement */}
      <AIRouteMap
        routes={routes}
        selectedRoute={selectedRoute}
        startPosition={startPosition}
        destPosition={destPosition}
        onRouteSelect={setSelectedRoute}
        onMapClick={handleMapClick}
        onMarkerDrag={handleMarkerDrag}
        placementMode={placementMode}
        startLocationName={startLocation}
        destLocationName={destination}
      />

      {/* Route Comparison */}
      {routes.length > 0 && (
        <div className={styles.comparisonSection}>
          <div className={styles.comparisonHeader}>
            <div className={styles.comparisonTitleRow}>
              <span className={styles.comparisonIcon}>📊</span>
              <h3>Route Comparison</h3>
            </div>
            <div className={styles.analysisContext}>
              <span>📅 {new Date(travelDate + 'T12:00:00').toLocaleDateString('en-PK', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>
              <span className={styles.contextDot}>•</span>
              <span>🕐 {travelTime}</span>
            </div>
          </div>
          <div className={styles.routeCards}>
            {routes.map((route, index) => {
              const safety = getSafetyBadge(route.safety_analysis.overall_score);
              const isSelected = selectedRoute?.route_type === route.route_type;
              
              return (
                <div
                  key={index}
                  className={`${styles.routeCard} ${isSelected ? styles.selected : ''}`}
                  onClick={() => setSelectedRoute(route)}
                  style={{
                    '--rc': getRouteColor(route.label),
                    boxShadow: isSelected ? `0 0 32px ${getRouteColor(route.label)}33, 0 8px 24px rgba(0,0,0,0.5)` : 'none'
                  }}
                >
                  <div className={styles.routeHeader}>
                    <div className={styles.routeLabelPill} style={{ background: `${getRouteColor(route.label)}22`, border: `1px solid ${getRouteColor(route.label)}55`, color: getRouteColor(route.label) }}>
                      <span>{getRouteIcon(route.label)}</span>
                      <span>{
                        route.label === 'fastest_alt'  ? 'FASTEST ALT' :
                        route.label === 'shortest_alt' ? 'SHORTEST ALT' :
                        route.label === 'alternative'
                          ? (route.alt_via ? `VIA ${route.alt_via.toUpperCase()}` : `ROUTE ${route.alt_index || ''}`)
                          : (route.label?.toUpperCase() || 'ROUTE')
                      }</span>
                    </div>
                    {route.secondary_labels?.length > 0 && route.secondary_labels.map(sl => (
                      <span key={sl} className={styles.secondaryLabelChip}>
                        Also {sl.charAt(0).toUpperCase() + sl.slice(1)}
                      </span>
                    ))}
                    {route.label === 'safest' && (
                      <span className={styles.recommendedBadge}>⭐ RECOMMENDED</span>
                    )}
                  </div>
                  <div className={styles.routeObjective}>
                    {getRouteBestFor(route)}
                  </div>

                  <div className={styles.routeStats}>
                    <div className={styles.stat}>
                      <i className="fas fa-road"></i>
                      <span style={{ color: 'white' }}>{route.route_data.distance_km} km</span>
                    </div>
                    <div className={styles.stat}>
                      <i className="fas fa-clock"></i>
                      <span style={{ color: 'white' }}>
                        {route.route_data.duration_min_traffic ?? route.route_data.duration_min} min
                        {route.route_data.traffic_multiplier > 1 && (
                          <span className={styles.trafficNote}> (incl. traffic)</span>
                        )}
                      </span>
                    </div>
                    {route.route_data.traffic_multiplier > 1 && (
                      <div className={styles.stat}>
                        <i className="fas fa-traffic-light"></i>
                        <span style={{ color: '#f59e0b' }}>
                          {route.route_data.traffic_multiplier >= 1.4 ? '🚦 Heavy' :
                           route.route_data.traffic_multiplier >= 1.2 ? '🟡 Moderate' : '🟢 Light'} traffic
                        </span>
                      </div>
                    )}
                  </div>

                  <div className={styles.safetyScore}>
                    <div className={styles.scoreCircle} style={{ borderColor: safety.color }}>
                      <span style={{ color: safety.color }}>
                        {route.safety_analysis.overall_score}%
                      </span>
                    </div>
                    <div className={styles.safetyInfo}>
                      <span style={{ color: safety.color }}>
                        {safety.icon} {safety.text}
                      </span>
                      <small style={{ color: 'rgba(167,139,250,0.95)', fontWeight: 500 }}>
                        🤖 AI prediction for {formatTravelDateTime()}
                      </small>
                      <small style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {route.safety_analysis.summary.high_risk_points} high-risk points
                      </small>
                    </div>
                  </div>

                  {route.safety_analysis.alerts.length > 0 && (
                    <div className={styles.alerts}>
                      {route.safety_analysis.alerts.slice(0, 2).map((alert, i) => (
                        <div key={i} className={`${styles.alert} ${styles[alert.severity]}`}>
                          <small>{alert.description}</small>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Areas the route passes through */}
                  {route.areas_along_route?.length > 0 && (() => {
                    const cardKey = route.route_type || `idx_${index}`;
                    const showAll = !!expandedAreas[cardKey];
                    const visible = showAll ? route.areas_along_route : route.areas_along_route.slice(0, 4);
                    const extra = route.areas_along_route.length - 4;
                    return (
                      <div className={styles.areasRow}>
                        <small className={styles.areasLabel}><i className="fas fa-map-marker-alt"></i> Route passes through:</small>
                        <div className={styles.areaChips}>
                          {visible.map((a, i) => (
                            <span key={i} className={styles.areaChip}>{a}</span>
                          ))}
                          {extra > 0 && (
                            <button
                              type="button"
                              className={styles.areaChipMore}
                              onClick={toggleExpanded('areas', cardKey)}
                            >
                              {showAll ? '− show less' : `+${extra} more`}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Crime types detected along route — with per-area attribution */}
                  {route.crime_types_detected?.length > 0 && (() => {
                    const cardKey = route.route_type || `idx_${index}`;
                    const showAll = !!expandedCrimes[cardKey];
                    const visible = showAll ? route.crime_types_detected : route.crime_types_detected.slice(0, 3);
                    const extra = route.crime_types_detected.length - 3;
                    return (
                      <div className={styles.crimeTypesRow}>
                        <small className={styles.crimeTypesLabel}><i className="fas fa-exclamation-triangle"></i> Crimes in path:</small>
                        <div className={styles.crimeChips}>
                          {visible.map((ct, i) => {
                            // Backwards compat: backend may return either a
                            // string (old shape) or {area, crime_type}.
                            const isObj = ct && typeof ct === 'object';
                            const crimeType = isObj ? ct.crime_type : ct;
                            const area      = isObj ? ct.area : null;
                            return (
                              <span key={i} className={styles.crimeChip}>
                                {crimeType}
                                {area && (
                                  <span style={{ opacity: 0.65, marginLeft: 4, fontWeight: 400 }}>
                                    — in {area}
                                  </span>
                                )}
                              </span>
                            );
                          })}
                          {extra > 0 && (
                            <button
                              type="button"
                              className={styles.crimeChipMore}
                              onClick={toggleExpanded('crimes', cardKey)}
                            >
                              {showAll ? '− show less' : `+${extra} more`}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Detailed Analysis */}
      {selectedRoute && (
        <div className={styles.detailedAnalysis}>
          <h3>🔍 Detailed Analysis - {selectedRoute.label?.toUpperCase()}</h3>

          <div style={{
            background: 'rgba(59,130,246,0.08)',
            border: '1px solid rgba(59,130,246,0.25)',
            borderRadius: '8px',
            padding: '10px 14px',
            margin: '0 0 14px 0',
            fontSize: '0.85rem',
            color: 'rgba(255,255,255,0.85)',
            lineHeight: 1.5,
          }}>
            ℹ️ <strong>AI prediction</strong> = risk specifically for your selected travel date &amp; time.{' '}
            <strong>Area baseline</strong> = the area's historical average safety (same number shown on your dashboard).
          </div>

          <div className={styles.analysisGrid}>
            <div className={styles.analysisCard}>
              <h4>📍 Risk Points</h4>
              <div className={styles.riskPoints}>
                {selectedRoute.safety_analysis.point_predictions
                  .filter(p => p.prediction.risk_level !== 'Low')
                  .map((point, i) => {
                    const baseline = selectedRoute.area_baselines?.[point.area];
                    return (
                      <div key={i} className={styles.riskPoint}>
                        <span className={styles.riskLevel} style={{
                          color: point.prediction.risk_level === 'High' ? '#ef4444' : '#f59e0b'
                        }}>
                          {point.prediction.risk_level === 'High' ? '🔴' : '🟠'}
                          {point.area || 'Unknown Area'}
                        </span>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                          <small style={{ color: 'white' }}>
                            🤖 AI: {point.prediction.risk_percentage}% risk
                          </small>
                          {baseline?.safety_score != null && (
                            <small style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.72rem' }}>
                              Area baseline: {baseline.safety_score}% safe
                            </small>
                          )}
                        </div>
                      </div>
                    );
                  })}
                {selectedRoute.safety_analysis.summary.high_risk_points === 0 &&
                 selectedRoute.safety_analysis.summary.medium_risk_points === 0 && (
                  <p className={styles.noRisks}>✅ No significant risk points detected</p>
                )}
              </div>
            </div>

            <div className={styles.analysisCard}>
              <h4 style={{ color: 'white' }}>⚠️ Safety Alerts</h4>
              <div className={styles.alertsList}>
                {selectedRoute.safety_analysis.alerts.map((alert, i) => (
                  <div key={i} className={`${styles.alertItem} ${styles[alert.severity]}`}>
                    <strong style={{ color: 'white' }}>{alert.type}</strong>
                    <p style={{ color: 'rgba(255,255,255,0.9)' }}>{alert.description}</p>
                    <small style={{ color: 'rgba(255,255,255,0.6)' }}>Location: {alert.location}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIRouteAnalysis;
