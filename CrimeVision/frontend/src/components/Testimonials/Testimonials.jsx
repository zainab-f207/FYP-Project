// src/components/Testimonials/Testimonials.js
import React, { useEffect } from 'react';
import './Testimonials.css';

const Testimonials = () => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    const fadeElements = document.querySelectorAll('.testimonial-card');
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
    <section className="testimonials section-padding" id="testimonials">
      <div className="section-title">
        <h2>User Testimonials</h2>
        <span className="urdu-text">صارفین کے تاثرات</span>
        <p>What our users say about CrimeVision Pakistan</p>
      </div>

      <div className="testimonial-cards">
        <div className="testimonial-card fade-in">
          <img src="https://randomuser.me/api/portraits/men/32.jpg" alt="User" className="testimonial-avatar" />
          <p className="testimonial-text">"CrimeVision helped our community identify high-risk areas and take preventive measures. The prediction tool is remarkably accurate."</p>
          <p className="testimonial-author">- Ahmed R., Gulberg</p>
        </div>

        <div className="testimonial-card fade-in">
          <img src="https://randomuser.me/api/portraits/women/44.jpg" alt="User" className="testimonial-avatar" />
          <p className="testimonial-text">"The safety alerts have been invaluable for my family. We feel much safer knowing which areas to avoid at certain times."</p>
          <p className="testimonial-author">- Fatima S., DHA</p>
        </div>

        <div className="testimonial-card fade-in">
          <img src="https://randomuser.me/api/portraits/men/22.jpg" alt="User" className="testimonial-avatar" />
          <p className="testimonial-text">"As a community police officer, I've found the crime analytics incredibly useful for planning patrol routes and allocating resources."</p>
          <p className="testimonial-author">- Asif J., Lahore Police</p>
        </div>
      </div>
    </section>
  );
};

export default Testimonials;