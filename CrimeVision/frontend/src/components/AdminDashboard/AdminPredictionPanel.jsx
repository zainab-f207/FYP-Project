// AdminPredictionPanel.jsx — Advanced predictive analytics for Admin dashboard
import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../../services/apiService';
import styles from './AdminPredictionPanel.module.css';

const today = () => new Date().toISOString().split('T')[0];

const RISK_COLORS = { Critical: '#7c3aed', High: '#dc2626', Moderate: '#f97316', Low: '#22c55e' };
const RISK_ICONS  = { Critical: 'fa-skull-crossbones', High: 'fa-exclamation-circle', Moderate: 'fa-info-circle', Low: 'fa-check-circle' };

const normalizeRiskLevel = (value) => {
  const v = String(value || '').toLowerCase();
  if (v.includes('critical') || v.includes('avoid')) return 'Critical';
  if (v.includes('high') || v.includes('warning')) return 'High';
  if (v.includes('moderate') || v.includes('medium') || v.includes('caution')) return 'Moderate';
  return 'Low';
};

const actionLabel = (level) => {
  if (level === 'Critical') return 'Avoid';
  if (level === 'High') return 'Warning';
  if (level === 'Moderate') return 'Caution';
  return 'Safe';
};

const fmtHour = (h) => `${h % 12 || 12} ${h < 12 ? 'AM' : 'PM'}`;

const RiskBadge = ({ level, pct }) => {
  const nl = normalizeRiskLevel(level);
  const color = RISK_COLORS[nl] || '#6b7280';
  const icon = RISK_ICONS[nl] || 'fa-circle';
  return (
    <span className={styles.riskBadge} style={{ background: color + '20', color, border: `1px solid ${color}40` }}>
      <i className={`fas ${icon}`}></i> {nl}{pct != null && <span> ({pct}%)</span>}
    </span>
  );
};

const MomentumBadge = ({ momentum }) => {
  if (!momentum) return null;
  const color = momentum.direction === 'rising' ? '#ef4444' : momentum.direction === 'declining' ? '#22c55e' : '#9ca3af';
  const icon  = momentum.direction === 'rising' ? 'fa-arrow-trend-up' : momentum.direction === 'declining' ? 'fa-arrow-trend-down' : 'fa-minus';
  const label = momentum.direction === 'rising' ? 'Rising' : momentum.direction === 'declining' ? 'Declining' : 'Stable';
  return (
    <span className={styles.momentumBadge} style={{ color, borderColor: color + '30', background: color + '12' }}>
      <i className={`fas ${icon}`}></i> {label}
      {momentum.pct_change > 0 && <span> {momentum.direction === 'declining' ? '−' : '+'}{momentum.pct_change}%</span>}
      <span className={styles.momentumSub}> · 90d</span>
    </span>
  );
};

const ScoreBar = ({ score, color }) => (
  <div className={styles.scoreBarWrap}>
    <div className={styles.scoreBarTrack}>
      <div className={styles.scoreBarFill} style={{ width: `${score}%`, background: color }} />
    </div>
    <span className={styles.scoreBarVal}>{score}</span>
  </div>
);

// ── Tab 1: Manual Prediction ──────────────────────────────────────────────────
const ManualPrediction = ({ areas, crimeTypes }) => {
  const [area, setArea]           = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [date, setDate]           = useState(today());
  const [time, setTime]           = useState('');
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState('');

  const run = async () => {
    if (!area || !crimeType) { setError('Select area and crime type.'); return; }
    setError(''); setLoading(true); setResult(null);
    try {
      const r = await apiService.predictRisk(area, crimeType, date, time || null);
      if (!r) throw new Error('No response');
      setResult(r);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <div className={styles.formField}>
          <label>Area</label>
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </div>
        <div className={styles.formField}>
          <label>Crime Type</label>
          <select value={crimeType} onChange={e => setCrimeType(e.target.value)}>
            <option value="">Select crime type…</option>
            {crimeTypes.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className={styles.formField}>
          <label>Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
        <div className={styles.formField}>
          <label>Time <span className={styles.optional}>(optional)</span></label>
          <input type="time" value={time} onChange={e => setTime(e.target.value)} />
        </div>
      </div>
      {error && <div className={styles.errorMsg}><i className="fas fa-exclamation-triangle"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Analyzing…</> : <><i className="fas fa-brain"></i> Run Prediction</>}
      </button>

      {result && (
        <div className={styles.resultCard}>
          {/** RF composite returns an index, not a direct Poisson probability. */}
          {(() => {
            const isRfComposite = result.model === 'rf_composite';
            const displayLevel = normalizeRiskLevel(result.risk_level);
            return (
              <>
          <div className={styles.resultHeader}>
            <div className={styles.resultTitle}>
              <i className="fas fa-shield-alt"></i> Prediction Result
            </div>
            <RiskBadge level={result.risk_level} pct={result.risk_percentage} />
          </div>

          <div className={styles.resultMetrics}>
            <div className={styles.bigScore}>
              {isRfComposite && (
                <div className={styles.riskLevelHero} style={{ color: RISK_COLORS[displayLevel] || '#e2e8f0' }}>
                  {displayLevel}
                </div>
              )}
              <div className={styles.bigScoreNum} style={{ color: RISK_COLORS[normalizeRiskLevel(result.risk_level)] }}>
                {result.risk_percentage}<span>%</span>
              </div>
              <div className={styles.bigScoreLabel}>{result.risk_percentage_label || (isRfComposite ? 'Risk Index' : 'Estimated Risk')}</div>
              <div className={styles.bigScoreBar}>
                <div style={{ width: `${result.risk_percentage}%`, height: '100%', borderRadius: 4, background: RISK_COLORS[normalizeRiskLevel(result.risk_level)] }} />
              </div>
            </div>

            <div className={styles.metaGrid}>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>{isRfComposite ? 'Reliability' : 'Model Confidence'}</span>
                <strong>{Math.round((result.confidence || 0) * 100)}%</strong>
                <span className={styles.metaExplain}>
                  {isRfComposite
                    ? (result.reliability_note || 'RF reliability is based on historical data coverage for this area and crime type.')
                    : result.is_estimated
                    ? 'Estimated from regional patterns — limited direct observations for this area × crime combination'
                    : Math.round((result.confidence || 0) * 100) >= 85
                      ? 'High confidence — based on dense historical observations for this area × crime combination'
                      : Math.round((result.confidence || 0) * 100) >= 60
                        ? 'Moderate confidence — sufficient historical data; some sparsity in this specific combination'
                        : 'Lower confidence — sparse historical data; prediction uses regional base rates as fallback'}
                </span>
              </div>
              <div className={styles.metaItem}>
                <span className={styles.metaLabel}>Model Type</span>
                <strong>{result.model_label || result.model || 'Unknown'}</strong>
                <span className={styles.metaExplain}>
                  {result.risk_percentage_label || (isRfComposite ? 'Risk Index' : 'Risk Score')} is used for this prediction.
                </span>
              </div>
              {!isRfComposite && result.probability != null && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Poisson P(≥1)</span>
                  <strong>{(result.probability * 100).toFixed(1)}%</strong>
                </div>
              )}
              {!isRfComposite && result.lambda != null && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>λ (Expected crimes)</span>
                  <strong>{typeof result.lambda === 'number' ? result.lambda.toFixed(4) : '—'}</strong>
                </div>
              )}
              {isRfComposite && result.model_confidence != null && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>RF Class Confidence</span>
                  <strong>{Math.round((result.model_confidence || 0) * 100)}%</strong>
                </div>
              )}
              {result.is_estimated && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Model</span>
                  <strong style={{ color: '#f97316' }}>Estimated (sparse data)</strong>
                </div>
              )}
              {result.time_period && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Time Period</span>
                  <strong>{result.time_period}</strong>
                </div>
              )}
              {result.time_was_provided && result.time_used_by_model === false && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Visit Time</span>
                  <strong style={{ color: '#f97316' }}>Not used by model</strong>
                  <span className={styles.metaExplain}>Selected time is advisory for legacy predictions</span>
                </div>
              )}
              {result.area_trend && (
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Area Trend (6m)</span>
                  <strong style={{ color: result.area_trend.direction === 'decreasing' ? '#22c55e' : result.area_trend.direction === 'increasing' ? '#dc2626' : '#9ca3af' }}>
                    {result.area_trend.direction === 'increasing' ? '↑' : result.area_trend.direction === 'decreasing' ? '↓' : '→'} {result.area_trend.direction} ({result.area_trend.change_pct > 0 ? '+' : ''}{result.area_trend.change_pct}%)
                  </strong>
                </div>
              )}
            </div>
          </div>

          {result.comparability_note && (
            <div className={styles.periodModelNote}>
              <i className="fas fa-scale-balanced"></i> {result.comparability_note}
            </div>
          )}
              </>
            );
          })()}

          {result.safest_upcoming_dates?.length > 0 && (
            <div className={styles.upcomingBlock}>
              <div className={styles.blockTitle}><i className="fas fa-calendar-check"></i> Safest Upcoming Dates</div>
              <div className={styles.upcomingRow}>
                {result.safest_upcoming_dates.slice(0, 3).map(d => (
                  <div key={d.date} className={styles.upcomingChip}>
                    <span className={styles.upcomingDate}>{d.date}</span>
                    <span className={styles.upcomingDay}>{d.day}</span>
                    <RiskBadge level={d.risk_percentage < 30 ? 'Low' : d.risk_percentage < 60 ? 'Medium' : 'High'} pct={d.risk_percentage} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.hourly_risk_profile && Object.keys(result.hourly_risk_profile).length > 0 && (
            <div className={styles.periodBlock}>
              <div className={styles.blockTitle}><i className="fas fa-clock"></i> Risk by Time Period</div>
              <div className={styles.periodRows}>
                {Object.entries(result.hourly_risk_profile).map(([period, pct]) => (
                  <div key={period} className={styles.periodRow}>
                    <span className={styles.periodName}>{period}</span>
                    <div className={styles.periodBarTrack}>
                      <div className={styles.periodBarFill}
                        style={{ width: `${pct}%`, background: pct > 60 ? '#dc2626' : pct > 35 ? '#f97316' : '#22c55e' }} />
                    </div>
                    <span className={styles.periodPct}>{pct}%</span>
                  </div>
                ))}
              </div>
              <div className={styles.periodModelNote}>
                <i className="fas fa-circle-info"></i> {
                  (() => {
                    const model = (result.model || '').toString().toLowerCase();
                    const label = (result.model_label || '').toString().toLowerCase();
                    const isRf = model === 'rf_composite';
                    const isPoisson = model.includes('poisson') || label.includes('poisson');
                    const isLegacy = model.includes('legacy') || label.includes('legacy');
                    if (isRf) return 'Time period percentages show the RF composite Risk Index for each 4-hour window, using severity, hotspot rank, and time factors. The overall score may differ slightly from any single window.';
                    if (isPoisson) return 'Time period percentages show the average Poisson probability for each 4-hour window. The overall prediction combines the Poisson baseline × ML adjustment × day-of-week × seasonal factors — so the final score may differ from any single time window.';
                    if (isLegacy) return 'Time period percentages show historical window averages (legacy model is time-agnostic). The selected visit time is advisory and is not used by the legacy model — hourly profiles are empirical summaries.';
                    return 'Time period percentages show the model-specific window profile. For Poisson this is a probability; for RF composite this is an index; legacy responses use historical averages.';
                  })()
                }
              </div>
            </div>
          )}

          {/* ── Historical Comparison ─────────────────────────────────────── */}
          {result.historical_comparison && (
            <div className={styles.historicalBlock}>
              <div className={styles.blockTitle}><i className="fas fa-chart-bar"></i> Historical Comparison</div>
              <div className={styles.hcGrid}>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>12-Month Empirical Average</span>
                  <strong className={styles.hcVal}>{result.historical_comparison.historical_avg}%</strong>
                  <span className={styles.hcSub}>{result.historical_comparison.days_with_crime_12m} incident days / 365</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Current Prediction</span>
                  <strong className={styles.hcVal} style={{ color: RISK_COLORS[normalizeRiskLevel(result.risk_level)] }}>
                    {result.historical_comparison.current_predicted}%
                  </strong>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Vs. Historical</span>
                  <strong className={
                    result.historical_comparison.direction === 'higher' ? styles.hcDiffUp :
                    result.historical_comparison.direction === 'lower'  ? styles.hcDiffDown : styles.hcDiffNormal
                  }>
                    {result.historical_comparison.direction === 'higher' ? '↑' :
                     result.historical_comparison.direction === 'lower'  ? '↓' : '→'}{' '}
                    {Math.abs(result.historical_comparison.diff_pct)}% {result.historical_comparison.direction} than typical
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* ── Incident Expectation ─────────────────────────────────────── */}
          {result.expected_incidents && (
            <div className={styles.historicalBlock}>
              <div className={styles.blockTitle}><i className="fas fa-list-ol"></i> Incident Expectation</div>
              <div className={styles.hcGrid}>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Expected Incident Range</span>
                  <strong className={styles.hcVal}>
                    {result.expected_incidents.range_low}–{result.expected_incidents.range_high} incidents
                  </strong>
                  <span className={styles.hcSub}>95th-percentile upper bound</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>P(≥1 Incident)</span>
                  <strong className={styles.hcVal} style={{ color: RISK_COLORS[normalizeRiskLevel(result.risk_level)] }}>
                    {result.expected_incidents.prob_at_least_one}%
                  </strong>
                  <span className={styles.hcSub}>Poisson probability</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Daily Rate (λ)</span>
                  <strong className={styles.hcVal}>{result.expected_incidents.lambda}</strong>
                  <span className={styles.hcSub}>expected crimes / day</span>
                </div>
              </div>
            </div>
          )}

          {/* ── Risk Drivers ─────────────────────────────────────────────── */}
          {result.risk_drivers?.length > 0 && (
            <div className={styles.driversBlock}>
              <div className={styles.blockTitle}><i className="fas fa-magnifying-glass-chart"></i> Risk Drivers</div>
              <div className={styles.driversList}>
                {result.risk_drivers.map((d, i) => (
                  <div key={i} className={styles.driverItem}>
                    <i className="fas fa-circle-dot" style={{ color: '#6366f1', fontSize: '0.48rem', marginTop: 5, flexShrink: 0 }}></i>
                    <span>{d}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 7-Day Forecast ───────────────────────────────────────────── */}
          {result.seven_day_forecast?.length > 0 && (
            <div className={styles.forecastBlock}>
              <div className={styles.blockTitle}><i className="fas fa-calendar-days"></i> 7-Day Forecast</div>
              <div className={styles.forecastRows}>
                {result.seven_day_forecast.map((f, i) => (
                  <div key={i} className={styles.forecastRow}>
                    <span className={styles.forecastDay}>{f.day}</span>
                    <span className={styles.forecastDate}>{f.date}</span>
                    <div className={styles.forecastBarTrack}>
                      <div className={styles.forecastBarFill}
                        style={{ width: `${f.risk_percentage}%`, background: RISK_COLORS[normalizeRiskLevel(f.risk_level)] || '#9ca3af' }} />
                    </div>
                    <span className={styles.forecastPct} style={{ color: RISK_COLORS[normalizeRiskLevel(f.risk_level)] || '#9ca3af' }}>
                      {f.risk_percentage}%
                    </span>
                    <span className={styles.forecastBadge} style={{
                      background: (RISK_COLORS[normalizeRiskLevel(f.risk_level)] || '#9ca3af') + '18',
                      color:      RISK_COLORS[normalizeRiskLevel(f.risk_level)] || '#9ca3af',
                      border:     `1px solid ${(RISK_COLORS[normalizeRiskLevel(f.risk_level)] || '#9ca3af')}35`,
                    }}>{actionLabel(normalizeRiskLevel(f.risk_level))}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};

// ── Tab 2: Area Crime Risk Matrix ────────────────────────────────────────────
const MultiCrimeScan = ({ areas, crimeTypes }) => {
  const [area, setArea]     = useState('');
  const [date, setDate]     = useState(today());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError]   = useState('');
  const [sortCol, setSortCol] = useState('risk_percentage');
  const [sortAsc, setSortAsc] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const TABLE_LIMIT = 15;

  const run = async () => {
    if (!area) { setError('Select an area.'); return; }
    setError(''); setLoading(true); setResults(null);
    try {
      const entries = await Promise.all(
        crimeTypes.map(ct =>
          apiService.predictRisk(area, ct, date)
            .then(r => r ? { crime_type: ct, ...r } : null)
            .catch(() => null)
        )
      );
      setResults(entries.filter(Boolean));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const sorted = results ? [...results].sort((a, b) => {
    const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0;
    if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    return sortAsc ? va - vb : vb - va;
  }) : [];

  const categorize = (ct) => {
    const l = ct.toLowerCase();
    if (l.includes('murder') || l.includes('dacoity') || l.includes('robbery') ||
        l.includes('assault') || l.includes('rape')   || l.includes('kidnap')  ||
        l.includes('hurt')    || l.includes('abduct')  || l.includes('attempt') ||
        l.includes('arson')   || l.includes('terrorism')) return 'Violent Crimes';
    if (l.includes('theft') || l.includes('burglary') || l.includes('house break') ||
        l.includes('motor')  || l.includes('vehicle')  || l.includes('embezzl')    ||
        l.includes('fraud')  || l.includes('cheat')    || l.includes('forgery')    ||
        l.includes('misappropriat') || l.includes('trespass') || l.includes('criminal breach'))
      return 'Property & Financial';
    if (l.includes('riot')  || l.includes('affray')   || l.includes('unlawful') ||
        l.includes('nuis')  || l.includes('breach')   || l.includes('misconduct') ||
        l.includes('mischief') || l.includes('wrongful') || l.includes('restraint') ||
        l.includes('conspiracy')) return 'Public Order';
    if (l.includes('drug')  || l.includes('narco') || l.includes('arms') ||
        l.includes('weapon') || l.includes('illegal')) return 'Narcotics & Arms';
    return 'Other Offences';
  };

  const categories = {};
  sorted.forEach(r => {
    const cat = categorize(r.crime_type);
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(r);
  });

  const thClick = (col) => {
    if (sortCol === col) setSortAsc(p => !p);
    else { setSortCol(col); setSortAsc(false); }
  };

  const SortIcon = ({ col }) => sortCol === col
    ? <i className={`fas fa-sort-${sortAsc ? 'up' : 'down'}`} style={{ marginLeft: 4, fontSize: '0.7rem' }} />
    : <i className="fas fa-sort" style={{ marginLeft: 4, fontSize: '0.7rem', opacity: 0.3 }} />;

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <div className={styles.formField}>
          <label>Area</label>
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </div>
        <div className={styles.formField}>
          <label>Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
      </div>
      {error && <div className={styles.errorMsg}><i className="fas fa-exclamation-triangle"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || !area}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Scanning {crimeTypes.length} crime types…</> : <><i className="fas fa-layer-group"></i> Scan All Crime Types</>}
      </button>

      {sorted.length > 0 && (
        <div className={styles.scanResults}>
          <div className={styles.scanSummary}>
            <span className={styles.scanSumChip} style={{ color: '#dc2626', background: '#dc262615' }}>
              <i className="fas fa-circle"></i> Warning: {sorted.filter(r => normalizeRiskLevel(r.risk_level) === 'High').length}
            </span>
            <span className={styles.scanSumChip} style={{ color: '#f97316', background: '#f9731615' }}>
              <i className="fas fa-circle"></i> Caution: {sorted.filter(r => normalizeRiskLevel(r.risk_level) === 'Moderate').length}
            </span>
            <span className={styles.scanSumChip} style={{ color: '#22c55e', background: '#22c55e15' }}>
              <i className="fas fa-circle"></i> Safe: {sorted.filter(r => normalizeRiskLevel(r.risk_level) === 'Low').length}
            </span>
            <span className={styles.scanSumChip} style={{ color: '#7c3aed', background: '#7c3aed15' }}>
              <i className="fas fa-circle"></i> Avoid: {sorted.filter(r => normalizeRiskLevel(r.risk_level) === 'Critical').length}
            </span>
          </div>

          {/* ── Priority Risks ──────────────────────────────────────────── */}
          <div className={styles.prioritySection}>
            <div className={styles.blockTitle}><i className="fas fa-triangle-exclamation"></i> Priority Risks Today</div>
            <div className={styles.priorityGrid}>
              {sorted.slice(0, 3).map((r, i) => (
                <div key={r.crime_type} className={styles.priorityCard}
                  style={{ borderColor: (RISK_COLORS[normalizeRiskLevel(r.risk_level)] || '#9ca3af') + '55', background: (RISK_COLORS[normalizeRiskLevel(r.risk_level)] || '#9ca3af') + '0a' }}>
                  <div className={styles.priorityRank} style={{ color: RISK_COLORS[normalizeRiskLevel(r.risk_level)] }}>#{i + 1} Priority</div>
                  <div className={styles.priorityCrime}>{r.crime_type}</div>
                  <div className={styles.priorityPct} style={{ color: RISK_COLORS[normalizeRiskLevel(r.risk_level)] }}>{r.risk_percentage}%</div>
                  <RiskBadge level={r.risk_level} />
                </div>
              ))}
            </div>
          </div>

          {/* ── Risk Distribution Bar Chart ─────────────────────────────── */}
          <div className={styles.barChartSection}>
            <div className={styles.blockTitle}><i className="fas fa-chart-bar"></i> Crime Risk Distribution — Top {Math.min(sorted.length, 10)}</div>
            <div className={styles.barChartList}>
              {sorted.slice(0, 10).map((r) => (
                <div key={r.crime_type} className={styles.barChartRow}>
                  <span className={styles.barChartLabel} title={r.crime_type}>{r.crime_type}</span>
                  <div className={styles.barChartTrack}>
                    <div className={styles.barChartFill}
                      style={{ width: `${r.risk_percentage}%`, background: RISK_COLORS[normalizeRiskLevel(r.risk_level)] || '#9ca3af' }} />
                  </div>
                  <span className={styles.barChartPct} style={{ color: RISK_COLORS[normalizeRiskLevel(r.risk_level)] }}>{r.risk_percentage}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Crime Category Breakdown ─────────────────────────────────── */}
          {Object.keys(categories).length > 0 && (
            <div className={styles.categorySection}>
              <div className={styles.blockTitle}><i className="fas fa-layer-group"></i> Crime Category Breakdown</div>
              {Object.entries(categories)
                .sort((a, b) => b[1].reduce((s, r) => s + r.risk_percentage, 0) - a[1].reduce((s, r) => s + r.risk_percentage, 0))
                .map(([cat, crimes]) => (
                  <div key={cat} className={styles.categoryGroup}>
                    <div className={styles.categoryHeader}>
                      <span>{cat}</span>
                      <span className={styles.categoryCount}>{crimes.length} offence type{crimes.length > 1 ? 's' : ''}</span>
                    </div>
                    <div className={styles.categoryRows}>
                      {crimes.slice().sort((a, b) => b.risk_percentage - a.risk_percentage).map(r => (
                        <div key={r.crime_type} className={styles.categoryRow}>
                          <span>{r.crime_type}</span>
                          <RiskBadge level={r.risk_level} pct={r.risk_percentage} />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* ── Full Crime Risk Matrix ───────────────────────────────────── */}
          <div className={styles.blockTitle} style={{ marginBottom: 4 }}><i className="fas fa-table"></i> Full Crime Risk Matrix</div>
          <div className={styles.tableWrap}>
            <table className={styles.scanTable}>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th onClick={() => thClick('crime_type')} className={styles.sortTh}>Crime Type <SortIcon col="crime_type" /></th>
                  <th onClick={() => thClick('risk_level')} className={styles.sortTh}>Risk Level <SortIcon col="risk_level" /></th>
                  <th onClick={() => thClick('risk_percentage')} className={styles.sortTh}>Risk % <SortIcon col="risk_percentage" /></th>
                  <th onClick={() => thClick('confidence')} className={styles.sortTh}>Confidence <SortIcon col="confidence" /></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={r.crime_type} className={normalizeRiskLevel(r.risk_level) === 'High' ? styles.rowHigh : normalizeRiskLevel(r.risk_level) === 'Moderate' ? styles.rowMed : ''}>
                    <td className={styles.rankCell}>#{i + 1}</td>
                    <td><i className="fas fa-tag" style={{ marginRight: 6, opacity: 0.5 }}></i>{r.crime_type}</td>
                    <td><RiskBadge level={r.risk_level} /></td>
                    <td>
                      <div className={styles.inlineBar}>
                        <div className={styles.inlineBarFill} style={{ width: `${r.risk_percentage}%`, background: RISK_COLORS[normalizeRiskLevel(r.risk_level)] }} />
                        <span>{r.risk_percentage}%</span>
                      </div>
                    </td>
                    <td>{Math.round((r.confidence || 0) * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Tab 3: Area Safety Profile ────────────────────────────────────────────────
const AreaSafetyProfile = ({ areas }) => {
  const [area, setArea]         = useState('');
  const [months, setMonths]     = useState(12);
  const [loading, setLoading]   = useState(false);
  const [profile, setProfile]   = useState(null);
  const [error, setError]       = useState('');

  const run = async () => {
    if (!area) { setError('Select an area.'); return; }
    setError(''); setLoading(true); setProfile(null);
    try {
      const selectedAreaObj = areas.find((a) => (a?.name || a) === area);
      const scopeLat = selectedAreaObj?.coordinates?.lat;
      const scopeLng = selectedAreaObj?.coordinates?.lng;
      const r = await apiService.getAreaSafetyProfile(area, months, {
        lat: typeof scopeLat === 'number' ? scopeLat : undefined,
        lng: typeof scopeLng === 'number' ? scopeLng : undefined,
        radiusKm: 1.0,
      });
      setProfile(r);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const scoreColor = !profile ? '#9ca3af'
    : profile.safety_score >= 80 ? '#22c55e'
    : profile.safety_score >= 50 ? '#f97316'
    : profile.safety_score >= 20 ? '#dc2626' : '#7c3aed';
  const overall = profile?.overall_summary || null;
  const overallScoreColor = !overall ? '#9ca3af'
    : overall.safety_score >= 80 ? '#22c55e'
    : overall.safety_score >= 50 ? '#f97316'
    : overall.safety_score >= 20 ? '#dc2626' : '#7c3aed';

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <div className={styles.formField}>
          <label>Area</label>
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </div>
        <div className={styles.formField}>
          <label>Look-back Period</label>
          <select value={months} onChange={e => setMonths(Number(e.target.value))}>
            <option value={3}>3 months</option>
            <option value={6}>6 months</option>
            <option value={12}>12 months</option>
            <option value={24}>24 months</option>
          </select>
        </div>
      </div>
      {error && <div className={styles.errorMsg}><i className="fas fa-exclamation-triangle"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || !area}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Building profile…</> : <><i className="fas fa-shield-alt"></i> Load Area Profile</>}
      </button>

      {profile && (
        <div className={styles.profilePanel}>
          {/* Limited data warning */}
          {profile.low_data_warning && (
            <div className={styles.limitedDataWarning}>
              <i className="fas fa-triangle-exclamation"></i> {profile.low_data_warning}
            </div>
          )}
          {/* Header row */}
          <div className={styles.profileHeader}>
            <div className={styles.profileTitle}>
              <i className="fas fa-map-marker-alt"></i> {profile.area}
              <span className={styles.profileSub}>
                · Overall risk profile ({profile.period_months} months) · {profile.total_crimes.toLocaleString()} incidents
                {profile.analysis_anchor_date && (
                  <span style={{ fontSize: '0.75rem', opacity: 0.65, marginLeft: 6 }}>
                    (anchored to {profile.analysis_anchor_date})
                  </span>
                )}
              </span>
            </div>
            <div className={styles.profileHeaderRight}>
              <MomentumBadge momentum={profile.momentum} />
              <span className={styles.densityChip}>{profile.crime_density?.label}</span>
            </div>
          </div>

          {/* Score + pressure row */}
          <div className={styles.profileKpi}>
            <div className={styles.kpiBlock}>
              <div className={styles.kpiLabel}>Safety Score</div>
              <div className={styles.kpiBig} style={{ color: scoreColor }}>{profile.safety_score}<span>/100</span></div>
              <ScoreBar score={profile.safety_score} color={scoreColor} />
            </div>
            <div className={styles.kpiBlock}>
              <div className={styles.kpiLabel}>Risk Level</div>
              <div className={styles.kpiVal}>{profile.risk_level}</div>
              <div className={styles.kpiSub}>Grade {profile.safety_grade}</div>
            </div>
            <div className={styles.kpiBlock}>
              <div className={styles.kpiLabel}>City Rank</div>
              <div className={styles.kpiBig} style={{ color: '#818cf8' }}>#{profile.area_ranking?.rank}<span>/{profile.area_ranking?.total_areas}</span></div>
              <div className={styles.kpiSub}>Safer than {profile.safer_than_pct}% of Lahore</div>
            </div>
            <div className={styles.kpiBlock}>
              <div className={styles.kpiLabel}>Crime Pressure</div>
              <div className={styles.kpiVal} style={{ color: profile.crime_pressure === 'High' ? '#dc2626' : profile.crime_pressure === 'Elevated' ? '#f97316' : profile.crime_pressure === 'Low' ? '#22c55e' : '#9ca3af' }}>
                {profile.crime_pressure}
              </div>
              <div className={styles.kpiSub}>{profile.city_avg_crimes} city avg/area</div>
            </div>
            <div className={styles.kpiBlock}>
              <div className={styles.kpiLabel}>Recent 30 Days</div>
              <div className={styles.kpiBig}>{profile.last_30_days}</div>
              <div className={styles.kpiSub}>
                {profile.last_30_days_ref_date ? `up to ${profile.last_30_days_ref_date}` : 'incidents'}
              </div>
            </div>
          </div>

          {overall && (
            <div className={styles.visitWindows}>
              <div className={styles.visitItem} style={{ borderColor: '#60a5fa40', background: '#60a5fa08' }}>
                <i className="fas fa-globe-asia" style={{ color: '#60a5fa' }}></i>
                <div>
                  <div className={styles.visitLabel}>Overall (Complete History)</div>
                  <strong>{overall.total_crimes?.toLocaleString?.() || overall.total_crimes || 0} incidents</strong>
                </div>
              </div>
              <div className={styles.visitItem} style={{ borderColor: `${overallScoreColor}40`, background: `${overallScoreColor}12` }}>
                <i className="fas fa-shield-alt" style={{ color: overallScoreColor }}></i>
                <div>
                  <div className={styles.visitLabel}>Overall Safety</div>
                  <strong>{overall.safety_score}/100 · {actionLabel(normalizeRiskLevel(overall.risk_level))}</strong>
                </div>
              </div>
              <div className={styles.visitItem} style={{ borderColor: '#f59e0b40', background: '#f59e0b10' }}>
                <i className="fas fa-calendar" style={{ color: '#f59e0b' }}></i>
                <div>
                  <div className={styles.visitLabel}>History Range</div>
                  <strong>{overall.date_range?.start && overall.date_range?.end ? `${overall.date_range.start} to ${overall.date_range.end}` : 'Not available'}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Visit windows */}
          <div className={styles.visitWindows}>
            <div className={styles.visitItem} style={{ borderColor: '#22c55e40', background: '#22c55e08' }}>
              <i className="fas fa-moon" style={{ color: '#818cf8' }}></i>
              <div><div className={styles.visitLabel}>Lowest Risk Window</div><strong>{profile.safest_hour_range}</strong></div>
            </div>
            <div className={styles.visitItem} style={{ borderColor: '#22c55e40', background: '#22c55e08' }}>
              <i className="fas fa-sun" style={{ color: '#22c55e' }}></i>
              <div><div className={styles.visitLabel}>Recommended Visit</div><strong>{profile.recommended_visit_window}</strong></div>
            </div>
            <div className={styles.visitItem} style={{ borderColor: '#ef444440', background: '#ef444408' }}>
              <i className="fas fa-exclamation-triangle" style={{ color: '#ef4444' }}></i>
              <div><div className={styles.visitLabel}>Higher Risk Window</div><strong>{profile.riskiest_hour_range}</strong></div>
            </div>
          </div>

          {/* Top crimes */}
          <div className={styles.topCrimesBlock}>
            <div className={styles.blockTitle}><i className="fas fa-list"></i> Top Crime Types</div>
            {profile.top_crime_types?.slice(0, 5).map((c, i) => (
              <div key={i} className={styles.crimeRow}>
                <span className={styles.crimeRank}>{i + 1}</span>
                <span className={styles.crimeType}>{c.type}</span>
                <div className={styles.crimeBarTrack}>
                  <div className={styles.crimeBarFill} style={{ width: `${Math.max(c.pct, 2)}%`, background: i === 0 ? '#dc2626' : i === 1 ? '#f97316' : '#3b82f6' }} />
                </div>
                <span className={styles.crimePct}>{c.pct}%</span>
              </div>
            ))}
          </div>

          {/* Trend details */}
          <div className={styles.trendBlock}>
            <div className={styles.blockTitle}><i className="fas fa-chart-line"></i> Crime Trend</div>
            <div className={styles.trendRows}>
              <div className={styles.trendRow}>
                <span>Recent {Math.round(profile.period_months / 2)}m:</span>
                <strong>{profile.trend?.recent_count?.toLocaleString()} incidents</strong>
                <span className={styles.trendSub}>({profile.trend?.recent_monthly_avg}/mo avg)</span>
              </div>
              <div className={styles.trendRow}>
                <span>Prior {Math.round(profile.period_months / 2)}m:</span>
                <strong>{profile.trend?.older_count?.toLocaleString()} incidents</strong>
                <span className={styles.trendSub}>({profile.trend?.older_monthly_avg}/mo avg)</span>
              </div>
              <div className={styles.trendRow}>
                <span>Change:</span>
                <strong style={{ color: profile.trend?.direction === 'decreasing' ? '#22c55e' : profile.trend?.direction === 'increasing' ? '#dc2626' : '#9ca3af' }}>
                  {profile.trend?.direction === 'decreasing' ? '−' : profile.trend?.direction === 'increasing' ? '+' : '±'}{profile.trend?.change_pct}%
                </strong>
              </div>
            </div>
          </div>

          {/* Day of week */}
          <div className={styles.dowBlock}>
            <div className={styles.blockTitle}><i className="fas fa-calendar-week"></i> Day of Week</div>
            <div className={styles.dowChart}>
              {profile.day_of_week?.map((d, i) => (
                <div key={i} className={styles.dowCol} title={`${d.day}: ${d.count}`}>
                  <div className={styles.dowBarTrack}>
                    <div className={styles.dowBarFill} style={{
                      height: `${Math.max(d.pct, 4)}%`,
                      background: d.day === profile.riskiest_day ? '#dc2626' : d.day === profile.safest_day ? '#16a34a' : '#3b82f6'
                    }} />
                  </div>
                  <div className={styles.dowLabel}>{d.day?.slice(0, 3)}</div>
                </div>
              ))}
            </div>
            <div className={styles.dowSummary}>
              <span><i className="fas fa-check-circle" style={{ color: '#22c55e' }}></i> Safest: <strong>{profile.safest_day}</strong>
                {typeof profile.safest_day_vs_avg === 'number' && <span style={{ color: '#22c55e', fontSize: '0.75rem' }}> ({profile.safest_day_vs_avg}% vs avg)</span>}
              </span>
              <span><i className="fas fa-exclamation-circle" style={{ color: '#dc2626' }}></i> Riskiest: <strong>{profile.riskiest_day}</strong>
                {typeof profile.riskiest_day_vs_avg === 'number' && <span style={{ color: '#dc2626', fontSize: '0.75rem' }}> (+{profile.riskiest_day_vs_avg}% vs avg)</span>}
              </span>
            </div>
          </div>

          {/* ── Monthly Incident Trend ───────────────────────────────────── */}
          {profile.monthly_crime_counts?.length > 0 && (
            <div className={styles.monthlyBlock}>
              <div className={styles.blockTitle}><i className="fas fa-chart-area"></i> Monthly Incident Trend</div>
              <div className={styles.monthlyChart}>
                {(() => {
                  const maxCnt = Math.max(...profile.monthly_crime_counts.map(m => m.count), 1);
                  return profile.monthly_crime_counts.map((m, i) => (
                    <div key={i} className={styles.monthlyBar}>
                      <div className={styles.monthlyBarCount}>{m.count}</div>
                      <div className={styles.monthlyBarTrack}>
                        <div className={styles.monthlyBarFill}
                          style={{ height: `${Math.max(m.count / maxCnt * 100, 4)}%` }} />
                      </div>
                      <div className={styles.monthlyBarLabel}>{m.label}</div>
                    </div>
                  ));
                })()}
              </div>
            </div>
          )}

          {/* ── Locality Crime Hotspots ───────────────────────────────── */}
          {profile.sub_area_breakdown?.length > 0 && (
            <div className={styles.localityBlock}>
              <div className={styles.blockTitle}>
                <i className="fas fa-map-pin"></i> Locality Crime Hotspots
                <span className={styles.localitySubtitle}> — sub-area breakdown inside {profile.area}</span>
              </div>
              {profile.sub_area_breakdown[0] && (
                <div className={styles.localityTopBadge}>
                  <i className="fas fa-fire"></i> Highest Risk Locality: <strong>{profile.sub_area_breakdown[0].name}</strong>
                  <span> — accounts for {profile.sub_area_breakdown[0].pct}% of incidents in this area</span>
                </div>
              )}
              <div className={styles.localityTableWrap}>
                <table className={styles.localityTable}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Sub-Area / Locality</th>
                      <th>Incidents</th>
                      <th>Share</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const maxShare = Math.max(...profile.sub_area_breakdown.map(s => s.pct), 1);
                      return profile.sub_area_breakdown.map((sa, i) => (
                        <tr key={i}>
                          <td className={styles.localityRank}>{i + 1}</td>
                          <td className={styles.localityName}><i className="fas fa-location-dot" style={{ marginRight: 6, opacity: 0.4 }}></i>{sa.name}</td>
                          <td><strong>{sa.count}</strong></td>
                          <td>
                            <div className={styles.localityBarWrap}>
                              <div className={styles.localityBarTrack}>
                                <div className={styles.localityBarFill}
                                  style={{ width: `${(sa.pct / maxShare) * 100}%`, background: RISK_COLORS[normalizeRiskLevel(sa.risk_level)] || '#6b7280' }} />
                              </div>
                              <span>{sa.pct}%</span>
                            </div>
                          </td>
                          <td>
                            <span className={styles.localityRiskTag}
                              style={{ background: (RISK_COLORS[normalizeRiskLevel(sa.risk_level)] || '#6b7280') + '18', color: RISK_COLORS[normalizeRiskLevel(sa.risk_level)] || '#6b7280', border: `1px solid ${(RISK_COLORS[normalizeRiskLevel(sa.risk_level)] || '#6b7280')}30` }}>
                              {actionLabel(normalizeRiskLevel(sa.risk_level))}
                            </span>
                          </td>
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
              <div className={styles.localityDataNote}>
                <i className="fas fa-circle-info"></i> Sub-areas are extracted from Urdu FIR address descriptions (transliterated). Some localities may appear outside traditional area boundaries due to FIR registration practices — the filter ensures only FIRs filed under <strong>{profile.area}</strong> are included.
              </div>
            </div>
          )}

          {/* ── Recommended Actions ─────────────────────────────────────── */}
          <div className={styles.recommendationsBlock}>
            <div className={styles.blockTitle}><i className="fas fa-list-check"></i> Recommended Actions</div>
            <div className={styles.recList}>
              {[
                profile.riskiest_hour_range && profile.riskiest_hour_range !== 'N/A' && {
                  icon: 'fa-shield-halved', color: '#6366f1',
                  text: `Increase patrols during ${profile.riskiest_hour_range} — peak activity window for this area`,
                },
                profile.riskiest_day && {
                  icon: 'fa-calendar-xmark', color: '#f97316',
                  text: `Monitor ${profile.riskiest_day} more closely — historically highest-incident day${typeof profile.riskiest_day_vs_avg === 'number' ? ` (+${profile.riskiest_day_vs_avg}% vs average)` : ''}`,
                },
                profile.top_crime_types?.[0] && {
                  icon: 'fa-magnifying-glass', color: '#3b82f6',
                  text: `Prioritise resources on ${profile.top_crime_types[0].type} — ${profile.top_crime_types[0].pct}% of all recorded incidents in this area`,
                },
                profile.trend?.direction === 'increasing' && {
                  icon: 'fa-arrow-trend-up', color: '#dc2626',
                  text: 'Crime trend rising — consider preventive deployment and community engagement initiatives',
                },
                profile.trend?.direction === 'decreasing' && {
                  icon: 'fa-circle-check', color: '#22c55e',
                  text: `Crime trend declining ${profile.trend.change_pct}% — maintain current strategy and document effective interventions`,
                },
                profile.crime_pressure === 'High' && {
                  icon: 'fa-users', color: '#dc2626',
                  text: `High crime pressure (${profile.crime_density?.label}) — allocate additional patrol resources`,
                },
                profile.crime_pressure === 'Low' && {
                  icon: 'fa-circle-check', color: '#22c55e',
                  text: 'Low crime pressure — standard monitoring protocols are sufficient for this area',
                },
              ].filter(Boolean).map((rec, i) => (
                <div key={i} className={styles.recItem}>
                  <i className={`fas ${rec.icon}`} style={{ color: rec.color }}></i>
                  <span>{rec.text}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

// ── Main Component ────────────────────────────────────────────────────────────
const AdminPredictionPanel = () => {
  const [tab, setTab]                 = useState('manual');
  const [areas, setAreas]             = useState([]);
  const [crimeTypes, setCrimeTypes]   = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [lastTrainDate, setLastTrainDate] = useState(null);
  const [totalRecords, setTotalRecords]   = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [a, c, intel] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes(),
          apiService.getIntelligenceDashboard().catch(() => null),
        ]);
        setAreas(a?.areas || a || []);
        setCrimeTypes(c?.crime_types || c || []);
        if (intel) {
          setLastTrainDate(intel?.model_health?.last_train_date || null);
          setTotalRecords(intel?.dataset_health?.total_records ?? null);
        }
      } catch { /* */ }
      finally { setLoadingMeta(false); }
    })();
  }, []);

  const TABS = [
    { id: 'manual',  icon: 'fa-brain',       label: 'Crime Risk Prediction'   },
    { id: 'multi',   icon: 'fa-layer-group',  label: 'Area Crime Risk Matrix'  },
    { id: 'profile', icon: 'fa-shield-alt',   label: 'Area Risk Intelligence'  },
  ];

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <div className={styles.panelHeaderLeft}>
          <div className={styles.headerIcon}><i className="fas fa-brain"></i></div>
          <div>
            <h2 className={styles.panelTitle}>Predictive Intelligence</h2>
            <p className={styles.panelSub}>ML-powered crime risk analytics for administrative decision-making</p>
          </div>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.modelBadge}>
            <i className="fas fa-microchip"></i> Poisson + RF Ensemble
          </div>
          <div className={styles.dataSourceLabel}>
            <i className="fas fa-database"></i> {totalRecords != null ? totalRecords.toLocaleString() : '—'} FIR Records
          </div>
          {lastTrainDate && (
            <div className={styles.modelBadge} style={{ color: '#a78bfa' }}>
              <i className="fas fa-calendar-check"></i> Last Trained: {lastTrainDate}
            </div>
          )}
        </div>
      </div>

      <div className={styles.tabs}>
        {TABS.map(t => (
          <button key={t.id} className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`} onClick={() => setTab(t.id)}>
            <i className={`fas ${t.icon}`}></i> {t.label}
          </button>
        ))}
      </div>

      {loadingMeta ? (
        <div className={styles.metaLoading}><i className="fas fa-spinner fa-spin"></i> Loading model metadata…</div>
      ) : (
        <>
          {tab === 'manual'  && <ManualPrediction  areas={areas} crimeTypes={crimeTypes} />}
          {tab === 'multi'   && <MultiCrimeScan    areas={areas} crimeTypes={crimeTypes} />}
          {tab === 'profile' && <AreaSafetyProfile areas={areas} />}
        </>
      )}
    </div>
  );
};

export default AdminPredictionPanel;
