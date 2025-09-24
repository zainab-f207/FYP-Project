import React, { useState, useEffect } from 'react';
import styles from './PredictionSection.module.css';
import apiService from '../../services/apiService';

const riskDescriptions = {
  Low: {
    description: "This area has a low crime risk. It's generally safe to move around freely.",
    precautions: [
      "Stay aware of your surroundings.",
      "Keep your valuables secure.",
      "Report any suspicious activity.",
      "Follow normal safety precautions."
    ],
    color: "#22c55e",
    icon: "✅"
  },
  Medium: {
    description: "This area has a medium crime risk. Exercise caution especially during night time.",
    precautions: [
      "Stay in well-lit areas after dark.",
      "Avoid walking alone at night.",
      "Keep valuables out of sight.",
      "Remain aware of your surroundings.",
      "Use trusted transportation services."
    ],
    color: "#f59e0b",
    icon: "⚠️"
  },
  High: {
    description: "This area has a high crime risk. Take extra precautions to ensure your safety.",
    precautions: [
      "Avoid unnecessary travel after dark.",
      "Travel in groups if possible.",
      "Keep emergency contacts handy.",
      "Stay alert and avoid distractions.",
      "Consider alternative routes if possible."
    ],
    color: "#dc2626",
    icon: "🚨"
  }
};

const PredictionSection = ({ onPredictionComplete }) => {
  const [area, setArea] = useState('');
  const [date, setDate] = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [areas, setAreas] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [areasResponse, crimeTypesResponse] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);

        const areasData = areasResponse.areas || [];
        const crimeTypesData = crimeTypesResponse.crime_types || [];

        setAreas(areasData);
        setCrimeTypes(crimeTypesData);
      } catch (error) {
        console.error('Error fetching prediction data:', error);
        setMessage('Unable to load areas and crime types. Please check if the backend server is running.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Set default date to today
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setDate(today);
  }, []);

  const calculateRisk = async (areaParam = area, crimeTypeParam = crimeType, dateParam = date) => {
    setPredicting(true);
    setMessage('');

    try {
      const prediction = await apiService.predictRisk(areaParam, crimeTypeParam, dateParam);

      if (prediction && prediction.risk_level && prediction.risk_percentage !== undefined) {
        const newRiskPercentage = prediction.risk_percentage;
        const newRiskLevel = prediction.risk_level;
        const newConfidence = prediction.confidence || 0;

        if (prediction.message) {
          setMessage(prediction.message);
        }

        // Notify parent component about prediction completion
        if (onPredictionComplete) {
          onPredictionComplete({
            area: areaParam,
            crimeType: crimeTypeParam,
            date: dateParam,
            riskLevel: newRiskLevel,
            riskPercentage: newRiskPercentage,
            confidence: newConfidence
          });
        }
      } else {
        setMessage('Error: Invalid prediction response from server');
      }
    } catch (error) {
      console.error('Error calculating risk:', error);
      setMessage('Error connecting to prediction service. Please try again.');
    } finally {
      setPredicting(false);
    }
  };

  const formatAreaName = (name) => {
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className={`${styles.predictionSection} ${styles.fadeIn}`} id="risk-prediction">
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Risk Prediction Tool</h3>
        <p className={styles.sectionSubtitle}>Get AI-powered crime risk predictions for specific areas</p>
      </div>

      <div className={styles.predictionContainer}>
        <div className={styles.predictionForm}>
          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="prediction-area">Area</label>
              <select
                id="prediction-area"
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className={area ? styles.hasValue : ''}
              >
                <option value="">
                  {loading ? "Loading areas..." : "Select an area in Lahore"}
                </option>
                {areas.map((areaName, index) => (
                  <option key={index} value={areaName}>
                    {formatAreaName(areaName)}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="prediction-crime-type">Crime Type</label>
              <select
                id="prediction-crime-type"
                value={crimeType}
                onChange={(e) => setCrimeType(e.target.value)}
                className={crimeType ? styles.hasValue : ''}
              >
                <option value="">
                  {loading ? "Loading crime types..." : "Select crime type"}
                </option>
                {crimeTypes.map((crime, index) => (
                  <option key={index} value={crime}>
                    {crime}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label htmlFor="prediction-date">Date</label>
              <input
                type="date"
                id="prediction-date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={date ? styles.hasValue : ''}
              />
            </div>

            <div className={styles.formGroup}>
              <button
                className={`${styles.btn} ${styles.btnPrimary} ${predicting ? styles.loading : ''}`}
                onClick={() => {
                  if (!area || !crimeType) {
                    alert('Please select both area and crime type before checking risk level.');
                    return;
                  }
                  calculateRisk(area, crimeType, date);
                }}
                disabled={predicting || !area || !crimeType}
              >
                {predicting ? 'Analyzing...' : 'Predict Risk'}
              </button>
            </div>
          </div>

          {message && (
            <div className={styles.infoMessage}>
              <i className="fas fa-info-circle"></i> {message}
            </div>
          )}
        </div>

        {/* Empty state message */}
        <div className={styles.predictionResult}>
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <i className="fas fa-search-location"></i>
            </div>
            <p>Select an area and crime type, then click "Predict Risk" to see results</p>
            <small>The prediction results will appear above the dashboard cards</small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PredictionSection;