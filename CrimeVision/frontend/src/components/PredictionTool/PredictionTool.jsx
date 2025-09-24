import React, { useState, useEffect, useRef } from 'react';
import './PredictionTool.css';
import apiService from '../../services/api';

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

const PredictionTool = ({ selectedArea, selectedCrimeType }) => {
  const [area, setArea] = useState('');
  const [date, setDate] = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [areas, setAreas] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [riskPercentage, setRiskPercentage] = useState(0);
  const [riskLevel, setRiskLevel] = useState('');
  const [riskClass, setRiskClass] = useState('');
  const [description, setDescription] = useState('');
  const [precautions, setPrecautions] = useState([]);
  const [message, setMessage] = useState('');
  const [confidence, setConfidence] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const circleRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.prediction-form, .prediction-result');
    fadeElements.forEach(element => {
      observer.observe(element);
    });

    return () => {
      fadeElements.forEach(element => {
        observer.unobserve(element);
      });
    };
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching areas and crime types for prediction tool...');
        const [areasResponse, crimeTypesResponse] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);
        
        console.log('Prediction tool - Raw areas response:', areasResponse);
        console.log('Prediction tool - Raw crime types response:', crimeTypesResponse);
        
        const areasData = areasResponse.areas || [];
        const crimeTypesData = crimeTypesResponse.crime_types || [];
        
        console.log('Prediction tool - Processed areas:', areasData);
        console.log('Prediction tool - Processed crime types:', crimeTypesData);
        
        setAreas(areasData);
        setCrimeTypes(crimeTypesData);
      } catch (error) {
        console.error('Error fetching prediction data:', error);
        setAreas([]);
        setCrimeTypes([]);
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

  // Auto-select area from search
  useEffect(() => {
    if (selectedArea) {
      setArea(selectedArea);
      if (crimeType) {
        setTimeout(() => calculateRisk(selectedArea, crimeType, date), 500);
      }
    }
  }, [selectedArea]);

  // Auto-select crime type from search
  useEffect(() => {
    if (selectedCrimeType) {
      setCrimeType(selectedCrimeType);
      if (area) {
        setTimeout(() => calculateRisk(area, selectedCrimeType, date), 500);
      }
    }
  }, [selectedCrimeType]);

  // Animate circle stroke based on risk percentage
  useEffect(() => {
    if (circleRef.current && riskPercentage !== null && riskPercentage !== '...') {
      const radius = 54;
      const circumference = 2 * Math.PI * radius;
      const offset = circumference - (riskPercentage / 100) * circumference;
      
      circleRef.current.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
      circleRef.current.style.strokeDashoffset = offset;
      
      if (riskLevel.includes('High')) {
        circleRef.current.style.stroke = riskDescriptions.High.color;
      } else if (riskLevel.includes('Medium')) {
        circleRef.current.style.stroke = riskDescriptions.Medium.color;
      } else {
        circleRef.current.style.stroke = riskDescriptions.Low.color;
      }
    }
  }, [riskPercentage, riskLevel]);

  const calculateRisk = async (areaParam = area, crimeTypeParam = crimeType, dateParam = date) => {
    setPredicting(true);
    setRiskPercentage('...');
    setRiskLevel('');
    setRiskClass('');
    setDescription('');
    setPrecautions([]);
    setMessage('');
    setConfidence(0);
    setShowDetails(false);

    try {
      const prediction = await apiService.predictRisk(areaParam, crimeTypeParam, dateParam);

      if (prediction && prediction.risk_level && prediction.risk_percentage !== undefined) {
        const newRiskPercentage = prediction.risk_percentage;
        const newRiskLevel = prediction.risk_level;
        const newConfidence = prediction.confidence || 0;

        let newRiskClass = 'risk-medium';
        if (newRiskLevel === 'Low') {
          newRiskClass = 'risk-low';
        } else if (newRiskLevel === 'High') {
          newRiskClass = 'risk-high';
        }

        setRiskPercentage(newRiskPercentage);
        setRiskLevel(`${newRiskLevel} Risk`);
        setRiskClass(newRiskClass);
        setDescription(riskDescriptions[newRiskLevel]?.description || '');
        setPrecautions(riskDescriptions[newRiskLevel]?.precautions || []);
        setConfidence(newConfidence);

        if (prediction.message) {
          setMessage(prediction.message);
        }

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
    setRiskPercentage(50);
    setRiskLevel('Medium Risk');
    setRiskClass('risk-medium');
    setDescription(riskDescriptions['Medium'].description);
    setPrecautions(riskDescriptions['Medium'].precautions);
    setConfidence(0.5);
    setShowDetails(true);
  };

  const formatAreaName = (name) => {
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getRiskIcon = () => {
    if (riskLevel.includes('High')) return riskDescriptions.High.icon;
    if (riskLevel.includes('Medium')) return riskDescriptions.Medium.icon;
    return riskDescriptions.Low.icon;
  };

  return (
    <section className="prediction-tool section-padding" id="prediction">
      <div className="section-title">
        <h2>Check Area Safety</h2>
        <span className="urdu-text">علاقے کی حفاظت چیک کریں</span>
        <p>Use our AI prediction tool to assess crime risk for specific areas and times</p>
      </div>

      <div className="prediction-container">
        <div className="prediction-form fade-in">
          <h3>Risk Assessment Tool</h3>
          <p className="form-subtitle">Select an area and crime type to get started</p>

          <div className="form-group">
            <label htmlFor="area">Select Area</label>
            <select 
              id="area" 
              value={area} 
              onChange={(e) => setArea(e.target.value)}
              className={area ? 'has-value' : ''}
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

          <div className="form-group">
            <label htmlFor="crime-type">Crime Type</label>
            <select 
              id="crime-type" 
              value={crimeType} 
              onChange={(e) => setCrimeType(e.target.value)}
              className={crimeType ? 'has-value' : ''}
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

          <div className="form-group">
            <label htmlFor="date">Date</label>
            <input 
              type="date" 
              id="date" 
              value={date} 
              onChange={(e) => setDate(e.target.value)}
              className={date ? 'has-value' : ''}
            />
          </div>

          <button
            className={`btn btn-primary ${predicting ? 'loading' : ''}`}
            style={{width: '100%'}}
            onClick={() => {
              if (!area || !crimeType) {
                alert('Please select both area and crime type before checking risk level.');
                return;
              }
              calculateRisk(area, crimeType, date);
            }}
            disabled={predicting || !area || !crimeType}
          >
            {predicting ? 'Analyzing...' : 'Check Risk Level'}
          </button>

          {message && (
            <div className="info-message">
              <i className="fas fa-info-circle"></i> {message}
            </div>
          )}
        </div>

        <div className="prediction-result fade-in" id="predictionResult">
          <h3>Risk Assessment {riskLevel && getRiskIcon()}</h3>
          
          <div className="risk-visualization">
            <div className="risk-meter">
              <svg width="200" height="200" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="var(--light-bg)" strokeWidth="12" />
                <circle
                  ref={circleRef}
                  cx="60"
                  cy="60"
                  r="54"
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
              <div className={`risk-value ${riskClass}`}>
                {riskPercentage}{riskPercentage !== '...' && '%'}
              </div>
            </div>
            
            <div className="risk-info">
              <div className={`risk-label ${riskClass}`}>
                {riskLevel || 'No assessment yet'}
              </div>
              
              {area && crimeType && (
                <div className="prediction-context">
                  <p><strong>Area:</strong> {formatAreaName(area)}</p>
                  <p><strong>Crime Type:</strong> {crimeType}</p>
                  <p><strong>Date:</strong> {new Date(date).toLocaleDateString()}</p>
                </div>
              )}
            </div>
          </div>

          {showDetails && (
            <div className="risk-details">
              <div className="description-box">
                <h4>Overview</h4>
                <p>{description}</p>
              </div>

              <div className="confidence-indicator">
                <span className="confidence-label">Model Confidence: </span>
                <span className="confidence-value">{Math.round(confidence * 100)}%</span>
                <div className="confidence-bar">
                  <div 
                    className="confidence-fill" 
                    style={{width: `${confidence * 100}%`}}
                  ></div>
                </div>
              </div>

              <div className="safety-recommendations">
                <h4>Safety Recommendations</h4>
                <ul>
                  {precautions.map((precaution, index) => (
                    <li key={index}>
                      <i className="fas fa-shield-alt"></i> {precaution}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="action-buttons">
                <button 
                  className="btn btn-secondary"
                  onClick={() => calculateRisk(area, crimeType, date)}
                >
                  <i className="fas fa-sync-alt"></i> Re-assess Risk
                </button>
                <button 
                  className="btn btn-outline"
                  onClick={() => window.print()}
                >
                  <i className="fas fa-print"></i> Print Safety Plan
                </button>
              </div>
            </div>
          )}

          {!riskLevel && (
            <div className="empty-state">
              <div className="empty-icon">
                <i className="fas fa-search"></i>
              </div>
              <p>Select an area and crime type to see risk assessment</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default PredictionTool;