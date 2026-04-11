import React, { useState, useEffect } from 'react';
import { Modal, Radio, Card, Badge } from 'antd';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';
import { ppcSimpleLabel } from '../../utils/ppcUtils';

// Fix for default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Heatmap Layer Component
const HeatmapLayer = ({ points }) => {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    let heatLayer = null;

    const addLayer = () => {
      if (heatLayer) return;
      
      const size = map.getSize();
      if (size.x > 0 && size.y > 0) {
        // Format: [lat, lng, intensity]
        const heatPoints = points.map(p => [p.lat, p.lng, p.intensity || 1.0]);

        heatLayer = L.heatLayer(heatPoints, {
          radius: 25,
          blur: 15,
          maxZoom: 15,
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
      const timer = setTimeout(addLayer, 500); // Fallback
      
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

// Map Resizer to fix modal rendering issues
const MapResizer = () => {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 300);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
};

const RiskMapModal = ({ visible, onClose, incidents = [] }) => {
  const [viewMode, setViewMode] = useState('heatmap'); // 'heatmap', 'markers', 'both'

  // Filter valid coordinates
  const validIncidents = incidents.filter(
    inc => inc.coordinates && 
    (Array.isArray(inc.coordinates) ? inc.coordinates.length === 2 : (inc.latitude && inc.longitude))
  ).map(inc => ({
    ...inc,
    lat: Array.isArray(inc.coordinates) ? inc.coordinates[0] : inc.latitude,
    lng: Array.isArray(inc.coordinates) ? inc.coordinates[1] : inc.longitude,
    intensity: 1 // Default intensity
  }));

  const center = [31.5204, 74.3587]; // Lahore Center

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-map-marked-alt" style={{ color: '#00a6a6' }}></i>
          <span>Lahore Incident Risk Map</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
      style={{ top: 20 }}
      destroyOnClose
    >
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Radio.Group value={viewMode} onChange={e => setViewMode(e.target.value)} buttonStyle="solid">
          <Radio.Button value="heatmap">Heatmap View</Radio.Button>
          <Radio.Button value="markers">Pointer Map</Radio.Button>
          <Radio.Button value="both">Combined View</Radio.Button>
        </Radio.Group>
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <Badge color="red" text="High Risk" />
          <Badge color="yellow" text="Medium Risk" />
          <Badge color="blue" text="Low Risk" />
        </div>
      </div>

      <div style={{ height: '600px', width: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid #d9d9d9' }}>
        {visible && (
          <MapContainer
            center={center}
            zoom={12}
            style={{ height: '100%', width: '100%' }}
          >
            <MapResizer />
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />

            {(viewMode === 'heatmap' || viewMode === 'both') && (
              <HeatmapLayer points={validIncidents} />
            )}

            {(viewMode === 'markers' || viewMode === 'both') && validIncidents.map((inc, index) => (
              <Marker 
                key={index} 
                position={[inc.lat, inc.lng]}
              >
                <Popup>
                  <div style={{ minWidth: '200px' }}>
                    <h4 style={{ margin: '0 0 8px 0', color: '#00a6a6' }}>
                      <i className="fas fa-file-alt"></i> FIR Details
                    </h4>
                    <p style={{ margin: '4px 0', fontSize: '0.85rem' }}>
                      <strong>Type:</strong> {inc.crime_type || inc.type}
                      {(inc.crime_type || inc.type) && ppcSimpleLabel(inc.crime_type || inc.type) !== (inc.crime_type || inc.type) && (
                        <span style={{ color: '#6b7280', marginLeft: 4, fontSize: '0.8rem' }}>({ppcSimpleLabel(inc.crime_type || inc.type)})</span>
                      )}
                    </p>
                    <p style={{ margin: '4px 0', fontSize: '0.85rem' }}>
                      <strong>Area:</strong> {inc.crime_area || inc.area}
                      {(inc.area_translit || inc.crime_area_translit) && (inc.area_translit || inc.crime_area_translit) !== (inc.crime_area || inc.area) && (
                        <span style={{ color: '#6b7280', fontStyle: 'italic', display: 'block', fontSize: '0.82rem', marginTop: 1 }}>
                          {inc.area_translit || inc.crime_area_translit}
                        </span>
                      )}
                      {(inc.area_urdu || inc.crime_area_urdu) && (
                        <span style={{ fontFamily: "'Noto Nastaliq Urdu', serif", direction: 'rtl', display: 'block', fontSize: '0.82rem', color: '#374151', marginTop: 2 }}>
                          {inc.area_urdu || inc.crime_area_urdu}
                        </span>
                      )}
                    </p>
                    <p style={{ margin: '4px 0', fontSize: '0.85rem' }}><strong>Date:</strong> {new Date(inc.crime_date || inc.date).toLocaleDateString()}</p>
                    <p style={{ margin: '4px 0', fontSize: '0.85rem' }}><strong>Status:</strong> {inc.status || 'Reported'}</p>
                    <p style={{ margin: '4px 0', fontSize: '0.78rem', color: '#6b7280' }}>📍 {Number(inc.lat).toFixed(4)}, {Number(inc.lng).toFixed(4)}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>

      <div style={{ marginTop: 16, padding: '12px', background: '#f5f5f5', borderRadius: '8px' }}>
        <h4 style={{ margin: '0 0 8px 0' }}><i className="fas fa-info-circle"></i> Map Insights</h4>
        <p style={{ margin: 0, fontSize: '13px', color: '#666' }}>
          This interactive map visualizes incident density across Lahore. 
          The <strong>Heatmap</strong> shows high-concentration areas in red, indicating higher risk zones. 
          The <strong>Pointer Map</strong> allows you to inspect individual FIR details by clicking on markers.
          Use the toggle above to switch between views.
        </p>
      </div>
    </Modal>
  );
};

export default RiskMapModal;
