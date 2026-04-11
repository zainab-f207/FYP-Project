// src/components/News/News.js
import React, { useEffect } from 'react';
import './News.css';

const News = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.news-card');
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
    <section className="news section-padding" id="news">
      <div className="section-title">
        <h2>Safety News & Updates</h2>
        <span className="urdu-text">حفاظتی خبریں اور اپ ڈیٹس</span>
        <p>Latest safety news, crime prevention tips, and community updates from Pakistan</p>
      </div>

      <div className="news-grid">
        <div className="news-card fade-in">
          <div className="news-image">
            <i className="fas fa-newspaper"></i>
          </div>
          <div className="news-content">
            <div className="news-date">December 15, 2023</div>
            <h4>Lahore Police Launches New Safety Initiative</h4>
            <p>Lahore Police has introduced a new community safety program with increased patrols in high-risk areas and better coordination with local communities.</p>
          </div>
        </div>

        <div className="news-card fade-in">
          <div className="news-image">
            <i className="fas fa-shield-alt"></i>
          </div>
          <div className="news-content">
            <div className="news-date">December 12, 2023</div>
            <h4>Crime Prevention Workshop Success</h4>
            <p>Over 500 residents participated in the crime prevention workshop organized by SafeVision in collaboration with local authorities.</p>
          </div>
        </div>

        <div className="news-card fade-in">
          <div className="news-image">
            <i className="fas fa-users"></i>
          </div>
          <div className="news-content">
            <div className="news-date">December 10, 2023</div>
            <h4>Community Watch Program Expands</h4>
            <p>The neighborhood watch program has successfully expanded to 15 new areas in Lahore, significantly reducing crime rates.</p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default News;
