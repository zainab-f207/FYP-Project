import React from 'react';
import PredictionSection from './PredictionSection';
import styles from './UserDashboard.module.css'; // Reusing dashboard styles for consistency

const PredictionPage = ({ onPredictionComplete, initialArea = null }) => {
  return (
    <div className={styles.pageContainer}>
      <div className={styles.pageHeader}>
        <h1>Risk Prediction</h1>
        <p>Analyze crime risks for specific areas using AI</p>
      </div>
      
      <div className={styles.contentSection}>
        <PredictionSection onPredictionComplete={onPredictionComplete} initialArea={initialArea} />
      </div>
    </div>
  );
};

export default PredictionPage;
