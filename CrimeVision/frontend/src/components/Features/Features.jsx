// src/components/Features/Features.js
import React, { useRef, useEffect, useState } from 'react';
import './Features.css';
import apiService from '../../services/apiService';

const Features = () => {
  const [visibleSections, setVisibleSections] = useState({});
  const featuresRef = useRef(null);
  const cardRefs = useRef([]);
  const techRefs = useRef({});

  // Features data
  const features = [
    {
      id: 1,
      title: "AI Crime Risk Prediction",
      description: "Advanced machine learning algorithms analyze historical crime data, temporal patterns, and geographic factors to predict crime risk levels with 95% accuracy across Lahore.",
      badge: "AI Powered"
    },
    {
      id: 2,
      title: "Real-Time Crime Heatmaps",
      description: "Interactive geospatial visualization displaying crime density, hotspot zones, and incident clustering with dynamic filtering by crime type, time, and severity.",
      badge: "Live Data"
    },
    {
      id: 3,
      title: "Smart Safety Alerts",
      description: "Personalized, location-based notifications that warn users about high-risk areas, recent incidents nearby, and emerging crime patterns in real-time.",
      badge: "Intelligent"
    },
    {
      id: 4,
      title: "Safe Route Navigation",
      description: "AI-optimized route planning that avoids high-crime areas, provides real-time safety updates during travel, and suggests safer alternative paths.",
      badge: "Route Safety"
    },
    {
      id: 5,
      title: "Crime Analytics Dashboard",
      description: "Comprehensive data visualization with trend analysis, crime statistics, temporal patterns, and predictive insights for informed decision-making.",
      badge: "Data Intelligence"
    },
    {
      id: 6,
      title: "Emergency Response Hub",
      description: "Quick access to emergency services, nearby police stations, hospitals, and helplines with one-tap calling and location sharing capabilities.",
      badge: "24/7 Support"
    }
  ];

  // AI Capabilities
  const aiCapabilities = [
    {
      id: 1,
      title: "Crime Pattern Forecasting",
      description: "Deep learning models analyze 50,000+ historical crime records to predict future crime hotspots and patterns with exceptional accuracy.",
      icon: "fas fa-brain"
    },
    {
      id: 2,
      title: "Temporal Risk Analysis",
      description: "Advanced algorithms identify crime trends across different times of day, days of week, and seasonal variations to provide time-specific risk assessments.",
      icon: "fas fa-clock"
    },
    {
      id: 3,
      title: "Geographic Clustering",
      description: "Sophisticated spatial analysis detects crime clusters, identifies high-risk neighborhoods, and maps crime distribution patterns across Lahore.",
      icon: "fas fa-map-marked-alt"
    },
    {
      id: 4,
      title: "Predictive Risk Scoring",
      description: "Multi-factor risk assessment engine evaluates area safety, crime history, and environmental factors to generate real-time risk scores.",
      icon: "fas fa-shield-alt"
    },
    {
      id: 5,
      title: "Intelligent Alert System",
      description: "Context-aware notification engine that learns user patterns and delivers personalized safety alerts based on location, time, and behavior.",
      icon: "fas fa-bell"
    }
  ];

  // Real Prediction Tool State
  const [area, setArea] = useState('Gulberg');
  const [crimeType, setCrimeType] = useState('Theft');
  const [date, setDate] = useState('');
  const [areas, setAreas] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);

  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [riskPercentage, setRiskPercentage] = useState(0);
  const [riskLevel, setRiskLevel] = useState('');
  const [riskClass, setRiskClass] = useState('');
  const [description, setDescription] = useState('');
  const [precautions, setPrecautions] = useState([]);
  const [confidence, setConfidence] = useState(0);
  const [showResult, setShowResult] = useState(false);

  // Risk descriptions
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

  // Intersection Observer - FIXED VERSION
  useEffect(() => {
    const observers = [];
    
    // Observe feature cards
    cardRefs.current = cardRefs.current.slice(0, features.length);
    cardRefs.current.forEach((card, index) => {
      if (card) {
        const observer = new IntersectionObserver(
          ([entry]) => {
            if (entry.isIntersecting) {
              setVisibleSections(prev => ({ ...prev, [`card-${index}`]: true }));
            }
          },
          { threshold: 0.3, rootMargin: '-50px' }
        );
        observer.observe(card);
        observers.push(observer);
      }
    });

    // Observe tech sections - FIXED: Properly initialize refs
    const techSections = ['ai', 'visualization', 'content', 'demo'];
    techSections.forEach(section => {
      if (!techRefs.current[section]) {
        techRefs.current[section] = null;
      }
    });

    // Observe each tech section
    Object.keys(techRefs.current).forEach(key => {
      if (techRefs.current[key]) {
        const observer = new IntersectionObserver(
          ([entry]) => {
            if (entry.isIntersecting) {
              setVisibleSections(prev => ({ ...prev, [key]: true }));
            }
          },
          { threshold: 0, rootMargin: '0px' }
        );
        observer.observe(techRefs.current[key]);
        observers.push(observer);
      }
    });

    return () => observers.forEach(observer => observer.disconnect());
  }, []);

  // Load areas and crime types
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



  // Particle effect
  const createParticles = (event) => {
    const card = event.currentTarget;
    const particles = [];
    const particleCount = 8;

    for (let i = 0; i < particleCount; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle-burst';
      
      const angle = (i / particleCount) * Math.PI * 2;
      const distance = 50;
      const tx = Math.cos(angle) * distance;
      const ty = Math.sin(angle) * distance;
      
      particle.style.setProperty('--tx', `${tx}px`);
      particle.style.setProperty('--ty', `${ty}px`);
      particle.style.left = '50%';
      particle.style.top = '50%';
      
      particle.style.animation = `particleBurst 0.6s ease-out forwards`;
      card.appendChild(particle);
      
      particles.push(particle);
    }

    setTimeout(() => {
      particles.forEach(particle => {
        if (particle.parentNode === card) {
          card.removeChild(particle);
        }
      });
    }, 600);
  };

  // Professional Line Icons
  const FeatureIcons = {
    maps: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <path className="icon-path" d="M30,20 L70,20 L80,30 L80,70 L70,80 L30,80 L20,70 L20,30 Z" />
        <circle className="icon-dot" cx="35" cy="35" r="4" />
        <circle className="icon-dot" cx="50" cy="50" r="4" />
        <circle className="icon-dot" cx="65" cy="65" r="4" />
        <path className="icon-path" d="M35,35 L50,50 L65,65" />
      </svg>
    ),
    analysis: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <path className="icon-path" d="M20,80 L30,50 L50,60 L70,30 L80,40" />
        <circle className="icon-dot" cx="30" cy="50" r="4" />
        <circle className="icon-dot" cx="50" cy="60" r="4" />
        <circle className="icon-dot" cx="70" cy="30" r="4" />
        <path className="icon-path" d="M25,20 L25,80 M20,75 L80,75" />
      </svg>
    ),
    trends: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <path className="icon-path" d="M25,60 L40,40 L55,65 L70,35 L80,50" />
        <circle className="icon-dot" cx="40" cy="40" r="4" />
        <circle className="icon-dot" cx="55" cy="65" r="4" />
        <circle className="icon-dot" cx="70" cy="35" r="4" />
        <path className="icon-path" d="M20,20 L20,80 M20,80 L85,80" />
      </svg>
    ),
    reporting: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <path className="icon-path" d="M25,25 L75,25 L75,75 L25,75 Z" />
        <path className="icon-path" d="M35,35 L65,35 M35,45 L65,45 M35,55 L55,55" />
        <circle className="icon-dot" cx="30" cy="30" r="2" />
      </svg>
    ),
    insights: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <circle className="icon-path" cx="50" cy="50" r="35" />
        <path className="icon-path" d="M50,15 L50,25 M50,75 L50,85 M15,50 L25,50 M75,50 L85,50" />
        <circle className="icon-dot" cx="50" cy="50" r="6" />
        <path className="icon-path" d="M35,35 L45,45 M55,55 L65,65" />
      </svg>
    ),
    community: () => (
      <svg className="icon-svg" viewBox="0 0 100 100">
        <circle className="icon-path" cx="35" cy="40" r="12" />
        <circle className="icon-path" cx="65" cy="40" r="12" />
        <path className="icon-path" d="M25,65 Q35,50 50,55 Q65,50 75,65" />
        <circle className="icon-dot" cx="30" cy="35" r="2" />
        <circle className="icon-dot" cx="60" cy="35" r="2" />
      </svg>
    )
  };

  const getFeatureIcon = (index) => {
    const icons = [
      FeatureIcons.maps,
      FeatureIcons.analysis,
      FeatureIcons.trends,
      FeatureIcons.reporting,
      FeatureIcons.insights,
      FeatureIcons.community
    ];
    const IconComponent = icons[index] || FeatureIcons.maps;
    return <IconComponent />;
  };

  // Real Prediction Tool Functions
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
      {/* Features Section */}
      <section className="features-section" id="features" ref={featuresRef}>
        <div className="features-bg">
          <div className="features-grid-bg"></div>
        </div>

        <div className="features-container">
          <div className="features-header">
            <div className="features-badge">
              <i className="fas fa-shield-alt"></i>
              <span>Platform Features</span>
            </div>
            <h2 className="features-title">Intelligent Crime Prevention & Safety</h2>
            <p className="features-subtitle">
              Empowering citizens with AI-driven crime prediction, real-time safety alerts, and comprehensive 
              security intelligence to create safer communities across Lahore
            </p>
          </div>

          <div className="features-grid">
            {features.map((feature, index) => (
              <div
                key={feature.id}
                ref={el => cardRefs.current[index] = el}
                className={`feature-card ${visibleSections[`card-${index}`] ? 'visible' : ''}`}
                onMouseEnter={createParticles}
                style={{ transitionDelay: `${index * 0.1}s` }}
              >
                <div className="feature-card-inner">
                  <div className="feature-icon">
                    <div className="icon-container">
                      <div className="icon-bg"></div>
                      {getFeatureIcon(index)}
                    </div>
                  </div>

                  <div className="feature-content">
                    <h3 className="feature-title">{feature.title}</h3>
                    <p className="feature-description">{feature.description}</p>
                    <div className="feature-badge">
                      <i className="fas fa-check"></i>
                      <span>{feature.badge}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* AI Capabilities */}
          <div className="ai-capabilities">
            <div className="ai-capabilities-header">
              <div className="ai-badge">
                <i className="fas fa-brain"></i>
                <span>AI-Powered Intelligence</span>
              </div>
              <h3 className="ai-capabilities-title">Advanced Crime Prediction Engine</h3>
              <p className="ai-capabilities-subtitle">
                Cutting-edge machine learning algorithms analyze 50,000+ crime records to predict risks, 
                identify patterns, and deliver actionable safety insights with 95% accuracy
              </p>
            </div>
            <div
              ref={el => techRefs.current.ai = el}
              className={`ai-grid ${visibleSections.ai ? 'visible' : ''}`}
            >
              {aiCapabilities.map((capability, index) => (
                <div
                  key={capability.id}
                  className={`ai-card ${visibleSections.ai ? 'visible' : ''}`}
                  style={{ transitionDelay: `${index * 0.1}s` }}
                >
                  <div className="ai-icon">
                    <i className={capability.icon}></i>
                  </div>
                  <h4>{capability.title}</h4>
                  <p>{capability.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Technology Showcase Section */}
      <section className="technology-showcase" id="technology">
        <div className="tech-container">
          <div className="tech-header">
            <div className="tech-badge">
              <i className="fas fa-cogs"></i>
              <span>Technology Stack</span>
            </div>
            <h2 className="tech-title">Built with Cutting-Edge AI Technology</h2>
            <p className="tech-subtitle">
              SafeVision combines advanced machine learning, geospatial intelligence, and real-time 
              data processing to deliver accurate crime predictions and actionable safety insights
            </p>
          </div>

          {/* Tech Stack Visualization */}
          <div className="tech-stack">

            <div 
              ref={el => techRefs.current.visualization = el}
              className={`tech-visualization ${visibleSections.visualization ? 'visible' : ''}`}
            >
              <div className="tech-grid-display">
                <div className="tech-card-item">
                  <div className="tech-icon-wrapper">
                    <i className="fas fa-database"></i>
                  </div>
                  <h4>Data Aggregation</h4>
                  <p>50,000+ historical crime records processed</p>
                </div>

                <div className="tech-card-item">
                  <div className="tech-icon-wrapper">
                    <i className="fas fa-brain"></i>
                  </div>
                  <h4>AI Analysis</h4>
                  <p>Deep learning models for pattern recognition</p>
                </div>

                <div className="tech-card-item">
                  <div className="tech-icon-wrapper">
                    <i className="fas fa-shield-alt"></i>
                  </div>
                  <h4>Risk Assessment</h4>
                  <p>Real-time safety scoring engine</p>
                </div>

                <div className="tech-card-item">
                  <div className="tech-icon-wrapper">
                    <i className="fas fa-bell"></i>
                  </div>
                  <h4>Smart Alerts</h4>
                  <p>Instant location-based notifications</p>
                </div>
              </div>
            </div>

            <div 
              ref={el => techRefs.current.content = el}
              className={`tech-content ${visibleSections.content ? 'visible' : ''}`}
            >
              <h3>Crime Prediction Technology</h3>
              <p className="tech-description">
                SafeVision utilizes state-of-the-art machine learning algorithms, advanced geospatial 
                analysis, and real-time data processing to predict crime patterns with 95% accuracy and 
                empower citizens with actionable safety intelligence.
              </p>
              
              <div className="tech-features">
                <div className="tech-feature">
                  <i className="fas fa-brain"></i>
                  <span>Deep Learning Models</span>
                </div>
                <div className="tech-feature">
                  <i className="fas fa-map-marked-alt"></i>
                  <span>Geospatial Intelligence</span>
                </div>
                <div className="tech-feature">
                  <i className="fas fa-chart-line"></i>
                  <span>Predictive Analytics</span>
                </div>
                <div className="tech-feature">
                  <i className="fas fa-lock"></i>
                  <span>Secure Data Encryption</span>
                </div>
              </div>
            </div>
          </div>

          
          {/* <div
            ref={el => techRefs.current.demo = el}
            className={`interactive-demo ${visibleSections.demo ? 'visible' : ''}`}
          >
            <h3 className="demo-title">Experience SafeVision AI in Action</h3>
            <p className="demo-subtitle">
              Use our real AI prediction model to assess crime risk for specific areas and times
            </p>

            
            <div className="real-prediction-tool">
              <div className="prediction-header">
                <div className="prediction-badge">
                  <i className="fas fa-brain"></i>
                  <span>Live AI Prediction</span>
                </div>
                <h4 className="prediction-title">Real-time Risk Assessment</h4>
                <p className="prediction-subtitle">
                  Select an area and crime type to get AI-powered safety insights
                </p>
              </div>

              <div className="prediction-form">
                <div className="form-group">
                  <label htmlFor="area">Select Area</label>
                  <select
                    id="area"
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    className="form-select"
                    disabled={loading}
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
                    className="form-select"
                    disabled={loading}
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
                    className="form-input"
                  />
                </div>

                <button
                  className={`predict-btn ${predicting ? 'loading' : ''}`}
                  onClick={calculateRisk}
                  disabled={predicting || !area || !crimeType || loading}
                >
                  {predicting ? (
                    <>
                      <i className="fas fa-spinner fa-spin"></i>
                      Analyzing Risk...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-shield-alt"></i>
                      Check Risk Level
                    </>
                  )}
                </button>
              </div>

              {showResult && (
                <div className="prediction-result">
                  <div className="result-header">
                    <h4 className="result-title">
                      {getRiskIcon()} {riskLevel}
                    </h4>
                  </div>

                  <div className="risk-visualization">
                    <div className="risk-meter">
                      <svg className="risk-circle" viewBox="0 0 120 120">
                        <circle
                          cx="60"
                          cy="60"
                          r="54"
                          fill="none"
                          stroke="rgba(255,255,255,0.1)"
                          strokeWidth="12"
                        />
                        <circle
                          cx="60"
                          cy="60"
                          r="54"
                          fill="none"
                          stroke={getRiskColor()}
                          strokeWidth="12"
                          strokeDasharray="339.3"
                          strokeDashoffset={339.3 - (riskPercentage / 100) * 339.3}
                          transform="rotate(-90 60 60)"
                          style={{ transition: 'stroke-dashoffset 1.5s ease-in-out' }}
                        />
                      </svg>
                      <div className="risk-percentage" style={{ color: getRiskColor() }}>
                        {riskPercentage}%
                      </div>
                      <div className="risk-level">{riskLevel}</div>
                    </div>

                    <div className="risk-info">
                      <div className="risk-context">
                        <div className="context-item">
                          <span className="context-label">Area:</span>
                          <span className="context-value">{formatAreaName(area)}</span>
                        </div>
                        <div className="context-item">
                          <span className="context-label">Crime Type:</span>
                          <span className="context-value">{crimeType}</span>
                        </div>
                        <div className="context-item">
                          <span className="context-label">Date:</span>
                          <span className="context-value">{new Date(date).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="risk-details">
                    <div className="detail-section">
                      <h4>
                        <i className="fas fa-info-circle"></i>
                        Overview
                      </h4>
                      <p>{description}</p>
                    </div>

                    <div className="confidence-indicator">
                      <span className="confidence-label">AI Model Confidence:</span>
                      <span className="confidence-value">{Math.round(confidence * 100)}%</span>
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill"
                          style={{ width: `${confidence * 100}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="detail-section">
                      <h4>
                        <i className="fas fa-shield-alt"></i>
                        Safety Recommendations
                      </h4>
                      <ul className="safety-list">
                        {precautions.map((precaution, index) => (
                          <li key={index}>
                            <i className="fas fa-check"></i>
                            {precaution}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {!showResult && !predicting && (
                <div className="empty-state">
                  <div className="empty-icon">
                    <i className="fas fa-search"></i>
                  </div>
                  <p>Select an area and crime type to see AI risk assessment</p>
                </div>
              )}
            </div>
          </div>

          <div className="demo-controls active">
            <button
              className="demo-btn secondary"
              onClick={() => {
                setShowResult(false);
                setArea(areas[0] || '');
                setCrimeType(crimeTypes[0] || '');
              }}
            >
              <i className="fas fa-redo"></i>
              New Assessment
            </button>
            <button
              className="demo-btn primary"
              onClick={calculateRisk}
              disabled={predicting || !area || !crimeType}
            >
              <i className="fas fa-sync-alt"></i>
              Re-analyze
            </button>
          </div> */}
        </div> 
      </section>
    </>
  );
};

export default Features;
