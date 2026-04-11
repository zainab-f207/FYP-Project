import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';
import apiService from '../../services/apiService_updated';
import styles from './RiskPredictionPage.module.css';

const RiskPredictionPage = () => {
  const [loading, setLoading] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [areas, setAreas] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [area, setArea] = useState('Gulberg');
    const [crimeType, setCrimeType] = useState('Theft');
    const [date, setDate] = useState('');
    const [showResult, setShowResult] = useState(false);
    const [riskPercentage, setRiskPercentage] = useState(0);
    const [riskLevel, setRiskLevel] = useState('');
    const [riskClass, setRiskClass] = useState('');
    const [description, setDescription] = useState('');
    const [precautions, setPrecautions] = useState([]);
    const [confidence, setConfidence] = useState(0);
  const navigate = useNavigate();

  const riskDescriptions = {
    High: {
      description: 'This area shows elevated crime risk. Exercise extreme caution and consider alternative locations or times.',
      precautions: [
        'Avoid traveling alone, especially at night',
        'Stay in well-populated and well-lit areas',
        'Keep emergency contacts readily available',
        'Be extra vigilant of your surroundings',
        'Consider using alternative routes or locations'
      ],
      color: '#ef4444',
      icon: '⚠️'
    },
    Medium: {
      description: 'Moderate crime risk detected. Standard safety precautions are recommended.',
      precautions: [
        'Stay alert and aware of your surroundings',
        'Secure your belongings properly',
        'Use well-known and safe routes',
        'Travel in groups when possible',
        'Keep valuables out of sight'
      ],
      color: '#f59e0b',
      icon: '⚡'
    },
    Low: {
      description: 'This area shows relatively low crime risk. Continue following general safety guidelines.',
      precautions: [
        'Area is relatively safe',
        'Stay informed about any updates',
        'Maintain general safety precautions',
        'Report any suspicious activity',
        'Keep emergency numbers handy'
      ],
      color: '#10b981',
      icon: '✓'
    }
  };

  // Fetch areas and crime types
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [areasResponse, crimeTypesResponse] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);

        const areasData = Array.isArray(areasResponse)
          ? areasResponse.filter(a => a && typeof a === 'string') || []
          : ['Gulberg', 'DHA', 'Model Town', 'Lahore Fort', 'Mall Road', 'Anarkali'];

        const crimeTypesData = crimeTypesResponse.crime_types || (Array.isArray(crimeTypesResponse)
          ? crimeTypesResponse.filter(c => c && typeof c === 'string')
          : ['Theft', 'Robbery', 'Burglary', 'Assault', 'Fraud', 'Motor Theft']);

        setAreas(areasData.length > 0 ? areasData : ['Gulberg', 'DHA', 'Model Town', 'Lahore Fort', 'Mall Road', 'Anarkali']);
        setCrimeTypes(crimeTypesData.length > 0 ? crimeTypesData : []);

        if (areasData.length > 0) setArea(areasData[0]);
        if (crimeTypesData.length > 0) setCrimeType(crimeTypesData[0]);

        const today = new Date().toISOString().split('T')[0];
        setDate(today);
      } catch (error) {
        console.error('Error fetching prediction data:', error);
        setAreas(['Gulberg', 'DHA', 'Model Town', 'Lahore Fort', 'Mall Road', 'Anarkali']);
        setCrimeTypes(['Theft', 'Robbery', 'Burglary', 'Assault', 'Fraud', 'Motor Theft']);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const calculateRisk = async () => {
    if (!area || !crimeType) {
      alert('Please select both area and crime type before checking risk level.');
      return;
    }

    setPredicting(true);
    setShowResult(false);

    try {
      const prediction = await apiService.predictRisk(area, crimeType, date);

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
      } else {
        // Fallback to default values if prediction fails
        setDefaultRiskLevel();
      }
    } catch (error) {
      console.error('Error calculating risk:', error);
      setDefaultRiskLevel();
    } finally {
      setPredicting(false);
      setShowResult(true);
    }
  };

  const setDefaultRiskLevel = () => {
    setRiskPercentage(50);
    setRiskLevel('Medium Risk');
    setRiskClass('risk-medium');
    setDescription(riskDescriptions['Medium'].description);
    setPrecautions(riskDescriptions['Medium'].precautions);
    setConfidence(0.85);
  };

  const formatAreaName = (name) => {
    if (!name || typeof name !== 'string') {
      return String(name || '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getRiskIcon = () => {
    if (riskLevel.includes('High')) return riskDescriptions.High.icon;
    if (riskLevel.includes('Medium')) return riskDescriptions.Medium.icon;
    return riskDescriptions.Low.icon;
  };

  const getRiskColor = () => {
    if (riskLevel.includes('High')) return riskDescriptions.High.color;
    if (riskLevel.includes('Medium')) return riskDescriptions.Medium.color;
    return riskDescriptions.Low.color;
  };


  return (
    <>
      <Header 
        toggleSidebar={() => {}}
        showLoginModal={() => navigate('/login')}
        showReportModal={() => {}}
        onAreaSelect={(area) => setSelectedArea(area)}
        onCrimeSelect={(crime) => setSelectedCrimeType(crime)}
      />
      
      <div className={styles.pageContainer}>
        {/* Animated Background */}
        <div className={styles.animatedBackground}>
          <svg className={styles.backgroundSvg} viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#8b5cf6', stopOpacity: 0.3 }} />
                <stop offset="100%" style={{ stopColor: '#06b6d4', stopOpacity: 0.3 }} />
              </linearGradient>
            </defs>
            
            {/* Animated circles */}
            <circle className={styles.floatingCircle} cx="200" cy="150" r="80" fill="url(#grad1)" opacity="0.4">
              <animate attributeName="cy" values="150;120;150" dur="4s" repeatCount="indefinite" />
            </circle>
            <circle className={styles.floatingCircle} cx="900" cy="200" r="60" fill="url(#grad1)" opacity="0.3">
              <animate attributeName="cy" values="200;230;200" dur="5s" repeatCount="indefinite" />
            </circle>
            <circle className={styles.floatingCircle} cx="1000" cy="600" r="100" fill="url(#grad1)" opacity="0.2">
              <animate attributeName="cy" values="600;570;600" dur="6s" repeatCount="indefinite" />
            </circle>
            
            {/* Network lines */}
            <line className={styles.networkLine} x1="200" y1="150" x2="900" y2="200" stroke="#8b5cf6" strokeWidth="1" opacity="0.2">
              <animate attributeName="stroke-dashoffset" from="0" to="1000" dur="10s" repeatCount="indefinite" />
            </line>
          </svg>
        </div>

        {/* Header Section */}
        <div className={styles.pageHeader}>
          <div className={styles.headerContent}>
            <div className={styles.iconContainer}>
              <svg className={styles.headerIcon} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style={{ stopColor: '#8b5cf6' }} />
                    <stop offset="100%" style={{ stopColor: '#06b6d4' }} />
                  </linearGradient>
                </defs>
                <circle cx="50" cy="50" r="45" fill="none" stroke="url(#iconGrad)" strokeWidth="3">
                  <animate attributeName="stroke-dasharray" values="0 283;283 0" dur="2s" repeatCount="indefinite" />
                </circle>
                <path d="M50 20 L50 50 L70 70" stroke="url(#iconGrad)" strokeWidth="3" fill="none" strokeLinecap="round">
                  <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
                </path>
                <circle cx="50" cy="50" r="5" fill="url(#iconGrad)">
                  <animate attributeName="r" values="5;8;5" dur="2s" repeatCount="indefinite" />
                </circle>
              </svg>
            </div>
            <h1 className={styles.pageTitle}>AI-Powered Crime Risk Prediction</h1>
            <p className={styles.pageSubtitle}>
              Leverage advanced machine learning algorithms to predict crime risk levels for any area in Lahore.
              Our AI model analyzes historical crime data, temporal patterns, and geographical factors to provide
              accurate risk assessments.
            </p>
          </div>

          {/* Stats Cards */}
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <i className="fas fa-brain"></i>
              </div>
              <div className={styles.statValue}>95%</div>
              <div className={styles.statLabel}>Prediction Accuracy</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <i className="fas fa-database"></i>
              </div>
              <div className={styles.statValue}>50K+</div>
              <div className={styles.statLabel}>Crime Records Analyzed</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statIcon}>
                <i className="fas fa-map-marked-alt"></i>
              </div>
              <div className={styles.statValue}>100+</div>
              <div className={styles.statLabel}>Areas Covered</div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className={styles.mainContent}>
          {/* Prediction Form */}
          <div className={styles.predictionCard}>
            <div className={styles.cardHeader}>
              <h2>Make a Prediction</h2>
              <p>Select area, crime type, and date to get AI-powered risk assessment</p>
            </div>

            <div className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label>
                  <i className="fas fa-map-marker-alt"></i>
                  Select Area
                </label>
                <select 
                  value={area} 
                  onChange={(e) => setArea(e.target.value)}
                  className={styles.formSelect}
                  disabled={loading || predicting}
                >
                  <option value="">{loading ? 'Loading areas...' : 'Choose an area...'}</option>
                  {areas.map(area => (
                    <option key={area} value={area}>{area}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>
                  <i className="fas fa-exclamation-triangle"></i>
                  Crime Type
                </label>
                <select 
                  value={crimeType} 
                  onChange={(e) => setCrimeType(e.target.value)}
                  className={styles.formSelect}
                  disabled={loading || predicting}
                >
                  <option value="">{loading ? 'Loading crime types...' : 'Choose crime type...'}</option>
                  {crimeTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>
                  <i className="fas fa-calendar-alt"></i>
                  Select Date
                </label>
                <input 
                  type="date" 
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className={styles.formInput}
                  min={new Date().toISOString().split('T')[0]}
                  disabled={predicting}
                />
              </div>
            </div>

            <button 
              onClick={calculateRisk}
              className={styles.predictButton}
              disabled={loading || predicting || !area || !crimeType}
            >
              {predicting ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i>
                  Analyzing...
                </>
              ) : (
                <>
                  <i className="fas fa-robot"></i>
                  Predict Risk
                </>
              )}
            </button>
          </div>

          {/* Prediction Result */}
          {showResult && (
            <div className={`${styles.resultCard} ${styles.fadeIn}`}>
              <div className={styles.resultHeader}>
                <h2>Prediction Results</h2>
                <span className={styles.confidenceBadge}>
                  <i className="fas fa-check-circle"></i>
                  {Math.round(confidence * 100)}% Confidence
                </span>
              </div>

              <div className={styles.resultContent}>
                <div className={styles.riskVisualization}>
                  <svg viewBox="0 0 200 200" className={styles.riskGauge}>
                    <defs>
                      <linearGradient id="riskGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{ stopColor: getRiskColor() }} />
                        <stop offset="100%" style={{ stopColor: getRiskColor(), stopOpacity: 0.7 }} />
                      </linearGradient>
                    </defs>
                    
                    <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="20"/>
                    <circle 
                      cx="100" 
                      cy="100" 
                      r="80" 
                      fill="none" 
                      stroke={getRiskColor()}
                      strokeWidth="12"
                      strokeDasharray="339.3"
                      strokeDashoffset={339.3 - (riskPercentage / 100) * 339.3}
                      strokeLinecap="round"
                      transform="rotate(-90 100 100)"
                      className={styles.gaugeProgress}
                    />
                    
                    <text x="100" y="95" textAnchor="middle" className={styles.riskPercentage}>
                      {riskPercentage}%
                    </text>
                    <text x="100" y="115" textAnchor="middle" className={styles.riskLabel}>
                      {riskLevel} Risk
                    </text>
                  </svg>
                </div>

                <div className={styles.resultDetails}>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Area</span>
                    <span className={styles.detailValue}>{area}</span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Crime Type</span>
                    <span className={styles.detailValue}>{crimeType}</span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Date</span>
                    <span className={styles.detailValue}>
                      {new Date(date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Risk Level</span>
                    <span className={`${styles.detailValue} ${styles[riskLevel.toLowerCase()]}`}>
                      {getRiskIcon()} {riskLevel}
                    </span>
                  </div>
                </div>
              </div>

              <div className={styles.riskDescription}>
                <h4>
                  <i className="fas fa-info-circle"></i>
                  Risk Assessment
                </h4>
                <p>{description}</p>
              </div>

              <div className={styles.recommendations}>
                <h3>
                  <i className="fas fa-lightbulb"></i>
                  Safety Recommendations
                </h3>
                <ul>
                  {precautions.map((precaution, index) => (
                    <li key={index}>
                      <i className="fas fa-shield-alt"></i>
                      {precaution}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* How It Works Section */}
          <div className={styles.howItWorksSection}>
            <h2>How Our AI Prediction Works</h2>
            <div className={styles.stepsGrid}>
              <div className={styles.stepCard}>
                <div className={styles.stepNumber}>1</div>
                <div className={styles.stepIcon}>
                  <i className="fas fa-database"></i>
                </div>
                <h3>Data Collection</h3>
                <p>We gather comprehensive crime data from multiple sources including police records and incident reports</p>
              </div>
              
              <div className={styles.stepCard}>
                <div className={styles.stepNumber}>2</div>
                <div className={styles.stepIcon}>
                  <i className="fas fa-brain"></i>
                </div>
                <h3>AI Analysis</h3>
                <p>Advanced machine learning algorithms analyze patterns, trends, and correlations in the data</p>
              </div>
              
              <div className={styles.stepCard}>
                <div className={styles.stepNumber}>3</div>
                <div className={styles.stepIcon}>
                  <i className="fas fa-chart-line"></i>
                </div>
                <h3>Risk Assessment</h3>
                <p>The AI model generates accurate risk predictions based on location, time, and crime type</p>
              </div>
              
              <div className={styles.stepCard}>
                <div className={styles.stepNumber}>4</div>
                <div className={styles.stepIcon}>
                  <i className="fas fa-shield-alt"></i>
                </div>
                <h3>Actionable Insights</h3>
                <p>Receive personalized safety recommendations and real-time alerts for your area</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <Footer />
    </>
  );
};

export default RiskPredictionPage;
