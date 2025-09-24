// src/components/Features/Features.js
import React, { useEffect } from 'react';
import './Features.css';

const Features = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.feature-card');
    fadeElements.forEach(element => {
      observer.observe(element);
    });

    return () => {
      fadeElements.forEach(element => {
        observer.unobserve(element);
      });
    };
  }, []);

  return (
    <section className="features section-padding" id="features">
      <div className="section-title">
        <h2>Advanced Safety Features</h2>
        <span className="urdu-text">اعلیٰ حفاظتی خصوصیات</span>
        <p>Our AI-powered system provides comprehensive safety solutions for Pakistani communities</p>
      </div>

      <div className="feature-cards">
        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-map-marked-alt"></i>
          </div>
          <h3>Interactive Crime Maps</h3>
          <p>Real-time visualization of crime patterns across Lahore with detailed heatmaps and risk indicators.</p>
        </div>

        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-robot"></i>
          </div>
          <h3>AI Risk Prediction</h3>
          <p>Machine learning algorithms analyze historical data to predict crime risks for specific areas and times.</p>
        </div>

        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-bell"></i>
          </div>
          <h3>Smart Alerts</h3>
          <p>Instant notifications when entering high-risk zones or when new crimes are reported in your area.</p>
        </div>

        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-clipboard-list"></i>
          </div>
          <h3>Easy Reporting</h3>
          <p>Simple crime reporting system with Urdu/English support for quick and accurate incident logging.</p>
        </div>

        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-users"></i>
          </div>
          <h3>Community Network</h3>
          <p>Connect with local safety groups and share information to build safer neighborhoods together.</p>
        </div>

        <div className="feature-card fade-in">
          <div className="feature-icon">
            <i className="fas fa-chart-line"></i>
          </div>
          <h3>Crime Analytics</h3>
          <p>Comprehensive statistics and trends analysis to understand crime patterns in Pakistani cities.</p>
        </div>
      </div>
    </section>
  );
};

export default Features;