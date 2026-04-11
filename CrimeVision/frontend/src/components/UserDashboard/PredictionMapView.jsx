import React, { useState, useEffect } from 'react';
import styles from './PredictionMapView.module.css';
import apiService from '../../services/apiService_updated';
import RealPredictionMap from './RealPredictionMap';

const PredictionMapView = ({ prediction, onBack }) => {
  const [mapData, setMapData] = useState(null);
  const [areaDetails, setAreaDetails] = useState(null);
  const [crimes, setCrimes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRealMapData();
  }, [prediction.area]);

  const loadRealMapData = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Load data with better error handling
      const [areaData, crimesData] = await Promise.all([
        apiService.getAreaDetails(prediction.area).catch(error => {
          console.log('Area details not available:', error);
          return null;
        }),
        apiService.getCrimes({ area: prediction.area, limit: 500 }).catch(error => {
          console.log('Crimes data not available:', error);
          return [];
        })
      ]);

      console.log('📍 Real map data loaded:', { areaData, crimes: crimesData });

      setAreaDetails(areaData);
      setCrimes(crimesData || []);

      // Use coordinates from prediction (they should already be available)
      const coordinates = prediction.coordinates;
      
      if (!coordinates) {
        setError('No geographic data available for this area. Please try another area.');
        setLoading(false);
        return;
      }

      setMapData({
        center: coordinates,
        crimes: crimesData || [],
        analytics: areaData
      });

    } catch (error) {
      console.error('Error loading map data:', error);
      setError('Failed to load map data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatAreaName = (name) => {
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className={styles.mapViewContainer}>
        <div className={styles.loadingMessage}>
          <i className="fas fa-spinner fa-spin"></i>
          <p>Loading real prediction map for {formatAreaName(prediction.area)}...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.mapViewContainer}>
        <div className={styles.mapHeader}>
          <button className={styles.backButton} onClick={onBack}>
            <i className="fas fa-arrow-left"></i>
            Back to Results
          </button>
        </div>
        
        <div className={styles.errorMessage}>
          <i className="fas fa-exclamation-triangle"></i>
          <h3>Map Data Unavailable</h3>
          <p>{error}</p>
          <button className={styles.backBtn} onClick={onBack}>
            <i className="fas fa-arrow-left"></i> Back to Prediction Results
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.mapViewContainer}>
      {/* Header */}
      <div className={styles.mapHeader}>
        <button className={styles.backButton} onClick={onBack}>
          <i className="fas fa-arrow-left"></i>
          Back to Results
        </button>
        <div className={styles.headerTitle}>
          <h2>
            <i className="fas fa-map-marked-alt"></i>
            AI Risk Prediction Map - {formatAreaName(prediction.area)}
          </h2>
          <p>Interactive visualization of crime risk assessment with real data</p>
        </div>
      </div>

      {/* Real Prediction Map Component */}
      <RealPredictionMap 
        prediction={prediction}
        areaDetails={areaDetails}
        crimes={crimes}
      />
    </div>
  );
};

export default PredictionMapView;
