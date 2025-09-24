// src/components/SafetyTips/SafetyTips.js
import React, { useEffect } from 'react';
import './SafetyTips.css';

const SafetyTips = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.tip-card');
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
    <section className="safety-tips section-padding" id="safety-tips">
      <div className="section-title">
        <h2>Safety Tips for Pakistan</h2>
        <span className="urdu-text">پاکستان کے لیے حفاظتی ٹپس</span>
        <p>Essential safety guidelines tailored for Pakistani communities and urban areas</p>
      </div>

      <div className="tips-grid">
        <div className="tip-card fade-in" id="night">
          <div className="tip-icon">
            <i className="fas fa-moon"></i>
          </div>
          <h4>Night Time Safety</h4>
          <p>Avoid walking alone after dark in isolated areas. Use rickshaws or trusted transport services. Stay in well-lit areas and be aware of your surroundings.</p>
        </div>

        <div className="tip-card fade-in" id="emergency">
          <div className="tip-icon">
            <i className="fas fa-mobile-alt"></i>
          </div>
          <h4>Emergency Contacts</h4>
          <p>Save emergency numbers: Police (15), Rescue (1122), Edhi (115). Keep your phone charged and share your location with trusted contacts.</p>
        </div>

        <div className="tip-card fade-in" id="home">
          <div className="tip-icon">
            <i className="fas fa-home"></i>
          </div>
          <h4>Home Security</h4>
          <p>Install good locks, security cameras, and alarm systems. Keep emergency lights and first aid kits ready. Inform neighbors about your schedule.</p>
        </div>

        <div className="tip-card fade-in" id="vehicle">
          <div className="tip-icon">
            <i className="fas fa-car"></i>
          </div>
          <h4>Vehicle Safety</h4>
          <p>Park in well-lit areas, lock your vehicle, and don't leave valuables visible. Use carpooling services for late-night travel.</p>
        </div>

        <div className="tip-card fade-in" id="financial">
          <div className="tip-icon">
            <i className="fas fa-wallet"></i>
          </div>
          <h4>Financial Safety</h4>
          <p>Be cautious with ATMs and online transactions. Use secure payment methods and avoid carrying large amounts of cash.</p>
        </div>

        <div className="tip-card fade-in" id="community">
          <div className="tip-icon">
            <i className="fas fa-users"></i>
          </div>
          <h4>Community Awareness</h4>
          <p>Stay connected with local community groups. Report suspicious activities and participate in neighborhood watch programs.</p>
        </div>
      </div>
    </section>
  );
};

export default SafetyTips;