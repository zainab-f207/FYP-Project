// src/components/Introduction/Introduction.js
import React, { useState, useRef, useEffect } from 'react';
import './Introduction.css';

const Introduction = () => {
  const [visibleSections, setVisibleSections] = useState({});
  const sectionRefs = {
    intro: useRef(null),
    stats: useRef(null),
    video: useRef(null)
  };

  // Statistics data with animated counters
  const statistics = [
    {
      id: 1,
      icon: 'fas fa-map-marked-alt',
      endValue: 5,
      suffix: '+',
      label: 'Areas Covered',
      duration: 2500
    },
    {
      id: 2,
      icon: 'fas fa-database',
      endValue: 1000,
      suffix: '+',
      label: 'Incidents Analyzed',
      duration: 3000
    },
    {
      id: 3,
      icon: 'fas fa-chart-line',
      endValue: 90,
      suffix: '%',
      label: 'Prediction Accuracy',
      duration: 2000
    },
    {
      id: 4,
      icon: 'fas fa-shield-alt',
      endValue: 24,
      suffix: '/7',
      label: 'Real-time Monitoring',
      duration: 2000
    }
  ];

  // Intersection Observer for scroll animations
  useEffect(() => {
    const observers = [];

    Object.keys(sectionRefs).forEach(key => {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setVisibleSections(prev => ({ ...prev, [key]: true }));
          }
        },
        {
          threshold: 0.3,
          rootMargin: '-50px'
        }
      );

      if (sectionRefs[key].current) {
        observer.observe(sectionRefs[key].current);
        observers.push(observer);
      }
    });

    return () => {
      observers.forEach(observer => observer.disconnect());
    };
  }, []);

  // Animated counter component
  const AnimatedCounter = ({ endValue, suffix, duration }) => {
    const [count, setCount] = useState(0);
    const countRef = useRef(null);

    useEffect(() => {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            let startTime;
            const startValue = 0;
            const step = (timestamp) => {
              if (!startTime) startTime = timestamp;
              const progress = Math.min((timestamp - startTime) / duration, 1);
              
              setCount(Math.floor(progress * (endValue - startValue) + startValue));
              
              if (progress < 1) {
                requestAnimationFrame(step);
              }
            };
            
            requestAnimationFrame(step);
          }
        },
        { threshold: 0.5 }
      );

      if (countRef.current) {
        observer.observe(countRef.current);
      }

      return () => observer.disconnect();
    }, [endValue, duration]);

    return (
      <div ref={countRef}>
        <span className="stat-number">
          {count}{suffix}
        </span>
      </div>
    );
  };

  const handleVideoPlay = () => {
    // Placeholder for video play functionality
    alert('Professional explainer video would play here showcasing SafeVision capabilities');
  };

  return (
    <section className="introduction-section" id="introduction">
      {/* Animated Background Elements */}
      <div className="intro-bg-elements">
        <div className="intro-floating-orb orb-1"></div>
        <div className="intro-floating-orb orb-2"></div>
        <div className="intro-floating-orb orb-3"></div>
      </div>

      <div className="intro-container">
        {/* Section Header */}
        <div className="section-header">
          <div className="section-badge">
            <i className="fas fa-rocket"></i>
            <span>Platform Overview</span>
          </div>
          <h2 className="section-title">
            Transforming Urban Safety with AI
          </h2>
          <p className="section-subtitle">
            Advanced spatial intelligence platform for comprehensive crime analysis, 
            prediction, and community safety enhancement across Lahore
          </p>
        </div>

        {/* What is SafeVision Section */}
        <div 
          className="what-is-safevision"
          ref={sectionRefs.intro}
        >
          <div className={`intro-content ${visibleSections.intro ? 'visible' : ''}`}>
            <h3 className="intro-heading">
              What is SafeVision?
            </h3>
            <p className="intro-description">
              SafeVision is an innovative spatial analysis and visualization platform 
              that leverages artificial intelligence and advanced data analytics to 
              transform urban safety management. Our platform provides real-time insights, 
              predictive analytics, and comprehensive visualization tools for law 
              enforcement agencies and community safety initiatives.
            </p>
            
            <div className="infographics-grid">
              <div className="infographic-item">
                <div className="infographic-icon">
                  <i className="fas fa-brain"></i>
                </div>
                <div className="infographic-content">
                  <h4>AI-Powered Analytics</h4>
                  <p>Machine learning algorithms for pattern recognition and predictive insights</p>
                </div>
              </div>
              
              <div className="infographic-item">
                <div className="infographic-icon">
                  <i className="fas fa-map"></i>
                </div>
                <div className="infographic-content">
                  <h4>Spatial Intelligence</h4>
                  <p>Advanced GIS mapping with real-time incident visualization</p>
                </div>
              </div>
              
              <div className="infographic-item">
                <div className="infographic-icon">
                  <i className="fas fa-bolt"></i>
                </div>
                <div className="infographic-content">
                  <h4>Real-time Alerts</h4>
                  <p>Instant notifications and emergency response coordination</p>
                </div>
              </div>
              
              <div className="infographic-item">
                <div className="infographic-icon">
                  <i className="fas fa-shield-alt"></i>
                </div>
                <div className="infographic-content">
                  <h4>Community Safety</h4>
                  <p>Comprehensive safety scoring and risk assessment systems</p>
                </div>
              </div>
            </div>
          </div>

          <div className={`intro-visual ${visibleSections.intro ? 'visible' : ''}`}>
            <div className="visual-container">
              <div className="data-flow-animation">
                <div className="data-node node-1">
                  <i className="fas fa-map-marker-alt"></i>
                </div>
                <div className="data-node node-2">
                  <i className="fas fa-chart-bar"></i>
                </div>
                <div className="data-node node-3">
                  <i className="fas fa-database"></i>
                </div>
                <div className="data-node node-4">
                  <i className="fas fa-users"></i>
                </div>
                <div className="data-node node-center">
                  <i className="fas fa-eye"></i>
                </div>
                <div className="data-connection connection-1"></div>
                <div className="data-connection connection-2"></div>
                <div className="data-connection connection-3"></div>
                <div className="data-connection connection-4"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Key Statistics Section */}
        <div 
          className="key-statistics"
          ref={sectionRefs.stats}
        >
          <div className="stats-grid">
            {statistics.map((stat, index) => (
              <div 
                key={stat.id}
                className={`stat-card ${visibleSections.stats ? 'visible' : ''}`}
                style={{ transitionDelay: `${index * 200}ms` }}
              >
                <div className="stat-icon">
                  <i className={stat.icon}></i>
                </div>
                <AnimatedCounter 
                  endValue={stat.endValue}
                  suffix={stat.suffix}
                  duration={stat.duration}
                />
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Video Explainer Section */}
        {/* <div 
          className="video-explainer"
          ref={sectionRefs.video}
        >
          <div className={`video-container ${visibleSections.video ? 'visible' : ''}`}>
            <div className="video-placeholder" onClick={handleVideoPlay}>
              <div className="play-button">
                <i className="fas fa-play"></i>
              </div>
              <div className="video-overlay">
                <h3 className="video-title">SafeVision Platform Overview</h3>
                <p className="video-description">
                  Watch how SafeVision transforms urban safety with AI-powered analytics and real-time monitoring
                </p>
              </div>
            </div>
          </div>
        </div> */}
      </div>
    </section>
  );
};

export default Introduction;
