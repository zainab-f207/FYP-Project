// src/components/Footer/Footer.js
import React from 'react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-grid">
        <div className="footer-col">
          <h4>CrimeVision Pakistan</h4>
          <p>AI-powered crime prediction and prevention for safer Pakistani communities.</p>
          <div className="social-links">
            <a href="#"><i className="fab fa-facebook-f"></i></a>
            <a href="#"><i className="fab fa-twitter"></i></a>
            <a href="#"><i className="fab fa-instagram"></i></a>
            <a href="#"><i className="fab fa-linkedin-in"></i></a>
          </div>
        </div>

        <div className="footer-col">
          <h4>Quick Links</h4>
          <ul>
            <li><a href="#home">Home</a></li>
            <li><a href="#features">Features</a></li>
            <li><a href="#safety-tips">Safety Tips</a></li>
            <li><a href="#prediction">Risk Check</a></li>
            <li><a href="#map">Crime Map</a></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="#">Emergency Contacts</a></li>
            <li><a href="#">Safety Guidelines</a></li>
            <li><a href="#">Community Programs</a></li>
            <li><a href="#">Crime Prevention</a></li>
            <li><a href="#">Download App</a></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Contact Us</h4>
          <ul>
            <li><i className="fas fa-map-marker-alt"></i> 123 Main Boulevard, Lahore</li>
            <li><i className="fas fa-phone"></i> +92 42 123 4567</li>
            <li><i className="fas fa-envelope"></i> info@crimevision.pk</li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p>&copy; 2023 CrimeVision Pakistan. All rights reserved.</p>
      </div>
    </footer>
  );
};

export default Footer;