// src/components/HeatmapLayer.jsx
import { useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet.heat";

export default function HeatmapLayer({ points, radius = 25, blur = 15, maxZoom = 17, gradient }) {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const heat = window.L.heatLayer(
      points.map(p => [p.lat, p.lng, p.intensity || 1]),
      { 
        radius,
        blur,
        maxZoom,
        gradient: gradient || {
          0.4: 'blue',
          0.6: 'cyan',
          0.7: 'lime',
          0.8: 'yellow',
          0.9: 'red'
        }
      }
    );

    heat.addTo(map);

    return () => {
      map.removeLayer(heat);
    };
  }, [points, map, radius, blur, maxZoom, gradient]);

  return null;
}