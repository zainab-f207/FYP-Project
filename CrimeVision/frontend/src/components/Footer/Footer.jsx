// src/components/Footer/Footer.js
import React from 'react';
import { Link } from 'react-router-dom';
import './Footer.css';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-grid">
          {/* Brand Section */}
          <div className="footer-col footer-brand">
            <div className="footer-logo">
              <i className="fas fa-shield-alt"></i>
              <h3>SafeVision</h3>
            </div>
            <p className="footer-description">
              AI-powered incident prediction platform empowering citizens with real-time safety intelligence 
              and predictive analytics to create safer communities across Lahore.
            </p>
            <div className="footer-stats">
              <div className="stat-item">
                <span className="stat-value">95%</span>
                <span className="stat-label">Accuracy</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">50K+</span>
                <span className="stat-label">Records</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">24/7</span>
                <span className="stat-label">Monitoring</span>
              </div>
            </div>
          </div>

          {/* Platform Links */}
          <div className="footer-col">
            <h4>Platform</h4>
            <ul>
              <li><Link to="/">Home</Link></li>
              <li><Link to="/risk-prediction">Incident Risk Prediction</Link></li>
              <li><Link to="/crime-map">Interactive Incident Map</Link></li>
              <li><Link to="/emergency">Emergency Contacts</Link></li>
              <li><Link to="/about-project">About Project</Link></li>
            </ul>
          </div>

          {/* For Developers */}
          {/* <div className="footer-col">
            <h4>For Developers</h4>
            <ul>
              <li><a href="#">API Documentation</a></li>
              <li><a href="#">GitHub Repository</a></li>
              <li><a href="#">Technical Docs</a></li>
              <li><a href="#">Integration Guide</a></li>
              <li><a href="#">Developer Support</a></li>
            </ul>
          </div> */}

          {/* Emergency Contacts */}
          <div className="footer-col">
            <h4>Emergency Hotlines</h4>
            <ul className="emergency-list">
              <li>
                <i className="fas fa-phone-alt"></i>
                <div>
                  <strong>Police Emergency</strong>
                  <span>15</span>
                </div>
              </li>
              <li>
                <i className="fas fa-ambulance"></i>
                <div>
                  <strong>Rescue Services</strong>
                  <span>1122</span>
                </div>
              </li>
              <li>
                <i className="fas fa-fire-extinguisher"></i>
                <div>
                  <strong>Fire Brigade</strong>
                  <span>16</span>
                </div>
              </li>
            </ul>
          </div>

          {/* Contact & Social */}
          <div className="footer-col">
            <h4>Connect With Us</h4>
            <ul className="contact-list">
              <li>
                <i className="fas fa-map-marker-alt"></i>
                <span>Lahore, Punjab, Pakistan</span>
              </li>
              <li>
                <i className="fas fa-envelope"></i>
                <span>support@safevision.pk</span>
              </li>
              <li>
                <i className="fas fa-globe"></i>
                <span>www.safevision.pk</span>
              </li>
            </ul>
            <div className="social-links">
              <a href="#" aria-label="Facebook"><i className="fab fa-facebook-f"></i></a>
              <a href="#" aria-label="Twitter"><i className="fab fa-twitter"></i></a>
              <a href="#" aria-label="Instagram"><i className="fab fa-instagram"></i></a>
              <a href="#" aria-label="LinkedIn"><i className="fab fa-linkedin-in"></i></a>
            </div>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="footer-bottom">
          <div className="footer-bottom-content">
            <p className="copyright">
              © {currentYear} SafeVision. All rights reserved. | Powered by AI & Machine Learning
            </p>
            <div className="footer-links">
              <a href="#">Privacy Policy</a>
              <span className="separator">•</span>
              <a href="#">Terms of Service</a>
              <span className="separator">•</span>
              <a href="#">Data Security</a>
            </div>
          </div>
          <div className="footer-badge">
            <i className="fas fa-shield-check"></i>
            <span>Secure & Encrypted</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
