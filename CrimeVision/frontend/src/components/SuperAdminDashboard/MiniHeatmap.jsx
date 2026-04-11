import React, { useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

const HeatmapLayer = ({ points }) => {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    let heatLayer = null;

    const addLayer = () => {
      if (heatLayer) return;
      
      const size = map.getSize();
      if (size.x > 0 && size.y > 0) {
        const heatPoints = points
          .filter(p => p.coordinates || (p.latitude && p.longitude))
          .map(p => [
            Array.isArray(p.coordinates) ? p.coordinates[0] : p.latitude,
            Array.isArray(p.coordinates) ? p.coordinates[1] : p.longitude,
            1.0
          ]);

        heatLayer = L.heatLayer(heatPoints, {
          radius: 30,
          blur: 20,
          maxZoom: 12,
          max: 1.0,
          gradient: {
            0.4: 'blue',
            0.6: 'cyan',
            0.7: 'lime',
            0.8: 'yellow',
            1.0: 'red'
          }
        }).addTo(map);
      }
    };

    // Try adding immediately
    addLayer();

    // If failed (size 0), wait for resize or timeout
    if (!heatLayer) {
      map.on('resize', addLayer);
      const timer = setTimeout(addLayer, 500);
      
      return () => {
        map.off('resize', addLayer);
        clearTimeout(timer);
        if (heatLayer) map.removeLayer(heatLayer);
      };
    }

    return () => {
      if (heatLayer) map.removeLayer(heatLayer);
    };
  }, [map, points]);

  return null;
};

const MiniHeatmap = ({ incidents = [] }) => {
  const center = [31.5204, 74.3587]; // Lahore Center

  return (
    <MapContainer
      center={center}
      zoom={11}
      zoomControl={false}
      dragging={false}
      scrollWheelZoom={false}
      doubleClickZoom={false}
      attributionControl={false}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <HeatmapLayer points={incidents} />
    </MapContainer>
  );
};

export default MiniHeatmap;
