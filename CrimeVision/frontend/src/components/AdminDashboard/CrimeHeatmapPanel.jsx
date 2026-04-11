import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, useMap } from 'react-leaflet';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import HeatmapLayer from '../HeatMapLayer';
import apiService from '../../services/apiService_updated';
import { ppcSimpleLabel } from '../../utils/ppcUtils';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import styles from './CrimeHeatmapPanel.module.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const RISK_COLORS = { Critical: '#7c3aed', High: '#ef4444', Moderate: '#f59e0b', Low: '#22c55e' };

const normalizeRiskLevel = (value) => {
  const v = String(value || '').toLowerCase();
  if (v.includes('critical') || v.includes('avoid')) return 'Critical';
  if (v.includes('high') || v.includes('warning')) return 'High';
  if (v.includes('moderate') || v.includes('medium') || v.includes('caution')) return 'Moderate';
  return 'Low';
};

const actionLabel = (level) => {
  if (level === 'Critical') return 'Avoid';
  if (level === 'High') return 'Warning';
  if (level === 'Moderate') return 'Caution';
  return 'Safe';
};

const intensityFromRisk = (riskLevel) => {
  const level = normalizeRiskLevel(riskLevel);
  if (level === 'Critical') return 1;
  if (level === 'High') return 0.85;
  if (level === 'Moderate') return 0.6;
  return 0.3;
};

const MAP_STYLES = {
  streets: { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', label: 'Streets' },
  dark: { url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', label: 'Dark' },
  satellite: { url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', label: 'Satellite' },
};

// Syncs the Leaflet map's zoom level whenever the zoom state changes
// (MapContainer only reads the zoom prop on initial mount)
const ZoomSyncer = ({ zoom }) => {
  const map = useMap();
  useEffect(() => {
    if (map && zoom) map.setZoom(Number(zoom));
  }, [map, zoom]);
  return null;
};

const createRiskIcon = (riskLevel) => {
  const color = RISK_COLORS[normalizeRiskLevel(riskLevel)] || '#6b7280';
  return L.divIcon({
    className: 'custom-crime-marker',
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 6px ${color}80;"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
};

const CrimeHeatmapPanel = ({ token }) => {
  const { settings: systemSettings } = useSystemSettings();
  const [selectedArea, setSelectedArea] = useState('all');
  const [areas, setAreas] = useState([]);
  const [rawCrimes, setRawCrimes] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mapCenter, setMapCenter] = useState([31.5204, 74.3587]); // Lahore
  const [mapZoom, setMapZoom] = useState(11); // overridden by system settings below
  const [recordLimit, setRecordLimit] = useState(1000);
  const initialLoadDone = useRef(false);

  // Always sync mapZoom from system settings whenever they change (real-time updates)
  useEffect(() => {
    if (systemSettings?.default_map_zoom) {
      setMapZoom(Number(systemSettings.default_map_zoom));
    }
  }, [systemSettings?.default_map_zoom]);

  const [crimeTypeFilter, setCrimeTypeFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  const [viewMode, setViewMode] = useState('heatmap');
  const [mapStyle, setMapStyle] = useState('streets');
  const [showClusters, setShowClusters] = useState(true);

  const loadAreas = useCallback(async () => {
    try {
      const areaRows = await apiService.getAreas();
      const formatted = (areaRows || [])
        .map(a => ({
          value: a.name,
          label: a.name,
          coordinates: a.coordinates || null,
          record_count: a.record_count || 0,
        }))
        .sort((a, b) => a.label.localeCompare(b.label));
      setAreas(formatted);
    } catch (err) {
      console.error('Failed to load areas:', err);
    }
  }, []);

  // Helper: transform getCrimes response into heatmap points
  const transformCrimesToPoints = (crimes) => {
    const crimeList = Array.isArray(crimes) ? crimes : (crimes?.crimes || []);
    return crimeList
      .filter(c => {
        const lat = c.latitude ?? c.coordinates?.[0];
        const lng = c.longitude ?? c.coordinates?.[1];
        return lat != null && lng != null && !isNaN(parseFloat(lat)) && !isNaN(parseFloat(lng));
      })
      .map(c => ({
        lat: parseFloat(c.latitude ?? c.coordinates?.[0]),
        lng: parseFloat(c.longitude ?? c.coordinates?.[1]),
        intensity: intensityFromRisk(c.risk_level),
        risk_level: normalizeRiskLevel(c.risk_level),
        crime_type: c.crime_type || c.type || 'Unknown',
        date: c.date || c.crime_date || '',
        crime_time: c.crime_time || null,
        area: c.area || 'Unknown',
        area_translit: c.area_translit || null,
        area_urdu: c.area_urdu || null,
      }));
  };

  const centerMapOnPoints = (points) => {
    if (points.length > 0) {
      const avgLat = points.reduce((s, p) => s + p.lat, 0) / points.length;
      const avgLng = points.reduce((s, p) => s + p.lng, 0) / points.length;
      setMapCenter([avgLat, avgLng]);
      setMapZoom(12);
    }
  };

  const fetchHeatmapData = useCallback(async () => {
    setLoading(true);
    // Build limit param: recordLimit === 0 means "All" -> omit param so backend returns all
    const limitParam = recordLimit === 0 ? {} : { limit: recordLimit };
    try {
      if (selectedArea !== 'all') {
        // Fetch raw records first so marker/filter counts always reflect real incidents
        const crimes = await apiService.getCrimes({ area: selectedArea, ...limitParam });
        const points = transformCrimesToPoints(crimes).filter(p =>
          (p.area || '').trim().toLowerCase() === selectedArea.trim().toLowerCase()
        );
        setRawCrimes(points);
        centerMapOnPoints(points);

        // Try area-specific heatmap endpoint for optional precomputed clusters
        try {
          const data = await apiService.getHeatmapData(selectedArea);
          setClusters(data.clusters || []);
        } catch (err) {
          console.warn('Heatmap endpoint failed for area clusters:', err);
          setClusters([]);
        }
      } else {
        // All areas: fetch crimes up to the chosen limit
        const crimes = await apiService.getCrimes({ ...limitParam });
        const points = transformCrimesToPoints(crimes);
        setRawCrimes(points);
        setClusters([]);
        // Keep default Lahore center; only re-center when a specific area is selected
      }
    } catch (err) {
      console.error('Failed to fetch heatmap data:', err);
    } finally { setLoading(false); }
  }, [selectedArea, recordLimit]);

  useEffect(() => {
    if (!initialLoadDone.current) {
      loadAreas();
      initialLoadDone.current = true;
    }
  }, [loadAreas]);

  useEffect(() => { fetchHeatmapData(); }, [fetchHeatmapData]);

  const crimeTypes = useMemo(() => {
    const types = new Set(rawCrimes.map(c => c.crime_type));
    return ['all', ...Array.from(types).sort()];
  }, [rawCrimes]);

  const filteredCrimes = useMemo(() => {
    return rawCrimes.filter(c => {
      if (crimeTypeFilter !== 'all' && c.crime_type !== crimeTypeFilter) return false;
      if (riskFilter !== 'all' && normalizeRiskLevel(c.risk_level) !== riskFilter) return false;
      if (dateRange.start && c.date && c.date < dateRange.start) return false;
      if (dateRange.end && c.date && c.date > dateRange.end) return false;
      return true;
    });
  }, [rawCrimes, crimeTypeFilter, riskFilter, dateRange]);

  const filteredHeatmapPoints = useMemo(() => {
    return filteredCrimes.map(c => ({
      lat: c.lat, lng: c.lng,
      intensity: intensityFromRisk(c.risk_level)
    }));
  }, [filteredCrimes]);

  const groupedMarkers = useMemo(() => {
    const riskRank = { Low: 1, Moderate: 2, High: 3, Critical: 4 };
    const grouped = new Map();

    filteredCrimes.forEach(c => {
      const day = (c.date || '').split(' ')[0] || '';
      const time = (c.crime_time || '').trim();
      const areaKey = (c.area || '').trim().toLowerCase();
      const key = `${areaKey}|${day}|${time}|${Number(c.lat).toFixed(6)},${Number(c.lng).toFixed(6)}`;

      if (!grouped.has(key)) {
        grouped.set(key, {
          lat: c.lat,
          lng: c.lng,
          date: c.date,
          crime_time: c.crime_time || '',
          risk_level: normalizeRiskLevel(c.risk_level),
          area: c.area || 'Unknown',
          area_translit: c.area_translit || null,
          area_urdu: c.area_urdu || null,
          risks: {},
          crime_types: {},
          row_count: 0,
        });
      }

      const g = grouped.get(key);
      g.row_count += 1;
      const rl = normalizeRiskLevel(c.risk_level);
      g.risks[rl] = (g.risks[rl] || 0) + 1;
      const ct = c.crime_type || 'Unknown';
      g.crime_types[ct] = (g.crime_types[ct] || 0) + 1;

      if (!g.area_translit && c.area_translit) g.area_translit = c.area_translit;
      if (!g.area_urdu && c.area_urdu) g.area_urdu = c.area_urdu;
      if ((riskRank[rl] || 0) > (riskRank[g.risk_level || 'Low'] || 0)) g.risk_level = rl;
    });

    return Array.from(grouped.values());
  }, [filteredCrimes]);

  const markerDisplayPoints = useMemo(() => {
    const byCoord = new Map();
    groupedMarkers.forEach(c => {
      const key = `${Number(c.lat).toFixed(6)},${Number(c.lng).toFixed(6)}`;
      if (!byCoord.has(key)) byCoord.set(key, []);
      byCoord.get(key).push(c);
    });

    const out = [];
    byCoord.forEach(group => {
      if (group.length === 1) {
        out.push({ ...group[0], displayLat: group[0].lat, displayLng: group[0].lng });
        return;
      }

      group.forEach((c, i) => {
        const angle = (2 * Math.PI * i) / group.length;
        const ring = 1 + Math.floor(i / 8);
        const offset = 0.00012 * ring;
        out.push({
          ...c,
          displayLat: c.lat + Math.sin(angle) * offset,
          displayLng: c.lng + Math.cos(angle) * offset,
        });
      });
    });

    return out;
  }, [groupedMarkers]);

  const filteredClusters = useMemo(() => {
    const clusterMap = new Map();
    filteredCrimes.forEach(c => {
      const key = `${Number(c.lat).toFixed(4)},${Number(c.lng).toFixed(4)}`;
      if (!clusterMap.has(key)) {
        clusterMap.set(key, {
          lat: c.lat,
          lng: c.lng,
          count: 0,
          high_risk_count: 0,
          areas: {},
          crime_types: {},
        });
      }
      const cl = clusterMap.get(key);
      cl.count += 1;
      if (['High', 'Critical'].includes(normalizeRiskLevel(c.risk_level))) cl.high_risk_count += 1;
      const areaLabel = c.area || 'Unknown';
      cl.areas[areaLabel] = (cl.areas[areaLabel] || 0) + 1;
      const ct = c.crime_type || 'Unknown';
      cl.crime_types[ct] = (cl.crime_types[ct] || 0) + 1;
    });

    return Array.from(clusterMap.values()).map(cl => {
      const topArea = Object.entries(cl.areas).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
      const topType = Object.entries(cl.crime_types).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
      return {
        ...cl,
        high_risk_ratio: cl.count > 0 ? cl.high_risk_count / cl.count : 0,
        top_area: topArea[0],
        top_area_count: topArea[1],
        top_type: topType[0],
        top_type_count: topType[1],
      };
    });
  }, [filteredCrimes]);

  // Stable object reference — prevents HeatmapLayer useEffect from re-firing on every render
  const heatGradient = useMemo(() => ({
    0.2: '#2196f3', 0.4: '#00bcd4', 0.6: '#4caf50', 0.8: '#ff9800', 1.0: '#f44336'
  }), []);

  const stats = useMemo(() => {
    const critical = filteredCrimes.filter(c => normalizeRiskLevel(c.risk_level) === 'Critical').length;
    const high = filteredCrimes.filter(c => normalizeRiskLevel(c.risk_level) === 'High').length;
    const med = filteredCrimes.filter(c => normalizeRiskLevel(c.risk_level) === 'Moderate').length;
    const low = filteredCrimes.filter(c => normalizeRiskLevel(c.risk_level) === 'Low').length;
    const typeCounts = {};
    filteredCrimes.forEach(c => { typeCounts[c.crime_type] = (typeCounts[c.crime_type] || 0) + 1; });
    const topType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0];
    return {
      total: filteredCrimes.length,
      critical,
      high,
      med,
      low,
      topType: topType ? topType[0] : '—',
      topTypeCount: topType ? topType[1] : 0,
      clusterCount: filteredClusters.length,
    };
  }, [filteredCrimes, filteredClusters]);

  const handleReset = () => { setCrimeTypeFilter('all'); setRiskFilter('all'); setDateRange({ start: '', end: '' }); };

  return (
    <div className={styles.heatmapPanel}>
      {/* Header */}
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><i className="fas fa-fire"></i></div>
          <div>
            <h3>Advanced Crime Heat Map</h3>
            <p className={styles.headerSub}>Real-time crime density analysis &amp; cluster intelligence</p>
          </div>
        </div>
        <div className={styles.headerControls}>
          <select className={styles.areaSelect} value={selectedArea} onChange={e => setSelectedArea(e.target.value)}>
            <option value="all">All Areas</option>
            {areas.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
          <select
            className={styles.areaSelect}
            value={recordLimit}
            onChange={e => setRecordLimit(Number(e.target.value))}
            title="Number of records to load"
          >
            <option value={500}>500 Records</option>
            <option value={1000}>1,000 Records</option>
            <option value={2000}>2,000 Records</option>
            <option value={5000}>5,000 Records</option>
            <option value={0}>All Records</option>
          </select>
          <button className={styles.refreshBtn} onClick={fetchHeatmapData} disabled={loading}>
            <i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <div className={styles.filterGroup}>
          <label><i className="fas fa-shield-alt"></i> Risk</label>
          <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
            <option value="all">All Levels</option>
            <option value="Critical">Avoid</option>
            <option value="High">Warning</option>
            <option value="Moderate">Caution</option>
            <option value="Low">Safe</option>
          </select>
        </div>
        <div className={styles.filterGroup}>
          <label><i className="fas fa-tag"></i> Type</label>
          <select value={crimeTypeFilter} onChange={e => setCrimeTypeFilter(e.target.value)}>
            {crimeTypes.map(t => <option key={t} value={t}>{t === 'all' ? 'All Types' : t}</option>)}
          </select>
        </div>
        <div className={styles.filterGroup}>
          <label><i className="fas fa-calendar"></i> From</label>
          <input type="date" value={dateRange.start} onChange={e => setDateRange(d => ({ ...d, start: e.target.value }))} />
        </div>
        <div className={styles.filterGroup}>
          <label><i className="fas fa-calendar"></i> To</label>
          <input type="date" value={dateRange.end} onChange={e => setDateRange(d => ({ ...d, end: e.target.value }))} />
        </div>
        <button className={styles.resetBtn} onClick={handleReset} title="Reset filters">
          <i className="fas fa-undo"></i>
        </button>
      </div>

      {/* View Controls */}
      <div className={styles.viewControls}>
        <div className={styles.viewToggle}>
          {['heatmap', 'markers', 'both'].map(mode => (
            <button key={mode} className={`${styles.viewBtn} ${viewMode === mode ? styles.active : ''}`} onClick={() => setViewMode(mode)}>
              <i className={`fas fa-${mode === 'heatmap' ? 'fire' : mode === 'markers' ? 'map-marker-alt' : 'layer-group'}`}></i>
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
        <div className={styles.viewToggle}>
          {Object.entries(MAP_STYLES).map(([key, val]) => (
            <button key={key} className={`${styles.viewBtn} ${mapStyle === key ? styles.active : ''}`} onClick={() => setMapStyle(key)}>
              {val.label}
            </button>
          ))}
        </div>
        <label className={styles.checkLabel}>
          <input type="checkbox" checked={showClusters} onChange={e => setShowClusters(e.target.checked)} />
          Clusters
        </label>
      </div>

      {/* Stats Row */}
      <div className={styles.statsRow}>
        <div className={styles.statBadge}><i className="fas fa-map-pin"></i><span>{stats.total} Records</span></div>
        <div className={`${styles.statBadge} ${styles.highRiskBadge}`}><i className="fas fa-radiation"></i><span>{stats.critical} Avoid</span></div>
        <div className={`${styles.statBadge} ${styles.highRiskBadge}`}><i className="fas fa-exclamation-triangle"></i><span>{stats.high} Warning</span></div>
        <div className={`${styles.statBadge} ${styles.medRiskBadge}`}><i className="fas fa-exclamation-circle"></i><span>{stats.med} Caution</span></div>
        <div className={`${styles.statBadge} ${styles.lowRiskBadge}`}><i className="fas fa-check-circle"></i><span>{stats.low} Safe</span></div>
        <div className={styles.statBadge}><i className="fas fa-crosshairs"></i><span>Top: {stats.topType} ({stats.topTypeCount})</span></div>
        <div className={styles.statBadge}><i className="fas fa-layer-group"></i><span>{stats.clusterCount} Clusters</span></div>
      </div>

      {/* Map */}
      <div className={styles.mapContainer}>
        {loading && (
          <div className={styles.mapOverlay}>
            <div className={styles.spinner}></div>
            <p>Loading data{selectedArea !== 'all' ? ` for ${selectedArea}` : ''}...</p>
          </div>
        )}
        <MapContainer
          key={mapStyle}
          center={mapCenter}
          zoom={mapZoom}
          style={{ width: '100%', height: '100%' }}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          zoomControl={true}
        >
          <ZoomSyncer zoom={mapZoom} />
          <TileLayer url={MAP_STYLES[mapStyle].url} attribution='&copy; OpenStreetMap contributors' />
          {(viewMode === 'heatmap' || viewMode === 'both') && filteredHeatmapPoints.length > 0 && (
            <HeatmapLayer
              points={filteredHeatmapPoints}
              radius={systemSettings?.heatmap_radius || 25}
              blur={Math.round((systemSettings?.heatmap_intensity || 0.6) * 25)}
              maxZoom={17}
              gradient={heatGradient}
            />
          )}
          {(viewMode === 'markers' || viewMode === 'both') && markerDisplayPoints.map((c, i) => (
            <Marker key={`${c.id || 'c'}-${i}`} position={[c.displayLat, c.displayLng]} icon={createRiskIcon(c.risk_level)}>
              <Popup className={styles.crimePopup} maxWidth={250}>
                <div className={styles.popupCard}>
                  {(() => {
                    const level = normalizeRiskLevel(c.risk_level);
                    const color = RISK_COLORS[level] || '#6b7280';
                    return (
                      <>
                  <div className={styles.popupHeader}>
                    <span className={styles.popupDot} style={{ background: color, boxShadow: `0 0 6px ${color}` }}></span>
                    <span className={styles.popupTitle}>Incident Report</span>
                    <span className={styles.popupRiskBadge} style={{ background: `${color}22`, color, borderColor: `${color}55` }}>
                      {actionLabel(level)}
                    </span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Merged Database Rows</span>
                    <span className={styles.popupVal}>{c.row_count}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Mapped Area (OSM / Area Column)</span>
                    <span className={styles.popupVal}>{c.area || '—'}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>FIR Area (English / Transliteration)</span>
                    <span className={styles.popupVal}>{c.area_translit || '—'}</span>
                    {c.area_urdu && <span className={styles.popupUrdu}>{c.area_urdu}</span>}
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Date</span>
                    <span className={styles.popupVal}>{c.date ? new Date(c.date).toLocaleDateString() : '—'}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Time</span>
                    <span className={styles.popupVal}>{c.crime_time || '—'}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Crime Types</span>
                    <ul className={styles.popupCrimeTypeList}>
                      {Object.entries(c.crime_types || {})
                        .sort((a, b) => b[1] - a[1])
                        .map(([ct, count], idx) => (
                          <li key={`${ct}-${idx}`} className={styles.popupCrimeTypeItem}>
                            <span className={styles.popupCrimeTypeName}>{ppcSimpleLabel(ct)}</span>
                            <span className={styles.popupCrimeTypeCount}>x{count}</span>
                          </li>
                        ))}
                    </ul>
                  </div>
                  <div className={styles.popupCoords}>📍 {c.lat.toFixed(4)}, {c.lng.toFixed(4)}</div>
                      </>
                    );
                  })()}
                </div>
              </Popup>
            </Marker>
          ))}
          {showClusters && filteredClusters.map((cl, i) => (
            <CircleMarker key={`cl-${i}`} center={[cl.lat, cl.lng]}
              radius={Math.min(6 + cl.count * 0.5, 25)}
              pathOptions={{ fillColor: cl.high_risk_ratio > 0.5 ? '#ef4444' : cl.high_risk_ratio > 0.25 ? '#f59e0b' : '#22c55e', fillOpacity: 0.45, color: '#fff', weight: 2 }}>
              <Popup className={styles.crimePopup} maxWidth={180}>
                <div className={styles.popupCard}>
                  <div className={styles.popupHeader}>
                    <span className={styles.popupTitle}>Hotspot Cluster</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Filtered Crimes</span>
                    <span className={styles.popupVal}>{cl.count}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Area</span>
                    <span className={styles.popupVal}>{cl.top_area}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Top Type</span>
                    <span className={styles.popupVal}>{ppcSimpleLabel(cl.top_type)} ({cl.top_type_count})</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Warning + Avoid</span>
                    <span className={styles.popupVal} style={{ color: cl.high_risk_ratio > 0.5 ? '#ef4444' : cl.high_risk_ratio > 0.25 ? '#f59e0b' : '#22c55e', fontWeight: 600 }}>
                      {Math.round(cl.high_risk_ratio * 100)}%
                    </span>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      {/* Legend */}
      <div className={styles.legendRow}>
        <span className={styles.legendTitle}>Risk Legend:</span>
        {['Critical', 'High', 'Moderate', 'Low'].map((level) => (
          <span key={level} className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: RISK_COLORS[level] }}></span> {actionLabel(level)}
          </span>
        ))}
      </div>

      {filteredCrimes.length === 0 && !loading && (
        <div className={styles.emptyState}>
          <i className="fas fa-map-marked-alt"></i>
          <h4>No Data Available</h4>
          <p>No crime data found{selectedArea !== 'all' ? ` for ${selectedArea}` : ''} with the selected filters.</p>
        </div>
      )}
    </div>
  );
};

export default CrimeHeatmapPanel;

