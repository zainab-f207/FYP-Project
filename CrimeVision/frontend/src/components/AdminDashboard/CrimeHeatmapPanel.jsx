import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, useMap } from 'react-leaflet';
import { SYSTEM_SETTINGS_DEFAULTS, useSystemSettings } from '../../contexts/SystemSettingsContext';
import HeatmapLayer from '../HeatMapLayer';
import apiService from '../../services/apiService_updated';
import { ppcSimpleLabel } from '../../utils/ppcUtils';
import { calculate_unified_risk_summary } from '../../utils/riskCalculation';
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

const normalizeVisibilityThreshold = (value) => {
  const v = String(value || SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold).toLowerCase();
  if (v === 'critical') return 'Critical';
  if (v === 'high') return 'High';
  if (v === 'medium') return 'Moderate';
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

const normalizeAreaToken = (value) => {
  const raw = String(value || '').trim().replace(/،/g, ',').toLowerCase();
  if (!raw) return '';
  const noParens = raw.replace(/\s*\([^)]*\)\s*$/, '').trim();
  const base = noParens.split(',', 1)[0].trim();
  const noSuffix = base
    .replace(/\s+lahore\s*$/i, '')
    .replace(/\s+pakistan\s*$/i, '')
    .replace(/\s+punjab\s*$/i, '')
    .trim();
  return noSuffix || base;
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
  const { settings: systemSettings, loading: systemSettingsLoading } = useSystemSettings();
  const [selectedArea, setSelectedArea] = useState('all');
  const [areas, setAreas] = useState([]);
  const [rawCrimes, setRawCrimes] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lookbackFallback, setLookbackFallback] = useState(null); // { days } when fallback used
  const [mapCenter, setMapCenter] = useState([
    Number(systemSettings?.map_default_center_lat ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lat),
    Number(systemSettings?.map_default_center_lng ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lng),
  ]);
  const [mapZoom, setMapZoom] = useState(11); // overridden by system settings below
  const [recordLimit, setRecordLimit] = useState(SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
  const [settingsSyncedAt, setSettingsSyncedAt] = useState(() => new Date());
  const initialLoadDone = useRef(false);
  const recordLimitTouchedRef = useRef(false);
  const mapStyleTouchedRef = useRef(false);

  useEffect(() => {
    const configuredLimit = Number(systemSettings?.map_default_record_limit ?? SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
    if (!recordLimitTouchedRef.current && configuredLimit >= 0) {
      setRecordLimit(configuredLimit);
    }
  }, [systemSettings?.map_default_record_limit]);

  useEffect(() => {
    if (selectedArea !== 'all') return;
    const lat = Number(systemSettings?.map_default_center_lat ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lat);
    const lng = Number(systemSettings?.map_default_center_lng ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lng);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      setMapCenter([lat, lng]);
    }
  }, [selectedArea, systemSettings?.map_default_center_lat, systemSettings?.map_default_center_lng]);

  useEffect(() => {
    setSettingsSyncedAt(new Date());
  }, [systemSettings]);

  // Always sync mapZoom from system settings whenever they change (real-time updates)
  useEffect(() => {
    if (systemSettings?.default_map_zoom) {
      const minZoom = Number(systemSettings?.map_min_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_min_zoom);
      const maxZoom = Number(systemSettings?.map_max_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_max_zoom);
      const nextZoom = Number(systemSettings.default_map_zoom);
      setMapZoom(Math.max(minZoom, Math.min(maxZoom, nextZoom)));
    }
  }, [systemSettings?.default_map_zoom, systemSettings?.map_min_zoom, systemSettings?.map_max_zoom]);

  const [crimeTypeFilter, setCrimeTypeFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  const [viewMode, setViewMode] = useState('heatmap');
  const [mapStyle, setMapStyle] = useState(systemSettings?.map_default_style || SYSTEM_SETTINGS_DEFAULTS.map_default_style);

  const canonicalAreaFor = useMemo(() => {
    const variantToCanonical = new Map();
    areas.forEach((a) => {
      if (!a?.name) return;
      const canonical = normalizeAreaToken(a.name);
      if (!canonical) return;
      variantToCanonical.set(canonical, canonical);
      (a.variants || []).forEach((v) => {
        const vt = normalizeAreaToken(v);
        if (vt) variantToCanonical.set(vt, canonical);
      });
    });

    return (raw) => {
      const token = normalizeAreaToken(raw);
      if (!token) return '';
      return variantToCanonical.get(token) || token;
    };
  }, [areas]);

  useEffect(() => {
    const configuredStyle = String(systemSettings?.map_default_style || SYSTEM_SETTINGS_DEFAULTS.map_default_style);
    if (!mapStyleTouchedRef.current && MAP_STYLES[configuredStyle]) {
      setMapStyle(configuredStyle);
    }
  }, [systemSettings?.map_default_style]);
  const [showClusters, setShowClusters] = useState(true);

  // Auto-hide clusters when detail filters are applied (crime type, risk, date)
  // This prevents cluster overlay from blocking heatmap details
  useEffect(() => {
    const hasDetailFilters = crimeTypeFilter !== 'all' || riskFilter !== 'all' || dateRange.start || dateRange.end;
    if (hasDetailFilters) {
      setShowClusters(false);
    }
  }, [crimeTypeFilter, riskFilter, dateRange]);

  const loadAreas = useCallback(async () => {
    try {
      const areaRows = await apiService.getAreas();
      const formatted = (areaRows || [])
        .map(a => ({
          value: a.name,
          label: a.name,
          coordinates: a.coordinates || null,
          record_count: a.record_count || 0,
          variants: Array.isArray(a.variants) ? a.variants : [],
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

    const queryParams = {
      ...limitParam,
      // Don't filter by crime_type here - filter on frontend to preserve full list
    };

    // Auto data-lookback: apply system_settings.data_retention_days as start_date
    // unless the admin set a custom date range. If the lookback returns no rows,
    // retry once without it so a stale DB still shows real data.
    const retentionDays = Number(systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days);
    const lookbackEligible = !dateRange.start && !dateRange.end && retentionDays > 0;
    if (dateRange.start) queryParams.start_date = dateRange.start;
    if (dateRange.end) queryParams.end_date = dateRange.end;
    if (lookbackEligible) {
      const start = new Date();
      start.setDate(start.getDate() - retentionDays);
      queryParams.start_date = start.toISOString().slice(0, 10);
    }

    const fetchCrimesWithFallback = async (params) => {
      const initial = await apiService.getCrimes(params);
      const list = Array.isArray(initial) ? initial : (initial?.crimes || []);
      if (lookbackEligible && list.length === 0) {
        const fallbackParams = { ...params };
        delete fallbackParams.start_date;
        const fallback = await apiService.getCrimes(fallbackParams);
        setLookbackFallback({ days: retentionDays });
        return fallback;
      }
      setLookbackFallback(null);
      return initial;
    };

    try {
      if (selectedArea !== 'all') {
        // Fetch raw records first so marker/filter counts always reflect real incidents
        const crimes = await fetchCrimesWithFallback({ area: selectedArea, ...queryParams });
        const selectedCanonical = canonicalAreaFor(selectedArea);
        
        // DEBUG: Log what we're receiving from backend
        console.log('🔍 DEBUG: Selected Area:', selectedArea);
        console.log('🔍 DEBUG: Selected Canonical:', selectedCanonical);
        console.log('🔍 DEBUG: Crimes returned from backend:', crimes);
        console.log('🔍 DEBUG: Number of crimes:', Array.isArray(crimes) ? crimes.length : crimes?.crimes?.length);
        
        const transformedPoints = transformCrimesToPoints(crimes);
        console.log('🔍 DEBUG: Transformed points (before filter):', transformedPoints);
        console.log('🔍 DEBUG: Areas state:', areas);
        
        const points = transformedPoints.filter((p) => {
          const mappedAreaCanonical = canonicalAreaFor(p.area);
          const firAreaCanonical = canonicalAreaFor(p.area_translit || p.area);
          const passes = mappedAreaCanonical === selectedCanonical || firAreaCanonical === selectedCanonical;
          if (!passes) {
            console.log(`  ❌ Filtered out: p.area="${p.area}", p.area_translit="${p.area_translit}", mapped="${mappedAreaCanonical}", fir="${firAreaCanonical}", selected="${selectedCanonical}"`);
          }
          return passes;
        });
        console.log('🔍 DEBUG: Filtered points (after filter):', points);
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
        const crimes = await fetchCrimesWithFallback({ ...queryParams });
        const points = transformCrimesToPoints(crimes);
        setRawCrimes(points);
        setClusters([]);
        // Keep default Lahore center; only re-center when a specific area is selected
      }
    } catch (err) {
      console.error('Failed to fetch heatmap data:', err);
    } finally { setLoading(false); }
  }, [
    selectedArea,
    canonicalAreaFor,
    recordLimit,
    crimeTypeFilter,
    riskFilter,
    dateRange,
    systemSettings?.data_retention_days,
  ]);

  useEffect(() => {
    if (!initialLoadDone.current) {
      loadAreas();
      initialLoadDone.current = true;
    }
  }, [loadAreas]);

  useEffect(() => {
    // Wait for system settings before the first fetch so the default record
    // limit comes from the configured value (not the JS fallback).
    if (systemSettingsLoading) return;
    fetchHeatmapData();
  }, [fetchHeatmapData, systemSettingsLoading]);

  const crimeTypes = useMemo(() => {
    const types = new Set(rawCrimes.map(c => c.crime_type));
    return ['all', ...Array.from(types).sort()];
  }, [rawCrimes]);

  const filteredCrimes = useMemo(() => {
    const visibilityThreshold = normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold);
    const minRank = { Low: 1, Moderate: 2, High: 3, Critical: 4 }[visibilityThreshold] || 1;

    return rawCrimes.filter(c => {
      const effectiveRisk = normalizeRiskLevel(c.risk_level);
      const currentRank = { Low: 1, Moderate: 2, High: 3, Critical: 4 }[effectiveRisk] || 1;
      if (currentRank < minRank) return false;
      if (crimeTypeFilter !== 'all' && String(c.crime_type || '').trim().toLowerCase() !== String(crimeTypeFilter).trim().toLowerCase()) return false;
      if (riskFilter !== 'all' && effectiveRisk !== riskFilter) return false;
      const crimeDateKey = String(c.date || '').slice(0, 10);
      if (dateRange.start || dateRange.end) {
        const crimeDateObj = crimeDateKey ? new Date(`${crimeDateKey}T00:00:00`) : null;
        if (crimeDateObj && !Number.isNaN(crimeDateObj.getTime())) {
          if (dateRange.start) {
            const startObj = new Date(`${dateRange.start}T00:00:00`);
            if (!Number.isNaN(startObj.getTime()) && crimeDateObj < startObj) return false;
          }
          if (dateRange.end) {
            const endObj = new Date(`${dateRange.end}T23:59:59`);
            if (!Number.isNaN(endObj.getTime()) && crimeDateObj > endObj) return false;
          }
        }
      }
      return true;
    });
  }, [rawCrimes, crimeTypeFilter, riskFilter, dateRange, systemSettings?.map_alert_visibility_threshold]);

  const filteredHeatmapPoints = useMemo(() => {
    return filteredCrimes.map(c => ({
      lat: c.lat, lng: c.lng,
      intensity: intensityFromRisk(c.risk_level)
    }));
  }, [filteredCrimes]);

  const subareaRiskScoreByFIRArea = useMemo(() => {
    const areaLevelCounts = new Map();
    const areaDateData = new Map();
    const now = new Date();
    const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);

    filteredCrimes.forEach((c) => {
      const firSubareaKey = (c.area_translit || c.area || 'Unknown').trim().toLowerCase() || 'unknown';
      if (!areaLevelCounts.has(firSubareaKey)) {
        areaLevelCounts.set(firSubareaKey, { Critical: 0, High: 0, Moderate: 0, Low: 0 });
        areaDateData.set(firSubareaKey, {
          total: 0,
          high_risk_count: 0,
          medium_risk_count: 0,
          last_30_days: 0,
          last_90_days: 0,
          recent_count: 0,
          older_count: 0,
        });
      }
      const bucket = areaLevelCounts.get(firSubareaKey);
      const level = normalizeRiskLevel(c.risk_level);
      bucket[level] = (bucket[level] || 0) + 1;

      const dateData = areaDateData.get(firSubareaKey);
      dateData.total += 1;
      if (level === 'Critical' || level === 'High') dateData.high_risk_count += 1;
      else if (level === 'Moderate') dateData.medium_risk_count += 1;

      const crimeDate = c.date ? new Date(c.date) : null;
      if (crimeDate && !isNaN(crimeDate.getTime())) {
        if (crimeDate >= cutoff_30) dateData.last_30_days += 1;
        if (crimeDate >= cutoff_90) dateData.last_90_days += 1;
        if (crimeDate >= cutoff_45) dateData.recent_count += 1;
        else dateData.older_count += 1;
      }
    });

    const scores = new Map();
    areaLevelCounts.forEach((counts, firSubareaKey) => {
      const dateData = areaDateData.get(firSubareaKey);
      const stats = {
        total_crimes: dateData.total,
        high_risk_count: dateData.high_risk_count,
        medium_risk_count: dateData.medium_risk_count,
        last_30_days: dateData.last_30_days,
        last_90_days: dateData.last_90_days,
        recent_count: dateData.recent_count,
        older_count: dateData.older_count,
      };
      const riskSummary = calculate_unified_risk_summary(stats);
      scores.set(firSubareaKey, riskSummary.risk_score);
    });
    return scores;
  }, [filteredCrimes]);

  const groupedMarkers = useMemo(() => {
    const riskRank = { Low: 1, Moderate: 2, High: 3, Critical: 4 };
    const grouped = new Map();
    const now = new Date();
    const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);

    filteredCrimes.forEach(c => {
      const day = (c.date || '').split(' ')[0] || '';
      const time = (c.crime_time || '').trim();
      const areaKey = (c.area || '').trim().toLowerCase();
      const subareaKey = (c.area_translit || c.area || '').trim().toLowerCase();
      const key = `${areaKey}|${subareaKey}|${day}|${time}|${Number(c.lat).toFixed(6)},${Number(c.lng).toFixed(6)}`;

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
          high_risk_count: 0,
          medium_risk_count: 0,
          last_30_days: 0,
          last_90_days: 0,
          recent_count: 0,
          older_count: 0,
        });
      }

      const g = grouped.get(key);
      g.row_count += 1;
      const rl = normalizeRiskLevel(c.risk_level);
      g.risks[rl] = (g.risks[rl] || 0) + 1;
      const ct = c.crime_type || 'Unknown';
      g.crime_types[ct] = (g.crime_types[ct] || 0) + 1;

      if (rl === 'Critical' || rl === 'High') g.high_risk_count += 1;
      else if (rl === 'Moderate') g.medium_risk_count += 1;

      const crimeDate = c.date ? new Date(c.date) : null;
      if (crimeDate && !isNaN(crimeDate.getTime())) {
        if (crimeDate >= cutoff_30) g.last_30_days += 1;
        if (crimeDate >= cutoff_90) g.last_90_days += 1;
        if (crimeDate >= cutoff_45) g.recent_count += 1;
        else g.older_count += 1;
      }

      if (!g.area_translit && c.area_translit) g.area_translit = c.area_translit;
      if (!g.area_urdu && c.area_urdu) g.area_urdu = c.area_urdu;
      if ((riskRank[rl] || 0) > (riskRank[g.risk_level || 'Low'] || 0)) g.risk_level = rl;
    });

    return Array.from(grouped.values())
      .map((g) => {
        const stats = {
          total_crimes: g.row_count,
          high_risk_count: g.high_risk_count,
          medium_risk_count: g.medium_risk_count,
          last_30_days: g.last_30_days,
          last_90_days: g.last_90_days,
          recent_count: g.recent_count,
          older_count: g.older_count,
        };
        const riskSummary = calculate_unified_risk_summary(stats);

        return {
          ...g,
          risk_score: riskSummary.risk_score,
        };
      });
  }, [filteredCrimes]);

  const filteredClusters = useMemo(() => {
    const clusterMap = new Map();
    const now = new Date();
    const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);

    filteredCrimes.forEach(c => {
      const coordKey = `${Number(c.lat).toFixed(4)},${Number(c.lng).toFixed(4)}`;
      const areaKey = (c.area || 'Unknown').trim().toLowerCase();
      const key = `${coordKey}|${areaKey}`;
      if (!clusterMap.has(key)) {
        clusterMap.set(key, {
          lat: c.lat,
          lng: c.lng,
          coord_key: coordKey,
          area_key: areaKey,
          mapped_area: c.area || 'Unknown',
          count: 0,
          high_risk_count: 0,
          medium_risk_count: 0,
          last_30_days: 0,
          last_90_days: 0,
          recent_count: 0,
          older_count: 0,
          areas: {},
          subareas: {},
          crime_types: {},
        });
      }
      const cl = clusterMap.get(key);
      cl.count += 1;

      const riskLevel = normalizeRiskLevel(c.risk_level);
      if (riskLevel === 'Critical' || riskLevel === 'High') cl.high_risk_count += 1;
      else if (riskLevel === 'Moderate') cl.medium_risk_count += 1;

      // Calculate recency
      const crimeDate = c.date ? new Date(c.date) : null;
      if (crimeDate && !isNaN(crimeDate.getTime())) {
        if (crimeDate >= cutoff_30) cl.last_30_days += 1;
        if (crimeDate >= cutoff_90) cl.last_90_days += 1;
        if (crimeDate >= cutoff_45) cl.recent_count += 1;
        else cl.older_count += 1;
      }

      const mappedAreaLabel = c.area || 'Unknown';
      cl.areas[mappedAreaLabel] = (cl.areas[mappedAreaLabel] || 0) + 1;
      const firSubareaLabel = c.area_translit || c.area || 'Unknown';
      cl.subareas[firSubareaLabel] = (cl.subareas[firSubareaLabel] || 0) + 1;
      const ct = c.crime_type || 'Unknown';
      cl.crime_types[ct] = (cl.crime_types[ct] || 0) + 1;
    });

    return Array.from(clusterMap.values()).map(cl => {
      const topArea = Object.entries(cl.areas).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
      const topSubarea = Object.entries(cl.subareas).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
      const topType = Object.entries(cl.crime_types).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];

      // Use unified risk calculation (matching backend exactly)
      const stats = {
        total_crimes: cl.count,
        high_risk_count: cl.high_risk_count,
        medium_risk_count: cl.medium_risk_count,
        last_30_days: cl.last_30_days,
        last_90_days: cl.last_90_days,
        recent_count: cl.recent_count,
        older_count: cl.older_count,
      };
      const riskSummary = calculate_unified_risk_summary(stats);

      return {
        ...cl,
        high_risk_ratio: (cl.high_risk_count) / cl.count,
        risk_score: riskSummary.risk_score,
        risk_level: riskSummary.risk_level,
        risk_label: riskSummary.risk_label,
        top_area: topArea[0],
        top_area_count: topArea[1],
        top_subarea: topSubarea[0],
        top_subarea_count: topSubarea[1],
        top_type: topType[0],
        top_type_count: topType[1],
      };
    });
  }, [filteredCrimes]);

  const displayClusters = useMemo(() => {
    const byCoord = new Map();
    filteredClusters.forEach((cl) => {
      const key = cl.coord_key || `${Number(cl.lat).toFixed(4)},${Number(cl.lng).toFixed(4)}`;
      if (!byCoord.has(key)) byCoord.set(key, []);
      byCoord.get(key).push(cl);
    });

    const out = [];
    byCoord.forEach((group) => {
      if (group.length === 1) {
        out.push({ ...group[0], displayLat: group[0].lat, displayLng: group[0].lng });
        return;
      }

      group.forEach((cl, i) => {
        const angle = (2 * Math.PI * i) / group.length;
        const ring = 1 + Math.floor(i / 8);
        const offset = 0.00015 * ring;
        out.push({
          ...cl,
          displayLat: cl.lat + Math.sin(angle) * offset,
          displayLng: cl.lng + Math.cos(angle) * offset,
        });
      });
    });

    return out;
  }, [filteredClusters]);

  const areaClusterCenterMap = useMemo(() => {
    const centers = new Map();
    displayClusters.forEach((cl) => {
      const coordKey = `${Number(cl.lat).toFixed(4)},${Number(cl.lng).toFixed(4)}`;
      const areaKey = (cl.area_key || (cl.mapped_area || 'Unknown')).trim().toLowerCase();
      centers.set(`${coordKey}|${areaKey}`, [cl.displayLat, cl.displayLng]);
    });
    return centers;
  }, [displayClusters]);

  const markerDisplayPoints = useMemo(() => {
    // Group crimes by coordinate + area + date + time to show merged data
    const byCoord = new Map();
    groupedMarkers.forEach((marker) => {
      const coordKey = `${Number(marker.lat).toFixed(4)},${Number(marker.lng).toFixed(4)}`;
      if (!byCoord.has(coordKey)) byCoord.set(coordKey, []);
      byCoord.get(coordKey).push(marker);
    });

    const out = [];
    byCoord.forEach((group, groupKey) => {
      const baseLat = group[0].lat;
      const baseLng = group[0].lng;

      if (group.length === 1) {
        out.push({ ...group[0], displayLat: baseLat, displayLng: baseLng });
        return;
      }

      // Multiple markers at same spot - spread them in a circle
      group.forEach((marker, i) => {
        const angle = (2 * Math.PI * i) / group.length;
        const ring = 1 + Math.floor(i / 8);
        const offset = 0.00008 * ring;
        out.push({
          ...marker,
          displayLat: baseLat + Math.sin(angle) * offset,
          displayLng: baseLng + Math.cos(angle) * offset,
        });
      });
    });

    return out;
  }, [groupedMarkers]);

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
            onChange={e => {
              recordLimitTouchedRef.current = true;
              setRecordLimit(Number(e.target.value));
            }}
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

      {lookbackFallback && (
        <div style={{ padding: '10px 14px', margin: '8px 0', background: '#fef3c7', color: '#78350f', borderLeft: '4px solid #f59e0b', borderRadius: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            <i className="fas fa-info-circle" style={{ marginRight: 8 }}></i>
            No incidents in the last {lookbackFallback.days} days (system retention window). Showing all available data instead.
          </span>
          <button onClick={() => setLookbackFallback(null)} style={{ background: 'transparent', border: 'none', color: '#78350f', cursor: 'pointer', fontSize: 14 }}>
            <i className="fas fa-times"></i>
          </button>
        </div>
      )}

      <div className={styles.settingsSnapshotBar}>
        <span className={styles.settingsSnapshotLabel}>Applied from System Settings</span>
        <span className={styles.settingsSnapshotTime}>
          Last synced: {settingsSyncedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
        <span className={`${styles.settingsChip} ${styles.settingsChipBlue}`}>
          Records: {recordLimit === 0 ? 'All records' : Number(recordLimit).toLocaleString()}
        </span>
        <span className={`${styles.settingsChip} ${styles.settingsChipGreen}`}>
          Visibility: {normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold)}+
        </span>
        <span className={`${styles.settingsChip} ${styles.settingsChipAmber}`}>
          Lookback: {Number(systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days)} days
        </span>
        <span className={`${styles.settingsChip} ${styles.settingsChipPurple}`}>
          Hotspot min: {Number(systemSettings?.map_hotspot_min_incidents ?? SYSTEM_SETTINGS_DEFAULTS.map_hotspot_min_incidents)}
        </span>
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
            <button
              key={key}
              className={`${styles.viewBtn} ${mapStyle === key ? styles.active : ''}`}
              onClick={() => {
                mapStyleTouchedRef.current = true;
                setMapStyle(key);
              }}
            >
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
          minZoom={Number(systemSettings?.map_min_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_min_zoom)}
          maxZoom={Number(systemSettings?.map_max_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_max_zoom)}
          maxBounds={[[
            Number(systemSettings?.map_bounds_south ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_south),
            Number(systemSettings?.map_bounds_west ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_west),
          ], [
            Number(systemSettings?.map_bounds_north ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_north),
            Number(systemSettings?.map_bounds_east ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_east),
          ]]}
          maxBoundsViscosity={Number(systemSettings?.map_bounds_viscosity ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_viscosity)}
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
              radius={Number(systemSettings?.heatmap_radius) || SYSTEM_SETTINGS_DEFAULTS.heatmap_radius}
              blur={Number(systemSettings?.heatmap_blur_multiplier) || SYSTEM_SETTINGS_DEFAULTS.heatmap_blur_multiplier}
              minOpacity={Number(systemSettings?.heatmap_intensity) || SYSTEM_SETTINGS_DEFAULTS.heatmap_intensity}
              maxZoom={Number(systemSettings?.heatmap_layer_max_zoom) || SYSTEM_SETTINGS_DEFAULTS.heatmap_layer_max_zoom}
            />
          )}
          {(viewMode === 'markers' || viewMode === 'both') && markerDisplayPoints.map((c, i) => (
            <Marker key={`${c.id || 'c'}-${i}`} position={[c.displayLat, c.displayLng]} icon={createRiskIcon(c.risk_level)}>
              <Popup className={styles.crimePopup} maxWidth={320}>
                <div className={styles.popupCard}>
                  {(() => {
                    const riskScore = subareaRiskScoreByFIRArea.get(String(c.area_translit || c.area || 'Unknown').trim().toLowerCase() || 'unknown') ?? 0;
                    const safetyScore = Math.round(100 - riskScore);
                    const riskClass = riskScore > 50 ? styles.popupScoreHigh : riskScore > 30 ? styles.popupScoreMedium : styles.popupScoreLow;
                    const safetyClass = safetyScore > 80 ? styles.popupScoreLow : safetyScore > 50 ? styles.popupScoreMedium : styles.popupScoreHigh;

                    const crimeTypeEntries = Object.entries(c.crime_types || {}).sort((a, b) => b[1] - a[1]);
                    return (
                      <div className={styles.popupStack}>
                        <div className={styles.popupHero}>
                          <span className={styles.popupLabel}>Merged Database Rows</span>
                          <div className={styles.popupHeroValue}>{c.row_count || 1}</div>
                        </div>

                        <div className={styles.popupSection}>
                          <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>📍</span><span>Mapped Area (OSM / Area Column)</span></div>
                          <div className={styles.popupValueMain}>{c.area || '—'}</div>
                        </div>

                        <div className={styles.popupSection}>
                          <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>🧭</span><span>FIR Area (English / Transliteration)</span></div>
                          <div className={styles.popupValueMain}>{c.area_translit || '—'}</div>
                          {c.area_urdu && <div className={styles.popupValueSubUrdu}>{c.area_urdu}</div>}
                        </div>

                        <div className={styles.popupMetricsGrid}>
                          <div className={styles.popupMetricCard}>
                            <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>⚠</span><span>Risk Score</span></div>
                            <div className={`${styles.popupScoreValue} ${riskClass}`}>{riskScore}%</div>
                          </div>
                          <div className={styles.popupMetricCard}>
                            <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>🛡</span><span>Safety Score</span></div>
                            <div className={`${styles.popupScoreValue} ${safetyClass}`}>{safetyScore}%</div>
                          </div>
                        </div>

                        <div className={styles.popupInlineGrid}>
                          <div className={styles.popupSection}>
                            <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>🗓</span><span>Date</span></div>
                            <div className={styles.popupValueSub}>{c.date ? new Date(c.date).toLocaleDateString() : '—'}</div>
                          </div>
                          <div className={styles.popupSection}>
                            <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>⏰</span><span>Time</span></div>
                            <div className={styles.popupValueSub}>{c.crime_time || '—'}</div>
                          </div>
                        </div>

                        <div className={styles.popupSection}>
                          <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>📑</span><span>Crime Types</span></div>
                          {crimeTypeEntries.length > 0 ? (
                            <ul className={styles.popupCrimeTypeList}>
                              {crimeTypeEntries.map(([ct, count], idx) => (
                                <li key={`${ct}-${idx}`} className={styles.popupCrimeTypeItem}>
                                  <span className={styles.popupCrimeTypeName}>{ppcSimpleLabel(ct)}</span>
                                  <span className={styles.popupCrimeTypeCount}>x{count}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className={styles.popupValueSub}>—</div>
                          )}
                        </div>

                        <div className={styles.popupFooter}>
                          <div className={styles.popupSectionTitle}><span className={styles.popupSectionIcon}>📍</span><span>Coordinates</span></div>
                          <div className={styles.popupCoordsText}>📍 {c.lat.toFixed(4)}, {c.lng.toFixed(4)}</div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </Popup>
            </Marker>
          ))}
          {showClusters && displayClusters.map((cl, i) => (
            <CircleMarker key={`cl-${i}`} center={[cl.displayLat, cl.displayLng]}
              radius={Math.min(4 + cl.count * 0.25, 12)}
              pathOptions={{ fillColor: cl.high_risk_ratio > 0.5 ? '#ef4444' : cl.high_risk_ratio > 0.25 ? '#f59e0b' : '#22c55e', fillOpacity: 0.55, color: 'rgba(255,255,255,0.7)', weight: 1 }}>
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
                    <span className={styles.popupLabel}>Top FIR Sub-area</span>
                    <span className={styles.popupVal}>{cl.top_subarea}</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Top Type</span>
                    <span className={styles.popupVal}>{ppcSimpleLabel(cl.top_type)} ({cl.top_type_count})</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Risk Score</span>
                    <span className={styles.popupVal}>{cl.risk_score}%</span>
                  </div>
                  <div className={styles.popupRow}>
                    <span className={styles.popupLabel}>Safety Score</span>
                    <span className={styles.popupVal} style={{ color: (100 - cl.risk_score) > 80 ? '#22c55e' : (100 - cl.risk_score) > 50 ? '#f59e0b' : '#ef4444', fontWeight: 600 }}>
                      {Math.round(100 - cl.risk_score)}%
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

