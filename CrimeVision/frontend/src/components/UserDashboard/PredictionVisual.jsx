import React, { memo } from 'react';
import styles from './PredictionSection.module.css';

const PredictionVisual = memo(() => {
  return (
    <div className={styles.visualBackground}>
      <svg 
        viewBox="0 0 400 400" 
        xmlns="http://www.w3.org/2000/svg" 
        className={styles.backgroundSvg}
      >
        <defs>
          <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
            <stop offset="0%" stopColor="rgba(59, 130, 246, 0.2)" />
            <stop offset="100%" stopColor="rgba(59, 130, 246, 0)" />
          </radialGradient>
        </defs>

        {/* Rotating Rings */}
        <g transform="translate(200, 200)">
          <circle cx="0" cy="0" r="100" fill="url(#radarGradient)" />
          
          <circle cx="0" cy="0" r="150" fill="none" stroke="rgba(59, 130, 246, 0.2)" strokeWidth="1" strokeDasharray="10, 10">
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="20s" repeatCount="indefinite" />
          </circle>
          
          <circle cx="0" cy="0" r="120" fill="none" stroke="rgba(59, 130, 246, 0.3)" strokeWidth="1">
             <animate attributeName="r" values="120;125;120" dur="4s" repeatCount="indefinite" />
          </circle>

          <circle cx="0" cy="0" r="80" fill="none" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1" strokeDasharray="5, 5">
            <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="15s" repeatCount="indefinite" />
          </circle>

          {/* Scanning Line */}
          <line x1="0" y1="0" x2="0" y2="-150" stroke="rgba(59, 130, 246, 0.5)" strokeWidth="2">
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="4s" repeatCount="indefinite" />
          </line>
        </g>
      </svg>
    </div>
  );
});

export default PredictionVisual;
