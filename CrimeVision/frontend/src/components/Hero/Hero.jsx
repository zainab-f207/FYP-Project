// src/components/Hero/Hero.js
import React from 'react';
import './Hero.css';

const Hero = () => {
  return (
    <section className="hero" id="home">
      <div className="hero-content">
        <h1 data-en="SafeVision Pakistan" data-ur="کرائم ویژن پاکستان">SafeVision Pakistan</h1>
        <span className="urdu-text" data-en="کرائم ویژن پاکستان" data-ur="کرائم ویژن پاکستان">کرائم ویژن پاکستان</span>
        <p data-en="AI-powered crime prediction and prevention system for Lahore, Pakistan. Stay safe with intelligent crime analytics and real-time alerts." data-ur="لاہور، پاکستان کے لیے اے آئی سے چلنے والا جرم کی پیش گوئی اور روک تھام کا نظام۔ ذہین جرم کے تجزیوں اور ریئل ٹائم الرٹس کے ساتھ محفوظ رہیں۔">AI-powered crime prediction and prevention system for Lahore, Pakistan. Stay safe with intelligent crime analytics and real-time alerts.</p>
        <div className="hero-buttons">
          <a href="#prediction" className="btn btn-primary" data-en="Check Area Safety" data-ur="علاقے کی حفاظت چیک کریں">Check Area Safety</a>
          <a href="#map" className="btn btn-outline" data-en="View Crime Map" data-ur="جرم کا نقشہ دیکھیں">View Crime Map</a>
        </div>
      </div>
    </section>
  );
};

export default Hero;
