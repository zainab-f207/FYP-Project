import React, { useState, useEffect, useMemo } from 'react';
import styles from './AnalyticsPanel.module.css';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import apiService from '../../services/apiService_updated';

const AnalyticsPanel = ({ stats, token, fullView }) => {
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch crime trend data when in full view
  useEffect(() => {
    if (!token) return;
    const fetchTrends = async () => {
      try {
        setLoading(true);
        const end = new Date().toISOString().split('T')[0];
        const start = new Date(Date.now() - 180 * 86400000).toISOString().split('T')[0];
        const data = await apiService.getCrimeTrends(token, { start_date: start, end_date: end, area: 'all' });
        setTrendData(Array.isArray(data) ? data : (data?.trends || []));
      } catch (err) {
        console.error('Failed to fetch crime trends:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrends();
  }, [token]);

  // Build crime trend chart from real data
  const crimeTrendData = useMemo(() => {
    if (trendData && trendData.length > 0) {
      // Group by month
      const monthMap = {};
      trendData.forEach(item => {
        const d = item.date || '';
        const month = d.substring(0, 7); // YYYY-MM
        if (!monthMap[month]) monthMap[month] = 0;
        monthMap[month] += (item.actual || item.count || 0);
      });
      const sortedMonths = Object.keys(monthMap).sort();
      const labels = sortedMonths.map(m => {
        const [y, mo] = m.split('-');
        return new Date(y, parseInt(mo) - 1).toLocaleString('default', { month: 'short', year: '2-digit' });
      });
      return {
        labels,
        datasets: [{
          label: 'Crimes Reported',
          data: sortedMonths.map(m => monthMap[m]),
          fill: true,
          backgroundColor: 'rgba(26, 79, 114, 0.08)',
          borderColor: '#1a4f72',
          tension: 0.4,
          pointBackgroundColor: '#f9a826',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          borderWidth: 3,
        }],
      };
    }
    return null;
  }, [trendData]);

  // Build risk area doughnut from stats.crimes_by_risk
  const riskAreaData = useMemo(() => {
    const riskMap = stats?.crimes_by_risk || {};
    const labels = Object.keys(riskMap);
    const data = Object.values(riskMap);
    if (labels.length === 0) {
      return { labels: ['No Data'], datasets: [{ data: [1], backgroundColor: ['#64748b'], borderColor: ['#fff'], borderWidth: 3 }] };
    }
    const colorMap = { High: '#ff6b6b', Medium: '#f9a826', Low: '#1dd1a1' };
    const colors = labels.map(l => colorMap[l] || '#2d7fb8');
    return {
      labels: labels.map(l => `${l} Risk`),
      datasets: [{ label: 'Risk Areas', data, backgroundColor: colors, borderColor: colors.map(() => '#fff'), borderWidth: 3, hoverOffset: 8 }],
    };
  }, [stats]);

  // Build area bar chart from stats.crimes_by_area
  const areaBarData = useMemo(() => {
    const areaMap = stats?.crimes_by_area || {};
    const labels = Object.keys(areaMap);
    const data = Object.values(areaMap);
    if (labels.length === 0) return null;
    return {
      labels,
      datasets: [{
        label: 'Crimes by Area',
        data,
        backgroundColor: 'rgba(249, 168, 38, 0.7)',
        borderColor: '#f9a826',
        borderWidth: 1,
        borderRadius: 4,
      }],
    };
  }, [stats]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { labels: { font: { family: 'Poppins', size: 12 }, color: 'var(--text-secondary, #666)' } },
    },
    scales: {
      y: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { family: 'Poppins', size: 11 }, color: 'var(--text-muted, #888)' } },
      x: { grid: { display: false }, ticks: { font: { family: 'Poppins', size: 11 }, color: 'var(--text-muted, #888)' } },
    },
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: true,
    cutout: '65%',
    plugins: {
      legend: { position: 'bottom', labels: { padding: 16, font: { family: 'Poppins', size: 12 }, color: 'var(--text-secondary, #666)', usePointStyle: true } },
    },
  };

  return (
    <div className={styles.analyticsPanel}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionTitle}>
          <i className="fas fa-chart-line"></i>
          <h3>{fullView ? 'Analytics Dashboard' : 'Analytics Overview'}</h3>
        </div>
        <span className={styles.sectionBadge}>{loading ? 'Loading...' : 'Live Data'}</span>
      </div>
      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h4>Crime Trend (Monthly)</h4>
          {crimeTrendData ? (
            <Line data={crimeTrendData} options={chartOptions} />
          ) : (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
              {loading ? 'Loading trend data...' : 'No trend data available'}
            </p>
          )}
        </div>
        <div className={styles.chartCard}>
          <h4>Risk Level Distribution</h4>
          <Doughnut data={riskAreaData} options={doughnutOptions} />
        </div>
      </div>
      {fullView && areaBarData && (
        <div className={styles.chartsGrid} style={{ marginTop: '24px' }}>
          <div className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
            <h4>Top Crime Areas</h4>
            <Bar data={areaBarData} options={chartOptions} />
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsPanel;
