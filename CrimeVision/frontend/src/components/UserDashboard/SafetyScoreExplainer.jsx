// UI Component to Explain Different Safety Scores
// Add this to your UserDashboard component

import React, { useState } from 'react';
import styles from './ScoreExplainer.module.css';

export const SafetyScoreExplainer = ({ dashboardScore, areaProfileScore, areaName, timeFilter }) => {
  const [showExplainer, setShowExplainer] = useState(false);

  const getTimeFilterLabel = (filter) => {
    const labels = {
      '7d': 'Last 7 Days',
      '30d': 'Last 30 Days',
      '12m': 'Last 12 Months',
      'all': 'All Time'
    };
    return labels[filter] || filter;
  };

  const scoreDifference = Math.abs(dashboardScore - areaProfileScore);
  const showIcon = scoreDifference > 10; // Show icon if difference > 10%

  if (!showIcon) return null;

  return (
    <>
      {/* Small info icon */}
      <i
        className="fas fa-info-circle"
        onClick={() => setShowExplainer(!showExplainer)}
        style={{
          marginLeft: '8px',
          cursor: 'pointer',
          color: '#f59e0b',
          fontSize: '12px',
          opacity: 0.7,
          transition: 'opacity 0.2s'
        }}
        title="Click to understand score differences"
        onMouseEnter={(e) => e.target.style.opacity = 1}
        onMouseLeave={(e) => e.target.style.opacity = 0.7}
      />

      {/* Modal/Overlay when clicked */}
      {showExplainer && (
        <div className={styles.explainerModal} onClick={() => setShowExplainer(false)}>
          <div className={styles.explainerContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>📊 Why Different Safety Scores?</h3>
              <button
                className={styles.closeButton}
                onClick={() => setShowExplainer(false)}
              >
                ×
              </button>
            </div>

          <div className={styles.comparisonGrid}>
            {/* Dashboard Score */}
            <div className={styles.scoreCard}>
              <div className={styles.cardHeader}>
                <i className="fas fa-map-marked-alt"></i>
                <span>Current View</span>
              </div>
              <div className={styles.scoreDisplay}>
                <div className={styles.scoreBig}>{dashboardScore}%</div>
                <div className={styles.scoreLabel}>Safety Score</div>
              </div>
              <div className={styles.cardDetails}>
                <p><strong>Time Period:</strong> {getTimeFilterLabel(timeFilter)}</p>
                <p><strong>Area Coverage:</strong> {areaName} + 1.5km radius</p>
                <p><strong>Purpose:</strong> Real-time navigation safety</p>
                <div className={styles.detailsBox}>
                  <strong>Includes:</strong>
                  <ul>
                    <li>Nearby crimes within walking distance</li>
                    <li>Similar area names (e.g., "{areaName} Phase 1")</li>
                    <li>Recent activity emphasis</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Area Profile Score */}
            <div className={styles.scoreCard}>
              <div className={styles.cardHeader}>
                <i className="fas fa-chart-area"></i>
                <span>Area Profile</span>
              </div>
              <div className={styles.scoreDisplay}>
                <div className={styles.scoreBig}>{areaProfileScore}%</div>
                <div className={styles.scoreLabel}>Safety Score</div>
              </div>
              <div className={styles.cardDetails}>
                <p><strong>Time Period:</strong> Complete History</p>
                <p><strong>Area Coverage:</strong> Exact "{areaName}" only</p>
                <p><strong>Purpose:</strong> Comprehensive area analysis</p>
                <div className={styles.detailsBox}>
                  <strong>Includes:</strong>
                  <ul>
                    <li>All historical crime data</li>
                    <li>Only exact area name matches</li>
                    <li>Statistical long-term view</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className={styles.explanationBox}>
            <h4>🤔 Which Score Should I Trust?</h4>
            <div className={styles.useCaseGrid}>
              <div className={styles.useCase}>
                <div className={styles.useCaseIcon}>🚶</div>
                <div className={styles.useCaseContent}>
                  <strong>For Daily Navigation:</strong>
                  <p>Use the <strong>Current View</strong> score ({dashboardScore}%)</p>
                  <p className={styles.reason}>Better for "Should I walk here now?" decisions</p>
                </div>
              </div>
              <div className={styles.useCase}>
                <div className={styles.useCaseIcon}>🏠</div>
                <div className={styles.useCaseContent}>
                  <strong>For Moving/Planning:</strong>
                  <p>Use the <strong>Area Profile</strong> score ({areaProfileScore}%)</p>
                  <p className={styles.reason}>Better for "Should I live/work here?" decisions</p>
                </div>
              </div>
            </div>
          </div>

          <div className={styles.technicalNote}>
            <i className="fas fa-lightbulb"></i>
            <strong>Technical Note:</strong> Both scores use the same risk formula
            (35% volume + 15% severity + 30% recency + 10% trends + 10% time)
            but analyze different datasets. Neither is "wrong" – they serve different purposes.
          </div>

        </div>
      </div>
      )}
    </>
  );
};

export default SafetyScoreExplainer;