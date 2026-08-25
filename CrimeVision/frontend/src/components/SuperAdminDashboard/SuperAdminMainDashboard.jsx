import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../../services/apiService';
import styles from './SuperAdminMainDashboard.module.css';

const RISK_COLORS = { Critical: '#7c3aed', High: '#dc2626', Medium: '#f97316', Low: '#22c55e' };

const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString());

const KPICard = ({ icon, label, value, sub, color = '#6366f1', loading }) => (
  <div className={styles.kpiCard} style={{ '--kpi-color': color }}>
    <div className={styles.kpiIconWrap} style={{ background: color + '22', borderColor: color + '44' }}>
      <i className={icon} style={{ color }}></i>
    </div>
    <div className={styles.kpiBody}>
      <div className={styles.kpiValue}>{loading ? <span className={styles.kpiSkel} /> : fmt(value)}</div>
      <div className={styles.kpiLabel}>{label}</div>
      {sub && <div className={styles.kpiSub}>{sub}</div>}
    </div>
  </div>
);

const TrendRow = ({ rank, item, type }) => {
  const isRising = type === 'rising';
  const color   = isRising ? '#dc2626' : '#22c55e';
  const icon    = isRising ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down';
  const sign    = isRising ? '+' : '';
  return (
    <div className={styles.trendRow}>
      <span className={styles.trendRank}>{rank}</span>
      <span className={styles.trendCrime}>{item.crime_type}</span>
      <span className={styles.trendPct} style={{ color }}><i className={`fas ${icon}`}></i> {sign}{item.pct_change}%</span>
      <span className={styles.trendCounts}>{item.prior}→{item.recent}</span>
    </div>
  );
};

const AlertRow = ({ alert }) => {
  const colorMap = { High: '#dc2626', Critical: '#7c3aed', Medium: '#f97316', Low: '#22c55e' };
  const color = colorMap[alert.risk_level] || '#f97316';
  return (
    <div className={styles.alertRow} style={{ '--alert-color': color }}>
      <div className={styles.alertDot} style={{ background: color }}></div>
      <div className={styles.alertBody}>
        <span className={styles.alertArea}>{alert.area}</span>
        <span className={styles.alertCrime}>{alert.crime_type}</span>
      </div>
      <span className={styles.alertCount} style={{ color }}>{alert.count} incidents</span>
    </div>
  );
};

const SuperAdminMainDashboard = ({ token, onNavigate }) => {
  const [intel,   setIntel]   = useState(null);
  const [stats,   setStats]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [intelData, statsData] = await Promise.all([
        apiService.getIntelligenceDashboard().catch(() => null),
        fetch(`${apiService.API_BASE_URL}/admin/stats`, {
          headers: { Authorization: `Bearer ${token || localStorage.getItem('SafeVision_token') || sessionStorage.getItem('SafeVision_token')}` }
        }).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      setIntel(intelData);
      setStats(statsData);
      setLastRefresh(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const dh  = intel?.dataset_health  || {};
  const mh  = intel?.model_health    || {};
  const dr  = intel?.drift           || {};
  const ct  = intel?.crime_trends    || {};
  const hra = intel?.high_risk_alerts || [];
  const fc  = intel?.forecast_7day   || {};

  const topArea = Object.entries(stats?.crimes_by_area || {})
    .sort(([, a], [, b]) => b - a)[0];

  const riskDist = stats?.crimes_by_risk || {};
  const totalRisk = Object.values(riskDist).reduce((s, v) => s + v, 0) || 1;

  const forecastAreas = Object.entries(fc).slice(0, 4);

  return (
    <div className={styles.root}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerBg}></div>
        <div className={styles.headerContent}>
          <div className={styles.headerLeft}>
            <div className={styles.headerIconWrap}>
              <div className={styles.headerIconBg}></div>
              <i className="fas fa-shield-halved"></i>
            </div>
            <div>
              <h1 className={styles.headerTitle}>Crime Intelligence Command Center</h1>
              <p className={styles.headerSub}>
                Lahore Police FIR Dataset&nbsp;·&nbsp;{fmt(dh.total_records)} records&nbsp;·&nbsp;{dh.areas_covered || '—'} areas&nbsp;·&nbsp;{dh.crime_types_count || '—'} crime types
              </p>
            </div>
          </div>
          <div className={styles.headerRight}>
            {lastRefresh && <span className={styles.refreshTime}><i className="fas fa-circle-dot" style={{ color: '#22c55e', fontSize: '0.5rem' }}></i> Updated {lastRefresh}</span>}
            <button className={styles.refreshBtn} onClick={load} disabled={loading}>
              <i className={`fas fa-rotate${loading ? ' fa-spin' : ''}`}></i> Refresh
            </button>
          </div>
        </div>
      </div>

      {/* ── KPI Row ── */}
      <div className={styles.kpiRow}>
        <KPICard icon="fas fa-database"     label="Total FIR Records"  value={dh.total_records}    sub={`Last: ${dh.last_update ? new Date(dh.last_update).toLocaleDateString() : '—'}`} color="#6366f1" loading={loading} />
        <KPICard icon="fas fa-users"         label="Registered Users"   value={stats?.total_users}   sub="Active public accounts"  color="#0ea5e9" loading={loading} />
        <KPICard icon="fas fa-user-shield"   label="Admins"             value={stats?.total_admins}  sub="System administrators"   color="#8b5cf6" loading={loading} />
        <KPICard icon="fas fa-map-location-dot" label="Areas Covered"  value={dh.areas_covered}     sub="Lahore districts"        color="#06b6d4" loading={loading} />
        <KPICard icon="fas fa-tag"           label="Crime Types"        value={dh.crime_types_count} sub="Classified FIR offences" color="#f97316" loading={loading} />
        <KPICard icon="fas fa-clock-rotate-left" label="Last 30 Days"  value={stats?.recent_crimes} sub="Recent FIR entries"      color="#dc2626" loading={loading} />
      </div>

      {/* ── Main grid ── */}
      <div className={styles.mainGrid}>

        {/* ── Crime Trends ── */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <i className="fas fa-chart-line" style={{ color: '#f97316' }}></i> Crime Trend Intelligence
            <span className={styles.cardSub}>90-day vs prior 90-day</span>
          </div>
          <div className={styles.trendCols}>
            <div>
              <div className={styles.trendSectionLabel} style={{ color: '#dc2626' }}>
                <i className="fas fa-arrow-trend-up"></i> Rising Trends
              </div>
              {loading
                ? Array(4).fill(0).map((_, i) => <div key={i} className={styles.skelRow} />)
                : (ct.rising || []).slice(0, 5).map((r, i) => <TrendRow key={i} rank={i + 1} item={r} type="rising" />)}
              {!loading && !ct.rising?.length && <div className={styles.empty}>No rising trends detected</div>}
            </div>
            <div>
              <div className={styles.trendSectionLabel} style={{ color: '#22c55e' }}>
                <i className="fas fa-arrow-trend-down"></i> Falling Trends
              </div>
              {loading
                ? Array(4).fill(0).map((_, i) => <div key={i} className={styles.skelRow} />)
                : (ct.falling || []).slice(0, 5).map((r, i) => <TrendRow key={i} rank={i + 1} item={r} type="falling" />)}
              {!loading && !ct.falling?.length && <div className={styles.empty}>No falling trends</div>}
            </div>
          </div>
        </div>

        {/* ── Risk Distribution ── */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <i className="fas fa-chart-pie" style={{ color: '#8b5cf6' }}></i> Risk Distribution
            <span className={styles.cardSub}>All-time FIR records</span>
          </div>
          {loading
            ? <div className={styles.skelBlock} />
            : (
              <div className={styles.riskDist}>
                {['Critical', 'High', 'Medium', 'Low'].map(level => {
                  const count = riskDist[level] || 0;
                  const pct   = Math.round((count / totalRisk) * 100);
                  return (
                    <div key={level} className={styles.riskDistRow}>
                      <span className={styles.riskDistLabel} style={{ color: RISK_COLORS[level] }}>{level}</span>
                      <div className={styles.riskDistTrack}>
                        <div className={styles.riskDistFill} style={{ width: `${pct}%`, background: RISK_COLORS[level] }}></div>
                      </div>
                      <span className={styles.riskDistCount}>{fmt(count)}</span>
                      <span className={styles.riskDistPct} style={{ color: RISK_COLORS[level] }}>{pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}

          {/* Top areas */}
          <div className={styles.cardHeader} style={{ marginTop: 20 }}>
            <i className="fas fa-map-marker-alt" style={{ color: '#dc2626' }}></i> Top Crime Areas
          </div>
          {loading
            ? <div className={styles.skelBlock} />
            : Object.entries(stats?.crimes_by_area || {}).slice(0, 6).map(([area, count], i) => {
              const maxArea = Object.values(stats.crimes_by_area || {})[0] || 1;
              return (
                <div key={area} className={styles.areaRow}>
                  <span className={styles.areaRank}>{i + 1}</span>
                  <span className={styles.areaName}>{area}</span>
                  <div className={styles.areaTrack}>
                    <div className={styles.areaFill} style={{ width: `${(count / maxArea) * 100}%` }}></div>
                  </div>
                  <span className={styles.areaCount}>{fmt(count)}</span>
                </div>
              );
            })}
        </div>

        {/* ── High Risk Alerts ── */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <i className="fas fa-triangle-exclamation" style={{ color: '#dc2626' }}></i> High-Risk Alerts
            <span className={styles.cardSub}>Last 30 days</span>
          </div>
          {loading
            ? Array(5).fill(0).map((_, i) => <div key={i} className={styles.skelRow} />)
            : hra.length > 0
              ? hra.slice(0, 6).map((a, i) => <AlertRow key={i} alert={a} />)
              : (
                <div className={styles.emptyAlert}>
                  <i className="fas fa-check-circle" style={{ color: '#22c55e', fontSize: '1.5rem' }}></i>
                  <span>No high-risk alerts in the last 30 days</span>
                </div>
              )}
        </div>

        {/* ── Model Health ── */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <i className="fas fa-brain" style={{ color: '#6366f1' }}></i> Model Health
          </div>
          {loading
            ? <div className={styles.skelBlock} />
            : (
              <div className={styles.modelGrid}>
                <div className={styles.modelStat}>
                  <div className={styles.modelVal} style={{ color: '#22c55e' }}>{mh.rf_accuracy}%</div>
                  <div className={styles.modelKey}>RF Accuracy</div>
                </div>
                <div className={styles.modelStat}>
                  <div className={styles.modelVal} style={{ color: '#f97316' }}>{mh.poisson_mae_pct}%</div>
                  <div className={styles.modelKey}>Poisson MAE</div>
                </div>
                <div className={styles.modelStat}>
                  <div className={styles.modelVal} style={{ color: mh.reliability === 'High' ? '#22c55e' : mh.reliability === 'Moderate' ? '#f97316' : '#dc2626' }}>
                    {mh.reliability}
                  </div>
                  <div className={styles.modelKey}>Reliability</div>
                </div>
                <div className={styles.modelStat}>
                  <div className={styles.modelVal} style={{ color: '#94a3b8' }}>{mh.oov_count}</div>
                  <div className={styles.modelKey}>OOV Pairs</div>
                </div>
              </div>
            )}
          {!loading && (
            <>
              <div className={styles.modelMeta}>
                <span><i className="fas fa-calendar-alt"></i> Last trained: <strong>{mh.last_train_date}</strong></span>
                <span><i className="fas fa-database"></i> Training size: <strong>{fmt(mh.training_size)}</strong></span>
              </div>

              {/* Drift */}
              <div className={styles.cardHeader} style={{ marginTop: 18 }}>
                <i className="fas fa-arrows-rotate" style={{ color: '#f97316' }}></i> Data Drift
              </div>
              <div className={styles.driftRow}>
                <div className={styles.driftStat}>
                  <span className={styles.driftVal}>{dr.new_areas_count ?? 0}</span>
                  <span className={styles.driftKey}>New Areas</span>
                </div>
                <div className={styles.driftStat}>
                  <span className={styles.driftVal}>{dr.new_crime_types_count ?? 0}</span>
                  <span className={styles.driftKey}>New Crime Types</span>
                </div>
                <div className={styles.driftStat}>
                  <span className={styles.driftVal} style={{ color: (dr.avg_shift_pct || 0) > 30 ? '#dc2626' : '#f97316' }}>
                    {dr.avg_shift_pct ?? 0}%
                  </span>
                  <span className={styles.driftKey}>Avg Shift</span>
                </div>
              </div>
              <div className={styles.driftAction} style={{ color: (dr.recommended_action === 'Retrain Model') ? '#f97316' : '#22c55e' }}>
                <i className={`fas ${dr.recommended_action === 'Retrain Model' ? 'fa-circle-exclamation' : 'fa-check'}`}></i>
                {dr.recommended_action || 'Monitor'}
              </div>
            </>
          )}
        </div>

        {/* ── 7-Day Forecast ── */}
        <div className={`${styles.card} ${styles.cardWide}`}>
          <div className={styles.cardHeader}>
            <i className="fas fa-calendar-days" style={{ color: '#06b6d4' }}></i> 7-Day Risk Forecast
            <span className={styles.cardSub}>Top 4 most active areas</span>
            <button className={styles.mapLink} onClick={() => onNavigate && onNavigate('crime-map')}>
              <i className="fas fa-map"></i> Full Map View
            </button>
          </div>
          {loading
            ? <div className={styles.skelBlock} style={{ height: 120 }} />
            : forecastAreas.length === 0
              ? <div className={styles.empty}>Run city scan to generate forecasts</div>
              : (
                <div className={styles.forecastTable}>
                  <div className={styles.forecastHeader}>
                    <span className={styles.forecastArea}>Area</span>
                    <span className={styles.forecastCrime}>Top Crime</span>
                    {(forecastAreas[0]?.[1]?.days || []).map(d => (
                      <span key={d.date} className={styles.forecastDay}>{d.day}<br /><small>{d.date}</small></span>
                    ))}
                  </div>
                  {forecastAreas.map(([area, data]) => (
                    <div key={area} className={styles.forecastRow}>
                      <span className={styles.forecastArea}>{area}</span>
                      <span className={styles.forecastCrime}>{data.crime_type}</span>
                      {(data.days || []).map(d => (
                        <span key={d.date} className={styles.forecastCell}
                          style={{
                            color: d.risk === 'High' ? '#dc2626' : d.risk === 'Medium' ? '#f97316' : '#22c55e',
                            background: d.risk === 'High' ? '#dc262612' : d.risk === 'Medium' ? '#f9731612' : '#22c55e12',
                          }}>
                          {d.risk}
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              )}
        </div>

        {/* ── Quick Actions ── */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <i className="fas fa-bolt" style={{ color: '#fbbf24' }}></i> Quick Actions
          </div>
          <div className={styles.quickGrid}>
            {[
              { icon: 'fas fa-map',          label: 'Crime Map',       key: 'crime-map',       color: '#06b6d4' },
              { icon: 'fas fa-brain',         label: 'AI Predictions',  key: 'predictions',     color: '#6366f1' },
              { icon: 'fas fa-chart-bar',     label: 'Analytics',       key: 'analytics',       color: '#8b5cf6' },
              { icon: 'fas fa-users',         label: 'Users',           key: 'user-management', color: '#0ea5e9' },
              { icon: 'fas fa-user-shield',   label: 'Admins',          key: 'admin-management',color: '#f97316' },
              { icon: 'fas fa-gavel',         label: 'FIR Approvals',   key: 'approvals',       color: '#22c55e' },
              { icon: 'fas fa-file-alt',      label: 'Reports',         key: 'reports',         color: '#ec4899' },
              { icon: 'fas fa-balance-scale', label: 'Law Sections',    key: 'law-sections',    color: '#a78bfa' },
            ].map(a => (
              <button key={a.key} className={styles.quickBtn} onClick={() => onNavigate && onNavigate(a.key)}
                style={{ '--qa-color': a.color }}>
                <i className={a.icon} style={{ color: a.color }}></i>
                <span>{a.label}</span>
              </button>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default SuperAdminMainDashboard;
