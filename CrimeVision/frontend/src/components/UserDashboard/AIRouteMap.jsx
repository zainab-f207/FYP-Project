// AIRouteMap.jsx - Complete version with draggable markers, popups, and manual placement

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import styles from './AIRouteMap.module.css';

// Fix for default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const AIRouteMap = ({ 
  routes, 
  selectedRoute, 
  startPosition, 
  destPosition, 
  onRouteSelect,
  onMapClick,
  onMarkerDrag,
  placementMode,
  startLocationName,
  destLocationName
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef({});
  const startMarkerRef = useRef(null);
  const destMarkerRef = useRef(null);
  const fitTimeoutRef = useRef(null);
  const [legendVisible, setLegendVisible] = useState(true);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current) return;
    
    // If map is already initialized on this ref, don't do it again
    if (mapInstanceRef.current) return;

    // CRITICAL: Check if the DOM element already has a leaflet instance
    // This is the most common cause of "Map container is already initialized"
    if (mapRef.current._leaflet_id) {
      // If it exists but we don't have a ref to it, it's a "ghost" map
      // We should try to find it and remove it, or just skip
      console.warn("Ghost map detected on container, skipping initialization");
      return;
    }

    try {
      const map = L.map(mapRef.current).setView([31.5204, 74.3587], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      // Add click handler for manual placement
      map.on('click', (e) => {
        if (onMapClick) {
          onMapClick(e.latlng.lat, e.latlng.lng);
        }
      });

      mapInstanceRef.current = map;
    } catch (err) {
      console.error("Failed to initialize Leaflet map:", err);
    }

    return () => {
      if (mapInstanceRef.current) {
        const map = mapInstanceRef.current;
        try {
          // Clear all layers first
          map.eachLayer(layer => {
            try { map.removeLayer(layer); } catch (e) {}
          });
          map.stop();
          map.off();
          map.remove();
        } catch (err) {
          console.warn("Map cleanup error:", err);
        }
        mapInstanceRef.current = null;
      }
    };
  }, [onMapClick]);

  // Update map cursor based on placement mode
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    
    const map = mapInstanceRef.current;
    const container = map.getContainer();
    if (!container) return;
    
    if (placementMode) {
      container.style.cursor = 'crosshair';
    } else {
      container.style.cursor = '';
    }
  }, [placementMode]);

  // Update start/destination markers
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Remove old markers
    if (startMarkerRef.current) {
      map.removeLayer(startMarkerRef.current);
      startMarkerRef.current = null;
    }
    if (destMarkerRef.current) {
      map.removeLayer(destMarkerRef.current);
      destMarkerRef.current = null;
    }

    // Add start marker
    if (startPosition) {
      const startIcon = L.divIcon({
        className: '',
        html: `<div style="
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 2px solid #3b82f6;
          border-radius: 10px;
          padding: 5px 12px;
          color: white;
          font-weight: 700;
          font-size: 0.75rem;
          white-space: nowrap;
          box-shadow: 0 0 0 4px rgba(59,130,246,0.18), 0 6px 20px rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          gap: 6px;
          letter-spacing: 0.05em;
          font-family: system-ui, sans-serif;
        ">
          <span style="width:8px;height:8px;background:#3b82f6;border-radius:50%;display:inline-block;"></span>
          START
        </div>`,
        iconSize: [90, 34],
        iconAnchor: [45, 34],
      });

      const startMarker = L.marker([startPosition.lat, startPosition.lng], {
        icon: startIcon,
        draggable: true,
      }).addTo(map);

      // Add popup
      const startAreaName = startLocationName || 'Start Location';
      startMarker.bindPopup(`
        <div style="font-family:system-ui,sans-serif;min-width:195px;background:linear-gradient(160deg,#0f172a,#1e293b);border-radius:12px;overflow:hidden;border:1px solid rgba(59,130,246,0.3);">
          <div style="background:rgba(59,130,246,0.12);border-left:4px solid #3b82f6;padding:10px 14px;display:flex;align-items:center;gap:8px;">
            <span style="font-size:1rem;">📍</span>
            <span style="color:#3b82f6;font-weight:700;font-size:0.88rem;letter-spacing:0.05em;">STARTING POINT</span>
          </div>
          <div style="padding:10px 14px;display:flex;flex-direction:column;gap:4px;">
            <div style="color:white;font-weight:600;font-size:0.85rem;margin-bottom:2px;">${startAreaName}</div>
            <div style="color:rgba(255,255,255,0.4);font-size:0.72rem;">${startPosition.lat.toFixed(5)}&deg;N &nbsp; ${startPosition.lng.toFixed(5)}&deg;E</div>
            <div style="color:#3b82f6;font-size:0.72rem;margin-top:4px;">&#x2630;&nbsp;Drag to reposition</div>
          </div>
        </div>
      `, { className: styles.darkPopup, maxWidth: 240 });

      // Handle drag
      startMarker.on('dragend', (e) => {
        const pos = e.target.getLatLng();
        if (onMarkerDrag) {
          onMarkerDrag('start', pos.lat, pos.lng);
        }
      });

      startMarkerRef.current = startMarker;
    }

    // Add destination marker
    if (destPosition) {
      const destIcon = L.divIcon({
        className: '',
        html: `<div style="
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 2px solid #10b981;
          border-radius: 10px;
          padding: 5px 12px;
          color: white;
          font-weight: 700;
          font-size: 0.75rem;
          white-space: nowrap;
          box-shadow: 0 0 0 4px rgba(16,185,129,0.18), 0 6px 20px rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          gap: 6px;
          letter-spacing: 0.05em;
          font-family: system-ui, sans-serif;
        ">
          <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;"></span>
          DESTINATION
        </div>`,
        iconSize: [110, 34],
        iconAnchor: [55, 34],
      });

      const destMarker = L.marker([destPosition.lat, destPosition.lng], {
        icon: destIcon,
        draggable: true,
      }).addTo(map);

      // Add popup
      const destAreaName = destLocationName || 'Destination';
      destMarker.bindPopup(`
        <div style="font-family:system-ui,sans-serif;min-width:195px;background:linear-gradient(160deg,#0f172a,#1e293b);border-radius:12px;overflow:hidden;border:1px solid rgba(16,185,129,0.3);">
          <div style="background:rgba(16,185,129,0.12);border-left:4px solid #10b981;padding:10px 14px;display:flex;align-items:center;gap:8px;">
            <span style="font-size:1rem;">🏁</span>
            <span style="color:#10b981;font-weight:700;font-size:0.88rem;letter-spacing:0.05em;">DESTINATION</span>
          </div>
          <div style="padding:10px 14px;display:flex;flex-direction:column;gap:4px;">
            <div style="color:white;font-weight:600;font-size:0.85rem;margin-bottom:2px;">${destAreaName}</div>
            <div style="color:rgba(255,255,255,0.4);font-size:0.72rem;">${destPosition.lat.toFixed(5)}&deg;N &nbsp; ${destPosition.lng.toFixed(5)}&deg;E</div>
            <div style="color:#10b981;font-size:0.72rem;margin-top:4px;">&#x2630;&nbsp;Drag to reposition</div>
          </div>
        </div>
      `, { className: styles.darkPopup, maxWidth: 240 });

      // Handle drag
      destMarker.on('dragend', (e) => {
        const pos = e.target.getLatLng();
        if (onMarkerDrag) {
          onMarkerDrag('destination', pos.lat, pos.lng);
        }
      });

      destMarkerRef.current = destMarker;
    }

    // Fit bounds if both markers exist
    if (startPosition && destPosition && mapInstanceRef.current) {
      const mapObj = mapInstanceRef.current;
      if (mapObj._animatingZoom) return; // Guard against zoom crash

      const bounds = L.latLngBounds(
        [startPosition.lat, startPosition.lng],
        [destPosition.lat, destPosition.lng]
      );
      try {
        mapObj.fitBounds(bounds, { padding: [100, 100], animate: false });
      } catch (e) { console.warn("fitBounds error:", e); }
    } else if (startPosition && mapInstanceRef.current) {
      if (!mapInstanceRef.current._animatingZoom) {
        mapInstanceRef.current.setView([startPosition.lat, startPosition.lng], 13, { animate: false });
      }
    } else if (destPosition && mapInstanceRef.current) {
      if (!mapInstanceRef.current._animatingZoom) {
        mapInstanceRef.current.setView([destPosition.lat, destPosition.lng], 13, { animate: false });
      }
    }
  }, [startPosition, destPosition, onMarkerDrag]);

  // Update routes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Clear existing route layers (but keep markers)
    Object.entries(layersRef.current).forEach(([key, layer]) => {
      if (key.startsWith('route_') || key.startsWith('risk_')) {
        try {
          if (layer && map.hasLayer(layer)) {
            map.removeLayer(layer);
          }
        } catch (e) {
          console.warn(`Error removing layer ${key}:`, e);
        }
      }
    });
    layersRef.current = {};

    if (!routes.length) return;

    const routeColors = {
      safest:       '#10b981',
      fastest:      '#3b82f6',
      shortest:     '#f59e0b',
      balanced:     '#a855f7',
      fastest_alt:  '#60a5fa', // light blue
      shortest_alt: '#fcd34d', // light amber
      alternative:  '#64748b', // slate-gray
    };

    // Add all routes to map
    routes.forEach((route, index) => {
      const color = routeColors[route.label] || '#64748b';
      const isSelected = selectedRoute?.route_type === route.route_type;

      const routeIcons = { safest: '🛡️', fastest: '⚡', shortest: '🛣️', alternative: '🔀' };
      const routeIcon = routeIcons[route.label] || '🗺️';
      const routeDisplayName = route.label === 'alternative'
        ? (route.alt_via ? `VIA ${route.alt_via.toUpperCase()}` : `ROUTE ${route.alt_index || ''}`)
        : (route.label || 'route').toUpperCase();
      const safetyColor = route.safety_analysis.overall_score >= 80 ? '#10b981'
        : route.safety_analysis.overall_score >= 60 ? '#3b82f6'
        : route.safety_analysis.overall_score >= 40 ? '#f59e0b' : '#ef4444';
      const trafficAdjusted = route.route_data.duration_min_traffic ?? route.route_data.duration_min;
      const hasTraffic = (route.route_data.traffic_multiplier || 1.0) > 1.0;

      // Add a small offset to overlapping routes to make them distinct
      const offset = (index - 1) * 0.00005;
      const coordinates = route.route_data.geometry.coordinates.map(coord => [
        coord[1] + offset,
        coord[0] + offset
      ]);

      // ── Glow casing (selected only) ─────────────────────────────────────
      const casing = L.polyline(coordinates, {
        color: color,
        weight: isSelected ? 20 : 0,
        opacity: 0.15,
        smoothFactor: 2,
        interactive: false,
      }).addTo(map);

      // ── Main polyline — all routes clearly visible, selected stands out ──
      const polyline = L.polyline(coordinates, {
        color: color,
        weight: isSelected ? 7 : 4,
        opacity: isSelected ? 1.0 : 0.78,
        dashArray: null,   // all solid — no dashes on any route
        lineCap: 'round',
        lineJoin: 'round',
        smoothFactor: 1.5,
      }).addTo(map);

      if (isSelected) {
        setTimeout(() => {
          casing.bringToFront();
          polyline.bringToFront();
        }, 0);
      }

      layersRef.current[`route_casing_${index}`] = casing;
      layersRef.current[`route_${index}`] = polyline;

      polyline.on('click', () => {
        if (onRouteSelect) onRouteSelect(route);
      });

      // ── Professional dark-glass popup ────────────────────────────────────
      const safetyLabel = route.safety_analysis.overall_score >= 80 ? 'Very Safe'
        : route.safety_analysis.overall_score >= 60 ? 'Safe'
        : route.safety_analysis.overall_score >= 40 ? 'Moderate' : 'Risky';
      const highRisk = route.safety_analysis.summary.high_risk_points;
      const medRisk  = route.safety_analysis.summary.medium_risk_points;
      const areasSnippet = (route.areas_along_route || []).slice(0, 3).join(' → ');
      const secondaryChips = (route.secondary_labels || []).map(sl =>
        `<span style="background:rgba(255,255,255,0.09);border:1px solid rgba(255,255,255,0.18);border-radius:8px;padding:1px 7px;font-size:0.62rem;font-weight:600;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.04em;">Also ${sl}</span>`
      ).join('');
      polyline.bindPopup(`
        <div style="font-family:system-ui,sans-serif;min-width:240px;background:linear-gradient(160deg,#0c1526,#1a2740);border-radius:14px;overflow:hidden;border:1px solid ${color}44;">
          <div style="background:linear-gradient(90deg,${color}28,${color}08);border-left:4px solid ${color};padding:11px 14px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:${secondaryChips ? '5px' : '0'};">
              <span style="font-size:1.15rem;">${routeIcon}</span>
              <span style="color:${color};font-weight:800;font-size:0.92rem;letter-spacing:0.06em;">${routeDisplayName} ROUTE</span>
              ${route.label === 'safest' ? '<span style="margin-left:auto;background:#f59e0b1a;border:1px solid #f59e0b55;color:#fbbf24;font-size:0.62rem;font-weight:700;padding:2px 8px;border-radius:20px;white-space:nowrap;">⭐ RECOMMENDED</span>' : ''}
            </div>
            ${secondaryChips ? `<div style="display:flex;gap:5px;flex-wrap:wrap;">${secondaryChips}</div>` : ''}
          </div>
          <div style="padding:12px 14px;display:flex;flex-direction:column;gap:9px;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
              <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 10px;">
                <div style="color:rgba(255,255,255,0.4);font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Distance</div>
                <div style="color:white;font-weight:700;font-size:0.95rem;">${route.route_data.distance_km}&nbsp;<span style="font-size:0.7rem;font-weight:400;color:rgba(255,255,255,0.5);">km</span></div>
              </div>
              <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 10px;">
                <div style="color:rgba(255,255,255,0.4);font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Est. Time${hasTraffic ? ' (w/ traffic)' : ''}</div>
                <div style="color:white;font-weight:700;font-size:0.95rem;">${trafficAdjusted}&nbsp;<span style="font-size:0.7rem;font-weight:400;color:rgba(255,255,255,0.5);">min</span></div>
              </div>
            </div>
            <div style="background:${safetyColor}12;border:1px solid ${safetyColor}33;border-radius:8px;padding:8px 11px;display:flex;align-items:center;justify-content:space-between;">
              <div>
                <div style="color:rgba(255,255,255,0.4);font-size:0.62rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:2px;">AI Safety Score</div>
                <div style="color:${safetyColor};font-weight:800;font-size:1.1rem;">${route.safety_analysis.overall_score}% <span style="font-size:0.75rem;font-weight:600;">${safetyLabel}</span></div>
              </div>
              <div style="text-align:right;">
                ${highRisk > 0 ? `<div style="color:#ef4444;font-size:0.72rem;">🔴 ${highRisk} high-risk point${highRisk > 1 ? 's' : ''}</div>` : ''}
                ${medRisk  > 0 ? `<div style="color:#f59e0b;font-size:0.72rem;">🟠 ${medRisk} medium-risk point${medRisk > 1 ? 's' : ''}</div>` : ''}
                ${highRisk === 0 && medRisk === 0 ? `<div style="color:#10b981;font-size:0.72rem;">✅ No risk points</div>` : ''}
              </div>
            </div>
            ${areasSnippet ? `<div style="color:rgba(255,255,255,0.35);font-size:0.7rem;"><span style="color:rgba(255,255,255,0.5);">Route: </span>${areasSnippet}${(route.areas_along_route || []).length > 3 ? ' &hellip;' : ''}</div>` : ''}
          </div>
          <div style="border-top:1px solid rgba(255,255,255,0.06);padding:7px 14px;display:flex;align-items:center;justify-content:space-between;">
            <span style="color:rgba(255,255,255,0.25);font-size:0.65rem;">Click route to select</span>
            <span style="color:${color};font-size:0.65rem;font-weight:600;">${isSelected ? '✔ Currently Selected' : 'Click to Compare'}</span>
          </div>
        </div>
      `, { className: styles.darkPopup, maxWidth: 300 });

      // Add risk point markers for selected route
      if (isSelected && route.safety_analysis.point_predictions) {
        route.safety_analysis.point_predictions.forEach((point, pIndex) => {
          const riskLevel = point.prediction.risk_level;

          // Show all risk levels with different colors
          let markerColor, markerIcon;
          if (riskLevel === 'High') {
            markerColor = '#ef4444';
            markerIcon = '🔴';
          } else if (riskLevel === 'Medium') {
            markerColor = '#f59e0b';
            markerIcon = '🟠';
          } else {
            markerColor = '#10b981';
            markerIcon = '🟢';
          }

          const riskMarkerIcon = L.divIcon({
            className: '',
            html: `
              <div style="
                width: 28px; height: 28px;
                border-radius: 50%;
                background: ${markerColor}22;
                border: 2px solid ${markerColor};
                display: flex; align-items: center; justify-content: center;
                font-size: 0.75rem; font-weight: 700;
                box-shadow: 0 0 0 4px ${markerColor}22, 0 4px 12px rgba(0,0,0,0.4);
                animation: pulse 2s infinite;
              ">${riskLevel === 'High' ? '!' : riskLevel === 'Medium' ? '~' : '✓'}</div>
            `,
            iconSize: [28, 28],
            iconAnchor: [14, 14],
          });

          const marker = L.marker([point.latitude, point.longitude], {
            icon: riskMarkerIcon,
          }).addTo(map);

          // Crimes recorded in this point's area (from the route's per-area
          // attribution). Filter to this point's area and dedupe.
          const crimesHere = Array.from(new Set(
            (route.crime_types_detected || [])
              .filter(c => c && typeof c === 'object' && c.area === point.area)
              .map(c => c.crime_type)
          ));
          const crimesHereHtml = crimesHere.length > 0 ? `
            <div style="border-top:1px solid rgba(255,255,255,0.08);padding:8px 14px 10px;">
              <div style="color:rgba(255,255,255,0.45);font-size:0.62rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:5px;">⚠️ Crimes recorded here</div>
              <div style="display:flex;flex-wrap:wrap;gap:4px;">
                ${crimesHere.slice(0, 4).map(ct =>
                  `<span style="background:${markerColor}1a;border:1px solid ${markerColor}44;color:rgba(255,255,255,0.85);font-size:0.7rem;padding:2px 7px;border-radius:6px;">${ct}</span>`
                ).join('')}
                ${crimesHere.length > 4 ? `<span style="color:rgba(255,255,255,0.5);font-size:0.7rem;padding:2px 4px;">+${crimesHere.length - 4} more</span>` : ''}
              </div>
            </div>
          ` : '';

          // Area baseline (from unified score) — same number the dashboard shows.
          const baseline = route.area_baselines?.[point.area];
          const baselineHtml = (baseline && baseline.safety_score != null) ? `
            <div style="color:rgba(255,255,255,0.7);font-size:0.78rem;">🏘️ Area baseline:&nbsp;<strong style="color:rgba(255,255,255,0.9);">${baseline.safety_score}% safe</strong> <span style="opacity:0.55;">(${baseline.risk_level})</span></div>
          ` : '';

          marker.bindPopup(`
            <div style="font-family:system-ui,sans-serif;min-width:220px;background:linear-gradient(160deg,#0f172a,#1e293b);border-radius:12px;overflow:hidden;border:1px solid ${markerColor}44;">
              <div style="background:${markerColor}18;border-left:4px solid ${markerColor};padding:10px 14px;display:flex;align-items:center;gap:8px;">
                <span style="font-size:1rem;">${markerIcon}</span>
                <span style="color:${markerColor};font-weight:700;font-size:0.88rem;">${riskLevel} Risk Zone</span>
              </div>
              <div style="padding:10px 14px;display:flex;flex-direction:column;gap:6px;">
                <div style="color:rgba(255,255,255,0.85);font-size:0.82rem;">📍 <strong style="color:white;">${point.area || 'Unknown Area'}</strong></div>
                <div style="color:rgba(255,255,255,0.85);font-size:0.82rem;">🤖 AI Risk:&nbsp;<strong style="color:${markerColor};">${point.prediction.risk_percentage}%</strong></div>
                ${baselineHtml}
                <div style="color:rgba(255,255,255,0.7);font-size:0.78rem;">🎯 Confidence:&nbsp;<strong style="color:rgba(255,255,255,0.9);">${(point.prediction.confidence * 100).toFixed(0)}%</strong></div>
              </div>
              ${crimesHereHtml}
            </div>
          `, { className: styles.darkPopup, maxWidth: 280 });

          layersRef.current[`risk_${index}_${pIndex}`] = marker;
        });
      }
    });

    // Clear any pending timeout
    if (fitTimeoutRef.current) clearTimeout(fitTimeoutRef.current);

    // Fit map to show all routes
    if (routes.length > 0 && mapInstanceRef.current) {
      const map = mapInstanceRef.current;
      
      // CRITICAL: If map is currently zooming, don't try to fit bounds yet
      // This is often the cause of the _leaflet_pos error
      if (map._animatingZoom) {
        fitTimeoutRef.current = setTimeout(() => {
          // Re-trigger after animation finishes
          // (This is a simplified re-trigger, the effect will run again on deps anyway)
        }, 500);
        return;
      }

      try {
        const allCoords = routes.flatMap(route =>
          route.route_data.geometry.coordinates.map(coord => [coord[1], coord[0]])
        );
        if (allCoords.length > 0) {
          const bounds = L.latLngBounds(allCoords);
          
          fitTimeoutRef.current = setTimeout(() => {
            if (mapInstanceRef.current && !mapInstanceRef.current._animatingZoom) {
              try {
                const mapInstance = mapInstanceRef.current;
                if (mapInstance.getPane('mapPane')) {
                  mapInstance.invalidateSize();
                  // Force animate: false to be safe
                  mapInstance.fitBounds(bounds, { padding: [50, 50], animate: false });
                }
              } catch (e) {
                console.warn("fitBounds failed:", e);
              }
            }
          }, 300); // Increased timeout to be safer
        }
      } catch (err) {
        console.warn("Error fitting bounds:", err);
      }
    }

    return () => {
      if (fitTimeoutRef.current) clearTimeout(fitTimeoutRef.current);
    };
  }, [routes, selectedRoute, onRouteSelect]);

  return (
    <div className={styles.mapContainer}>
      {legendVisible ? (
        <div className={styles.mapLegend}>
          <div className={styles.legendHeader}>
            <h4>Map Legend</h4>
            <button
              className={styles.legendClose}
              onClick={() => setLegendVisible(false)}
              title="Close legend"
            >×</button>
          </div>
          <div className={styles.legendDivider}></div>
          <div className={styles.legendGroup}>
            <div className={styles.legendGroupLabel}>Routes</div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#10b981' }}></span>
              <span>🛡️ Safest Route</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#3b82f6' }}></span>
              <span>⚡ Fastest Route</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#f59e0b' }}></span>
              <span>🛣️ Shortest Route</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#64748b' }}></span>
              <span>🔀 Alternative Route</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#60a5fa' }}></span>
              <span>⚡ Fastest Alternative</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendColor} style={{ backgroundColor: '#fcd34d' }}></span>
              <span>🛣️ Shortest Alternative</span>
            </div>
          </div>
          <div className={styles.legendDivider}></div>
          <div className={styles.legendGroup}>
            <div className={styles.legendGroupLabel}>Risk Level</div>
            <div className={styles.legendItem}>
              <span className={styles.legendDot} style={{ backgroundColor: '#ef4444' }}></span>
              <span>🔴 High Risk (61–100%)</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendDot} style={{ backgroundColor: '#f59e0b' }}></span>
              <span>🟠 Medium Risk (21–60%)</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendDot} style={{ backgroundColor: '#10b981' }}></span>
              <span>🟢 Safe (0–20%)</span>
            </div>
          </div>
          {placementMode && (
            <>
              <div className={styles.legendDivider}></div>
              <div className={styles.legendItem} style={{ color: '#f59e0b' }}>
                <i className="fas fa-hand-pointer"></i>
                <span>Click map to place {placementMode}</span>
              </div>
            </>
          )}
        </div>
      ) : (
        <button
          className={styles.legendToggle}
          onClick={() => setLegendVisible(true)}
          title="Show map legend"
        >📍 Legend</button>
      )}
      <div ref={mapRef} className={styles.map}></div>
    </div>
  );
};

export default AIRouteMap;
