// src/components/SuperAdminDashboard/AnalyticsDashboard_updated.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Line, Bar, Scatter } from 'react-chartjs-2';
import { Chart as ChartJS } from 'chart.js/auto';
import { Spin } from 'antd';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import styles from './AnalyticsDashboard.module.css';
import RiskMapModal from './RiskMapModal';
import MiniHeatmap from './MiniHeatmap';

const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString());

const makeChartOpts = (extra = {}) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 500 },
  plugins: {
    legend: { labels: { color: '#94a3b8', font: { family: 'Inter, system-ui', size: 11 }, boxWidth: 12 } },
    tooltip: {
      backgroundColor: 'rgba(15,23,42,0.95)',
      titleColor: '#e2e8f0',
      bodyColor: '#94a3b8',
      borderColor: 'rgba(99,102,241,0.3)',
      borderWidth: 1,
      cornerRadius: 8,
    },
    ...extra.plugins,
  },
  scales: {
    x: { ticks: { color: '#64748b', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.04)' }, ...(extra.x || {}) },
    y: { ticks: { color: '#64748b', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.04)' }, ...(extra.y || {}) },
  },
});

const ALERT_META = {
  warning: { icon: 'fas fa-triangle-exclamation', color: '#f97316' },
  info:    { icon: 'fas fa-circle-info',           color: '#06b6d4' },
  success: { icon: 'fas fa-circle-check',          color: '#22c55e' },
  error:   { icon: 'fas fa-circle-xmark',          color: '#dc2626' },
};

const AnalyticsDashboard = () => {
  const { token } = useAuth();
  const today = new Date().toISOString().split('T')[0];
  const prior = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];

  const [startDate,       setStartDate]       = useState(prior);
  const [endDate,         setEndDate]         = useState(today);
  const [analyticsData,   setAnalyticsData]   = useState(null);
  const [loading,         setLoading]         = useState(true);
  const [selectedArea,    setSelectedArea]    = useState('all');
  const [chartType,       setChartType]       = useState('trends');
  const [areas,           setAreas]           = useState([]);
  const [systemAlerts,    setSystemAlerts]    = useState([]);
  const [adminStats,      setAdminStats]      = useState(null);
  const [riskFilter,      setRiskFilter]      = useState('all');
  const [mapModal,        setMapModal]        = useState(false);
  const [allIncidents,    setAllIncidents]    = useState([]);

  const loadAll = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const tok = token || localStorage.getItem('SafeVision_token');
      const [crimeTrends, predictiveData, areaAnalysis, statsData] = await Promise.all([
        apiService.getCrimeTrends(token, { start_date: startDate, end_date: endDate, area: selectedArea }).catch(() => []),
        apiService.getPredictiveAnalytics(token, { start_date: startDate, end_date: endDate }).catch(() => null),
        apiService.getAreaAnalysis(token, { start_date: startDate, end_date: endDate }).catch(() => null),
        fetch(`${apiService.API_BASE_URL}/admin/stats`, {
          headers: { Authorization: `Bearer ${tok}` }
        }).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);

      setAnalyticsData({ crimeTrends: crimeTrends || [], predictiveData, areaAnalysis });
      setAdminStats(statsData);

      if (areaAnalysis?.areas?.length) {
        setAreas(areaAnalysis.areas.map(a => a.name));
      }

      // ── Compute real system alerts from actual data ──
      const alerts = [];
      const trends = crimeTrends || [];
      if (trends.length >= 14) {
        const recent = trends.slice(-7).reduce((s, t) => s + (t.actual || 0), 0);
        const prev   = trends.slice(-14, -7).reduce((s, t) => s + (t.actual || 0), 0);
        if (prev > 0) {
          const pct = ((recent - prev) / prev) * 100;
          if (Math.abs(pct) > 5) {
            alerts.push({
              id: 1, urgent: pct > 25,
              type: pct > 0 ? 'warning' : 'success',
              message: `Incident rate ${pct > 0 ? 'rose' : 'fell'} by ${Math.abs(pct).toFixed(1)}% in last 7 days vs prior 7 days`,
            });
          }
        }
      }

      const topArea = areaAnalysis?.areas?.[0];
      if (topArea) {
        alerts.push({
          id: 2, urgent: topArea.risk_level === 'High',
          type: topArea.risk_level === 'High' ? 'error' : 'warning',
          message: `${topArea.name} is the highest-incident area — ${fmt(topArea.crime_count)} FIRs (${topArea.risk_level} risk)`,
        });
      }

      if (statsData?.total_crimes) {
        const areaCount = Object.keys(statsData.crimes_by_area || {}).length;
        alerts.push({
          id: 3, urgent: false, type: 'info',
          message: `FIR database: ${fmt(statsData.total_crimes)} total records across ${areaCount} areas, ${statsData.total_users || 0} users, ${statsData.total_admins || 0} admins`,
        });
      }

      const risky = (areaAnalysis?.areas || []).filter(a => a.risk_level === 'High').length;
      if (risky > 0) {
        alerts.push({ id: 4, urgent: false, type: 'warning', message: `${risky} area${risky > 1 ? 's' : ''} currently classified as High Risk` });
      }

      if (statsData?.recent_crimes != null) {
        alerts.push({ id: 5, urgent: false, type: 'info', message: `${fmt(statsData.recent_crimes)} incidents recorded in the last 30 days` });
      }

      setSystemAlerts(alerts);
    } catch (err) {
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  }, [token, startDate, endDate, selectedArea]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Load raw crimes for mini heatmap
  useEffect(() => {
    if (token) {
      apiService.get('/api/crimes?limit=2000', token).then(c => setAllIncidents(Array.isArray(c) ? c : [])).catch(() => {});
    }
  }, [token]);

  const renderCharts = () => {
    if (!analyticsData) return null;

    if (chartType === 'trends') {
      const trends = analyticsData.crimeTrends || [];
      return (
        <div className={styles.card}>
          <div className={styles.cardHead}>
            <i className="fas fa-chart-line" style={{ color: '#6366f1' }}></i> Incident Trends
            <span className={styles.cardSub}>{startDate} → {endDate}</span>
            <select value={selectedArea} onChange={e => setSelectedArea(e.target.value)} className={styles.inlineSelect}>
              <option value="all">All Areas</option>
              {areas.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div style={{ height: 300 }}>
            {trends.length > 0 ? (
              <Line
                data={{
                  labels: trends.map(t => t.date),
                  datasets: [
                    { label: 'Actual Incidents', data: trends.map(t => t.actual), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', fill: true, tension: 0.4, borderWidth: 2, pointRadius: 2 },
                    ...(trends.some(t => t.predicted > 0) ? [{ label: 'Projected', data: trends.map(t => t.predicted), borderColor: '#f97316', borderDash: [5, 4], backgroundColor: 'transparent', tension: 0.4, borderWidth: 2, pointRadius: 0 }] : []),
                  ],
                }}
                options={makeChartOpts()}
              />
            ) : <div className={styles.emptyChart}>No trend data for selected range</div>}
          </div>
        </div>
      );
    }

    if (chartType === 'patterns') {
      const patterns = analyticsData.predictiveData?.patterns || [];
      return (
        <div className={styles.twoCols}>
          <div className={styles.card}>
            <div className={styles.cardHead}>
              <i className="fas fa-brain" style={{ color: '#8b5cf6' }}></i> Incident Pattern Analysis
              <span className={styles.cardSub}>Hour × Day intensity</span>
            </div>
            <div style={{ height: 280 }}>
              {patterns.length > 0 ? (
                <Scatter
                  data={{
                    datasets: [{
                      label: 'Intensity',
                      data: patterns.map(p => ({ x: p.hour, y: p.day_of_week, r: Math.max(4, p.intensity || 1) })),
                      backgroundColor: patterns.map(p =>
                        p.intensity > 15 ? 'rgba(220,38,38,0.75)' :
                        p.intensity > 8  ? 'rgba(249,115,22,0.75)' :
                                            'rgba(99,102,241,0.65)'),
                      borderColor: 'transparent',
                    }],
                  }}
                  options={makeChartOpts({
                    x: { min: 0, max: 23, title: { display: true, text: 'Hour', color: '#64748b' }, ticks: { stepSize: 2 } },
                    y: { min: 0, max: 6, title: { display: true, text: 'Day', color: '#64748b' }, ticks: { callback: v => ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][v] } },
                  })}
                />
              ) : <div className={styles.emptyChart}>No pattern data for selected range</div>}
            </div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardHead}>
              <i className="fas fa-fire" style={{ color: '#dc2626' }}></i> Risk Heatmap Preview
            </div>
            <div style={{ height: 280, position: 'relative', borderRadius: 10, overflow: 'hidden' }}>
              <MiniHeatmap incidents={allIncidents} />
              <div className={styles.heatmapOverlay}>
                <div className={styles.heatmapModalLabel}>
                  <i className="fas fa-map-location-dot"></i>
                  <span>Lahore Crime Density Map</span>
                  <button className={styles.viewMapBtn} onClick={() => setMapModal(true)}>
                    <i className="fas fa-expand"></i> Full View
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (chartType === 'areas') {
      const allAreasData = analyticsData.areaAnalysis?.areas || [];
      const filtered = riskFilter === 'all' ? allAreasData : allAreasData.filter(a => a.risk_level === riskFilter);
      const sorted = [...filtered].sort((a, b) => b.crime_count - a.crime_count).slice(0, 12);
      const maxC = allAreasData[0]?.crime_count || 1;
      const rColor = (r) => r === 'High' ? '#dc2626' : r === 'Medium' ? '#f97316' : '#22c55e';
      return (
        <div className={styles.twoCols}>
          <div className={styles.card}>
            <div className={styles.cardHead}>
              <i className="fas fa-chart-bar" style={{ color: '#8b5cf6' }}></i> Area-wise Distribution
              <div className={styles.riskBtns}>
                {['all','High','Medium','Low'].map(r => (
                  <button key={r}
                    className={`${styles.rBtn} ${riskFilter === r ? styles.rBtnOn : ''}`}
                    style={riskFilter === r ? { background: r === 'all' ? '#6366f1' : rColor(r), borderColor: r === 'all' ? '#6366f1' : rColor(r) } : {}}
                    onClick={() => setRiskFilter(r)}>{r}</button>
                ))}
              </div>
            </div>
            <div style={{ height: 280 }}>
              {sorted.length > 0 ? (
                <Bar
                  data={{
                    labels: sorted.map(a => a.name),
                    datasets: [{ data: sorted.map(a => a.crime_count), backgroundColor: sorted.map(a => rColor(a.risk_level) + 'bb'), borderRadius: 4, barThickness: 16 }],
                  }}
                  options={{ ...makeChartOpts(), indexAxis: 'y', plugins: { ...makeChartOpts().plugins, legend: { display: false } } }}
                />
              ) : <div className={styles.emptyChart}>No area data</div>}
            </div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardHead}>
              <i className="fas fa-ranking-star" style={{ color: '#f97316' }}></i> Top Risk Areas
            </div>
            <div className={styles.areaList}>
              {allAreasData.slice(0, 8).map((area, i) => (
                <div key={area.name} className={styles.areaRow}>
                  <span className={styles.areaRank}>{i + 1}</span>
                  <span className={styles.areaName}>{area.name}</span>
                  <div className={styles.areaBar}><div className={styles.areaFill} style={{ width: `${(area.crime_count / maxC) * 100}%`, background: `linear-gradient(90deg,${rColor(area.risk_level)},${rColor(area.risk_level)}88)` }}></div></div>
                  <span className={styles.areaCnt} style={{ color: rColor(area.risk_level) }}>{fmt(area.crime_count)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={styles.root}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerGlow}></div>
        <div className={styles.headerContent}>
          <div className={styles.headerLeft}>
            <div className={styles.headerIcon}><i className="fas fa-chart-bar"></i></div>
            <div>
              <h1 className={styles.title}>Analytics Intelligence Center</h1>
              <p className={styles.subtitle}>Real-time FIR data analytics · Lahore district coverage</p>
            </div>
          </div>
          <button className={styles.refreshBtn} onClick={loadAll} disabled={loading}>
            <i className={`fas fa-rotate${loading ? ' fa-spin' : ''}`}></i> Refresh
          </button>
        </div>
      </div>

      {/* ── Controls ── */}
      <div className={styles.controls}>
        <div className={styles.ctrlGroup}>
          <label><i className="fas fa-calendar"></i> From</label>
          <input type="date" value={startDate} max={endDate} onChange={e => setStartDate(e.target.value)} className={styles.dateInput} />
        </div>
        <div className={styles.ctrlGroup}>
          <label><i className="fas fa-calendar"></i> To</label>
          <input type="date" value={endDate} min={startDate} max={today} onChange={e => setEndDate(e.target.value)} className={styles.dateInput} />
        </div>
        <div className={styles.viewToggle}>
          {[['trends','fa-chart-line','Incident Trends'],['patterns','fa-brain','Patterns'],['areas','fa-map-marker-alt','Areas']].map(([v,ic,l]) => (
            <button key={v} className={`${styles.toggleBtn} ${chartType === v ? styles.toggleActive : ''}`} onClick={() => setChartType(v)}>
              <i className={`fas ${ic}`}></i> {l}
            </button>
          ))}
        </div>
      </div>

      {/* ── KPI Strip ── */}
      <div className={styles.kpiRow}>
        {[
          { icon: 'fas fa-database',          label: 'Total FIRs',       value: adminStats?.total_crimes,   color: '#6366f1' },
          { icon: 'fas fa-users',              label: 'Total Users',       value: adminStats?.total_users,    color: '#0ea5e9' },
          { icon: 'fas fa-user-shield',        label: 'Admins',            value: adminStats?.total_admins,   color: '#8b5cf6' },
          { icon: 'fas fa-clock-rotate-left',  label: 'Recent (30d)',      value: adminStats?.recent_crimes,  color: '#dc2626' },
        ].map(c => (
          <div key={c.label} className={styles.kpiCard} style={{ '--kc': c.color }}>
            <div className={styles.kpiIcon} style={{ background: c.color + '1a', color: c.color, borderColor: c.color + '33' }}><i className={c.icon}></i></div>
            <div>
              <div className={styles.kpiVal}>{loading ? '…' : fmt(c.value)}</div>
              <div className={styles.kpiLbl}>{c.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Chart Panel ── */}
      <div className={styles.chartSection}>
        {loading
          ? <div className={styles.loadingBox}><Spin size="large" /><p>Loading analytics data…</p></div>
          : renderCharts()}
      </div>

      {/* ── System Alerts ── */}
      <div className={styles.alertsSection}>
        <div className={styles.alertsHead}>
          <i className="fas fa-bell" style={{ color: '#f97316' }}></i>
          System Alerts &amp; Insights
          {systemAlerts.length > 0 && <span className={styles.alertBadge}>{systemAlerts.length}</span>}
          {systemAlerts.some(a => a.urgent) && <span className={styles.urgentLabel}><i className="fas fa-circle-dot"></i> {systemAlerts.filter(a => a.urgent).length} Urgent</span>}
        </div>
        <div className={styles.alertsList}>
          {loading && <div className={styles.loadingAlerts}><Spin size="small" /> Computing alerts from live data…</div>}
          {!loading && systemAlerts.length === 0 && <div className={styles.emptyAlerts}><i className="fas fa-check-circle" style={{ color: '#22c55e' }}></i> System operating normally — no alerts</div>}
          {systemAlerts.map(a => {
            const m = ALERT_META[a.type] || ALERT_META.info;
            return (
              <div key={a.id} className={styles.alertItem} style={{ '--ac': m.color }}>
                <div className={styles.alertIcon} style={{ color: m.color, background: m.color + '1a' }}><i className={m.icon}></i></div>
                <span className={styles.alertMsg}>{a.message}</span>
                {a.urgent && <span className={styles.urgentTag}>URGENT</span>}
              </div>
            );
          })}
        </div>
      </div>

      {mapModal && <RiskMapModal onClose={() => setMapModal(false)} token={token} />}
    </div>
  );
};

export default AnalyticsDashboard;
