import React from 'react';
import styles from './AnalyticsPanel.module.css';
import { Line, Doughnut } from 'react-chartjs-2';

const AnalyticsPanel = () => {
  // Example data for charts
  const crimeTrendData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
    datasets: [
      {
        label: 'Crimes Reported',
        data: [120, 150, 170, 140, 180, 200, 160, 190],
        fill: false,
        backgroundColor: '#1a4f72',
        borderColor: '#f9a826',
        tension: 0.4,
      },
    ],
  };

  const riskAreaData = {
    labels: ['High', 'Medium', 'Low'],
    datasets: [
      {
        label: 'Risk Areas',
        data: [12, 7, 5],
        backgroundColor: ['#ff6b6b', '#f9a826', '#1dd1a1'],
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className={styles.analyticsPanel}>
      <h3>Analytics Overview</h3>
      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h4>Crime Trend (Monthly)</h4>
          <Line data={crimeTrendData} />
        </div>
        <div className={styles.chartCard}>
          <h4>Risk Area Distribution</h4>
          <Doughnut data={riskAreaData} />
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPanel;
