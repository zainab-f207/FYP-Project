import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import CrimeMap from '../CrimeMap/CrimeMap_updated';
import apiService from '../../services/apiService_updated';
import { ppcSimpleLabel } from '../../utils/ppcUtils';
import { useAuth } from '../../contexts/AuthContext_updated';
import { SYSTEM_SETTINGS_DEFAULTS, useSystemSettings } from '../../contexts/SystemSettingsContext';
import { calculate_unified_risk_summary } from '../../utils/riskCalculation';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import './CrimeMapInterface_updated.css';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import HeatmapLayer from '../HeatMapLayer';
import TrendStatCard from './components/TrendStatCard';
import SafetyStats from './components/SafetyStats';
import QuickActions from './components/QuickActions';
import EmergencyContacts from './components/EmergencyContacts';

// Fix for default markers in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Enhanced Chart.js theme with modern styling
const updateChartTheme = (isDark) => {
  if (isDark) {
    ChartJS.defaults.color = '#e2e8f0';
    ChartJS.defaults.borderColor = 'rgba(148,163,184,0.15)';
    ChartJS.defaults.plugins.legend.labels.color = '#e2e8f0';
    ChartJS.defaults.plugins.title.color = '#e2e8f0';
    ChartJS.defaults.scale.grid.color = 'rgba(148,163,184,0.12)';
    ChartJS.defaults.scale.ticks.color = '#cbd5e1';
  } else {
    ChartJS.defaults.color = '#374151';
    ChartJS.defaults.borderColor = 'rgba(107,114,128,0.15)';
    ChartJS.defaults.plugins.legend.labels.color = '#374151';
    ChartJS.defaults.plugins.title.color = '#374151';
    ChartJS.defaults.scale.grid.color = 'rgba(107,114,128,0.12)';
    ChartJS.defaults.scale.ticks.color = '#6b7280';
  }
  ChartJS.defaults.font.family = "'Inter', 'Poppins', 'Open Sans', system-ui, sans-serif";
  ChartJS.defaults.font.size = 12;
};

const LAHORE_BOUNDS = [[31.25, 74.05], [31.80, 74.70]];

const normalizeVisibilityThreshold = (value) => {
  const v = String(value || SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold).toLowerCase();
  if (v === 'critical') return 'Critical';
  if (v === 'high') return 'High';
  if (v === 'medium') return 'Medium';
  return 'Low';
};

const riskRank = {
  Low: 1,
  Medium: 2,
  Moderate: 2,
  High: 3,
  Critical: 4,
};

const riskScoreForLevel = (level) => {
  const v = String(level || 'Low').toLowerCase();
  if (v.includes('critical')) return 100;
  if (v.includes('high')) return 80;
  if (v.includes('medium') || v.includes('moderate')) return 55;
  return 30;
};

const normalizeAreaName = (area) => (area || 'Unknown').toString().trim().toLowerCase() || 'unknown';

// Normalize area tokens to match backend canonicalization:
// - replace Urdu comma with ascii comma
// - strip parentheses and their contents
// - split on comma, take first segment
// - remove trailing generic suffixes like 'lahore', 'punjab', 'pakistan'
// - collapse whitespace and lowercase
const normalizeAreaToken = (s) => {
  if (!s) return '';
  let t = String(s).replace(/،/g, ','); // Urdu comma
  // remove parentheses and contents
  t = t.replace(/\(.*?\)/g, '');
  // lower and trim
  t = t.toLowerCase().trim();
  // split on comma, take first meaningful segment
  const first = t.split(',')[0].trim();
  // remove common suffix words
  const cleaned = first.replace(/\b(lahore|punjab|pakistan|city|lahore city)\b/gi, '').trim();
  // remove extra punctuation
  const normalized = cleaned.replace(/[\s\-\._]+/g, ' ').replace(/[^a-z0-9\s]/g, '').trim();
  return normalized;
};

const CrimeMapInterface = ({ predictionData = null, showAdditionalSections = true, initialArea = null }) => {
  const { token, isAuthenticated } = useAuth();
  const { settings: systemSettings, loading: systemSettingsLoading } = useSystemSettings();
  const [activeMode, setActiveMode] = useState('markers');
  const [controlsVisible, setControlsVisible] = useState(true);
  const [activeTab, setActiveTab] = useState('trends');
  const [selectedTimePeriod, setSelectedTimePeriod] = useState('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [filters, setFilters] = useState({});
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [crimes, setCrimes] = useState([]);
  const [areas, setAreas] = useState([]);
  const [locationFilters, setLocationFilters] = useState({});
  const [showResetAlert, setShowResetAlert] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lookbackFallback, setLookbackFallback] = useState(null); // { days } when fallback used
  const [trendsData, setTrendsData] = useState([]);
  const [predictionMultiplier, setPredictionMultiplier] = useState(0.8);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState(null);
  const [hasMoreData, setHasMoreData] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedTile, setSelectedTile] = useState('streets');
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [incidentLimit, setIncidentLimit] = useState(SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
  const [mappedIncidentsLoading, setMappedIncidentsLoading] = useState(false);
  const [showUnmappedList, setShowUnmappedList] = useState(false);
  const [incidentCounts, setIncidentCounts] = useState({
    total: 0,
    mapped: 0,
    unmapped: 0,
    loading: true
  });
  const [availableTiles, setAvailableTiles] = useState([
    { id: 'streets', label: 'Streets', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', icon: 'fa-road' },
    { id: 'basic', label: 'Minimal', url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', icon: 'fa-border-all' },
    { id: 'satellite', label: 'Satellite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', icon: 'fa-satellite' },
    //{ id: 'hybrid', label: 'Hybrid', url: 'https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}', icon: 'fa-layer-group' },
    { id: 'outdoor', label: 'Terrain', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', icon: 'fa-mountain' },
    { id: 'dark', label: 'Dark', url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', icon: 'fa-moon' }
  ]);

  // Load saved map tile preference from localStorage on mount
  useEffect(() => {
    const savedTile = localStorage.getItem('selectedMapTile');
    if (savedTile && availableTiles.find(t => t.id === savedTile)) {
      setSelectedTile(savedTile);
    }
  }, []);

  // Save map tile preference to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('selectedMapTile', selectedTile);
  }, [selectedTile]);
  const [showTileDropdown, setShowTileDropdown] = useState(false);
  const [chartAnimation, setChartAnimation] = useState(true);
  const incidentLimitTouchedRef = useRef(false);
  const tileTouchedRef = useRef(false);

  // Enhanced visualization modes with modern icons
  const visualizationModes = [
    { id: 'markers', label: 'Interactive Map', icon: 'fas fa-map-marked-alt', color: '#3b82f6' },
    { id: 'heatmap', label: 'Heat Analysis', icon: 'fas fa-fire', color: '#ef4444' },
    { id: 'cluster', label: 'Pattern Clusters', icon: 'fas fa-circle-nodes', color: '#8b5cf6' },
    { id: 'timeline', label: 'Time Analysis', icon: 'fas fa-chart-line', color: '#10b981' }
  ];

  // Enhanced time periods
  const timePeriods = [
    { id: '24h', label: '24 Hours', icon: 'fas fa-clock' },
    { id: '7d', label: '7 Days', icon: 'fas fa-calendar-week' },
    { id: '30d', label: '30 Days', icon: 'fas fa-calendar-alt' },
    { id: 'all', label: 'All Time', icon: 'fas fa-infinity' },
    { id: 'custom', label: 'Custom', icon: 'fas fa-edit' }
  ];

  // Enhanced crime type colors for charts
  const crimeTypeColors = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
  ];

  // Update chart theme when theme changes
  useEffect(() => {
    updateChartTheme(isDarkTheme);
  }, [isDarkTheme]);

  // Custom marker icons
  const createCustomIcon = (color) => {
    return L.divIcon({
      className: 'custom-marker',
      html: `
        <div style="
          background: ${color};
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>
      `,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
  };

  const getRiskColor = useCallback((risk) => {
  if (risk === null || risk === undefined) return '#22c55e'; // green for low/unknown

  if (typeof risk === 'string') {
    const r = risk.toLowerCase().trim();
    if (r.includes('critical') || r.includes('avoid')) return '#7c3aed'; // purple
    if (r.includes('high')) return '#ef4444'; // red
    if (r.includes('medium') || r.includes('med')) return '#f59e0b'; // yellow
    if (r.includes('low')) return '#22c55e'; // green

    // Try to parse as number
    const num = parseFloat(r);
    if (!isNaN(num)) {
      if (num >= 3) return '#ef4444'; // red
      if (num >= 2) return '#f59e0b'; // yellow
      return '#22c55e'; // green
    }
  }

  // Handle numeric risk values
  const num = Number(risk);
  if (!isNaN(num)) {
    if (num >= 3) return '#ef4444'; // red
    if (num >= 2) return '#f59e0b'; // yellow
    return '#22c55e'; // green
  }

  return '#22c55e'; // green for unknown
}, []);

// FIXED: Add a function to get consistent risk level text
  const getRiskLevel = useCallback((risk) => {
  if (risk === null || risk === undefined) return 'Low';

  if (typeof risk === 'string') {
    const r = risk.toLowerCase().trim();
    if (r.includes('critical') || r.includes('avoid')) return 'Critical';
    if (r.includes('high')) return 'High';
    if (r.includes('medium') || r.includes('med')) return 'Medium';
    if (r.includes('low')) return 'Low';

    // Try to parse as number
    const num = parseFloat(r);
    if (!isNaN(num)) {
      if (num >= 3) return 'High';
      if (num >= 2) return 'Medium';
      return 'Low';
    }
  }

  // Handle numeric risk values
  const num = Number(risk);
  if (!isNaN(num)) {
    if (num >= 3) return 'High';
    if (num >= 2) return 'Medium';
    return 'Low';
  }

  return 'Low';
}, []);

  useEffect(() => {
    const configuredLimit = Number(systemSettings?.map_default_record_limit ?? SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);
    if (!incidentLimitTouchedRef.current && Number.isFinite(configuredLimit) && configuredLimit >= 0) {
      setIncidentLimit(configuredLimit);
    }
  }, [systemSettings?.map_default_record_limit]);

  useEffect(() => {
    const configuredStyle = String(systemSettings?.map_default_style || SYSTEM_SETTINGS_DEFAULTS.map_default_style);
    const hasConfiguredStyle = availableTiles.some((tile) => tile.id === configuredStyle);
    if (!tileTouchedRef.current && hasConfiguredStyle) {
      setSelectedTile(configuredStyle);
    }
  }, [availableTiles, systemSettings?.map_default_style]);

  // Parse area_translit into structured lines for the popup
  // line1: "LDA City – Sector 5, Block F"
  // line2: "Sub-Block N, Cantt Road"
  const parseAddress = useCallback((translit) => {
    if (!translit) return { line1: null, line2: null };
    let str = translit.trim();

    // 1. Extract trailing road/chowk/street/interchange suffix
    const roadM = str.match(/(?:\s+)([\w][\w\s-]*?\s+(?:Road|Street|Chowk|Bagh|Avenue|Market|Stop|Lane|Bridge|Interchange))\s*$/i);
    const road = roadM ? roadM[1].trim() : null;
    if (roadM) str = str.slice(0, roadM.index).trim();

    // 2. Extract Sub-Block (before regular Block extraction)
    const subBlockM = str.match(/\s+(Sub[-\s]?Block\s+\S+)/i);
    const subBlock = subBlockM ? subBlockM[1].trim() : null;
    if (subBlockM) str = str.slice(0, subBlockM.index).trim();

    // 3. Split society from Sector/Phase part
    const sectorIdx = str.search(/\s+(?=\b(?:Sector|Phase)\b)/i);
    let society, sectorPart, blockPart;
    if (sectorIdx !== -1) {
      society = str.slice(0, sectorIdx).trim();
      let rest = str.slice(sectorIdx).trim();           // "Sector 5 Block F"
      const bIdx = rest.search(/\s+(?=\bBlock\b)/i);
      if (bIdx !== -1) {
        sectorPart = rest.slice(0, bIdx).trim();        // "Sector 5"
        blockPart  = rest.slice(bIdx).trim();           // "Block F"
      } else {
        sectorPart = rest; blockPart = null;
      }
    } else {
      const bIdx = str.search(/\s+(?=\bBlock\b)/i);
      if (bIdx !== -1) {
        society = str.slice(0, bIdx).trim();
        blockPart = str.slice(bIdx).trim();
        sectorPart = null;
      } else {
        society = str; sectorPart = null; blockPart = null;
      }
    }

    // Build line1: "LDA City – Sector 5, Block F"
    const sectorBlock = [sectorPart, blockPart].filter(Boolean).join(', ');
    const line1 = society
      ? (sectorBlock ? `${society} – ${sectorBlock}` : society)
      : (sectorBlock || translit.trim());

    // Build line2: "Sub-Block N, Cantt Road"
    const line2Parts = [subBlock, road].filter(Boolean);
    const line2 = line2Parts.length ? line2Parts.join(', ') : null;

    return { line1: line1 || null, line2 };
  }, []);

  const formatCrimeDate = useCallback((dateStr) => {
    if (!dateStr) return 'Unknown Date';
    try {
      let d;
      // "YYYY-MM-DD" (date-only, no time) — parse as LOCAL midnight to avoid
      // UTC→local offset shifting the displayed date/time forward by +5 h.
      if (/^\d{4}-\d{2}-\d{2}$/.test(String(dateStr).trim())) {
        const [y, m, day] = dateStr.split('-').map(Number);
        d = new Date(y, m - 1, day);       // local midnight — no UTC shift
      } else {
        d = new Date(dateStr);             // includes time → parse normally
      }
      if (isNaN(d.getTime())) return String(dateStr);
      const datePart = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      // Only show time when the original string contained a time component
      const hasTime = String(dateStr).includes(' ') || String(dateStr).includes('T');
      const timePart = hasTime ? d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : null;
      return timePart ? `${datePart} · ${timePart}` : datePart;
    } catch {
      return String(dateStr);
    }
  }, []);

  const formatCrimeDateParts = useCallback((dateStr) => {
    if (!dateStr) return { date: 'Unknown', time: 'Unknown' };
    try {
      let d;
      if (/^\d{4}-\d{2}-\d{2}$/.test(String(dateStr).trim())) {
        const [y, m, day] = dateStr.split('-').map(Number);
        d = new Date(y, m - 1, day);
      } else {
        d = new Date(dateStr);
      }
      if (isNaN(d.getTime())) return { date: String(dateStr), time: 'Unknown' };
      return {
        date: d.toLocaleDateString('en-GB'),
        time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      };
    } catch {
      return { date: String(dateStr), time: 'Unknown' };
    }
  }, []);

  const computeClusters = useCallback((list, gridSize = 0.005) => {
    const grid = {};
    list.forEach(c => {
      const lat = Array.isArray(c.coordinates) ? c.coordinates[0] : c.latitude;
      const lng = Array.isArray(c.coordinates) ? c.coordinates[1] : c.longitude;
      if (typeof lat !== 'number' || typeof lng !== 'number' || !isFinite(lat) || !isFinite(lng)) return;
      const gy = Math.floor(lat / gridSize) * gridSize;
      const gx = Math.floor(lng / gridSize) * gridSize;
      const key = `${gy},${gx}`;
      if (!grid[key]) {
        grid[key] = { count: 0, crimes: [], center: [gy + gridSize / 2, gx + gridSize / 2] };
      }
      grid[key].count++;
      grid[key].crimes.push(c);
    });
    return Object.values(grid).sort((a, b) => b.count - a.count);
  }, []);

  const groupByDay = useCallback((list) => {
    const counts = {};
    list.forEach(c => {
      const d = new Date(c.date);
      if (!isNaN(d.getTime())) {
        const key = d.toISOString().split('T')[0];
        counts[key] = (counts[key] || 0) + 1;
      }
    });
    const labels = Object.keys(counts).sort();
    return { labels, data: labels.map(l => counts[l]) };
  }, []);

  // Fetch data with enhanced error handling
  useEffect(() => {
    // Wait for system settings to load so the default record limit reflects
    // the actual configured value (not the hard-coded JS fallback).
    if (systemSettingsLoading) return;

    const fetchData = async () => {
      try {
        setLoading(true);

        // Build query params based on filters
        const queryParams = {};

        // Record limit: use system setting (or manual if touched)
        let recordLimit = incidentLimitTouchedRef.current
          ? incidentLimit
          : Number(systemSettings?.map_default_record_limit ?? SYSTEM_SETTINGS_DEFAULTS.map_default_record_limit);

        if (recordLimit > 0) {
          queryParams.limit = recordLimit;
        }

        // Auto data-lookback: apply system_settings.data_retention_days as start_date
        // unless the user has set a custom date range. If the lookback returns no
        // crimes (typically because the DB is stale relative to today), retry once
        // without the lookback so the map still shows real data.
        const retentionDays = Number(systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days);
        // Only apply lookback when the user has NOT explicitly chosen "All records"
        // (incidentLimit === 0 means All records). This ensures "All records" truly
        // fetches the full dataset instead of being trimmed by the retention window.
        const lookbackEligible = !customStartDate && !customEndDate && retentionDays > 0 && incidentLimit !== 0;
        if (customStartDate) queryParams.start_date = customStartDate;
        if (customEndDate) queryParams.end_date = customEndDate;
        if (lookbackEligible) {
          const start = new Date();
          start.setDate(start.getDate() - retentionDays);
          queryParams.start_date = start.toISOString().slice(0, 10);
        }

        const [crimeTypesData, crimesDataInitial, areasData] = await Promise.all([
          apiService.getCrimeTypes(),
          apiService.getCrimes(queryParams),
          apiService.getAreas()
        ]);

        let crimesData = crimesDataInitial;
        const initialList = Array.isArray(crimesData) ? crimesData : (crimesData?.crimes || []);
        if (lookbackEligible && initialList.length === 0) {
          // Stale-data fallback: re-fetch without the lookback window
          const fallbackParams = { ...queryParams };
          delete fallbackParams.start_date;
          crimesData = await apiService.getCrimes(fallbackParams);
          setLookbackFallback({ days: retentionDays });
        } else {
          setLookbackFallback(null);
        }

        console.log('Fetched crime types:', crimeTypesData);
        console.log('Fetched crimes:', crimesData);
        console.log('Fetched areas:', areasData);

        setCrimeTypes(Array.isArray(crimeTypesData) ? crimeTypesData : (crimeTypesData.crime_types || []));
        setCrimes(Array.isArray(crimesData) ? crimesData : (crimesData.crimes || []));
        setAreas(Array.isArray(areasData) ? areasData : (areasData.areas || []));
        setInitialLoadComplete(true);
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setDataError('Unable to load crime data from server. Please check your connection and try again.');

        setCrimeTypes([]);
        setCrimes([]);
        setAreas([]);
        setInitialLoadComplete(true);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedTimePeriod, customStartDate, customEndDate, incidentLimit, systemSettings, systemSettingsLoading]);

  // Handle initialArea selection from dashboard/email links / alert cards.
  // Match leniently — exact > prefix > substring — so a deep link from an
  // alert card whose area string differs slightly in casing/punctuation from
  // the canonical name in the `areas` table still narrows the map down.
  useEffect(() => {
    if (initialArea && areas.length > 0) {
      const wanted = String(initialArea)
        .replace(/[-_]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
      if (!wanted) return;

      let areaObj = areas.find(a => (a.name || '').toLowerCase() === wanted);
      if (!areaObj) {
        areaObj = areas.find(a => {
          const n = (a.name || '').toLowerCase();
          return n.startsWith(wanted) || wanted.startsWith(n);
        });
      }
      if (!areaObj) {
        areaObj = areas.find(a => {
          const n = (a.name || '').toLowerCase();
          return n.includes(wanted) || wanted.includes(n);
        });
      }

      if (areaObj) {
        // Clear other filters and select this one. Also drop any active
        // time-period filter so the area's incidents are not hidden by a
        // narrow date window that the user didn't ask for.
        setLocationFilters({ [areaObj.name]: true });
        setFilters({});
        setSelectedTimePeriod('all');
        console.log(`✅ Pre-selected area from deep link: ${areaObj.name}`);
      } else {
        console.warn(`⚠️ Could not match initialArea "${initialArea}" to any known area`);
      }
    }
  }, [initialArea, areas]);

  // Generate mock crimes for demonstration
  const generateMockCrimes = () => {
    const mockCrimes = [];
    const crimeTypes = ['Theft', 'Assault', 'Burglary', 'Vandalism', 'Robbery'];
    const areas = ['Gulberg', 'Defence', 'Cantt', 'Model Town', 'Johar Town'];
    const riskLevels = ['Low', 'Medium', 'High'];

    for (let i = 0; i < 50; i++) {
      mockCrimes.push({
        id: i + 1,
        crime_type: crimeTypes[Math.floor(Math.random() * crimeTypes.length)],
        area: areas[Math.floor(Math.random() * areas.length)],
        date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        latitude: 31.52 + (Math.random() - 0.5) * 0.1,
        longitude: 74.35 + (Math.random() - 0.5) * 0.1,
        risk_level: riskLevels[Math.floor(Math.random() * riskLevels.length)],
        coordinates: null
      });
    }
    return mockCrimes;
  };

  // Track theme changes
  useEffect(() => {
    const updateTheme = () => {
      const dark = document.body.classList.contains('dark-mode') || 
                   document.body.getAttribute('data-theme') === 'dark' ||
                   window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkTheme(dark);
    };

    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.body, { 
      attributes: true, 
      attributeFilter: ['class', 'data-theme'] 
    });

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', updateTheme);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', updateTheme);
    };
  }, []);

  // Enhanced filter functions with animations
  const toggleFilter = useCallback((crimeType) => {
    setFilters(prev => ({
      ...prev,
      [crimeType]: !prev[crimeType]
    }));
  }, []);

  const toggleLocationFilter = useCallback((area) => {
    setLocationFilters(prev => ({
      ...prev,
      [area]: !prev[area]
    }));
  }, []);

  const handleModeChange = useCallback((modeId) => {
    setActiveMode(modeId);
    setChartAnimation(false);
    setTimeout(() => setChartAnimation(true), 100);
  }, []);

  const handleTimePeriodChange = useCallback((periodId) => {
    setSelectedTimePeriod(periodId);
    if (periodId !== 'custom') {
      setCustomStartDate('');
      setCustomEndDate('');
    }
  }, []);

  // Enhanced filtered crimes with better performance - FIXED: Now includes all crimes regardless of coordinates
  const filteredCrimes = useMemo(() => {
    console.log('Filtering crimes...', crimes.length);
    let filtered = [...crimes];

    // If the user has actively selected one or more locations, show all
    // incidents in those locations regardless of the global risk visibility
    // threshold. This ensures selecting "Chuburji" shows all its incidents.
    const activeLocationKeys = Object.keys(locationFilters).filter(key => locationFilters[key]);
    const threshold = normalizeVisibilityThreshold(systemSettings?.map_alert_visibility_threshold ?? SYSTEM_SETTINGS_DEFAULTS.map_alert_visibility_threshold);
    let thresholdRank = riskRank[threshold] || 1;
    if (activeLocationKeys.length > 0) {
      thresholdRank = 1; // lowest rank (show everything)
    }

    // If predictionData is provided, filter crimes to match prediction area, crimeType, and date
    if (predictionData) {
      filtered = filtered.filter(crime => {
        // Area matching for predictionData: be tolerant to spelling variants
        let matchesArea = true;
        if (predictionData.area) {
          // normalize crime area tokens
          const raw = (crime.area || '').toString();
          const cleaned = normalizeAreaToken(raw);

          // build normalized variant set from area cluster
          const areaObj = areas.find(a => String(a?.name || '').toLowerCase() === String(predictionData.area || '').toLowerCase());
          const variantSet = new Set();
          if (areaObj?.variants?.length) {
            for (const v of areaObj.variants) variantSet.add(normalizeAreaToken(v));
            // also add canonical name normalized
            variantSet.add(normalizeAreaToken(areaObj.name));
          } else {
            variantSet.add(normalizeAreaToken(predictionData.area));
          }

          matchesArea = variantSet.has(cleaned) || variantSet.has(normalizeAreaToken(raw));
        }

        const matchesCrimeType = predictionData.crimeType ? (crime.crime_type || '').toLowerCase() === predictionData.crimeType.toLowerCase() : true;
        const matchesDate = predictionData.date ? (new Date(crime.date).toDateString() === new Date(predictionData.date).toDateString()) : true;
        return matchesArea && matchesCrimeType && matchesDate;
      });
    }

    // Filter by crime types
    const activeFilters = Object.keys(filters).filter(key => filters[key]);
    if (activeFilters.length > 0) {
      filtered = filtered.filter(crime =>
        activeFilters.some(filter =>
          filter.toLowerCase().trim() === (crime.crime_type || '').toLowerCase().trim()
        )
      );
    }

    // Filter by locations.
    // The /api/areas response clusters spelling variants under one canonical
    // name, but crime rows still carry the raw spelling (e.g. "Allama Iqbal
    // Town", "Iqbal Town, Lahore"). Match against the cluster's `variants`
    // list so a chip labelled "Iqbal Town" picks up every variant.
    const activeLocations = Object.keys(locationFilters).filter(key => locationFilters[key]);
    console.log('🔍 DEBUG FILTER: activeLocations:', activeLocations);
    console.log('🔍 DEBUG FILTER: areas state:', areas);
    if (activeLocations.length > 0) {
      const variantSet = new Set();
      for (const loc of activeLocations) {
        console.log(`  Searching for area with name="${loc}"`);
        const areaObj = areas.find(a => String(a?.name || '').toLowerCase() === String(loc || '').toLowerCase());
        console.log(`  Found areaObj:`, areaObj);
        if (areaObj?.variants?.length) {
          for (const v of areaObj.variants) variantSet.add(normalizeAreaToken(v));
          variantSet.add(normalizeAreaToken(areaObj.name));
        } else {
          variantSet.add(normalizeAreaToken(loc));
        }
      }
      console.log('🔍 DEBUG FILTER: variantSet:', Array.from(variantSet));
      filtered = filtered.filter(crime => {
        const raw = (crime.area || crime.area_translit || '').toString();
        if (!raw) return false;
        const cleaned = normalizeAreaToken(raw);

        // First, prefer cluster-aware canonical match (precise): if the
        // canonical area for this crime equals the selected canonical name,
        // include it. This mirrors the backend clustering behavior.
        try {
          const canonical = canonicalAreaFor(raw);
          if (canonical && activeLocations.some(l => String(l).toLowerCase() === String(canonical).toLowerCase())) {
            return true;
          }
        } catch (e) {
          // ignore and fallback to normalized matching
        }

        // Exact normalized match against any variant
        if (variantSet.has(cleaned)) return true;

        // Looser prefix-based matches for cases like "chuburji underpass ..." -> "chuburji"
        for (const v of variantSet) {
          if (!v) continue;
          if (cleaned.startsWith(v)) return true;
          if (v.startsWith(cleaned)) return true;
        }

        console.log(`  ❌ Crime area="${crime.area}" (cleaned="${cleaned}") not matched for selected areas`, Array.from(variantSet).slice(0,6));
        return false;
      });
    }

    // Filter by time period
    const now = new Date();
    let timeFilter = null;

    switch (selectedTimePeriod) {
      case '24h':
        timeFilter = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        timeFilter = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        timeFilter = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'custom':
        if (customStartDate && customEndDate) {
          const startDate = new Date(customStartDate);
          const endDate = new Date(customEndDate);
          endDate.setHours(23, 59, 59, 999);
          if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
            timeFilter = { start: startDate, end: endDate };
          }
        }
        break;
      default:
        break;
    }

    if (timeFilter) {
      if (typeof timeFilter === 'object') {
        filtered = filtered.filter(crime => {
          try {
            const crimeDate = new Date(crime.date);
            return !isNaN(crimeDate.getTime()) && crimeDate >= timeFilter.start && crimeDate <= timeFilter.end;
          } catch (error) {
            console.error('Error parsing crime date:', crime.date, error);
            return false;
          }
        });
      } else {
        filtered = filtered.filter(crime => {
          try {
            const crimeDate = new Date(crime.date);
            return !isNaN(crimeDate.getTime()) && crimeDate >= timeFilter;
          } catch (error) {
            console.error('Error parsing crime date:', crime.date, error);
            return false;
          }
        });
      }
    }

    filtered = filtered.filter((crime) => {
      const risk = getRiskLevel(crime.risk_level);
      return (riskRank[risk] || 1) >= thresholdRank;
    });

    console.log('Filtered crimes count (all):', filtered.length);
    return filtered;
  }, [crimes, areas, filters, locationFilters, selectedTimePeriod, customStartDate, customEndDate, predictionData, systemSettings?.map_alert_visibility_threshold, getRiskLevel]);

// FIXED: More lenient mappable crimes logic
const mappableCrimes = useMemo(() => {
  return filteredCrimes.filter(crime => {
    // Try multiple ways to get coordinates
    let lat, lng;
    
    if (Array.isArray(crime.coordinates) && crime.coordinates.length >= 2) {
      [lat, lng] = crime.coordinates;
    } else if (crime.latitude !== undefined && crime.longitude !== undefined) {
      lat = crime.latitude;
      lng = crime.longitude;
    } else if (crime.lat !== undefined && crime.lng !== undefined) {
      lat = crime.lat;
      lng = crime.lng;
    } else {
      console.log('Crime has no coordinates:', crime.id, crime.crime_type, crime.area);
      return false; // No coordinates found
    }

    // Convert to numbers if they're strings
    lat = parseFloat(lat);
    lng = parseFloat(lng);

    // Check if coordinates are valid numbers
    if (isNaN(lat) || isNaN(lng) || !isFinite(lat) || !isFinite(lng)) {
      console.log('Crime has invalid coordinates:', crime.id, {lat, lng});
      return false;
    }

    // Remove strict bounds checking for now to see all crimes
    // Just ensure they're not exactly 0,0
    if (lat === 0 && lng === 0) {
      console.log('Crime has 0,0 coordinates:', crime.id);
      return false;
    }

    // For debugging
    console.log('Mappable crime:', crime.id, crime.crime_type, crime.area, {lat, lng});
    
    return true; // Include all crimes with valid coordinates
  });
}, [filteredCrimes]);

// Add debugging to see what's happening
// FIXED: Move displayCrimes definition BEFORE the useEffect that uses it
// IMPORTANT: When filters are active, show ALL filtered crimes (ignore incident limit)
// When no filters are active, apply incident limit
const displayCrimes = useMemo(() => {
  const hasActiveFilters = Object.keys(filters).some(k => filters[k]) ||
                          Object.keys(locationFilters).some(k => locationFilters[k]) ||
                          predictionData !== null ||
                          selectedTimePeriod !== 'all';

  if (incidentLimit === 0) {
    return filteredCrimes;
  }

  // If filters are active, show ALL filtered crimes (no limit)
  // If no filters, apply the incident limit
  return hasActiveFilters ? filteredCrimes : filteredCrimes.slice(0, incidentLimit);
}, [filteredCrimes, incidentLimit, filters, locationFilters, predictionData, selectedTimePeriod]);

// FIXED: Add renderedCrimes to ensure count matches actual markers shown on map
const renderedCrimes = useMemo(() => {
  return displayCrimes.filter(crime => {
    const lat = Array.isArray(crime.coordinates) ? crime.coordinates[0] : crime.latitude;
    const lng = Array.isArray(crime.coordinates) ? crime.coordinates[1] : crime.longitude;
    const numLat = parseFloat(lat);
    const numLng = parseFloat(lng);
    return !(isNaN(numLat) || isNaN(numLng) || !isFinite(numLat) || !isFinite(numLng) || (numLat === 0 && numLng === 0));
  });
}, [displayCrimes]);

// Variant → canonical name lookup so spelling variants ("Chuburji" vs
// "Chauburji") merge into the same marker / heatmap cluster instead of
// stacking on sibling pins.
const canonicalAreaFor = useMemo(() => {
  const variantToCanonical = new Map();
  areas.forEach((a) => {
    if (!a?.name) return;
    variantToCanonical.set(a.name.toLowerCase().trim(), a.name);
    (a.variants || []).forEach((v) => {
      if (v) variantToCanonical.set(String(v).toLowerCase().trim(), a.name);
    });
  });
  return (raw) => {
    const t = (raw || '').toLowerCase().trim();
    if (!t) return null;
    if (variantToCanonical.has(t)) return variantToCanonical.get(t);
    const cleaned = t.split(',')[0].trim();
    if (variantToCanonical.has(cleaned)) return variantToCanonical.get(cleaned);
    return null;
  };
}, [areas]);

const plottedMarkers = useMemo(() => {
  const byCoord = new Map();

  renderedCrimes.forEach((crime) => {
    const latRaw = Array.isArray(crime.coordinates) ? crime.coordinates[0] : crime.latitude;
    const lngRaw = Array.isArray(crime.coordinates) ? crime.coordinates[1] : crime.longitude;
    const lat = Number(latRaw);
    const lng = Number(lngRaw);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

    const coordKey = `${lat.toFixed(6)},${lng.toFixed(6)}`;
    const subarea = (crime.area_translit || crime.area || 'Unknown').trim() || 'Unknown';
    // FIXED: Group by raw subarea name (not canonical) to show distinct subareas separately
    // This preserves subarea distinctions (e.g., "Allama Iqbal Town" vs "Iqbal Town East")
    // while still merging spelling variants (e.g., "Allama Iqbal Town" and "Allama Iqbal Town, Lahore")
    const subareaKey = subarea.toLowerCase();

    if (!byCoord.has(coordKey)) {
      byCoord.set(coordKey, new Map());
    }

    const coordGroup = byCoord.get(coordKey);
    if (!coordGroup.has(subareaKey)) {
      coordGroup.set(subareaKey, {
        key: `${coordKey}|${subareaKey}`,
        lat,
        lng,
        subarea,
        area: (crime.area || 'Unknown').trim() || 'Unknown',
        area_urdu: crime.area_urdu || null,
        crimes: [],
      });
    }

    coordGroup.get(subareaKey).crimes.push(crime);
  });

  const out = [];
  byCoord.forEach((coordGroup) => {
    const subareaGroups = Array.from(coordGroup.values());
    subareaGroups.forEach((group, index) => {
      const angle = (2 * Math.PI * index) / Math.max(subareaGroups.length, 1);
      const ring = 1 + Math.floor(index / 8);
      const offset = subareaGroups.length > 1 ? 0.00012 * ring : 0;
      const riskLevel = group.crimes.reduce((highest, crime) => {
        const current = getRiskLevel(crime.risk_level);
        return (riskRank[current] || 1) > (riskRank[highest] || 1) ? current : highest;
      }, 'Low');

      const crimeTypes = {};
      const areaCounts = {};
      let highRiskCount = 0;
      let moderateCount = 0;
      let last_30_days = 0;
      let last_90_days = 0;
      let recent_count = 0;
      let older_count = 0;
      const now = new Date();
      const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);
      group.crimes.forEach((crime) => {
        const crimeType = crime.crime_type || 'Unknown';
        crimeTypes[crimeType] = (crimeTypes[crimeType] || 0) + 1;
        const areaName = (crime.area || 'Unknown').trim() || 'Unknown';
        areaCounts[areaName] = (areaCounts[areaName] || 0) + 1;
        const lvl = getRiskLevel(crime.risk_level);
        if (lvl === 'High' || lvl === 'Critical') highRiskCount += 1;
        else if (lvl === 'Moderate') moderateCount += 1;

        const crimeDate = crime.date ? new Date(crime.date) : null;
        if (crimeDate && !isNaN(crimeDate.getTime())) {
          if (crimeDate >= cutoff_30) last_30_days += 1;
          if (crimeDate >= cutoff_90) last_90_days += 1;
          if (crimeDate >= cutoff_45) recent_count += 1;
          else older_count += 1;
        }
      });

      const topType = Object.entries(crimeTypes).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
      const warningAvoidPct = group.crimes.length ? Math.round((highRiskCount / group.crimes.length) * 100) : 0;
      const stats = {
        total_crimes: group.crimes.length,
        high_risk_count: highRiskCount,
        medium_risk_count: moderateCount,
        last_30_days,
        last_90_days,
        recent_count,
        older_count,
      };
      const riskSummary = calculate_unified_risk_summary(stats);
      const riskScore = riskSummary.risk_score;

      out.push({
        ...group,
        count: group.crimes.length,
        highestRisk: riskLevel,
        crime_types: crimeTypes,
        area_counts: areaCounts,
        warning_avoid_pct: warningAvoidPct,
        risk_score: riskScore,
        top_type: topType[0],
        top_type_count: topType[1],
        displayLat: group.lat + Math.sin(angle) * offset,
        displayLng: group.lng + Math.cos(angle) * offset,
      });
    });
  });

  return out;
}, [renderedCrimes, getRiskLevel]);

const heatmapClusterSummaryMap = useMemo(() => {
  const grouped = new Map();
  const now = new Date();
  const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
  const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);

  displayCrimes.forEach((crime) => {
    const lat = Array.isArray(crime.coordinates) ? crime.coordinates[0] : crime.latitude;
    const lng = Array.isArray(crime.coordinates) ? crime.coordinates[1] : crime.longitude;
    if (typeof lat !== 'number' || typeof lng !== 'number' || !isFinite(lat) || !isFinite(lng)) return;

    const coordKey = `${Number(lat).toFixed(4)},${Number(lng).toFixed(4)}`;
    const rawAreaName = (crime.area || 'Unknown').trim() || 'Unknown';
    // Use canonical area for the cluster key so spelling variants merge.
    const areaName = canonicalAreaFor(rawAreaName) || rawAreaName;
    const areaKey = normalizeAreaName(areaName);
    const key = `${coordKey}|${areaKey}`;

    if (!grouped.has(key)) {
      grouped.set(key, {
        count: 0,
        top_area: areaName,
        areaCounts: {},
        subareaCounts: {},
        typeCounts: {},
        criticalCount: 0,
        highCount: 0,
        moderateCount: 0,
        lowCount: 0,
        last_30_days: 0,
        last_90_days: 0,
        recent_count: 0,
        older_count: 0,
      });
    }

    const summary = grouped.get(key);
    summary.count += 1;
    const mappedArea = areaName;
    const firSubarea = (crime.area_translit || crime.area || 'Unknown').trim() || 'Unknown';
    const typeName = crime.crime_type || 'Unknown';
    const level = getRiskLevel(crime.risk_level);

    summary.areaCounts[mappedArea] = (summary.areaCounts[mappedArea] || 0) + 1;
    summary.subareaCounts[firSubarea] = (summary.subareaCounts[firSubarea] || 0) + 1;
    summary.typeCounts[typeName] = (summary.typeCounts[typeName] || 0) + 1;

    if (level === 'Critical') summary.criticalCount += 1;
    else if (level === 'High') summary.highCount += 1;
    else if (level === 'Moderate') summary.moderateCount += 1;
    else summary.lowCount += 1;

    // Calculate recency
    const crimeDate = crime.date ? new Date(crime.date) : null;
    if (crimeDate && !isNaN(crimeDate.getTime())) {
      if (crimeDate >= cutoff_30) summary.last_30_days += 1;
      if (crimeDate >= cutoff_90) summary.last_90_days += 1;
      if (crimeDate >= cutoff_45) summary.recent_count += 1;
      else summary.older_count += 1;
    }
  });

  const summaries = new Map();
  grouped.forEach((summary, key) => {
    const topArea = Object.entries(summary.areaCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
    const topSubarea = Object.entries(summary.subareaCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
    const topType = Object.entries(summary.typeCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];

    // Use unified risk calculation (matching backend exactly)
    const stats = {
      total_crimes: summary.count,
      high_risk_count: summary.criticalCount + summary.highCount,
      medium_risk_count: summary.moderateCount,
      last_30_days: summary.last_30_days,
      last_90_days: summary.last_90_days,
      recent_count: summary.recent_count,
      older_count: summary.older_count,
    };
    const riskSummary = calculate_unified_risk_summary(stats);
    const warningAvoidPct = summary.count > 0 ? Math.round(((summary.criticalCount + summary.highCount) / summary.count) * 100) : 0;

    summaries.set(key, {
      ...summary,
      top_area: topArea[0],
      top_subarea: topSubarea[0],
      top_type: topType[0],
      top_type_count: topType[1],
      warning_avoid_pct: warningAvoidPct,
      risk_score: riskSummary.risk_score,
    });
  });

  return summaries;
}, [displayCrimes, canonicalAreaFor, getRiskLevel]);

// FIXED: Move debugging useEffect AFTER displayCrimes is defined
useEffect(() => {
  console.log('=== CRIME DATA DEBUG ===');
  console.log('Total crimes:', crimes.length);
  console.log('Filtered crimes:', filteredCrimes.length);
  console.log('Mappable crimes:', mappableCrimes.length);
  console.log('Display crimes:', displayCrimes.length);
  
  // Log the difference between filtered and mappable
  if (filteredCrimes.length !== mappableCrimes.length) {
    const unmapped = filteredCrimes.filter(fc => 
      !mappableCrimes.some(mc => mc.id === fc.id)
    );
    console.log('Unmapped crimes:', unmapped);
  }
}, [crimes, filteredCrimes, mappableCrimes, displayCrimes]);

// Progressive loading effect for mapped incidents
useEffect(() => {
  if (displayCrimes.length > 0 && mappableCrimes.length > 0) {
    setMappedIncidentsLoading(true);
    const timer = setTimeout(() => {
      setMappedIncidentsLoading(false);
    }, 300);
    return () => clearTimeout(timer);
  }
}, [displayCrimes, mappableCrimes]);

// Calculate unmapped incidents
const unmappedCrimes = useMemo(() => {
  return filteredCrimes.filter(fc =>
    !mappableCrimes.some(mc => mc.id === fc.id)
  );
}, [filteredCrimes, mappableCrimes]);

// Update incident counts with progressive loading effect
useEffect(() => {
  if (displayCrimes.length > 0) {
    // First, show mapped count immediately
    setIncidentCounts(prev => ({
      ...prev,
      mapped: displayCrimes.length,
      loading: true
    }));

    // Then show all counts after a short delay for progressive loading effect
    const timer = setTimeout(() => {
      setIncidentCounts({
        total: displayCrimes.length,
        mapped: displayCrimes.length,
        unmapped: 0,
        loading: false
      });
    }, 300); // 300ms delay for progressive loading

    return () => clearTimeout(timer);
  } else {
    // Reset when no data
    setIncidentCounts({
      total: 0,
      mapped: 0,
      unmapped: 0,
      loading: false
    });
  }
}, [displayCrimes.length]);

  const getCountForFilter = useCallback((filterType, filterValue) => {
  return displayCrimes.filter(crime => {
    if (filterType === 'crime_type') {
      return (crime.crime_type || '').toLowerCase().trim() === filterValue.toLowerCase().trim();
    } else if (filterType === 'area') {
      return (crime.area || '').toLowerCase().trim() === filterValue.toLowerCase().trim();
    }
    return false;
  }).length;
}, [displayCrimes]);

 const analyticsData = useMemo(() => {
  if (crimeTypes.length === 0 || displayCrimes.length === 0) {
    console.log('No data for analytics');
    return [];
  }
    const data = crimeTypes.slice(0, 8).map((type, index) => {
    const typeCrimes = displayCrimes.filter(crime =>
      (crime.crime_type || '').toLowerCase().trim() === type.toLowerCase().trim()
    );
    const count = typeCrimes.length;
    const percentage = displayCrimes.length > 0 ? Math.round((count / displayCrimes.length) * 100) : 0;

    return {
      type,
      count,
      percentage,
      color: crimeTypeColors[index % crimeTypeColors.length]
    };
  }).filter(item => item.count > 0).sort((a, b) => b.count - a.count);

  console.log('Analytics data:', data);
  return data;
}, [crimeTypes, displayCrimes]);

const keyMetrics = useMemo(() => {
  if (displayCrimes.length === 0) {
    return {
      totalIncidents: 0,
      weeklyChange: 0,
      highRiskShare: 0,
      averageResponse: 0,
      areasAffected: 0
    };
  }

  const totalIncidents = displayCrimes.length;
  const areasAffected = new Set(displayCrimes.map(crime => crime.area)).size;

  // Use consistent risk calculation
  const highRiskCount = displayCrimes.filter(crime =>
    getRiskLevel(crime.risk_level) === 'High'
  ).length;

  const highRiskShare = totalIncidents > 0 ? Math.round((highRiskCount / totalIncidents) * 100) : 0;

  return {
    totalIncidents,
    weeklyChange: 12.5,
    highRiskShare,
    averageResponse: 24,
    areasAffected
  };
}, [displayCrimes, getRiskLevel]);

  const insightsData = useMemo(() => {
  if (displayCrimes.length === 0) return [];

  const insights = [];
  const hourCounts = {};
  const areaCounts = {};
  const typeCounts = {};

  displayCrimes.forEach(crime => {
    // Peak hours analysis
    try {
      const hour = new Date(crime.date).getHours();
      if (!isNaN(hour)) hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    } catch (error) {
      console.error('Error parsing date for insights:', crime.date);
    }

    // Area analysis
    const area = crime.area || 'Unknown';
    areaCounts[area] = (areaCounts[area] || 0) + 1;

    // Type analysis
    const type = crime.crime_type || 'Unknown';
    typeCounts[type] = (typeCounts[type] || 0) + 1;
  });

    if (Object.keys(hourCounts).length > 0) {
      const peakHour = Object.keys(hourCounts).reduce((a, b) => hourCounts[a] > hourCounts[b] ? a : b);
      insights.push({
        title: 'Peak Activity Hours',
        description: `Highest crime activity between ${peakHour}:00-${(parseInt(peakHour)+1)%24}:00`,
        icon: 'fas fa-clock',
        type: 'time'
      });
    }

    if (Object.keys(areaCounts).length > 0) {
      const highRiskArea = Object.keys(areaCounts).reduce((a, b) => areaCounts[a] > areaCounts[b] ? a : b);
      insights.push({
        title: 'Risk Hotspot',
        description: `${highRiskArea} shows concentrated activity patterns`,
        icon: 'fas fa-map-marker-alt',
        type: 'location'
      });
    }

    if (Object.keys(typeCounts).length > 0) {
      const mostCommonType = Object.keys(typeCounts).reduce((a, b) => typeCounts[a] > typeCounts[b] ? a : b);
      insights.push({
        title: 'Dominant Crime Type',
        description: `${mostCommonType} represents significant activity share`,
        icon: 'fas fa-chart-pie',
        type: 'trend'
      });
    }

    insights.push({
    title: 'Data Coverage',
    description: `Analyzing ${displayCrimes.length} incidents across ${Object.keys(areaCounts).length} locations`,
    icon: 'fas fa-database',
    type: 'summary'
  });

  return insights;
}, [displayCrimes]);

const fetchTrendsData = useCallback(async () => {
  try {
    setDataLoading(true);
    setDataError(null);

    const apiFilters = {};
    const now = new Date();

    switch (selectedTimePeriod) {
      case '24h':
        apiFilters.start_date = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        apiFilters.end_date = now.toISOString().split('T')[0];
        break;
      case '7d':
        apiFilters.start_date = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        apiFilters.end_date = now.toISOString().split('T')[0];
        break;
      case '30d':
        apiFilters.start_date = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        apiFilters.end_date = now.toISOString().split('T')[0];
        break;
      case 'custom':
        if (customStartDate && customEndDate) {
          apiFilters.start_date = customStartDate;
          apiFilters.end_date = customEndDate;
        }
        break;
      default:
        break;
    }

    const activeFilters = Object.keys(filters).filter(k => filters[k]);
    if (activeFilters.length === 1) {
      apiFilters.crime_type = activeFilters[0];
    }

    const activeLocations = Object.keys(locationFilters).filter(k => locationFilters[k]);
    if (activeLocations.length === 1) {
      apiFilters.area = activeLocations[0];
    }

    // Try to fetch from API if authenticated
    if (token && isAuthenticated) {
      try {
        console.log('Fetching trends data with token...');
        const response = await apiService.getCrimeSummaryReport(token, apiFilters);
        console.log('Trends API response:', response);

        if (response && Array.isArray(response.monthly_trend)) {
          const trends = response.monthly_trend.map(item => ({
            month: item.month || 'Unknown',
            crimes: item.count || 0
          }));
          setTrendsData(trends);
          return;
        }
      } catch (apiError) {
        console.warn('API trends fetch unavailable, using local data:', apiError.message);
      }
    }

    console.log('Generating trends from local data (REAL DATA ONLY)...');
    const monthlyData = {};
    displayCrimes.forEach(crime => {
      try {
        const date = new Date(crime.date);
        if (!isNaN(date.getTime())) {
          const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
          monthlyData[monthKey] = (monthlyData[monthKey] || 0) + 1;
        }
      } catch (error) {
        console.error('Error processing crime date for trends:', crime.date);
      }
    });

    // If we have very few data points, fill in missing months to show a better trend
    const sortedMonths = Object.keys(monthlyData).sort();
    if (sortedMonths.length > 0 && sortedMonths.length < 3) {
      // Add previous months with 0 counts to show context
      const latestMonth = sortedMonths[sortedMonths.length - 1];
      const [year, month] = latestMonth.split('-').map(Number);
      const latestDate = new Date(year, month - 1, 1);

      // Add 5 months before the latest month
      for (let i = 5; i >= 1; i--) {
        const prevDate = new Date(latestDate);
        prevDate.setMonth(prevDate.getMonth() - i);
        const prevMonthKey = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;
        if (!monthlyData[prevMonthKey]) {
          monthlyData[prevMonthKey] = 0;
        }
      }
    }

    const trends = Object.keys(monthlyData).sort().map(month => ({
      month,
      crimes: monthlyData[month]
    }));

    console.log('Trends data generated:', trends);
    setTrendsData(trends);

  } catch (error) {
    console.error('Unexpected error in trends data fetch:', error);
    setDataError('Failed to load trends data');
    setTrendsData([]);
  } finally {
    setDataLoading(false);
  }
}, [token, isAuthenticated, selectedTimePeriod, customStartDate, customEndDate, displayCrimes, filters, locationFilters]);

  // Load trends data when dependencies change
  useEffect(() => {
    if (activeTab === 'trends') {
      fetchTrendsData();
    }
  }, [activeTab, fetchTrendsData]);

  // Enhanced trends data with modern chart structure - REAL DATA ONLY
  const trendsChartData = useMemo(() => {
    if (trendsData.length === 0) {
      return {
        labels: [],
        datasets: [
          {
            label: 'FIR Incidents',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            fill: true,
            borderWidth: 3
          }
        ]
      };
    }

    return {
      labels: trendsData.map(item => item.month),
      datasets: [
        {
          label: 'FIR Incidents (Real Data)',
          data: trendsData.map(item => item.crimes),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
          fill: true,
          borderWidth: 3
        }
      ]
    };
  }, [trendsData]);

  // Enhanced analytics chart data
  const analyticsChartData = useMemo(() => {
    return {
      labels: analyticsData.map(item => item.type),
      datasets: [
        {
          data: analyticsData.map(item => item.count),
          backgroundColor: analyticsData.map(item => item.color),
          borderWidth: 2,
          borderColor: isDarkTheme ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.1)',
          hoverOffset: 15
        }
      ]
    };
  }, [analyticsData, isDarkTheme]);

  // Enhanced bar chart data for crime distribution
  const barChartData = useMemo(() => {
    return {
      labels: analyticsData.map(item => item.type),
      datasets: [
        {
          label: 'Incidents by Type',
          data: analyticsData.map(item => item.count),
          backgroundColor: analyticsData.map(item => item.color),
          borderColor: analyticsData.map(item => item.color),
          borderWidth: 1,
          borderRadius: 6
        }
      ]
    };
  }, [analyticsData]);

  // Chart options with modern styling
  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: chartAnimation ? {
      duration: 1000,
      easing: 'easeOutQuart'
    } : false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: isDarkTheme ? '#e2e8f0' : '#0f172a',
          usePointStyle: true,
          padding: 15,
          font: {
            size: 11,
            weight: '500'
          }
        }
      },
      tooltip: {
        backgroundColor: isDarkTheme ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        titleColor: isDarkTheme ? '#e2e8f0' : '#1e293b',
        bodyColor: isDarkTheme ? '#e2e8f0' : '#1e293b',
        borderColor: isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.2)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 6,
        displayColors: true,
        titleFont: {
          size: 12
        },
        bodyFont: {
          size: 11
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        display: true,
        grid: {
          color: isDarkTheme ? 'rgba(148, 163, 184, 0.1)' : 'rgba(107, 114, 128, 0.2)',
          display: true
        },
        ticks: {
          color: isDarkTheme ? '#cbd5e1' : '#1e293b',
          font: {
            size: 11,
            weight: '600'
          },
          padding: 8,
          display: true
        }
      },
      x: {
        display: true,
        grid: {
          color: isDarkTheme ? 'rgba(148, 163, 184, 0.05)' : 'rgba(107, 114, 128, 0.15)',
          display: true
        },
        ticks: {
          color: isDarkTheme ? '#cbd5e1' : '#1e293b',
          font: {
            size: 11,
            weight: '600'
          },
          padding: 8,
          display: true
        }
      }
    }
  }), [chartAnimation, isDarkTheme]);

  const handleGeneratePDF = async () => {
  try {
    const pdf = new jsPDF('p', 'mm', 'a4');
    let yPosition = 20;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const margin = 20;

    // Add professional header
    pdf.setFillColor(59, 130, 246);
    pdf.rect(0, 0, pageWidth, 40, 'F');
    pdf.setTextColor(255, 255, 255);
    pdf.setFontSize(20);
    pdf.setFont('helvetica', 'bold');
    pdf.text('CRIME ANALYTICS REPORT', pageWidth / 2, 25, { align: 'center' });
    
    pdf.setFontSize(12);
    pdf.setFont('helvetica', 'normal');
    pdf.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, 35, { align: 'center' });
    
    // Add logo placeholder
    pdf.setFillColor(255, 255, 255);
    pdf.circle(25, 25, 8, 'F');
    pdf.setFillColor(59, 130, 246);
    pdf.setFontSize(8);
    pdf.setTextColor(59, 130, 246);
    pdf.text('SV', 22, 28);

    yPosition = 50;

    // Executive Summary
    pdf.setTextColor(0, 0, 0);
    pdf.setFontSize(16);
    pdf.setFont('helvetica', 'bold');
    pdf.text('EXECUTIVE SUMMARY', margin, yPosition);
    yPosition += 12;

    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');
    
    const summaryItems = [
      `• Total Incidents Analyzed: ${displayCrimes.length}`,
      `• Time Period: ${timePeriods.find(p => p.id === selectedTimePeriod)?.label || 'All Time'}`,
      `• Areas Covered: ${keyMetrics.areasAffected} locations`,
      `• High Risk Incidents: ${keyMetrics.highRiskShare}%`,
      `• Data Coverage: ${((mappableCrimes.length / Math.max(displayCrimes.length, 1)) * 100).toFixed(1)}% mappable`
    ];

    summaryItems.forEach(item => {
      if (yPosition > 250) {
        pdf.addPage();
        yPosition = 20;
      }
      pdf.text(item, margin, yPosition);
      yPosition += 6;
    });

    yPosition += 10;

    // Key Metrics Table
    pdf.setFontSize(14);
    pdf.setFont('helvetica', 'bold');
    pdf.text('KEY METRICS', margin, yPosition);
    yPosition += 8;

    // Metrics table
    const metrics = [
      ['Metric', 'Value', 'Trend'],
      ['Total Incidents', keyMetrics.totalIncidents.toString(), '📊'],
      ['High Risk Share', `${keyMetrics.highRiskShare}%`, keyMetrics.highRiskShare > 20 ? '🔴' : '🟡'],
      ['Areas Affected', keyMetrics.areasAffected.toString(), '🗺️'],
      ['Weekly Change', `${keyMetrics.weeklyChange}%`, keyMetrics.weeklyChange > 0 ? '📈' : '📉']
    ];

    // Table header
    pdf.setFillColor(59, 130, 246);
    pdf.rect(margin, yPosition, pageWidth - margin * 2, 8, 'F');
    pdf.setTextColor(255, 255, 255);
    pdf.setFontSize(9);
    pdf.text('Metric', margin + 2, yPosition + 5);
    pdf.text('Value', margin + 80, yPosition + 5);
    pdf.text('Trend', pageWidth - margin - 15, yPosition + 5);
    yPosition += 8;

    // Table rows
    metrics.slice(1).forEach((metric, index) => {
      if (yPosition > 250) {
        pdf.addPage();
        yPosition = 20;
      }
      
      pdf.setFillColor(index % 2 === 0 ? 245 : 255);
      pdf.rect(margin, yPosition, pageWidth - margin * 2, 6, 'F');
      pdf.setTextColor(0, 0, 0);
      pdf.text(metric[0], margin + 2, yPosition + 4);
      pdf.text(metric[1], margin + 80, yPosition + 4);
      pdf.text(metric[2], pageWidth - margin - 15, yPosition + 4);
      yPosition += 6;
    });

    yPosition += 12;

    // Crime Type Analysis
    if (analyticsData.length > 0) {
      pdf.setFontSize(14);
      pdf.setFont('helvetica', 'bold');
      pdf.text('CRIME TYPE ANALYSIS', margin, yPosition);
      yPosition += 8;

      // Crime type table
      pdf.setFillColor(59, 130, 246);
      pdf.rect(margin, yPosition, pageWidth - margin * 2, 8, 'F');
      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(9);
      pdf.text('Crime Type', margin + 2, yPosition + 5);
      pdf.text('Count', margin + 100, yPosition + 5);
      pdf.text('Percentage', pageWidth - margin - 25, yPosition + 5);
      yPosition += 8;

      analyticsData.forEach((item, index) => {
        if (yPosition > 250) {
          pdf.addPage();
          yPosition = 20;
        }
        
        pdf.setFillColor(index % 2 === 0 ? 245 : 255);
        pdf.rect(margin, yPosition, pageWidth - margin * 2, 6, 'F');
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(8);
        pdf.text(item.type, margin + 2, yPosition + 4);
        pdf.text(item.count.toString(), margin + 100, yPosition + 4);
        pdf.text(`${item.percentage}%`, pageWidth - margin - 25, yPosition + 4);
        yPosition += 6;
      });

      yPosition += 12;
    }

    // AI Insights & Recommendations
    pdf.setFontSize(14);
    pdf.setFont('helvetica', 'bold');
    pdf.text('AI INSIGHTS & RECOMMENDATIONS', margin, yPosition);
    yPosition += 8;

    const recommendations = [
      '🚨 Increase patrol frequency in high-risk areas during peak hours',
      '📊 Focus resources on dominant crime types identified in analysis',
      '🔍 Implement preventive measures in identified hotspots',
      '👥 Enhance community engagement in areas with concentrated activity',
      '📱 Deploy mobile surveillance in emerging risk zones'
    ];

    pdf.setFontSize(9);
    pdf.setFont('helvetica', 'normal');
    recommendations.forEach(rec => {
      if (yPosition > 250) {
        pdf.addPage();
        yPosition = 20;
      }
      
      const lines = pdf.splitTextToSize(rec, pageWidth - margin * 2 - 5);
      lines.forEach(line => {
        pdf.text(line, margin + 5, yPosition);
        yPosition += 4;
      });
      yPosition += 2;
    });

    yPosition += 8;

    // Data Quality Assessment
    pdf.setFontSize(14);
    pdf.setFont('helvetica', 'bold');
    pdf.text('DATA QUALITY ASSESSMENT', margin, yPosition);
    yPosition += 8;

    const qualityMetrics = [
      `• Data Completeness: ${((mappableCrimes.length / Math.max(displayCrimes.length, 1)) * 100).toFixed(1)}%`,
      `• Time Coverage: ${trendsData.length} periods analyzed`,
      `• Geographical Coverage: ${new Set(displayCrimes.map(c => c.area)).size} areas`,
      `• Risk Assessment Coverage: ${((displayCrimes.filter(c => c.risk_level).length / Math.max(displayCrimes.length, 1)) * 100).toFixed(1)}%`
    ];

    pdf.setFontSize(9);
    qualityMetrics.forEach(metric => {
      if (yPosition > 250) {
        pdf.addPage();
        yPosition = 20;
      }
      pdf.text(metric, margin, yPosition);
      yPosition += 5;
    });

    // Add footer to all pages
    const totalPages = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFontSize(8);
      pdf.setTextColor(128, 128, 128);
      pdf.text(`Page ${i} of ${totalPages}`, pageWidth - margin - 20, pdf.internal.pageSize.getHeight() - 10);
      pdf.text('SafeVision Analytics Platform • Confidential', margin, pdf.internal.pageSize.getHeight() - 10);
      pdf.text(`Generated on: ${new Date().toLocaleDateString()}`, pageWidth / 2, pdf.internal.pageSize.getHeight() - 10, { align: 'center' });
    }

    // Save the PDF
    pdf.save(`crime_analytics_report_${new Date().toISOString().slice(0, 10)}.pdf`);

  } catch (error) {
    console.error('Error generating PDF:', error);
    alert('Error generating PDF report. Please try again.');
  }
};

  const handleCaptureMap = async () => {
    try {
      const mapElement = document.querySelector('.map-container');
      if (!mapElement) {
        alert('Map container not found');
        return;
      }

      // Show loading state
      const originalContent = mapElement.innerHTML;
      const loadingDiv = document.createElement('div');
      loadingDiv.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 20px;
        border-radius: 10px;
        z-index: 1000;
        text-align: center;
      `;
      loadingDiv.innerHTML = `
        <div class="loading-spinner" style="
          border: 4px solid #f3f3f3;
          border-top: 4px solid #3b82f6;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          animation: spin 2s linear infinite;
          margin: 0 auto 10px;
        "></div>
        <p>Capturing map snapshot...</p>
      `;
      mapElement.style.position = 'relative';
      mapElement.appendChild(loadingDiv);

      // Wait a moment for the loading indicator to show
      await new Promise(resolve => setTimeout(resolve, 500));

      // Capture the map
      const canvas = await html2canvas(mapElement, {
        useCORS: true,
        allowTaint: true,
        scale: 2, // Higher quality
        backgroundColor: isDarkTheme ? '#0f172a' : '#ffffff',
        onclone: (clonedDoc) => {
          // Remove loading indicator from clone
          const loadingElement = clonedDoc.querySelector('.loading-spinner')?.parentElement;
          if (loadingElement) {
            loadingElement.remove();
          }
        }
      });

      // Remove loading indicator
      mapElement.removeChild(loadingDiv);

      // Create PDF with map screenshot
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const margin = 20;

      // Add header
      pdf.setFillColor(59, 130, 246);
      pdf.rect(0, 0, pageWidth, 30, 'F');
      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(16);
      pdf.text('Crime Map Snapshot', margin, 18);
      pdf.setFontSize(10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, margin, 25);

      // Add map image to PDF
      const imgData = canvas.toDataURL('image/png');
      const imgWidth = pageWidth - margin * 2;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      // Check if image fits on first page
      if (imgHeight > pdf.internal.pageSize.getHeight() - 60) {
        // Image is too tall, split across pages
        let heightLeft = imgHeight;
        let position = 40;

        while (heightLeft > 0) {
          pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
          heightLeft -= pdf.internal.pageSize.getHeight() - 60;
          position -= pdf.internal.pageSize.getHeight() - 60;

          if (heightLeft > 0) {
            pdf.addPage();
          }
        }
      } else {
        // Image fits on one page
        pdf.addImage(imgData, 'PNG', margin, 40, imgWidth, imgHeight);
      }

      // Add map details
      const detailsY = 40 + imgHeight + 10;
      if (detailsY < pdf.internal.pageSize.getHeight() - 20) {
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(12);
        pdf.text('Map Details:', margin, detailsY);
        pdf.setFontSize(10);
        
        const details = [
          `Total Incidents: ${displayCrimes.length}`,
          `Visible on Map: ${displayCrimes.length}`,
          `Visualization Mode: ${visualizationModes.find(m => m.id === activeMode)?.label}`,
          `Map Style: ${availableTiles.find(t => t.id === selectedTile)?.label}`,
          `Active Filters: ${Object.keys(filters).filter(k => filters[k]).length} crime types, ${Object.keys(locationFilters).filter(k => locationFilters[k]).length} areas`
        ];

        details.forEach((detail, index) => {
          pdf.text(`• ${detail}`, margin + 5, detailsY + 8 + (index * 5));
        });
      } else {
        // Add new page for details
        pdf.addPage();
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(12);
        pdf.text('Map Details:', margin, 20);
        pdf.setFontSize(10);

        const details = [
          `Total Incidents: ${displayCrimes.length}`,
          `Visible on Map: ${displayCrimes.length}`,
          `Visualization Mode: ${visualizationModes.find(m => m.id === activeMode)?.label}`,
          `Map Style: ${availableTiles.find(t => t.id === selectedTile)?.label}`,
          `Active Filters: ${Object.keys(filters).filter(k => filters[k]).length} crime types, ${Object.keys(locationFilters).filter(k => locationFilters[k]).length} areas`
        ];

        details.forEach((detail, index) => {
          pdf.text(`• ${detail}`, margin + 5, 30 + (index * 5));
        });
      }

      // Save the PDF
      pdf.save(`crime_map_snapshot_${new Date().toISOString().slice(0, 10)}.pdf`);

    } catch (error) {
      console.error('Error capturing map:', error);
      alert('Error capturing map snapshot. Please try again.');
      
      // Clean up loading indicator on error
      const loadingElement = document.querySelector('.loading-spinner')?.parentElement;
      if (loadingElement) {
        loadingElement.remove();
      }
    }
  };

  // Enhanced export function for chart images
  const captureChartAsImage = async (chartElement, chartName) => {
    try {
      const canvas = await html2canvas(chartElement, {
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true
      });
      return canvas.toDataURL('image/png');
    } catch (error) {
      console.error(`Error capturing ${chartName}:`, error);
      return null;
    }
  };

  // Render custom date inputs when custom time period is selected
  const renderCustomDateInputs = () => {
    if (selectedTimePeriod !== 'custom') return null;

    return (
      <div className="custom-date-section">
        <div className="date-input-group">
          <label>Start Date:</label>
          <input
            type="date"
            value={customStartDate}
            onChange={(e) => setCustomStartDate(e.target.value)}
            className="date-input"
            max={customEndDate || new Date().toISOString().split('T')[0]}
          />
        </div>
        <div className="date-input-group">
          <label>End Date:</label>
          <input
            type="date"
            value={customEndDate}
            onChange={(e) => setCustomEndDate(e.target.value)}
            className="date-input"
            min={customStartDate}
            max={new Date().toISOString().split('T')[0]}
          />
        </div>
      </div>
    );
  };

  // Render map based on active mode - FIXED: Now uses mappableCrimes for map display
  const renderMapVisualization = () => {
    const selectedTileConfig = availableTiles.find(tile => tile.id === selectedTile);

    const mapProps = {
      center: [
        Number(systemSettings?.map_default_center_lat ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lat),
        Number(systemSettings?.map_default_center_lng ?? SYSTEM_SETTINGS_DEFAULTS.map_default_center_lng),
      ],
      zoom: Number(systemSettings?.default_map_zoom ?? SYSTEM_SETTINGS_DEFAULTS.default_map_zoom),
      minZoom: Number(systemSettings?.map_min_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_min_zoom),
      maxZoom: Number(systemSettings?.map_max_zoom ?? SYSTEM_SETTINGS_DEFAULTS.map_max_zoom),
      maxBounds: [[
        Number(systemSettings?.map_bounds_south ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_south),
        Number(systemSettings?.map_bounds_west ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_west),
      ], [
        Number(systemSettings?.map_bounds_north ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_north),
        Number(systemSettings?.map_bounds_east ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_east),
      ]] || LAHORE_BOUNDS,
      maxBoundsViscosity: Number(systemSettings?.map_bounds_viscosity ?? SYSTEM_SETTINGS_DEFAULTS.map_bounds_viscosity),
      style: { width: '100%', height: '100%' },
      scrollWheelZoom: false,
      keyboard: false,
      doubleClickZoom: false,
      boxZoom: false,
      zoomControl: true
    };

    const resolveComputedTileUrl = () => selectedTileConfig?.url ?? 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

    switch (activeMode) {
      case 'markers':
        return (
          <MapContainer {...mapProps}>
            <TileLayer
              url={resolveComputedTileUrl()}
              attribution='&copy; OpenStreetMap contributors'
            />
            {plottedMarkers.map((markerPoint, index) => {
              const riskColor = getRiskColor(markerPoint.highestRisk);
              const crimeTypeList = Object.entries(markerPoint.crime_types || {}).sort((a, b) => b[1] - a[1]);
              const areaList = Object.entries(markerPoint.area_counts || {}).sort((a, b) => b[1] - a[1]);
              const topArea = areaList[0] || ['Unknown', 0];
              const topType = crimeTypeList[0] || ['Unknown', 0];
              const topAddress = parseAddress(markerPoint.subarea);

              return (
                <Marker
                  key={markerPoint.key || `marker-${index}`}
                  position={[markerPoint.displayLat, markerPoint.displayLng]}
                  icon={createCustomIcon(riskColor)}
                >
                  <Popup className="crime-popup-wrapper crime-popup-interactive">
                    <div className="crime-popup-card">
                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">📚</span>
                          <span>Merged Database Rows</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{markerPoint.count}</div>
                        </div>
                      </div>

                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">📍</span>
                          <span>Mapped Area (OSM / Area Column)</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{topArea[0]}</div>
                        </div>
                      </div>

                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">🧭</span>
                          <span>FIR Area (English / Transliteration)</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{topAddress.line1 || markerPoint.subarea || 'Unknown'}</div>
                          {topAddress.line2 && <div className="crime-popup-addr-sub">{topAddress.line2}</div>}
                          {markerPoint.area_urdu && <div className="crime-popup-addr-urdu">{markerPoint.area_urdu}</div>}
                        </div>
                      </div>

                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">⚠</span>
                          <span>Risk Score</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{markerPoint.risk_score}%</div>
                        </div>
                      </div>

                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">🛡</span>
                          <span>Safety Score</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{Math.round(100 - markerPoint.risk_score)}%</div>
                        </div>
                      </div>

                      <div className="crime-popup-section crime-popup-section-last">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">🗓</span>
                          <span>Date</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{formatCrimeDateParts(markerPoint.crimes?.[0]?.date).date}</div>
                        </div>
                      </div>

                      <div className="crime-popup-section crime-popup-section-last">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">⏰</span>
                          <span>Time</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">{formatCrimeDateParts(markerPoint.crimes?.[0]?.date).time}</div>
                        </div>
                      </div>

                      <div className="crime-popup-section">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">📑</span>
                          <span>Crime Types</span>
                        </div>
                        <div className="crime-popup-section-body">
                          {crimeTypeList.map(([type, count]) => (
                            <div key={`${index}-${type}`} className="crime-popup-addr-sub">
                              {ppcSimpleLabel(type)}
                              <span style={{ display: 'block' }}>x{count}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="crime-popup-section crime-popup-section-last">
                        <div className="crime-popup-section-title">
                          <span className="crime-popup-sec-icon">📍</span>
                          <span>Coordinates</span>
                        </div>
                        <div className="crime-popup-section-body">
                          <div className="crime-popup-addr-main">📍 {markerPoint.displayLat.toFixed(4)}, {markerPoint.displayLng.toFixed(4)}</div>
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        );

      case 'heatmap':
        return isAuthenticated ? (
          <MapContainer {...mapProps}>
            <TileLayer
              url={resolveComputedTileUrl()}
              attribution='&copy; OpenStreetMap contributors'
            />
            <HeatmapLayer
              points={displayCrimes.map(crime => {
                const lat = Array.isArray(crime.coordinates) ? crime.coordinates[0] : crime.latitude;
                const lng = Array.isArray(crime.coordinates) ? crime.coordinates[1] : crime.longitude;
                if (typeof lat === 'number' && typeof lng === 'number' && isFinite(lat) && isFinite(lng)) {
                  // Severity-weighted intensity. High/Critical pull the gradient
                  // into the warm end; lower-risk incidents still contribute
                  // mass so density shows through even in safer areas.
                  let intensity = 0.4;
                  const riskLevel = (crime.risk_level || '').toLowerCase();
                  if (riskLevel.includes('critical') || riskLevel.includes('avoid')) intensity = 1.5;
                  else if (riskLevel.includes('high')) intensity = 1.2;
                  else if (riskLevel.includes('medium') || riskLevel.includes('med') || riskLevel.includes('moderate')) intensity = 0.8;
                  else if (riskLevel.includes('low')) intensity = 0.4;
                  return { lat, lng, intensity };
                }
                return null;
              }).filter(Boolean)}
              radius={Number(systemSettings?.heatmap_radius) || SYSTEM_SETTINGS_DEFAULTS.heatmap_radius}
              blur={Number(systemSettings?.heatmap_blur_multiplier) || SYSTEM_SETTINGS_DEFAULTS.heatmap_blur_multiplier}
              minOpacity={Number(systemSettings?.heatmap_intensity) || SYSTEM_SETTINGS_DEFAULTS.heatmap_intensity}
              maxZoom={Number(systemSettings?.heatmap_layer_max_zoom) || SYSTEM_SETTINGS_DEFAULTS.heatmap_layer_max_zoom}
            />
            {displayCrimes.map((crime, index) => {
              const lat = Array.isArray(crime.coordinates) ? crime.coordinates[0] : crime.latitude;
              const lng = Array.isArray(crime.coordinates) ? crime.coordinates[1] : crime.longitude;
              if (typeof lat === 'number' && typeof lng === 'number' && isFinite(lat) && isFinite(lng)) {
                const riskColor = getRiskColor(crime.risk_level);
                return (
                  <Marker
                    key={crime.id || index}
                    position={[lat, lng]}
                    icon={L.divIcon({
                      className: 'heatmap-marker',
                      html: `<div style="width: 9px; height: 9px; border-radius: 50%; background: ${riskColor}; border: 1.5px solid #ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.25);"></div>`,
                      iconSize: [9, 9],
                      iconAnchor: [4.5, 4.5]
                    })}
                  >
                    <Popup className="crime-popup-wrapper crime-popup-compact crime-popup-cluster">
                      {(() => {
                          const rawArea = (crime.area || 'Unknown').trim() || 'Unknown';
                          // Match the cluster key used by heatmapClusterSummaryMap, which keys
                          // by canonical area so spelling variants merge into one cluster.
                          const topArea = canonicalAreaFor(rawArea) || rawArea;
                          const coordKey = `${Number(lat).toFixed(4)},${Number(lng).toFixed(4)}`;
                          const clusterKey = `${coordKey}|${normalizeAreaName(topArea)}`;
                          const summary = heatmapClusterSummaryMap.get(clusterKey) || {
                            count: 1,
                            top_area: topArea,
                            top_subarea: crime.area_translit || crime.area || 'Unknown',
                            top_type: crime.crime_type || 'Unknown',
                            top_type_count: 1,
                            warning_avoid_pct: (getRiskLevel(crime.risk_level) === 'High' || getRiskLevel(crime.risk_level) === 'Critical') ? 100 : 0,
                            risk_score: (getRiskLevel(crime.risk_level) === 'High' || getRiskLevel(crime.risk_level) === 'Critical') ? 100 : 0,
                          };
                        return (
                          <div className="cluster-popup">
                            <p><strong>Filtered Crimes</strong></p>
                              <p>{summary.count}</p>
                            <p><strong>Area</strong></p>
                              <p>{summary.top_area}</p>
                            <p><strong>Top FIR Sub-area</strong></p>
                              <p>{summary.top_subarea}</p>
                            <p><strong>Top Type</strong></p>
                              <p>{ppcSimpleLabel(summary.top_type)} ({summary.top_type_count})</p>
                            <p><strong>Risk Score</strong></p>
                              <p>{summary.risk_score}%</p>
                            <p><strong>Safety Score</strong></p>
                              <p style={{ color: (100 - summary.risk_score) > 80 ? '#22c55e' : (100 - summary.risk_score) > 50 ? '#f59e0b' : '#ef4444', fontWeight: 'bold' }}>
                                {Math.round(100 - summary.risk_score)}%
                              </p>
                          </div>
                        );
                      })()}
                    </Popup>
                  </Marker>
                );
              }
              return null;
            })}
          </MapContainer>
        ) : (
          <div className="auth-required-placeholder">
            <div className="auth-placeholder-content">
              <i className="fas fa-lock"></i>
              <h4>Authentication Required</h4>
              <p>Please log in to view heatmap analysis</p>
            </div>
          </div>
        );

      case 'cluster': {
        const clusters = computeClusters(displayCrimes);
        return (
          <MapContainer {...mapProps}>
            <TileLayer
              url={resolveComputedTileUrl()}
              attribution='&copy; OpenStreetMap contributors'
            />
            {clusters.map((cluster, index) => {
              const riskColors = cluster.crimes.map(crime => getRiskColor(crime.risk_level));
              const dominantColor = riskColors[0] || '#3b82f6';
              const areaCounts = {};
              const subareaCounts = {};
              const typeCounts = {};
              let criticalCount = 0;
              let highCount = 0;
              let moderateCount = 0;
              let lowCount = 0;

              // Use consistent time reference from parent scope
              // This ensures all clusters use the same "now" for recency calculations
              cluster.crimes.forEach((crime) => {
                const areaName = (crime.area || 'Unknown').trim() || 'Unknown';
                const subareaName = (crime.area_translit || crime.area || 'Unknown').trim() || 'Unknown';
                const typeName = crime.crime_type || 'Unknown';
                areaCounts[areaName] = (areaCounts[areaName] || 0) + 1;
                subareaCounts[subareaName] = (subareaCounts[subareaName] || 0) + 1;
                typeCounts[typeName] = (typeCounts[typeName] || 0) + 1;

                const lvl = getRiskLevel(crime.risk_level);
                if (lvl === 'Critical') criticalCount += 1;
                else if (lvl === 'High') highCount += 1;
                else if (lvl === 'Moderate') moderateCount += 1;
                else lowCount += 1;
              });

              // Calculate recency using consistent reference
              let last_30_days = 0;
              let last_90_days = 0;
              let recent_count = 0;
              let older_count = 0;

              const now = new Date();
              const cutoff_90 = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
              const cutoff_30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
              const cutoff_45 = new Date(now.getTime() - 45 * 24 * 60 * 60 * 1000);

              cluster.crimes.forEach((crime) => {
                const crimeDate = crime.date ? new Date(crime.date) : null;
                if (crimeDate && !isNaN(crimeDate.getTime())) {
                  if (crimeDate >= cutoff_30) last_30_days += 1;
                  if (crimeDate >= cutoff_90) last_90_days += 1;
                  if (crimeDate >= cutoff_45) recent_count += 1;
                  else older_count += 1;
                }
              });

              const topArea = Object.entries(areaCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
              const topSubarea = Object.entries(subareaCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];
              const topType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0] || ['Unknown', 0];

              // Use unified risk calculation (matching backend exactly)
              const stats = {
                total_crimes: cluster.count,
                high_risk_count: criticalCount + highCount,
                medium_risk_count: moderateCount,
                last_30_days,
                last_90_days,
                recent_count,
                older_count,
              };
              const riskSummary = calculate_unified_risk_summary(stats);
              const riskScore = riskSummary.risk_score;

              return (
                <Marker
                  key={index}
                  position={cluster.center}
                  icon={L.divIcon({
                    className: 'cluster-marker',
                    html: `<div style="
                      display: flex;
                      align-items: center;
                      justify-content: center;
                      width: ${Math.min(40 + cluster.count * 2, 60)}px;
                      height: ${Math.min(40 + cluster.count * 2, 60)}px;
                      border-radius: 50%;
                      background: ${dominantColor};
                      color: white;
                      border: 3px solid white;
                      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                      font-weight: bold;
                      font-size: ${Math.min(14 + cluster.count * 0.5, 18)}px;
                    ">${cluster.count}</div>`,
                    iconSize: [Math.min(40 + cluster.count * 2, 60), Math.min(40 + cluster.count * 2, 60)],
                    iconAnchor: [Math.min(20 + cluster.count, 30), Math.min(20 + cluster.count, 30)]
                  })}
                >
                  <Popup className="crime-popup-wrapper crime-popup-compact crime-popup-cluster">
                    <div className="cluster-popup">
                      <p><strong>Filtered Crimes</strong></p>
                      <p>{cluster.count}</p>
                      <p><strong>Area</strong></p>
                      <p>{topArea[0]}</p>
                      <p><strong>Top FIR Sub-area</strong></p>
                      <p>{topSubarea[0]}</p>
                      <p><strong>Top Type</strong></p>
                      <p>{ppcSimpleLabel(topType[0])} ({topType[1]})</p>
                      <p><strong>Risk Score</strong></p>
                      <p>{riskScore}%</p>
                      <p><strong>Safety Score</strong></p>
                      <p style={{ color: (100 - riskScore) > 80 ? '#22c55e' : (100 - riskScore) > 50 ? '#f59e0b' : '#ef4444', fontWeight: 'bold' }}>
                        {Math.round(100 - riskScore)}%
                      </p>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        );
      }

      case 'timeline': {
        const timelineData = groupByDay(displayCrimes);
        const timelineChartData = {
          labels: timelineData.labels,
          datasets: [
            {
              label: 'Daily Incidents',
              data: timelineData.data,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              tension: 0.4,
              fill: true,
              borderWidth: 3,
              pointBackgroundColor: '#3b82f6',
              pointBorderColor: '#ffffff',
              pointRadius: 4,
              pointHoverRadius: 6
            }
          ]
        };

        return (
          <div className="timeline-chart-container">
            <div className="timeline-header">
              <h3>Incident Timeline</h3>
              <p>Daily crime incidents over time</p>
            </div>
            <div className="chart-container">
              {timelineData.labels.length === 0 ? (
                <div className="no-data-message">
                  <i className="fas fa-chart-line"></i>
                  <h4>No Timeline Data</h4>
                  <p>No incidents found for the selected time period</p>
                </div>
              ) : (
                <Line data={timelineChartData} options={chartOptions} />
              )}
            </div>
            {timelineData.labels.length > 0 && (
              <div className="timeline-stats">
                <div className="stat-item">
                  <span className="stat-label">Total Days:</span>
                  <span className="stat-value">{timelineData.labels.length}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Peak Day:</span>
                  <span className="stat-value">
                    {timelineData.labels[timelineData.data.indexOf(Math.max(...timelineData.data))]} ({Math.max(...timelineData.data)} incidents)
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Average:</span>
                  <span className="stat-value">
                    {(timelineData.data.reduce((total, nextValue) => total + nextValue, 0) / timelineData.data.length).toFixed(1)} per day
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      }

      default:
        return (
          <div className="map-placeholder">
            <i className="fas fa-map"></i>
            <h4>Map Visualization</h4>
            <p>Select a visualization mode to begin analysis</p>
          </div>
        );
    }
  };

  return (
    <section className={`crime-map-modern${!showAdditionalSections ? " userdashboard-heatmap" : ""}`} id="maps">
      {/* Enhanced Header */}
      {showAdditionalSections && (
        <div className="modern-header">
          <div className="header-content">
            <div className="header-badge">
              <i className="fas fa-shield-alt"></i>
              <span>SafeVision: Your Urban Safety Companion</span>
            </div>
            <h1 className="header-title">Incident Intelligence Dashboard</h1>
            <p className="header-subtitle">
              Empowering communities with real-time analytics and actionable insights to enhance urban safety.
            </p>
          </div>
        </div>
      )}

      {/* Main Dashboard Grid */}
      <div className="dashboard-grid">
        
        {/* Left Panel - Controls */}
        <div className={`control-panel ${controlsVisible ? 'active' : ''}`}>
          <div className="panel-header">
            <div className="panel-title">
              <i className="fas fa-sliders-h"></i>
              <h3>Dashboard Controls</h3>
            </div>
           <button 
      className="panel-toggle"
      onClick={() => setControlsVisible(!controlsVisible)}
      aria-label={controlsVisible ? "Close panel" : "Open panel"}
    >
      <i className={`fas fa-chevron-${controlsVisible ? 'left' : 'right'}`}></i>
    </button>
          </div>

          <div className="panel-content">
            {/* Visualization Modes */}
            <div className="control-section">
              <h4 className="section-title">
                <i className="fas fa-chart-line"></i>
                Visualization Mode
              </h4>
              <div className="mode-grid">
                {visualizationModes.map(mode => (
                  <button
                    key={mode.id}
                    className={`mode-card ${activeMode === mode.id ? 'active' : ''}`}
                    onClick={() => handleModeChange(mode.id)}
                    style={{ '--mode-color': mode.color }}
                  >
                    <div className="mode-icon">
                      <i className={mode.icon}></i>
                    </div>
                    <span className="mode-label">{mode.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Time Filter */}
            <div className="control-section">
              <h4 className="section-title">
                <i className="fas fa-calendar"></i>
                Time Period
              </h4>
              <div className="time-grid">
                {timePeriods.map(period => (
                  <button
                    key={period.id}
                    className={`time-card ${selectedTimePeriod === period.id ? 'active' : ''}`}
                    onClick={() => handleTimePeriodChange(period.id)}
                  >
                    <i className={period.icon}></i>
                    <span>{period.label}</span>
                  </button>
                ))}
              </div>
              {renderCustomDateInputs()}
            </div>

            {/* Incident Type Filters */}
            <div className="control-section">
              <h4 className="section-title">
                <i className="fas fa-filter"></i>
                Incident Types
                {loading && <span className="loading-dots">...</span>}
              </h4>
              <div className="filter-scroll">
                {crimeTypes.length > 0 ? (
                  crimeTypes.map((type, index) => (
                    <div
                      key={index}
                      className={`filter-chip ${filters[type] ? 'active' : ''}`}
                      onClick={() => toggleFilter(type)}
                    >
                      <div className="chip-indicator"></div>
                      <span className="chip-label">{type}</span>
                    </div>
                  ))
                ) : (
                  <div className="no-data-message">
                    <i className="fas fa-exclamation-circle"></i>
                    <span>No crime types available</span>
                  </div>
                )}
              </div>
            </div>

            {/* Location Filters */}
            <div className="control-section">
              <h4 className="section-title">
                <i className="fas fa-map-marker-alt"></i>
                Locations
                {loading && <span className="loading-dots">...</span>}
              </h4>
              <div className="filter-scroll">
                {areas.length > 0 ? (
                  areas.map((area, index) => {
                    const areaName = typeof area === 'object' ? (area.name || '') : area;
                    return (
                    <div
                      key={index}
                      className={`filter-chip ${locationFilters[areaName] ? 'active' : ''}`}
                      onClick={() => toggleLocationFilter(areaName)}
                    >
                      <div className="chip-indicator"></div>
                      <span className="chip-label">{areaName}</span>
                    </div>
                    );
                  })
                ) : (
                  <div className="no-data-message">
                    <i className="fas fa-exclamation-circle"></i>
                    <span>No areas available</span>
                  </div>
                )}
              </div>
            </div>

            {/* Incident Limit Control */}
            <div className="control-section">
              <h4 className="section-title">
                <i className="fas fa-list-ol"></i>
                Display Limit
              </h4>
              <div className="slider-control">
                <label>Show Incidents: {incidentLimit === 0 ? 'All records' : incidentLimit}</label>
                <select
                  value={incidentLimit}
                  onChange={(e) => {
                    incidentLimitTouchedRef.current = true;
                    setIncidentLimit(parseInt(e.target.value, 10));
                  }}
                  className="modern-select"
                >
                  <option value={500}>500 records</option>
                  <option value={1000}>1,000 records</option>
                  <option value={2000}>2,000 records</option>
                  <option value={5000}>5,000 records</option>
                  <option value={0}>All records</option>
                </select>
                <button 
                  className="reset-button"
                  onClick={() => {
                    setFilters({});
                    setLocationFilters({});
                    setSelectedTimePeriod('all');
                    setCustomStartDate('');
                    setCustomEndDate('');
                    setShowResetAlert(true);
                  }}
                >
                  <i className="fas fa-undo"></i>
                  Reset Filters
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="main-content">
          
          {/* Stats Overview - Made smaller */}
          <div className="stats-overview compact">
            <TrendStatCard
              icon="fa-layer-group"
              label="Community Engagement"
              value={`${crimes.length} incidents reported`}
              caption="Data collected from community sources"
              loading={loading}
              compact={true}
            />
            <TrendStatCard
              icon="fa-shield-alt"
              label="Critical Zones"
              value={`${keyMetrics.highRiskShare}% High Risk`}
              caption="Areas with elevated safety concerns"
              loading={loading}
              compact={true}
            />
            <TrendStatCard
              icon="fa-clock"
              label="Response Efficiency"
              value={`${keyMetrics.averageResponse} min avg response`}
              caption="Emergency response performance"
              loading={loading}
              compact={true}
            />
            <TrendStatCard
              icon="fa-map"
              label="Regions Monitored"
              value={`${keyMetrics.areasAffected} areas active`}
              caption="Geographical coverage"
              loading={loading}
              compact={true}
            />
          </div>

          {/* Map Visualization */}
          <div className="visualization-section">
            <div className="viz-header">
              <h3>
                {visualizationModes.find(m => m.id === activeMode)?.label || 'Spatial Analysis'}
                {displayCrimes.length > 0 && (
                  <span className="crime-count-badge">
                    {mappedIncidentsLoading ? (
                      <>
                        <i className="fas fa-spinner fa-spin"></i>
                        Loading locations...
                      </>
                    ) : (
                      <>
                        {/* {mappableCrimes.length} on map */}
                      </>
                    )}
                  </span>
                )}
              </h3>
              <div className="viz-controls">
                <div className="tile-selector">
                  <button 
                    className="tile-button"
                    onClick={() => setShowTileDropdown(!showTileDropdown)}
                  >
                    <i className={`fas ${availableTiles.find(t => t.id === selectedTile)?.icon}`}></i>
                    <span>{availableTiles.find(t => t.id === selectedTile)?.label}</span>
                    <i className="fas fa-chevron-down"></i>
                  </button>
                  {showTileDropdown && (
                    <div className="tile-dropdown">
                      {availableTiles.map(tile => (
                        <button
                          key={tile.id}
                          className={`tile-option ${selectedTile === tile.id ? 'active' : ''}`}
                          onClick={() => {
                            tileTouchedRef.current = true;
                            setSelectedTile(tile.id);
                            setShowTileDropdown(false);
                          }}
                        >
                          <i className={`fas ${tile.icon}`}></i>
                          {tile.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="map-container">
              {loading ? (
                <div className="loading-placeholder">
                  <div className="loading-spinner"></div>
                  <p>Loading crime data...</p>
                </div>
              ) : dataError ? (
                <div className="error-placeholder">
                  <i className="fas fa-exclamation-triangle"></i>
                  <h4>Data Loading Error</h4>
                  <p>{dataError}</p>
                  <button 
                    className="retry-button"
                    onClick={() => window.location.reload()}
                  >
                    <i className="fas fa-redo"></i>
                    Retry
                  </button>
                </div>
              ) : (
                renderMapVisualization()
              )}
            </div>
          </div>

          {/* Analytics Tabs - Made more compact */}
          <div className="analytics-tabs compact">
            <div className="tab-header">
              <div className="tab-navigation">
                <button 
                  className={`tab-button ${activeTab === 'trends' ? 'active' : ''}`}
                  onClick={() => setActiveTab('trends')}
                >
                  <i className="fas fa-chart-line"></i>
                  Trends
                </button>
                <button 
                  className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analytics')}
                >
                  <i className="fas fa-chart-pie"></i>
                  Analytics
                </button>
                <button 
                  className={`tab-button ${activeTab === 'insights' ? 'active' : ''}`}
                  onClick={() => setActiveTab('insights')}
                >
                  <i className="fas fa-lightbulb"></i>
                  Insights
                </button>
                <button 
                  className={`tab-button ${activeTab === 'export' ? 'active' : ''}`}
                  onClick={() => setActiveTab('export')}
                >
                  <i className="fas fa-download"></i>
                  Export
                </button>
              </div>
            </div>

            <div className="tab-content compact">
              {/* Trends Tab */}
              {activeTab === 'trends' && (
                <div className="trends-content compact">
                  {dataLoading ? (
                    <div className="loading-placeholder">
                      <div className="loading-spinner"></div>
                      <p>Loading trends data...</p>
                    </div>
                  ) : (
                    <>
                      <div className="chart-container compact">
                        <Line data={trendsChartData} options={chartOptions} />
                      </div>
                      <div className="trends-insights compact">
                        <h4>Trend Analysis</h4>
                        <div className="insight-cards compact">
                          <div className="insight-card compact">
                            <i className="fas fa-arrow-up trend-up"></i>
                            <div>
                              <h5>Activity Pattern</h5>
                              <p>Based on {displayCrimes.length} incidents</p>
                            </div>
                          </div>
                          <div className="insight-card compact">
                            <i className="fas fa-chart-bar trend-data"></i>
                            <div>
                              <h5>Data Coverage</h5>
                              <p>{trendsData.length} time periods analyzed</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Analytics Tab */}
              {activeTab === 'analytics' && (
                <div className="analytics-content compact">
                  {analyticsData.length === 0 ? (
                    <div className="no-data-placeholder">
                      <i className="fas fa-chart-bar"></i>
                      <h4>No Analytics Data</h4>
                      <p>Apply filters to see crime type distribution</p>
                    </div>
                  ) : (
                    <>
                      <div className="charts-grid compact">
                        <div className="chart-wrapper compact">
                          <h4>Crime Type Distribution</h4>
                          <div className="chart-container compact">
                            <Doughnut data={analyticsChartData} options={chartOptions} />
                          </div>
                        </div>
                        <div className="chart-wrapper compact">
                          <h4>Incidents by Category</h4>
                          <div className="chart-container compact">
                            <Bar data={barChartData} options={chartOptions} />
                          </div>
                        </div>
                      </div>
                      <div className="analytics-table compact">
                        <h4>Detailed Breakdown</h4>
                        <div className="table-container compact">
                          <table>
                            <thead>
                              <tr>
                                <th>Crime Type</th>
                                <th>Count</th>
                                <th>Percentage</th>
                                <th>Trend</th>
                              </tr>
                            </thead>
                            <tbody>
                              {analyticsData.map((item, index) => (
                                <tr key={index}>
                                  <td>
                                    <div className="type-indicator" style={{backgroundColor: item.color}}></div>
                                    {item.type}
                                  </td>
                                  <td>{item.count}</td>
                                  <td>{item.percentage}%</td>
                                  <td>
                                    <span className={`trend-badge ${item.percentage > 20 ? 'high' : item.percentage > 10 ? 'medium' : 'low'}`}>
                                      <i className={`fas fa-arrow-${item.percentage > 20 ? 'up' : item.percentage > 10 ? 'right' : 'down'}`}></i>
                                      {item.percentage > 20 ? 'High' : item.percentage > 10 ? 'Medium' : 'Low'}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Insights Tab */}
              {activeTab === 'insights' && (
                <div className="insights-content compact">
                  {insightsData.length === 0 ? (
                    <div className="no-data-placeholder">
                      <i className="fas fa-lightbulb"></i>
                      <h4>No Insights Available</h4>
                      <p>Crime data is needed to generate insights</p>
                    </div>
                  ) : (
                    <>
                      <div className="insights-grid compact">
                        {insightsData.map((insight, index) => (
                          <div key={index} className="insight-card compact">
                            <div className="insight-icon">
                              <i className={insight.icon}></i>
                            </div>
                            <div className="insight-content">
                              <h4>{insight.title}</h4>
                              <p>{insight.description}</p>
                              <span className="insight-tag">{insight.type}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="ai-recommendations compact">
                        <h4>AI Recommendations</h4>
                        <div className="recommendation-list compact">
                          <div className="recommendation compact">
                            <i className="fas fa-robot"></i>
                            <p>Consider increasing patrols in high-risk areas during peak hours</p>
                          </div>
                          <div className="recommendation compact">
                            <i className="fas fa-robot"></i>
                            <p>Pattern analysis suggests potential for preventive measures in identified hotspots</p>
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Export Tab */}
              {activeTab === 'export' && (
                <div className="export-content compact">
                  <div className="export-options compact">
                    <div className="export-card compact">
                      <div className="export-icon">
                        <i className="fas fa-chart-line"></i>
                      </div>
                      <h4>Analytics Report</h4>
                      <p>Generate comprehensive analytics report with charts and insights</p>
                      <button 
                        className="export-button"
                        onClick={handleGeneratePDF}
                        disabled={displayCrimes.length === 0}
                      >
                        <i className="fas fa-file-pdf"></i>
                        Generate PDF Report
                      </button>
                    </div>

                    <div className="export-card compact">
                      <div className="export-icon">
                        <i className="fas fa-map"></i>
                      </div>
                      <h4>Map Snapshot</h4>
                      <p>Export current map view as high-resolution image</p>
                      <button 
                        className="export-button"
                        onClick={handleCaptureMap}
                      >
                        <i className="fas fa-camera"></i>
                        Capture Map
                      </button>
                    </div>
                  </div>
                  
                  <div className="export-info compact">
                    <h4>Export Information</h4>
                    <div className="info-grid compact">
                      <div className="info-item compact">
                        <i className="fas fa-database"></i>
                        <div>
                          <strong>Incidents Displayed:</strong> {displayCrimes.length}
                        </div>
                      </div>
                      <div className="info-item compact">
                        <i className="fas fa-filter"></i>
                        <div>
                          <strong>Active Filters:</strong> {Object.keys(filters).filter(k => filters[k]).length} crime types, {Object.keys(locationFilters).filter(k => locationFilters[k]).length} areas
                        </div>
                      </div>
                      <div className="info-item compact">
                        <i className="fas fa-calendar"></i>
                        <div>
                          <strong>Time Period:</strong> {timePeriods.find(p => p.id === selectedTimePeriod)?.label}
                        </div>
                      </div>
                      <div className="info-item compact">
                        <i className="fas fa-map-marker-alt"></i>
                        <div>
                          <strong>Mappable Incidents:</strong> {mappableCrimes.length} of {displayCrimes.length}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Additional Components */}
      {showAdditionalSections && (
        <div className="additional-sections">
          <SafetyStats keyMetrics={keyMetrics} />
          <QuickActions />
          <EmergencyContacts />
        </div>
      )}

      {/* Unmapped Incidents Modal */}
      {showUnmappedList && unmappedCrimes.length > 0 && (
        <div className="unmapped-incidents-modal" onClick={() => setShowUnmappedList(false)}>
          <div className="unmapped-incidents-panel" onClick={(e) => e.stopPropagation()}>
            <div className="unmapped-header">
              <h3>Incidents Without Location Data</h3>
              <button 
                className="close-button"
                onClick={() => setShowUnmappedList(false)}
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
            <div className="unmapped-list">
              {unmappedCrimes.map((crime, index) => (
                <div key={index} className="unmapped-item">
                  <div className="unmapped-item-header">
                    <span className="unmapped-item-type">
                      {crime.crime_type || 'Unknown Incident'}
                    </span>
                    <span className="unmapped-item-reason">
                      No coordinates
                    </span>
                  </div>
                  <div className="unmapped-item-details">
                    <div className="detail-row">
                      <span className="detail-label">Area:</span>
                      <span>{crime.area || 'Unknown'}</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Risk Level:</span>
                      <span>{getRiskLevel(crime.risk_level)}</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Date:</span>
                      <span>{new Date(crime.date).toLocaleDateString()}</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Time:</span>
                      <span>{new Date(crime.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Floating Action Button for Mobile */}
      <button
        className="fab-mobile"
        onClick={() => setControlsVisible(!controlsVisible)}
      >
        <i className={`fas fa-${controlsVisible ? 'times' : 'sliders-h'}`}></i>
      </button>
      {showResetAlert && (
        <div className="reset-alert">
          <span>Filters have been reset to show all incidents.</span>
          <button onClick={() => setShowResetAlert(false)}>Close</button>
        </div>
      )}
      {lookbackFallback && (
        <div className="reset-alert" style={{ background: '#fef3c7', color: '#78350f', borderLeft: '4px solid #f59e0b' }}>
          <span>
            <i className="fas fa-info-circle" style={{ marginRight: 8 }}></i>
            No incidents in the last {lookbackFallback.days} days (system retention window). Showing all available data instead.
          </span>
          <button onClick={() => setLookbackFallback(null)}>Close</button>
        </div>
      )}
    </section>
  );
};

export default CrimeMapInterface;
