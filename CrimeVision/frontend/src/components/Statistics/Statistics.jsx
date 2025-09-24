// src/components/Statistics/Statistics.js
import React, { useEffect } from 'react';
import './Statistics.css';

const Statistics = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.stat-item');
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
    <section className="stats section-padding" id="stats">
      <div className="section-title">
        <h2>Crime Statistics</h2>
        <span className="urdu-text">جرم کے اعداد و شمار</span>
        <p>Latest crime statistics and trends for Lahore</p>
      </div>

      <div className="stats-grid">
        <div className="stat-item fade-in">
          <h3>24%</h3>
          <p>Decrease in street crime in the last 6 months</p>
        </div>

        <div className="stat-item fade-in">
          <h3>62%</h3>
          <p>Of crimes occur between 6 PM and midnight</p>
        </div>

        <div className="stat-item fade-in">
          <h3>38%</h3>
          <p>Increase in community crime reporting</p>
        </div>

        <div className="stat-item fade-in">
          <h3>17%</h3>
          <p>Reduction in home burglaries this year</p>
        </div>
      </div>
    </section>
  );
};

export default Statistics;