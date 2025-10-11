import React, { useState, useEffect } from 'react';
import { DatePicker, Button, Select, Card, Row, Col, Statistic, Spin, message } from 'antd';
import { Line, Bar, Pie, Doughnut, Scatter } from 'react-chartjs-2';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService';
import styles from './AnalyticsDashboard.module.css';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const AnalyticsDashboard = ({ stats, notifications }) => {
  const { token } = useAuth();
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedArea, setSelectedArea] = useState('all');
  const [chartType, setChartType] = useState('trends');

  useEffect(() => {
    if (token) {
      loadAnalyticsData();
    }
  }, [dateRange, selectedArea, token]);

  const loadAnalyticsData = async () => {
    setLoading(true);
    try {
      const startDate = dateRange[0].format('YYYY-MM-DD');
      const endDate = dateRange[1].format('YYYY-MM-DD');

      // Get comprehensive analytics data
      const [crimeTrends, predictiveData, areaAnalysis] = await Promise.all([
        apiService.getCrimeTrends(token, { start_date: startDate, end_date: endDate, area: selectedArea }),
        apiService.getPredictiveAnalytics(token, { start_date: startDate, end_date: endDate }),
        apiService.getAreaAnalysis(token, { start_date: startDate, end_date: endDate })
      ]);

      setAnalyticsData({
        crimeTrends,
        predictiveData,
        areaAnalysis
      });
    } catch (error) {
      console.error('Failed to load analytics data:', error);
      message.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const getIconForType = (type) => {
    switch (type) {
      case 'warning': return 'fas fa-exclamation-triangle';
      case 'info': return 'fas fa-info-circle';
      case 'success': return 'fas fa-check-circle';
      case 'error': return 'fas fa-times-circle';
      default: return 'fas fa-bell';
    }
  };

  const getColorForType = (type) => {
    switch (type) {
      case 'warning': return '#ffc107';
      case 'info': return '#17a2b8';
      case 'success': return '#28a745';
      case 'error': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const renderInteractiveCharts = () => {
    if (!analyticsData) return null;

    switch (chartType) {
      case 'trends':
        return (
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card title="Crime Trends Over Time" extra={
                <Select value={selectedArea} onChange={setSelectedArea} style={{ width: 150 }}>
                  <Option value="all">All Areas</Option>
                  <Option value="gulberg">Gulberg</Option>
                  <Option value="johartown">Johar Town</Option>
                  <Option value="modeltown">Model Town</Option>
                </Select>
              }>
                <Line
                  data={{
                    labels: analyticsData.crimeTrends?.map(item => item.date) || [],
                    datasets: [{
                      label: 'Actual Crimes',
                      data: analyticsData.crimeTrends?.map(item => item.actual) || [],
                      borderColor: '#f9a826',
                      backgroundColor: 'rgba(249, 168, 38, 0.1)',
                      fill: true,
                      tension: 0.4,
                    }, {
                      label: 'Predicted Crimes',
                      data: analyticsData.crimeTrends?.map(item => item.predicted) || [],
                      borderColor: '#FF6384',
                      backgroundColor: 'rgba(255, 99, 132, 0.1)',
                      borderDash: [5, 5],
                      fill: false,
                      tension: 0.4,
                    }]
                  }}
                  options={{
                    responsive: true,
                    plugins: { legend: { display: true } },
                    interaction: {
                      mode: 'index',
                      intersect: false,
                    },
                    scales: {
                      x: { display: true, title: { display: true, text: 'Date' } },
                      y: { display: true, title: { display: true, text: 'Crime Count' } }
                    }
                  }}
                />
              </Card>
            </Col>
          </Row>
        );

      case 'patterns':
        return (
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="Crime Pattern Analysis">
                <Scatter
                  data={{
                    datasets: [{
                      label: 'Crime Patterns',
                      data: analyticsData.predictiveData?.patterns?.map(item => ({
                        x: item.hour,
                        y: item.day_of_week,
                        r: item.intensity
                      })) || [],
                      backgroundColor: 'rgba(249, 168, 38, 0.6)',
                      borderColor: '#f9a826',
                    }]
                  }}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: { display: true },
                      tooltip: {
                        callbacks: {
                          label: (context) => `Hour: ${context.parsed.x}, Day: ${context.parsed.y}, Intensity: ${context.parsed.r}`
                        }
                      }
                    },
                    scales: {
                      x: { title: { display: true, text: 'Hour of Day' }, min: 0, max: 23 },
                      y: { title: { display: true, text: 'Day of Week' }, min: 0, max: 6 }
                    }
                  }}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Predictive Risk Heatmap">
                <div className={styles.heatmapContainer}>
                  {analyticsData.predictiveData?.risk_heatmap && (
                    <div className={styles.heatmap}>
                      {analyticsData.predictiveData.risk_heatmap.map((row, i) => (
                        <div key={i} className={styles.heatmapRow}>
                          {row.map((value, j) => (
                            <div
                              key={j}
                              className={styles.heatmapCell}
                              style={{
                                backgroundColor: `rgba(249, 168, 38, ${value / 100})`,
                                opacity: value / 100
                              }}
                              title={`Risk: ${value}%`}
                            />
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </Col>
          </Row>
        );

      case 'areas':
        return (
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="Area-wise Crime Distribution">
                <Pie
                  data={{
                    labels: analyticsData.areaAnalysis?.areas?.map(item => item.name) || [],
                    datasets: [{
                      data: analyticsData.areaAnalysis?.areas?.map(item => item.crime_count) || [],
                      backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'],
                    }]
                  }}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: { display: true, position: 'bottom' },
                      tooltip: {
                        callbacks: {
                          label: (context) => `${context.label}: ${context.parsed} crimes`
                        }
                      }
                    }
                  }}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Top Risk Areas">
                <div className={styles.areaList}>
                  {analyticsData.areaAnalysis?.areas?.slice(0, 5).map((area, index) => (
                    <div key={area.name} className={styles.areaItem}>
                      <div className={styles.areaRank}>#{index + 1}</div>
                      <div className={styles.areaInfo}>
                        <span className={styles.areaName}>{area.name}</span>
                        <span className={styles.areaStats}>
                          {area.crime_count} crimes • Risk: {area.risk_level}
                        </span>
                      </div>
                      <div className={styles.areaBar}>
                        <div
                          className={styles.areaFill}
                          style={{ width: `${(area.crime_count / Math.max(...analyticsData.areaAnalysis.areas.map(a => a.crime_count))) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </Col>
          </Row>
        );

      default:
        return null;
    }
  };

  return (
    <div className={styles.analyticsDashboard}>
      <div className={styles.dashboardHeader}>
        <h2><i className="fas fa-chart-network"></i> Advanced Analytics Dashboard</h2>
        <p>Interactive crime analytics with predictive insights</p>
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        <RangePicker
          value={dateRange}
          onChange={(dates) => setDateRange(dates)}
          allowClear={false}
          disabled={loading}
        />
        <Select
          value={chartType}
          onChange={setChartType}
          style={{ width: 200, marginLeft: 16 }}
          disabled={loading}
        >
          <Option value="trends">Crime Trends & Predictions</Option>
          <Option value="patterns">Crime Pattern Analysis</Option>
          <Option value="areas">Area Analysis & Drill-down</Option>
        </Select>
        <Button
          type="primary"
          onClick={loadAnalyticsData}
          loading={loading}
          style={{ marginLeft: 16 }}
        >
          Refresh Data
        </Button>
      </div>

      {/* Key Metrics */}
      <div className={styles.statsGrid}>
        {stats.total_crimes !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.total_crimes.toLocaleString()}</h3>
              <p>Total Crimes</p>
              <span className={styles.statTrend}>+8% this month</span>
            </div>
          </div>
        )}

        {stats.prediction_accuracy !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-brain"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.prediction_accuracy}%</h3>
              <p>Prediction Accuracy</p>
              <span className={styles.statTrend}>AI-powered</span>
            </div>
          </div>
        )}

        {stats.high_risk_areas !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-map-marker-alt"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.high_risk_areas}</h3>
              <p>High-Risk Areas</p>
              <span className={styles.statTrend}>Active monitoring</span>
            </div>
          </div>
        )}

        {stats.prevented_crimes !== undefined && (
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className={styles.statContent}>
              <h3>{stats.prevented_crimes}</h3>
              <p>Crimes Prevented</p>
              <span className={styles.statTrend}>+15% this month</span>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Charts */}
      <div className={styles.chartsSection}>
        {loading ? (
          <div className={styles.loadingContainer}>
            <Spin size="large" />
            <p>Loading analytics data...</p>
          </div>
        ) : (
          renderInteractiveCharts()
        )}
      </div>

      {/* Notifications */}
      <div className={styles.notificationsSection}>
        <h3><i className="fas fa-bell"></i> System Alerts & Insights</h3>
        <div className={styles.notificationsList}>
          {notifications.map((notification) => (
            <div key={notification.id} className={`${styles.notificationItem} ${styles[`notification${notification.type}`]}`}>
              <div className={styles.notificationIcon} style={{ color: getColorForType(notification.type) }}>
                <i className={getIconForType(notification.type)}></i>
              </div>
              <div className={styles.notificationContent}>
                <h4>{notification.title || notification.message.split(' ')[0]}</h4>
                <p>{notification.message}</p>
                <span className={styles.notificationTime}>{notification.timestamp ? new Date(notification.timestamp).toLocaleTimeString() : 'Just now'}</span>
              </div>
              {notification.urgent && <div className={styles.urgentBadge}>URGENT</div>}
            </div>
          ))}
          {notifications.length === 0 && (
            <div className={styles.noNotifications}>
              <i className="fas fa-check-circle"></i>
              <p>All systems operational - No active alerts</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
