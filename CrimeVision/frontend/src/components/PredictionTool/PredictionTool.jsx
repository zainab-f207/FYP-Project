import React, { useState, useEffect, useRef } from 'react';
import './PredictionTool.css';
import apiService from '../../services/api';
import { MapContainer, TileLayer, Circle, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

// Fix default leaflet icon paths broken by Webpack/Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const riskDescriptions = {
  Low: {
    description: "Historical data indicates a relatively low likelihood of this crime occurring in the selected area and time.",
    precautions: [
      "Stay aware of your surroundings.",
      "Keep your valuables secure.",
      "Report any suspicious activity.",
      "Follow normal safety precautions."
    ],
    color: "#22c55e", icon: "✅"
  },
  Medium: {
    description: "Historical data suggests a moderate likelihood of this type of crime occurring in the selected area and time.",
    precautions: [
      "Stay in well-lit areas after dark.",
      "Avoid walking alone at night.",
      "Keep valuables out of sight.",
      "Remain aware of your surroundings.",
      "Use trusted transportation services."
    ],
    color: "#f59e0b", icon: "⚠️"
  },
  High: {
    description: "Historical data indicates a higher likelihood of this type of crime occurring in this area during similar time periods.",
    precautions: [
      "Avoid unnecessary travel after dark.",
      "Travel in groups if possible.",
      "Keep emergency contacts handy.",
      "Stay alert and avoid distractions.",
      "Consider alternative routes if possible."
    ],
    color: "#dc2626", icon: "🚨"
  }
};

const TIME_PERIOD_ICONS = {
  Morning: '🌅', Afternoon: '☀️', Evening: '🌆', Night: '🌙',
};

const PERIOD_ORDER = ['Morning', 'Afternoon', 'Evening', 'Night'];

const formatConfidenceLabel = (value) => {
  if (!value) return 'Unknown';
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
};

// Small helper to auto-fit map to the circle marker
function MapFlyTo({ coords }) {
  const map = useMap();
  useEffect(() => { if (coords) map.flyTo(coords, 14, { duration: 1.2 }); }, [coords]);
  return null;
}

// Heatmap layer via leaflet.heat
function HeatLayer({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points?.length) return;
    // L.heatLayer is injected by leaflet.heat side-effect import
    const heat = L.heatLayer(points, { radius: 22, blur: 18, maxZoom: 17, max: 1.0 });
    heat.addTo(map);
    return () => heat.remove();
  }, [points, map]);
  return null;
}

// Deterministic coordinate jitter — spreads stacked area-centroid markers so all are visible
const getJitter = (id, i, axis) => {
  const seed = id ? Number(id) : (i + 1) * 997;
  const n = Math.abs((seed * (axis === 0 ? 127 : 311) + 49297) % 10000) / 10000;
  return (n - 0.5) * 0.005; // ±0.0025° ≈ ±275 m at Lahore's latitude
};

const PredictionTool = ({ selectedArea, selectedCrimeType }) => {
  const [area, setArea]             = useState('');
  const [date, setDate]             = useState('');
  const [time, setTime]             = useState('');
  const [crimeType, setCrimeType]   = useState('');
  const [areas, setAreas]           = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [predicting, setPredicting] = useState(false);

  // Core result
  const [riskPercentage, setRiskPercentage] = useState(0);
  const [riskLevel, setRiskLevel]     = useState('');
  const [riskClass, setRiskClass]     = useState('');
  const [description, setDescription] = useState('');
  const [precautions, setPrecautions] = useState([]);
  const [message, setMessage]         = useState('');
  const [confidence, setConfidence]   = useState(0);
  const [showDetails, setShowDetails] = useState(false);

  // Area Safety Profile state
  const [areaProfile, setAreaProfile]       = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  // Poisson insight fields
  const [timePeriod, setTimePeriod]               = useState(null);
  const [safestDays, setSafestDays]               = useState([]);
  const [riskiestDay, setRiskiestDay]             = useState('');
  const [safestMonths, setSafestMonths]           = useState([]);
  const [safestHours, setSafestHours]             = useState([]);
  const [riskiestHours, setRiskiestHours]         = useState([]);
  const [safestUpcoming, setSafestUpcoming]       = useState([]);
  const [hourlyProfile, setHourlyProfile]         = useState(null);
  const [visitComparison, setVisitComparison]     = useState([]);
  const [areaTrend, setAreaTrend]                 = useState(null);
  const [monthlyCrimeStats, setMonthlyCrimeStats] = useState([]);
  const [datasetStats, setDatasetStats]           = useState(null);

  // Map modal state
  const [showMap, setShowMap]         = useState(false);
  const [areaCoords, setAreaCoords]   = useState(null);
  const [coordsLoading, setCoordsLoading] = useState(false);
  const [nearbyCrimes, setNearbyCrimes]   = useState([]);

  // Map time-slider + view-mode + crime type filter
  const [hourFrom, setHourFrom]           = useState(0);
  const [hourTo, setHourTo]               = useState(23);
  const [showHeatmap, setShowHeatmap]     = useState(false);
  const [crimeTypeFilterMap, setCrimeTypeFilterMap] = useState('all');

  const circleRef    = useRef(null);
  const areaObjsRef  = useRef({});   // { [areaName]: { lat, lng } } — avoids Nominatim geocoding

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => { if (entry.isIntersecting) entry.target.classList.add('visible'); });
    }, { threshold: 0.1 });
    const fadeElements = document.querySelectorAll('.prediction-form, .prediction-result');
    fadeElements.forEach(el => observer.observe(el));
    return () => fadeElements.forEach(el => observer.unobserve(el));
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [areasResp, crimeTypesResp] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);
        // getAreas() returns {areas: [{name, coordinates}, ...]}; extract names + cache coords
        const rawAreas = Array.isArray(areasResp) ? areasResp : (areasResp?.areas || []);
        rawAreas.forEach(a => {
          if (a && typeof a === 'object' && a.name && a.coordinates) {
            areaObjsRef.current[a.name] = a.coordinates; // { lat, lng }
          }
        });
        setAreas(rawAreas.map(a => (typeof a === 'string' ? a : (a.name || a.area || ''))).filter(Boolean));
        // getCrimeTypes() returns string array directly
        const rawTypes = Array.isArray(crimeTypesResp) ? crimeTypesResp : (crimeTypesResp?.crime_types || []);
        setCrimeTypes(rawTypes.filter(Boolean));
      } catch (error) {
        console.error('Error fetching prediction data:', error);
        setAreas([]); setCrimeTypes([]);
        setMessage('Unable to load areas and crime types. Please check if the backend server is running.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setDate(today);
  }, []);

  useEffect(() => {
    if (selectedArea) {
      setArea(selectedArea);
      if (crimeType) setTimeout(() => calculateRisk(selectedArea, crimeType, date, time), 500);
    }
  }, [selectedArea]);

  useEffect(() => {
    if (selectedCrimeType) {
      setCrimeType(selectedCrimeType);
      if (area) setTimeout(() => calculateRisk(area, selectedCrimeType, date, time), 500);
    }
  }, [selectedCrimeType]);

  // Animate SVG circle
  useEffect(() => {
    if (circleRef.current && riskPercentage !== null && riskPercentage !== '...') {
      const radius = 54, circumference = 2 * Math.PI * radius;
      const offset = circumference - (riskPercentage / 100) * circumference;
      circleRef.current.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
      circleRef.current.style.strokeDashoffset = offset;
      if (riskLevel.includes('High'))        circleRef.current.style.stroke = riskDescriptions.High.color;
      else if (riskLevel.includes('Medium')) circleRef.current.style.stroke = riskDescriptions.Medium.color;
      else                                   circleRef.current.style.stroke = riskDescriptions.Low.color;
    }
  }, [riskPercentage, riskLevel]);

  const resetInsights = () => {
    setTimePeriod(null); setSafestDays([]); setRiskiestDay(''); setSafestMonths([]);
    setSafestHours([]); setRiskiestHours([]); setSafestUpcoming([]); setHourlyProfile(null);
    setVisitComparison([]); setAreaTrend(null); setDatasetStats(null); setMonthlyCrimeStats([]);
    setShowMap(false); setAreaCoords(null); setNearbyCrimes([]);
    setHourFrom(0); setHourTo(23); setShowHeatmap(false); setCrimeTypeFilterMap('all');
    setAreaProfile(null); setProfileLoading(false);
  };

  const calculateRisk = async (
    areaParam      = area,
    crimeTypeParam = crimeType,
    dateParam      = date,
    timeParam      = time
  ) => {
    setPredicting(true);
    setRiskPercentage('...'); setRiskLevel(''); setRiskClass('');
    setDescription(''); setPrecautions([]); setMessage('');
    setConfidence(0); setShowDetails(false);
    resetInsights();

    try {
      const prediction = await apiService.predictRisk(areaParam, crimeTypeParam, dateParam, timeParam || null);

      if (prediction && prediction.risk_level && prediction.risk_percentage !== undefined) {
        const lvl = prediction.risk_level;
        let cls   = 'risk-medium';
        if (lvl === 'Low')  cls = 'risk-low';
        if (lvl === 'High') cls = 'risk-high';

        setRiskPercentage(prediction.risk_percentage);
        setRiskLevel(`${lvl} Risk`);
        setRiskClass(cls);
        setDescription(riskDescriptions[lvl]?.description || '');
        setPrecautions(riskDescriptions[lvl]?.precautions || []);
        setConfidence(prediction.confidence || 0);

        if (prediction.time_period)            setTimePeriod(prediction.time_period);
        if (prediction.safest_days_of_week)    setSafestDays(prediction.safest_days_of_week);
        if (prediction.riskiest_day_of_week)   setRiskiestDay(prediction.riskiest_day_of_week);
        if (prediction.safest_months)          setSafestMonths(prediction.safest_months);
        if (prediction.safest_hours)           setSafestHours(prediction.safest_hours);
        if (prediction.riskiest_hours)         setRiskiestHours(prediction.riskiest_hours);
        if (prediction.safest_upcoming_dates)  setSafestUpcoming(prediction.safest_upcoming_dates);
        if (prediction.hourly_risk_profile)    setHourlyProfile(prediction.hourly_risk_profile);
        if (prediction.visit_time_comparison)  setVisitComparison(prediction.visit_time_comparison);
        if (prediction.area_trend)             setAreaTrend(prediction.area_trend);
        if (prediction.dataset_stats)          setDatasetStats(prediction.dataset_stats);
        if (prediction.monthly_crime_counts)   setMonthlyCrimeStats(prediction.monthly_crime_counts);
        if (prediction.message)                setMessage(prediction.message);

        setTimeout(() => setShowDetails(true), 1000);
      } else {
        setDefaultRiskLevel();
      }
    } catch (error) {
      console.error('Error calculating risk:', error);
      setDefaultRiskLevel();
    } finally {
      setPredicting(false);
    }
  };

  const setDefaultRiskLevel = () => {
    setRiskPercentage(50); setRiskLevel('Medium Risk'); setRiskClass('risk-medium');
    setDescription(riskDescriptions['Medium'].description);
    setPrecautions(riskDescriptions['Medium'].precautions);
    setConfidence(0.5); setShowDetails(true);
  };

  const handleAreaOverview = async () => {
    if (!area) return;
    // Clear existing prediction result
    setRiskPercentage(0); setRiskLevel(''); setRiskClass('');
    setDescription(''); setPrecautions([]); setConfidence(0); setShowDetails(false);
    setTimePeriod(null); setSafestDays([]); setRiskiestDay(''); setSafestMonths([]);
    setSafestHours([]); setRiskiestHours([]); setSafestUpcoming([]); setHourlyProfile(null);
    setVisitComparison([]); setAreaTrend(null); setDatasetStats(null); setMonthlyCrimeStats([]);
    setAreaProfile(null);
    setProfileLoading(true);
    try {
      const selectedAreaObj = areas.find((a) => (a?.name || a) === area);
      const scopeLat = selectedAreaObj?.coordinates?.lat;
      const scopeLng = selectedAreaObj?.coordinates?.lng;
      const profile = await apiService.getAreaSafetyProfile(area, 12, {
        crimeType: crimeType || undefined,
        date: date || undefined,
        visitTime: time || undefined,
        lat: typeof scopeLat === 'number' ? scopeLat : undefined,
        lng: typeof scopeLng === 'number' ? scopeLng : undefined,
        radiusKm: 1.0,
      });
      setAreaProfile(profile);
    } catch (e) {
      console.error('Area profile error:', e);
    } finally {
      setProfileLoading(false);
    }
  };

  const handleViewOnMap = async () => {
    if (!area) return;
    setShowMap(true);
    // Auto-set time filter from prediction period
    if (timePeriod) {
      const PERIOD_H = { Morning:[6,11], Afternoon:[12,17], Evening:[18,23], Night:[0,5] };
      const [f, t]   = PERIOD_H[timePeriod] || [0, 23];
      setHourFrom(f); setHourTo(t);
    }
    if (areaCoords) return; // already loaded
    setCoordsLoading(true);
    try {
      // Use coordinates cached from getAreas() at startup — no external geocoding needed
      const cachedCoords = areaObjsRef.current[area];

      // Fetch crimes for the area (all types) with higher limit for better coverage
      let crimesResp;
      try {
        crimesResp = await apiService.getCrimes({ area, limit: 500 });
      } catch (e) { console.warn('Crimes fetch failed:', e); crimesResp = []; }

      if (cachedCoords?.lat && cachedCoords?.lng) {
        setAreaCoords([cachedCoords.lat, cachedCoords.lng]);
      } else {
        // Fallback: derive centroid from the crimes we just fetched
        const withCoords = (Array.isArray(crimesResp) ? crimesResp : []).filter(c => c.latitude && c.longitude);
        if (withCoords.length > 0) {
          const avgLat = withCoords.reduce((s, c) => s + c.latitude, 0) / withCoords.length;
          const avgLng = withCoords.reduce((s, c) => s + c.longitude, 0) / withCoords.length;
          setAreaCoords([avgLat, avgLng]);
        } else {
          // Last resort: Nominatim
          try {
            const coordsResp = await apiService.getAreaCoordinates(area);
            const coords = coordsResp?.coordinates;
            if (coords?.lat && coords?.lng) setAreaCoords([coords.lat, coords.lng]);
          } catch (geoErr) { console.warn('Nominatim geocoding failed:', geoErr); }
        }
      }

      const crimesArr = Array.isArray(crimesResp) ? crimesResp : (crimesResp?.crimes || crimesResp?.data || []);
      setNearbyCrimes(crimesArr);
    } catch (e) { console.error('Map load error:', e); }
    finally { setCoordsLoading(false); }
  };

  const formatAreaName = (name) => name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  const normalizeRiskBandLabel = (value) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized.includes('high')) return 'High Risk';
    if (normalized.includes('moderate') || normalized.includes('medium')) return 'Moderate Risk';
    if (normalized.includes('low') || normalized.includes('safe')) return 'Low Risk';
    return 'Moderate Risk';
  };

  const getAreaProfileRiskLabel = (profile) => {
    const level = normalizeRiskBandLabel(profile?.risk_level || '');
    const trendDir = profile?.trend?.direction || 'stable';
    if (level === 'High Risk' && trendDir === 'decreasing') {
      return 'High Risk (Improving)';
    }
    return level;
  };

  // Extract 24-hour integer from a crime_time string like "03:22 AM" or "15:22:00"
  const getCrimeHour = (t) => {
    if (!t) return -1;
    try {
      const s = t.trim();
      if (s.includes('AM') || s.includes('PM')) {
        const [time, ampm] = s.split(' ');
        const h = parseInt(time.split(':')[0], 10);
        return ampm === 'PM' ? (h === 12 ? 12 : h + 12) : (h === 12 ? 0 : h);
      }
      return parseInt(s.split(':')[0], 10);
    } catch { return -1; }
  };

  const fmtHour = (h) => {
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12  = h % 12 || 12;
    return `${h12}:00 ${ampm}`;
  };

  const PERIOD_HOURS   = { Morning: '6 AM – 12 PM', Afternoon: '12 PM – 6 PM', Evening: '6 PM – 12 AM', Night: '12 AM – 6 AM' };
  const PERIOD_CONTEXT  = { Morning: 'morning', Afternoon: 'afternoon', Evening: 'evening', Night: 'late-night' };

  const getRiskIcon = () => {
    if (riskLevel.includes('High'))   return riskDescriptions.High.icon;
    if (riskLevel.includes('Medium')) return riskDescriptions.Medium.icon;
    return riskDescriptions.Low.icon;
  };
  const formatTimeDisplay = (t) => {
    if (!t) return '';
    const [h, m] = t.split(':').map(Number);
    if (isNaN(h)) return t;
    const ampm = h >= 12 ? 'PM' : 'AM';
    return `${h % 12 || 12}:${String(m || 0).padStart(2, '0')} ${ampm}`;
  };

  const getRiskColor = (pct) => {
    if (pct < 20) return '#22c55e';
    if (pct < 60) return '#f59e0b';
    return '#dc2626';
  };

  const maxProfile       = hourlyProfile ? Math.max(...Object.values(hourlyProfile)) : 1;
  const maxMonthlyCrimes = monthlyCrimeStats.length ? Math.max(...monthlyCrimeStats.map(m => m.count)) : 1;

  // Crimes filtered by the time-range slider + optional crime type filter
  const filteredCrimes = nearbyCrimes.filter(c => {
    const h      = getCrimeHour(c.crime_time);
    const timeOk = h === -1 || (h >= hourFrom && h <= hourTo);
    if (!timeOk) return false;
    if (crimeTypeFilterMap === 'selected' && crimeType) {
      const ct = (c.crime_type || '').toLowerCase();
      const pt = crimeType.toLowerCase();
      return ct.includes(pt) || pt.includes(ct);
    }
    return true;
  });

  // Heatmap points: [lat, lng, intensity 0-1] weighted by recency
  const heatPoints = filteredCrimes
    .filter(c => c.latitude && c.longitude)
    .map(c => {
      const months = c.date ? (Date.now() - new Date(c.date.split(' ')[0])) / (1000*60*60*24*30) : 999;
      const intensity = months <= 6 ? 1.0 : months <= 12 ? 0.6 : 0.3;
      return [c.latitude, c.longitude, intensity];
    });

  return (
    <section className="prediction-tool section-padding" id="prediction">
      <div className="section-title">
        <h2>Check Area Safety</h2>
        <span className="urdu-text">علاقے کی حفاظت چیک کریں</span>
        <p>Use our AI prediction tool to assess crime risk for specific areas and times</p>
      </div>

      <div className="prediction-container">
        {/* ── Left: Form ── */}
        <div className="prediction-form fade-in">
          <h3>Risk Assessment Tool</h3>
          <p className="form-subtitle">Select an area, crime type, date and time to get started</p>

          <div className="form-group">
            <label htmlFor="area">Select Area</label>
            <select id="area" value={area} onChange={(e) => setArea(e.target.value)} className={area ? 'has-value' : ''}>
              <option value="">{loading ? 'Loading areas...' : 'Select an area in Lahore'}</option>
              {areas.map((a, i) => <option key={i} value={a}>{formatAreaName(a)}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="crime-type">Crime Type</label>
            <select id="crime-type" value={crimeType} onChange={(e) => setCrimeType(e.target.value)} className={crimeType ? 'has-value' : ''}>
              <option value="">{loading ? 'Loading crime types...' : 'Select crime type'}</option>
              {crimeTypes.map((c, i) => <option key={i} value={c}>{c}</option>)}
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="date">Date</label>
              <input type="date" id="date" value={date} onChange={(e) => setDate(e.target.value)} className={date ? 'has-value' : ''} />
            </div>
            <div className="form-group">
              <label htmlFor="time">Visit Time <span className="optional-label">(optional)</span></label>
              <input type="time" id="time" value={time} onChange={(e) => setTime(e.target.value)} className={time ? 'has-value' : ''} />
            </div>
          </div>

          <p className="form-helper">
            Select a date and optional visit time to estimate crime risk based on historical patterns.
          </p>

          <button
            className={`btn btn-primary${predicting ? ' loading' : ''}`}
            style={{ width: '100%' }}
            onClick={() => {
              if (!area || !crimeType) { alert('Please select both area and crime type.'); return; }
              setAreaProfile(null);
              calculateRisk(area, crimeType, date, time);
            }}
            disabled={predicting || profileLoading || !area || !crimeType}
          >
            {predicting ? 'Analyzing…' : 'Check Risk Level'}
          </button>

          {area && !crimeType && (
            <button
              className={`btn btn-area-profile${profileLoading ? ' loading' : ''}`}
              style={{ width: '100%', marginTop: '0.65rem' }}
              onClick={handleAreaOverview}
              disabled={profileLoading || predicting}
            >
              {profileLoading
                ? <><i className="fas fa-spinner fa-spin"></i> Loading profile…</>
                : <><i className="fas fa-shield-alt"></i> View Area Safety Profile</>}
            </button>
          )}

          {message && (
            <div className="info-message">
              <i className="fas fa-info-circle"></i> {message}
            </div>
          )}

          {/* Dataset context badge */}
          {datasetStats && (
            <div className="dataset-badge">
              <i className="fas fa-database"></i>
              Based on <strong>{datasetStats.total_records.toLocaleString()}</strong> historical FIR records
              covering <strong>{datasetStats.date_range}</strong>
            </div>
          )}
        </div>

        {/* ── Right: Results ── */}
        <div className="prediction-result fade-in" id="predictionResult">
          <h3>Risk Assessment {riskLevel && getRiskIcon()}</h3>

          <div className="risk-visualization">
            <div className="risk-meter">
              <svg width="200" height="200" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="var(--light-bg)" strokeWidth="12" />
                <circle
                  ref={circleRef}
                  cx="60" cy="60" r="54"
                  fill="none"
                  stroke={riskClass === 'risk-high' ? 'var(--accent-red)' :
                          riskClass === 'risk-medium' ? 'var(--accent-teal)' : 'var(--accent-blue)'}
                  strokeWidth="12"
                  strokeDasharray="339.3"
                  strokeDashoffset="339.3"
                  transform="rotate(-90 60 60)"
                />
                <text x="60" y="65" textAnchor="middle" fontSize="16" fill="var(--text-dark)" fontWeight="bold">
                  {riskLevel ? riskLevel.split(' ')[0].toUpperCase() : 'RISK'}
                </text>
              </svg>
              <div className="risk-pct-label">Estimated Risk Probability</div>
              <div className={`risk-value ${riskClass}`}>
                {riskPercentage}{riskPercentage !== '...' && '%'}
              </div>
            </div>

            <div className="risk-info">
              <div className={`risk-label ${riskClass}`}>{riskLevel || 'No assessment yet'}</div>

              {timePeriod && (
                <div className="time-period-badge">
                  {TIME_PERIOD_ICONS[timePeriod]} {timePeriod}
                </div>
              )}

              {/* Area trend badge */}
              {areaTrend && (
                <div className={`trend-badge trend-${areaTrend.direction}`}>
                  {areaTrend.direction === 'decreasing' ? '↓' : areaTrend.direction === 'increasing' ? '↑' : '→'}
                  {' '}Crime trend (last 12 months): {areaTrend.direction}
                  {areaTrend.direction !== 'stable' && (
                    <span className="trend-pct"> ({Math.abs(areaTrend.change_pct)}% change)</span>
                  )}
                </div>
              )}

              {area && crimeType && (
                <div className="prediction-context">
                  <p><strong>Area:</strong> {formatAreaName(area)}</p>
                  <p><strong>Crime Type:</strong> {crimeType}</p>
                  <p><strong>Date:</strong> {new Date(date).toLocaleDateString()}</p>
                  {time && <p><strong>Time:</strong> {formatTimeDisplay(time)}</p>}
                </div>
              )}
            </div>
          </div>

          {showDetails && (
            <div className="risk-details">
              <div className="description-box">
                <h4>Risk Interpretation</h4>
                <p>{description}</p>
              </div>

              <div className="confidence-indicator">
                <span className="confidence-label">Prediction Reliability: </span>
                <span className="confidence-value">{Math.round(confidence * 100)}%</span>
                <div className="confidence-bar">
                  <div className="confidence-fill" style={{ width: `${confidence * 100}%` }} />
                </div>
                <p className="confidence-note">Based on how much historical data exists for this area and crime type combination.</p>
              </div>

              {/* ── Your Visit Time Risk ── */}
              {timePeriod && time && (
                <div className="visit-time-risk-card">
                  <div className="visit-time-risk-header">
                    <span className="visit-time-risk-icon">{TIME_PERIOD_ICONS[timePeriod]}</span>
                    <div className="visit-time-risk-title-col">
                      <span className="visit-time-risk-label">Your Visit Time Risk</span>
                      <span className="visit-time-risk-sub">{timePeriod} · {formatTimeDisplay(time)}</span>
                    </div>
                    <span className={`visit-time-risk-pct ${riskClass}`}>{riskPercentage}%</span>
                  </div>
                  <p className="visit-time-risk-desc">
                    This estimate reflects historical crime patterns observed during
                    {' '}<strong>{PERIOD_CONTEXT[timePeriod]}</strong> hours in this area.
                    {hourlyProfile?.[timePeriod] != null && (
                      <>{' '}Historically, <strong>{hourlyProfile[timePeriod]}%</strong> of daily crime risk in this area falls during {timePeriod.toLowerCase()} hours ({PERIOD_HOURS[timePeriod]}).</>
                    )}
                  </p>
                </div>
              )}

              {/* ── Hourly Risk Context ── */}
              {timePeriod && hourlyProfile?.[timePeriod] != null && (
                <div className="hourly-risk-context">
                  <div className="hourly-risk-context-title">
                    <i className="fas fa-clock"></i> Hourly Risk Context
                  </div>
                  <p className="hourly-risk-context-body">
                    <strong>{formatTimeDisplay(time)}</strong> falls within the <strong>{timePeriod}</strong> window ({PERIOD_HOURS[timePeriod]}), which is a
                    {' '}<strong>{hourlyProfile[timePeriod] < 20 ? 'lower-activity' : hourlyProfile[timePeriod] < 40 ? 'moderate-activity' : 'higher-activity'}</strong> period based on historical FIR records.
                  </p>
                  <div className="hourly-risk-context-stat">
                    <span className="hourly-risk-context-stat-label">Average crime share for {timePeriod} hours ({PERIOD_HOURS[timePeriod]})</span>
                    <div className="hourly-risk-context-bar-row">
                      <div className="hourly-risk-context-bar-track">
                        <div
                          className="hourly-risk-context-bar-fill"
                          style={{
                            width: `${hourlyProfile[timePeriod]}%`,
                            background: getRiskColor(hourlyProfile[timePeriod])
                          }}
                        />
                      </div>
                      <span className="hourly-risk-context-pct" style={{ color: getRiskColor(hourlyProfile[timePeriod]) }}>
                        {hourlyProfile[timePeriod]}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Time-of-Day Risk Profile ── */}
              {hourlyProfile && (
                <div className="insights-card period-profile-card">
                  <div className="insights-card-title">
                    <i className="fas fa-chart-bar"></i> Risk by Time of Day
                    {timePeriod && (
                      <span className="insights-subtag">{TIME_PERIOD_ICONS[timePeriod]} {timePeriod} selected</span>
                    )}
                  </div>
                  <div className="period-bars">
                    {PERIOD_ORDER.filter(p => hourlyProfile[p] !== undefined).map(period => {
                      const pct = hourlyProfile[period];
                      const barWidth = Math.round((pct / maxProfile) * 100);
                      const isActive = timePeriod === period;
                      return (
                        <div key={period} className={`period-bar-row${isActive ? ' period-bar-row-active' : ''}`}>
                          <span className="period-icon">{TIME_PERIOD_ICONS[period]}</span>
                          <span className="period-name">{period}</span>
                          <div className="period-bar-track">
                            <div
                              className="period-bar-fill"
                              style={{ width: `${barWidth}%`, background: getRiskColor(pct) }}
                            />
                          </div>
                          <span className="period-pct" style={{ color: getRiskColor(pct) }}>{pct}%</span>
                          {isActive && <span className="period-active-tag">← now</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}



              {/* ── Smart Safety Insights ── */}
              {(safestDays.length > 0 || safestMonths.length > 0 || safestUpcoming.length > 0 || safestHours.length > 0) && (
                <div className="insights-panel">
                  <h4><i className="fas fa-lightbulb"></i> Smart Safety Insights</h4>
                  <div className="insights-grid">

                    {safestDays.length > 0 && (
                      <div className="insight-card">
                        <div className="insight-card-title"><i className="fas fa-calendar-check"></i> Safest Days</div>
                        <div className="insight-chips">
                          {safestDays.map(day => <span key={day} className="chip chip-green">{day}</span>)}
                        </div>
                        {riskiestDay && (
                          <p className="insight-note">
                            <i className="fas fa-exclamation-triangle"></i> Higher risk historically: <strong>{riskiestDay}</strong>
                          </p>
                        )}
                      </div>
                    )}

                    {safestMonths.length > 0 && (
                      <div className="insight-card">
                        <div className="insight-card-title"><i className="fas fa-calendar-alt"></i> Safest Months</div>
                        <div className="insight-chips">
                          {safestMonths.map(m => <span key={m} className="chip chip-blue">{m}</span>)}
                        </div>
                      </div>
                    )}

                    {safestHours.length > 0 && (
                      <div className="insight-card">
                        <div className="insight-card-title"><i className="fas fa-sun"></i> Lowest Historical Risk Hours</div>
                        <p className="insight-subtitle">Historically quieter hours in this area</p>
                        <div className="insight-chips">
                          {safestHours.map(h => <span key={h.hour} className="chip chip-teal">✅ {h.label}</span>)}
                        </div>
                      </div>
                    )}

                    {riskiestHours.length > 0 && (
                      <div className="insight-card">
                        <div className="insight-card-title"><i className="fas fa-exclamation-circle"></i> Highest Historical Risk Hours</div>
                        <p className="insight-subtitle">Crime peaks at these hours based on historical data</p>
                        <div className="insight-chips">
                          {riskiestHours.map(h => <span key={h.hour} className="chip chip-red">🕐 {h.label}</span>)}
                        </div>
                      </div>
                    )}

                    {safestUpcoming.length > 0 && (
                      <div className="insight-card insight-card-full">
                        <div className="insight-card-title"><i className="fas fa-shield-alt"></i> Safest Upcoming Dates</div>
                        <p className="insight-subtitle">Lowest estimated risk dates within the next 30 days</p>
                        <div className="upcoming-dates">
                          {safestUpcoming.map(item => (
                            <div key={item.date} className="upcoming-date-row">
                              <span className="upcoming-date">{item.date}</span>
                              <span className="upcoming-day">{item.day}</span>
                              <span className={`upcoming-pct ${
                                item.risk_percentage < 20 ? 'chip chip-green' :
                                item.risk_percentage < 60 ? 'chip chip-yellow' : 'chip chip-red'
                              }`}>{item.risk_percentage}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── Monthly Crime Frequency Mini-Chart ── */}
              {monthlyCrimeStats.length > 0 && (
                <div className="insights-card monthly-chart-card">
                  <div className="insights-card-title">
                    <i className="fas fa-chart-bar"></i> Crime Frequency — Last 12 Months
                  </div>
                  <p className="insight-subtitle">{formatAreaName(area)} — total FIR incidents per month</p>
                  <div className="monthly-hbar-chart">
                    {monthlyCrimeStats.map(m => (
                      <div key={m.month} className="monthly-hbar-row">
                        <span className="monthly-hbar-label">{m.label}</span>
                        <div className="monthly-hbar-track">
                          <div
                            className="monthly-hbar-fill"
                            style={{ width: `${Math.round((m.count / maxMonthlyCrimes) * 100)}%` }}
                            title={`${m.month}: ${m.count} incidents`}
                          />
                        </div>
                        <span className="monthly-hbar-count">{m.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="safety-recommendations">
                <h4>Safety Recommendations</h4>
                <ul>
                  {precautions.map((p, i) => (
                    <li key={i}><i className="fas fa-shield-alt"></i> {p}</li>
                  ))}
                </ul>
              </div>

              {/* ── Action Buttons ── */}
              <div className="action-buttons">
                <button className="btn btn-secondary" onClick={() => calculateRisk(area, crimeType, date, time)}>
                  <i className="fas fa-sync-alt"></i> Re-assess Risk
                </button>
                <button className="btn btn-map" onClick={handleViewOnMap} disabled={!area}>
                  <i className="fas fa-map-marked-alt"></i> View on Map
                </button>
                <button className="btn btn-outline" onClick={() => window.print()}>
                  <i className="fas fa-print"></i> Print
                </button>
              </div>

              {/* ── Disclaimer ── */}
              <div className="disclaimer-block">
                <i className="fas fa-info-circle"></i>
                <p>
                  <strong>Statistical Prediction Disclaimer:</strong> These predictions are based on historical FIR
                  crime data and statistical models. They represent probabilities, not certainties. Actual conditions
                  may vary. Do not use this tool as a substitute for official law-enforcement advice.
                </p>
              </div>
            </div>
          )}

          {!riskLevel && (
            <div className="empty-state">
              <div className="empty-icon"><i className="fas fa-search"></i></div>
              <p>Select an area and crime type to see risk assessment</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Area Safety Profile Panel ── */}
      {(areaProfile || profileLoading) && (
        <div className="area-profile-panel">
          {profileLoading && !areaProfile && (
            <div className="ap-loading">
              <i className="fas fa-spinner fa-spin"></i> Building safety profile for {formatAreaName(area)}…
            </div>
          )}
          {areaProfile && (
            <>
              <div className="ap-header">
                <div className="ap-header-left">
                  <i className="fas fa-shield-alt ap-shield-icon"></i>
                  <div>
                    <div className="ap-title">Area Safety Profile</div>
                    <div className="ap-subtitle">
                      {formatAreaName(areaProfile.area)} · Last {areaProfile.period_months} months
                    </div>
                    <div className="ap-subtitle" style={{ fontSize: '0.78rem', opacity: 0.9 }}>
                      Historical Area Analysis ({areaProfile.period_months} months)
                    </div>
                  </div>
                </div>
                <div className="ap-header-meta">
                  Based on <strong>{areaProfile.total_crimes.toLocaleString()}</strong> FIR records ·
                  City avg: <strong>{areaProfile.city_avg_crimes}</strong>/area ·
                  Data Confidence: <strong>{formatConfidenceLabel(areaProfile.data_confidence)}</strong>
                </div>
              </div>

              {/* ── Crime Pressure Indicator ── */}
              <div className="ap-pressure-bar">
                <div className="ap-pressure-item">
                  <span className="ap-pressure-label">Crime Pressure</span>
                  <span className={`ap-pressure-value ap-pressure-${(areaProfile.crime_pressure || 'Moderate').toLowerCase()}`}>
                    {areaProfile.crime_pressure || '—'}
                  </span>
                </div>
                <div className="ap-pressure-divider" />
                <div className="ap-pressure-item">
                  <span className="ap-pressure-label">Crime Density</span>
                  <span className="ap-pressure-value">{areaProfile.crime_density?.label || '—'}</span>
                </div>
                <div className="ap-pressure-divider" />
                <div className="ap-pressure-item">
                  <span className="ap-pressure-label">Trend</span>
                  <span className="ap-pressure-value">
                    {areaProfile.trend?.direction === 'decreasing' ? '↓ Decreasing'
                     : areaProfile.trend?.direction === 'increasing' ? '↑ Increasing'
                     : '→ Stable'}
                  </span>
                </div>
                <div className="ap-pressure-divider" />
                <div className="ap-pressure-item">
                  <span className="ap-pressure-label">Last 30 Days</span>
                  <span className="ap-pressure-value">{areaProfile.last_30_days ?? '—'} incidents</span>
                </div>
                <div className="ap-pressure-divider" />
                <div className="ap-pressure-item">
                  <span className="ap-pressure-label">Crime Momentum</span>
                  <span className={`ap-pressure-value ap-momentum-${areaProfile.momentum?.direction || 'stable'}`}>
                    {areaProfile.momentum?.direction === 'rising'    ? '↑ Rising'   :
                     areaProfile.momentum?.direction === 'declining' ? '↓ Declining' : '→ Stable'}
                    {areaProfile.momentum?.pct_change > 0 && (
                      <span> ({areaProfile.momentum.direction === 'declining' ? '-' : '+'}{areaProfile.momentum.pct_change}%)</span>
                    )}
                    <span className="ap-momentum-sub"> last 90 days</span>
                  </span>
                </div>
              </div>

              <div className="ap-main-grid">
                {/* ── Score card ── */}
                <div className="ap-score-card">
                  <div className="ap-score-label">Safety Score</div>
                  <div className="ap-score-number">
                    <span className="ap-score-val">{areaProfile.safety_score}</span>
                    <span className="ap-score-denom">&thinsp;/ 100</span>
                  </div>
                  <div className="ap-score-bar-track">
                    <div className="ap-score-bar-fill" style={{
                      width: `${areaProfile.safety_score}%`,
                      background: areaProfile.safety_score >= 65 ? '#22c55e'
                                : areaProfile.safety_score >= 50 ? '#eab308'
                                : areaProfile.safety_score >= 35 ? '#f97316'
                                : '#dc2626'
                    }} />
                  </div>
                  <div className={`ap-risk-level-badge ap-risk-${areaProfile.safety_grade.toLowerCase()}`}>
                    {getAreaProfileRiskLabel(areaProfile)}
                  </div>
                  <div className="ap-ranking-text">
                    City Rank: <strong>#{areaProfile.area_ranking?.rank} / {areaProfile.area_ranking?.total_areas}</strong>
                  </div>
                  <div className="ap-safer-than">
                    Safer than <strong>{areaProfile.safer_than_pct}%</strong> of Lahore
                  </div>
                  {areaProfile.overall_summary && (
                    <div className="ap-visit-times" style={{ marginTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.12)', paddingTop: '0.65rem' }}>
                      <div className="ap-visit-row" style={{ fontWeight: 700 }}>
                        <i className="fas fa-globe-asia" style={{ color: '#60a5fa' }}></i>
                        <span>Overall (Complete History)</span>
                      </div>
                      <div className="ap-visit-row">
                        <i className="fas fa-shield-alt" style={{ color: '#22c55e' }}></i>
                        <span>
                          Safety: <strong>{areaProfile.overall_summary.safety_score}</strong>/100 ·
                          Level: <strong>{normalizeRiskBandLabel(areaProfile.overall_summary.risk_level)}</strong>
                        </span>
                      </div>
                      <div className="ap-visit-row">
                        <i className="fas fa-database" style={{ color: '#f59e0b' }}></i>
                        <span>
                          Records: <strong>{(areaProfile.overall_summary.total_crimes ?? 0).toLocaleString()}</strong> ·
                          Range: <strong>{areaProfile.overall_summary.date_range?.start && areaProfile.overall_summary.date_range?.end ? `${areaProfile.overall_summary.date_range.start} to ${areaProfile.overall_summary.date_range.end}` : 'Not available'}</strong>
                        </span>
                      </div>
                    </div>
                  )}
                  {areaProfile.safest_hour_range && (
                    <div className="ap-visit-times">
                      <div className="ap-visit-row">
                        <i className="fas fa-moon" style={{color:'#818cf8'}}></i>
                        <span>Lowest Risk Window: <strong>{areaProfile.safest_hour_range}</strong></span>
                      </div>
                      {areaProfile.recommended_visit_window && areaProfile.recommended_visit_window !== areaProfile.safest_hour_range && (
                        <div className="ap-visit-row">
                          <i className="fas fa-sun" style={{color:'#22c55e'}}></i>
                          <span>Recommended Visit Time: <strong>{areaProfile.recommended_visit_window}</strong></span>
                        </div>
                      )}
                      <div className="ap-visit-row">
                        <i className="fas fa-exclamation-triangle" style={{color:'#ef4444'}}></i>
                        <span>Higher Risk Window: <strong>{areaProfile.riskiest_hour_range}</strong></span>
                      </div>
                    </div>
                  )}
                </div>

                {/* ── Top crime types ── */}
                <div className="ap-crimes-card">
                  <div className="ap-card-title"><i className="fas fa-list"></i> Top Crime Types</div>
                  {areaProfile.top_crime_types?.slice(0, 5).map((c, i) => (
                    <div key={i} className="ap-crime-row">
                      <span className="ap-crime-rank">{i + 1}</span>
                      <span className="ap-crime-type">{c.display_type || c.type}</span>
                      <div className="ap-crime-bar-track">
                        <div
                          className="ap-crime-bar-fill"
                          style={{
                            width: `${Math.max(c.pct, 2)}%`,
                            background: i === 0 ? '#dc2626' : i === 1 ? '#f97316' : i === 2 ? '#eab308' : '#6b7280'
                          }}
                        />
                      </div>
                      <span className="ap-crime-pct">{c.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── 24-hour pattern ── */}
              <div className="ap-section">
                <div className="ap-section-title">
                  <i className="fas fa-clock"></i> 24-Hour Crime Pattern
                </div>
                <div className="ap-hourly-chart">
                  {areaProfile.hourly_distribution?.map((h) => {
                    const isRiskiest = areaProfile.riskiest_hours?.includes(h.hour);
                    const isSafest   = areaProfile.safest_hours?.includes(h.hour);
                    const barColor   = isRiskiest ? '#dc2626' : isSafest ? '#16a34a' : h.pct > 70 ? '#f97316' : '#3b82f6';
                    return (
                      <div key={h.hour} className="ap-hour-col"
                        title={`${fmtHour(h.hour)}: ${h.count} incidents`}>
                        <div className="ap-hour-bar-track">
                          <div
                            className="ap-hour-bar-fill"
                            style={{ height: `${Math.max(h.pct, 2)}%`, background: barColor }}
                          />
                        </div>
                        {h.hour % 6 === 0 && (
                          <div className="ap-hour-label">{fmtHour(h.hour)}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="ap-hourly-legend">
                  <span className="ap-legend-safe">
                    <i className="fas fa-check-circle"></i>
                    Lowest Risk Window: {areaProfile.safest_hour_range || areaProfile.safest_hours?.map(h => fmtHour(h)).join(', ')}
                  </span>
                  <span className="ap-legend-risk">
                    <i className="fas fa-exclamation-circle"></i>
                    Higher Risk Window: {areaProfile.riskiest_hour_range || areaProfile.riskiest_hours?.map(h => fmtHour(h)).join(', ')}
                  </span>
                </div>
              </div>

              {/* ── Day of week + Trend ── */}
              <div className="ap-bottom-grid">
                <div className="ap-section">
                  <div className="ap-section-title">
                    <i className="fas fa-calendar-week"></i> Day of Week Pattern
                  </div>
                  <div className="ap-dow-chart">
                    {areaProfile.day_of_week?.map((d, i) => (
                      <div key={i} className="ap-dow-col"
                        title={`${d.day}: ${d.count} incidents`}>
                        <div className="ap-dow-bar-track">
                          <div
                            className="ap-dow-bar-fill"
                            style={{
                              height: `${Math.max(d.pct, 4)}%`,
                              background: d.day === areaProfile.riskiest_day ? '#dc2626'
                                        : d.day === areaProfile.safest_day   ? '#16a34a'
                                        : '#3b82f6'
                            }}
                          />
                        </div>
                        <div className="ap-dow-label">{d.day?.slice(0, 3)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="ap-dow-summary">
                    <span>
                      <i className="fas fa-check-circle" style={{color:'#16a34a'}}></i>
                      Safest: <strong>{areaProfile.safest_day}</strong>
                      {typeof areaProfile.safest_day_vs_avg === 'number' && (
                        <span className="ap-dow-vs" style={{color:'#16a34a'}}>
                          {' '}({areaProfile.safest_day_vs_avg}% vs avg)
                        </span>
                      )}
                    </span>
                    <span>
                      <i className="fas fa-exclamation-circle" style={{color:'#dc2626'}}></i>
                      Riskiest: <strong>{areaProfile.riskiest_day}</strong>
                      {typeof areaProfile.riskiest_day_vs_avg === 'number' && (
                        <span className="ap-dow-vs" style={{color:'#dc2626'}}>
                          {' '}(+{areaProfile.riskiest_day_vs_avg}% vs avg)
                        </span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="ap-section">
                  <div className="ap-section-title">
                    <i className="fas fa-chart-line"></i> Crime Trend
                  </div>
                  <div className={`ap-trend-badge ap-trend-${areaProfile.trend?.direction}`}>
                    {areaProfile.trend?.direction === 'increasing' && <>📈 Crime <strong>up {areaProfile.trend.change_pct}%</strong> vs prior period</>}
                    {areaProfile.trend?.direction === 'decreasing' && <>📉 Crime <strong>down {areaProfile.trend.change_pct}%</strong> vs prior period</>}
                    {areaProfile.trend?.direction === 'stable'     && <>➡️ Crime is <strong>stable</strong> vs prior period</>}
                  </div>
                  <div className="ap-trend-counts">
                    <div className="ap-tc-row">
                      <span>Recent {Math.round(areaProfile.period_months / 2)} months:</span>
                      <strong>{areaProfile.trend?.recent_count?.toLocaleString() ?? '—'} incidents</strong>
                    </div>
                    {typeof areaProfile.trend?.recent_monthly_avg === 'number' && (
                      <div className="ap-tc-row ap-tc-sub">
                        <span>Monthly avg:</span>
                        <strong>{areaProfile.trend.recent_monthly_avg} / month</strong>
                      </div>
                    )}
                    <div className="ap-tc-row">
                      <span>Previous {Math.round(areaProfile.period_months / 2)} months:</span>
                      <strong>{areaProfile.trend?.older_count?.toLocaleString() ?? '—'} incidents</strong>
                    </div>
                    {typeof areaProfile.trend?.older_monthly_avg === 'number' && (
                      <div className="ap-tc-row ap-tc-sub">
                        <span>Monthly avg:</span>
                        <strong>{areaProfile.trend.older_monthly_avg} / month</strong>
                      </div>
                    )}
                    {typeof areaProfile.trend?.older_count === 'number' && areaProfile.trend.older_count > 0 && (
                      <div className="ap-tc-row">
                        <span>Change:</span>
                        <strong style={{color: areaProfile.trend.direction === 'decreasing' ? '#22c55e' : areaProfile.trend.direction === 'increasing' ? '#dc2626' : '#9ca3af'}}>
                          {areaProfile.trend.direction === 'decreasing' ? '−' : areaProfile.trend.direction === 'increasing' ? '+' : '±'}{areaProfile.trend.change_pct}%
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {/* ── Safety Insights ── */}
              <div className="ap-section ap-insights-section">
                <div className="ap-section-title">
                  <i className="fas fa-lightbulb"></i> Safety Insights
                </div>
                <ul className="ap-insight-list">
                  {areaProfile.riskiest_hour_range && (
                    <li>
                      <i className="fas fa-exclamation-circle" style={{color:'#f97316'}}></i>
                      Crime activity peaks during <strong>{areaProfile.riskiest_hour_range}</strong>
                    </li>
                  )}
                  {areaProfile.riskiest_day && (
                    <li>
                      <i className="fas fa-calendar-times" style={{color:'#f97316'}}></i>
                      <strong>{areaProfile.riskiest_day}s</strong> historically show higher crime frequency
                      {typeof areaProfile.riskiest_day_vs_avg === 'number' && (
                        <> (+{areaProfile.riskiest_day_vs_avg}% above weekly average)</>
                      )}
                    </li>
                  )}
                  {areaProfile.top_crime_types?.[0] && (
                    <li>
                      <i className="fas fa-tag" style={{color:'#f97316'}}></i>
                      <strong>{areaProfile.top_crime_types[0].display_type || areaProfile.top_crime_types[0].type}</strong> is the most reported incident ({areaProfile.top_crime_types[0].pct}%)
                    </li>
                  )}
                  <li>
                    <i className="fas fa-sun" style={{color:'#22c55e'}}></i>
                    Visits during <strong>{areaProfile.recommended_visit_window || '10 AM–5 PM'}</strong> tend to be relatively safer
                  </li>
                  {areaProfile.trend?.direction === 'decreasing' && (
                    <li>
                      <i className="fas fa-chart-line" style={{color:'#22c55e'}}></i>
                      Crime is trending <strong>down {areaProfile.trend.change_pct}%</strong> compared to the prior period
                    </li>
                  )}
                  {areaProfile.trend?.direction === 'increasing' && (
                    <li>
                      <i className="fas fa-chart-line" style={{color:'#dc2626'}}></i>
                      Crime is trending <strong>up {areaProfile.trend.change_pct}%</strong> — exercise extra caution
                    </li>
                  )}
                </ul>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Map Modal ── */}
      {showMap && (
        <div className="map-modal-overlay" onClick={(e) => { if (e.target.classList.contains('map-modal-overlay')) setShowMap(false); }}>
          <div className="map-modal">
            <div className="map-modal-header">
              <h3>
                <i className="fas fa-map-marked-alt"></i>
                {formatAreaName(area)} — {riskLevel}
              </h3>
              <button className="map-close-btn" onClick={() => setShowMap(false)}>
                <i className="fas fa-times"></i>
              </button>
            </div>

            <div className="map-modal-meta">
              <span className={`map-risk-pill ${riskClass}`}>{riskPercentage}% Estimated Risk</span>
              {areaTrend && (
                <span className={`map-trend-pill trend-${areaTrend.direction}`}>
                  {areaTrend.direction === 'decreasing' ? '↓' : areaTrend.direction === 'increasing' ? '↑' : '→'}
                  {' '}Crime {areaTrend.direction}
                </span>
              )}
              {crimeType && <span className="map-type-pill"><i className="fas fa-tag"></i> {crimeType}</span>}
            </div>

            {/* ── Time slider + view toggle controls ── */}
            <div className="map-controls">
              <div className="time-slider-wrap">
                <span className="slider-label-title"><i className="fas fa-clock"></i> Time Filter {timePeriod && <span className="period-active-tag">({timePeriod} auto-set)</span>}</span>
                <div className="time-range-group">
                  <div className="slider-row">
                    <span className="slider-label">From</span>
                    <input
                      type="range" min={0} max={23} value={hourFrom} className="time-slider"
                      onChange={e => { const v = +e.target.value; setHourFrom(Math.min(v, hourTo)); }}
                    />
                    <span className="slider-value">{fmtHour(hourFrom)}</span>
                  </div>
                  <div className="slider-row">
                    <span className="slider-label">To</span>
                    <input
                      type="range" min={0} max={23} value={hourTo} className="time-slider"
                      onChange={e => { const v = +e.target.value; setHourTo(Math.max(v, hourFrom)); }}
                    />
                    <span className="slider-value">{fmtHour(hourTo)}</span>
                  </div>
                </div>
              </div>
              <div className="map-view-controls">
                <span className="crime-count-badge">
                  <i className="fas fa-database"></i> {filteredCrimes.length}/{nearbyCrimes.length} incidents
                </span>
                <div className="map-view-toggle">
                  <button className={`toggle-btn${!showHeatmap ? ' active' : ''}`} onClick={() => setShowHeatmap(false)}>
                    <i className="fas fa-map-pin"></i> Markers
                  </button>
                  <button className={`toggle-btn${showHeatmap ? ' active' : ''}`} onClick={() => setShowHeatmap(true)}>
                    <i className="fas fa-fire"></i> Heatmap
                  </button>
                </div>                <div className="map-view-toggle">
                  <button className={`toggle-btn${crimeTypeFilterMap === 'selected' ? ' active' : ''}`}
                    onClick={() => setCrimeTypeFilterMap('selected')}
                    title={crimeType || 'Selected crime type'}>
                    <i className="fas fa-filter"></i> {crimeType ? (crimeType.length > 15 ? crimeType.slice(0,15)+'…' : crimeType) : 'This Type'}
                  </button>
                  <button className={`toggle-btn${crimeTypeFilterMap === 'all' ? ' active' : ''}`}
                    onClick={() => setCrimeTypeFilterMap('all')}>
                    <i className="fas fa-layer-group"></i> All Crimes
                  </button>
                </div>              </div>
            </div>

            <div className="map-container-wrap">
              {/* Prediction summary overlay */}
              {areaCoords && (
                <div className="map-summary-overlay">
                  <div className="map-sum-area">{formatAreaName(area)}</div>
                  <div className="map-sum-meta">{crimeType} · {new Date(date).toLocaleDateString('en-GB',{day:'numeric',month:'short'})}{time && <> · {formatTimeDisplay(time)}</>}</div>
                  <div className={`map-sum-risk ${riskClass}`}>{riskPercentage}% — {riskLevel}</div>
                  {timePeriod && <div className="map-sum-period">{({'Morning':'🌅','Afternoon':'☀️','Evening':'🌆','Night':'🌙'})[timePeriod]} {timePeriod} filter active</div>}
                </div>
              )}
              {coordsLoading && (
                <div className="map-loading">
                  <i className="fas fa-spinner fa-spin"></i> Loading map…
                </div>
              )}
              {!coordsLoading && areaCoords && (
                <MapContainer
                  center={areaCoords}
                  zoom={14}
                  style={{ width: '100%', height: '100%' }}
                  scrollWheelZoom={true}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  />
                  <MapFlyTo coords={areaCoords} />

                  {/* Risk zone circle */}
                  <Circle
                    center={areaCoords}
                    radius={800}
                    pathOptions={{
                      color: getRiskColor(riskPercentage),
                      fillColor: getRiskColor(riskPercentage),
                      fillOpacity: 0.18,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div style={{ minWidth: 160 }}>
                        <strong>{formatAreaName(area)}</strong><br />
                        Estimated Risk: <strong style={{ color: getRiskColor(riskPercentage) }}>{riskPercentage}%</strong><br />
                        Level: <strong>{riskLevel}</strong>
                        {timePeriod && <><br />Period: {TIME_PERIOD_ICONS[timePeriod]} {timePeriod}</>}
                      </div>
                    </Popup>
                  </Circle>

                  {/* Area pin */}
                  <Marker position={areaCoords}>
                    <Popup>
                      <div style={{ minWidth: 160 }}>
                        <strong>{formatAreaName(area)}</strong><br />
                        <span style={{ color: getRiskColor(riskPercentage), fontWeight: 600 }}>
                          {riskPercentage}% {riskLevel}
                        </span>
                        {crimeType && <><br />Crime type: {crimeType}</>}
                        {date && <><br />Date: {new Date(date).toLocaleDateString()}</>}
                      </div>
                    </Popup>
                  </Marker>

                  {/* Heatmap layer OR per-incident FIR markers */}
                  {showHeatmap
                    ? <HeatLayer points={heatPoints} />
                    : filteredCrimes.map((crime, i) => {
                        if (!crime.latitude || !crime.longitude) return null;
                        const months = crime.date
                          ? (Date.now() - new Date(crime.date.split(' ')[0])) / (1000*60*60*24*30)
                          : 999;
                        const rColor = months <= 6 ? '#dc2626' : months <= 12 ? '#f97316' : '#eab308';
                        const recencyLabel = months <= 6 ? 'Last 6 months' : months <= 12 ? 'Last 12 months' : 'Older than 1 year';
                        const jLat = crime.latitude  + getJitter(crime.id, i, 0);
                        const jLng = crime.longitude + getJitter(crime.id, i, 1);
                        const locationStr = crime.area_translit || (crime.area ? formatAreaName(crime.area) : 'Unknown Location');
                        return (
                          <Marker key={crime.id || i} position={[jLat, jLng]}
                            icon={L.divIcon({
                              html: `<div style="background:${rColor};width:16px;height:16px;border-radius:50%;border:2.5px solid rgba(255,255,255,0.95);box-shadow:0 2px 8px rgba(0,0,0,.6),0 0 0 3px ${rColor}44"></div>`,
                              className: '', iconSize: [16, 16], iconAnchor: [8, 8],
                            })}
                          >
                            <Popup className="crime-fir-popup">
                              <div style={{ fontFamily: "'Segoe UI', Arial, sans-serif", minWidth: 230, maxWidth: 280, overflow: 'hidden' }}>
                                <div style={{ background: rColor, padding: '9px 13px 8px', color: '#fff' }}>
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
                                  <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontSize: 10.5, fontWeight: 700, background: rColor + '18', color: rColor, border: `1px solid ${rColor}55` }}>{recencyLabel}</span>
                                </div>
                              </div>
                            </Popup>
                          </Marker>
                        );
                      })
                  }
                </MapContainer>
              )}
              {!coordsLoading && !areaCoords && (
                <div className="map-no-coords">
                  <i className="fas fa-map-marker-alt"></i>
                  <p>Could not determine coordinates for <strong>{formatAreaName(area)}</strong>.</p>
                </div>
              )}
            </div>

            <div className="map-modal-footer">
              <span><i className="fas fa-circle" style={{ color: '#dc2626' }}></i> Last 6 months</span>
              <span><i className="fas fa-circle" style={{ color: '#f97316' }}></i> Last 12 months</span>
              <span><i className="fas fa-circle" style={{ color: '#eab308' }}></i> Older</span>
              <span className="ml-auto">
                {showHeatmap
                  ? <><i className="fas fa-fire" style={{ color: '#f59e0b', marginRight: 4 }}></i>Heatmap (recency-weighted)</>  
                  : <><i className="fas fa-map-pin" style={{ color: '#0ea5e9', marginRight: 4 }}></i>Dots = FIR incident locations</>
                }
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default PredictionTool;

