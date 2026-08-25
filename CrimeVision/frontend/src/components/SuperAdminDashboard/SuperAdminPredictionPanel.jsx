// SuperAdminPredictionPanel.jsx — Command-level predictive intelligence for SuperAdmin
import React, { useState, useEffect, useRef } from 'react';
import apiService from '../../services/apiService';
import { SYSTEM_SETTINGS_DEFAULTS, useSystemSettings } from '../../contexts/SystemSettingsContext';
import { useAuth } from '../../contexts/AuthContext';
import styles from './SuperAdminPredictionPanel.module.css';

const today = () => new Date().toISOString().split('T')[0];

const RISK_COLORS = { Critical: '#7c3aed', High: '#dc2626', Medium: '#f97316', Low: '#22c55e' };
const RISK_ICONS  = { Critical: 'fa-skull-crossbones', High: 'fa-exclamation-circle', Medium: 'fa-info-circle', Low: 'fa-check-circle' };

const RiskBadge = ({ level, pct }) => (
  <span className={styles.riskBadge} style={{
    background: (RISK_COLORS[level] || '#6b7280') + '1a',
    color: RISK_COLORS[level] || '#6b7280',
    border: `1px solid ${RISK_COLORS[level] || '#6b7280'}35`
  }}>
    <i className={`fas ${RISK_ICONS[level] || 'fa-circle'}`}></i> {level}
    {pct != null && <span> ({pct}%)</span>}
  </span>
);

const MomentumBadge = ({ momentum }) => {
  if (!momentum) return null;
  const color  = momentum.direction === 'rising' ? '#ef4444' : momentum.direction === 'declining' ? '#22c55e' : '#9ca3af';
  const icon   = momentum.direction === 'rising' ? 'fa-arrow-trend-up' : momentum.direction === 'declining' ? 'fa-arrow-trend-down' : 'fa-minus';
  const label  = momentum.direction === 'rising' ? 'Rising' : momentum.direction === 'declining' ? 'Declining' : 'Stable';
  return (
    <span className={styles.momentumBadge} style={{ color, borderColor: color + '30', background: color + '10' }}>
      <i className={`fas ${icon}`}></i> {label}
      {momentum.pct_change > 0 && <span>{momentum.direction === 'declining' ? ' −' : ' +'}{momentum.pct_change}%</span>}
      <span className={styles.mSub}> · 90d</span>
    </span>
  );
};

// ── Tab 1: Manual Prediction ──────────────────────────────────────────────────
const ManualPrediction = ({ areas, crimeTypes }) => {
  const [form, setForm] = useState({ area: '', crimeType: '', date: today(), time: '' });
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState('');
  const up = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const run = async () => {
    if (!form.area || !form.crimeType) { setError('Select area and crime type.'); return; }
    setError(''); setLoading(true); setResult(null);
    try {
      const r = await apiService.predictRisk(form.area, form.crimeType, form.date, form.time || null);
      if (!r) throw new Error('Empty response');
      setResult(r);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const scoreColor = !result ? '#6366f1'
    : result.risk_level === 'Critical' ? '#7c3aed'
    : result.risk_level === 'High' ? '#dc2626'
    : result.risk_level === 'Medium' ? '#f97316' : '#22c55e';

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <FormField label="Area">
          <select value={form.area} onChange={e => up('area', e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </FormField>
        <FormField label="Crime Type">
          <select value={form.crimeType} onChange={e => up('crimeType', e.target.value)}>
            <option value="">Select crime type…</option>
            {crimeTypes.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </FormField>
        <FormField label="Date">
          <input type="date" value={form.date} onChange={e => up('date', e.target.value)} />
        </FormField>
        <FormField label={<>Time <span className={styles.opt}>(optional)</span></>}>
          <input type="time" value={form.time} onChange={e => up('time', e.target.value)} />
        </FormField>
      </div>

      {error && <div className={styles.errMsg}><i className="fas fa-triangle-exclamation"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Analyzing…</> : <><i className="fas fa-brain"></i> Run Prediction</>}
      </button>

      {result && (
        <div className={styles.resultCard}>
          {(() => {
            const isRfComposite = result.model === 'rf_composite';
            return (
              <>
          <div className={styles.rcHeader}>
            <span className={styles.rcTitle}><i className="fas fa-shield-halved"></i> Prediction Result</span>
            <RiskBadge level={result.risk_level} pct={result.risk_percentage} />
          </div>

          {/* ── Prediction Reliability Warning ── */}
          {(result.is_estimated || Math.round((result.confidence || 0) * 100) < 50) && (
            <div className={styles.reliabilityWarning}>
              <div className={styles.rwHeader}>
                <i className="fas fa-triangle-exclamation"></i>
                <strong>Prediction Reliability: Limited</strong>
                <span className={styles.rwBadge}>Low Confidence</span>
              </div>
              <div className={styles.rwGrid}>
                <div className={styles.rwItem}>
                  <span className={styles.rwLabel}>Reason</span>
                  <span className={styles.rwVal}>Insufficient historical incidents for this area × crime combination</span>
                </div>
                <div className={styles.rwItem}>
                  <span className={styles.rwLabel}>Confidence</span>
                  <span className={styles.rwVal} style={{ color: '#f97316' }}>{Math.round((result.confidence || 0) * 100)}%</span>
                </div>
                <div className={styles.rwItem}>
                  <span className={styles.rwLabel}>Recommendation</span>
                  <span className={styles.rwVal}>Collect more data to improve accuracy for this combination</span>
                </div>
              </div>
            </div>
          )}

          <div className={styles.rcMainRow}>
            {/* Big gauge */}
            <div className={styles.gaugeWrap}>
              <svg viewBox="0 0 120 70" className={styles.gaugeSvg}>
                <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" strokeLinecap="round" />
                <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke={scoreColor}
                  strokeWidth="10" strokeLinecap="round"
                  strokeDasharray={Math.round((result.risk_percentage / 100) * 157) + ' 157'}
                  className={styles.gaugeArc} />
              </svg>
              <div className={styles.gaugeCenter}>
                {isRfComposite && <div className={styles.gaugeRiskLevel}>{result.risk_level}</div>}
                <div className={styles.gaugeNum} style={{ color: scoreColor }}>{result.risk_percentage}%</div>
                <div className={styles.gaugeLabel}>{result.risk_percentage_label || (isRfComposite ? 'Risk Index' : 'Risk')}</div>
              </div>
            </div>

            {/* Tech metrics */}
            <div className={styles.techMetrics}>
              <div className={styles.techRow}>
                <span className={styles.techLabel}>{isRfComposite ? 'Reliability' : 'Confidence'}</span>
                <strong>{`${Math.round((result.confidence || 0) * 100)}%`}</strong>
              </div>
              <div className={styles.confExplain}>
                {isRfComposite
                  ? (result.reliability_note || 'RF reliability is based on historical data coverage for this area and crime type.')
                  : result.is_estimated
                  ? 'Estimated from regional patterns — limited direct observations for this area × crime combination'
                  : Math.round((result.confidence || 0) * 100) >= 85
                    ? 'High confidence — dense historical observations for this area × crime combination'
                    : Math.round((result.confidence || 0) * 100) >= 60
                      ? 'Moderate confidence — sufficient data; some sparsity in this combination'
                      : 'Lower confidence — sparse data; prediction uses regional base rates as fallback'}
              </div>
                          <TechRow label="Model Type" value={result.model_label || result.model || 'Unknown'} />
                          <TechRow label="Score Type" value={result.risk_percentage_label || (isRfComposite ? 'Risk Index' : 'Risk Score')} />
              {!isRfComposite && result.probability != null && <TechRow label="P(crime ≥1)" value={`${(result.probability * 100).toFixed(1)}%`} />}
              {!isRfComposite && result.lambda     != null && <TechRow label="Poisson λ"    value={typeof result.lambda === 'number' ? result.lambda.toFixed(4) : '—'} />}
              {isRfComposite && result.model_confidence != null && <TechRow label="RF Class Confidence" value={`${Math.round((result.model_confidence || 0) * 100)}%`} />}
              {result.time_period       && <TechRow label="Time Period"   value={result.time_period} />}
              {result.area_trend && (
                <>
                  <TechRow label="Area Trend (6m)"
                    value={`${result.area_trend.direction === 'increasing' ? '↑' : result.area_trend.direction === 'decreasing' ? '↓' : '→'} ${result.area_trend.change_pct > 0 ? '+' : ''}${result.area_trend.change_pct}%`}
                    color={result.area_trend.direction === 'decreasing' ? '#22c55e' : result.area_trend.direction === 'increasing' ? '#dc2626' : '#9ca3af'}
                  />
                  {result.time_was_provided && result.time_used_by_model === false && (
                    <div style={{ marginTop: 8, gridColumn: '1 / -1' }}>
                      <div style={{ fontSize: '0.85rem', color: '#f97316' }}>
                        <i className="fas fa-circle-info"></i> Selected visit time was provided but not used by this legacy model — it is advisory only.
                      </div>
                    </div>
                  )}
                </>
              )}
              <TechRow label="Data Quality" value={result.is_estimated ? 'Estimated (sparse)' : 'Modeled'} color={result.is_estimated ? '#f97316' : '#22c55e'} />
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

          {/* Hourly profile */}
          {result.hourly_risk_profile && Object.keys(result.hourly_risk_profile).length > 0 && (
            <div className={styles.periodBlock}>
              <div className={styles.blockTitle}><i className="fas fa-clock"></i> Risk by Time Period</div>
              {Object.entries(result.hourly_risk_profile).map(([p, v]) => (
                <div key={p} className={styles.periodRow}>
                  <span className={styles.periodName}>{p}</span>
                  <div className={styles.periodTrack}>
                    <div className={styles.periodFill} style={{ width: `${v}%`, background: v > 60 ? '#dc2626' : v > 35 ? '#f97316' : '#22c55e' }} />
                  </div>
                  <span className={styles.periodPct}>{v}%</span>
                </div>
              ))}
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

          {/* Safest upcoming */}
          {result.safest_upcoming_dates?.length > 0 && (
            <div className={styles.upcomingBlock}>
              <div className={styles.blockTitle}><i className="fas fa-calendar-check"></i> Safest Upcoming Dates</div>
              <div className={styles.upcomingRow}>
                {result.safest_upcoming_dates.slice(0, 4).map(d => (
                  <div key={d.date} className={styles.upcomingChip}>
                    <span className={styles.ucDate}>{d.date}</span>
                    <span className={styles.ucDay}>{d.day}</span>
                    <RiskBadge level={d.risk_percentage < 25 ? 'Low' : d.risk_percentage < 50 ? 'Medium' : d.risk_percentage < 80 ? 'High' : 'Critical'} pct={d.risk_percentage} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Historical Context ── */}
          {result.historical_frequency && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle}><i className="fas fa-clock-rotate-left"></i> Historical Context</div>
              <div className={styles.hcGrid}>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Last 12 Months</span>
                  <strong className={styles.hcVal}>{result.historical_frequency.last_12m}</strong>
                  <span className={styles.hcSub}>incidents in {form.area}</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Last 3 Months</span>
                  <strong className={styles.hcVal}>{result.historical_frequency.last_3m}</strong>
                  <span className={styles.hcSub}>incidents this quarter</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>City Average (12m)</span>
                  <strong className={styles.hcVal}>{result.historical_frequency.city_avg}</strong>
                  <span className={styles.hcSub}>incidents / area city-wide</span>
                </div>
              </div>
              {result.historical_frequency.last_12m < 5 && (
                <div className={styles.hcSparseNote}>
                  <i className="fas fa-circle-info"></i> Very few historical incidents — prediction relies on regional base rates
                </div>
              )}
            </div>
          )}

          {/* Historical Comparison */}
          {result.historical_comparison && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle}><i className="fas fa-chart-bar"></i> Historical Comparison</div>
              <div className={styles.hcGrid}>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>12-Month Empirical Average</span>
                  <strong className={styles.hcVal}>{result.historical_comparison.historical_avg}%</strong>
                  <span className={styles.hcSub}>{result.historical_comparison.days_with_crime_12m} incident days / 365</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Current Prediction</span>
                  <strong className={styles.hcVal} style={{ color: RISK_COLORS[result.risk_level] }}>{result.historical_comparison.current_predicted}%</strong>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Vs. Historical</span>
                  <strong style={{ color: result.historical_comparison.direction === 'higher' ? '#dc2626' : result.historical_comparison.direction === 'lower' ? '#22c55e' : '#9ca3af' }}>
                    {result.historical_comparison.direction === 'higher' ? '↑' : result.historical_comparison.direction === 'lower' ? '↓' : '→'}{' '}
                    {Math.abs(result.historical_comparison.diff_pct)}% {result.historical_comparison.direction} than typical
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* Incident Expectation */}
          {result.expected_incidents && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle}><i className="fas fa-list-ol"></i> Incident Expectation</div>
              <div className={styles.hcGrid}>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Expected Range</span>
                  <strong className={styles.hcVal}>{result.expected_incidents.range_low}–{result.expected_incidents.range_high} incidents</strong>
                  <span className={styles.hcSub}>95th-percentile upper bound</span>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>P(≥1 Incident)</span>
                  <strong className={styles.hcVal} style={{ color: RISK_COLORS[result.risk_level] }}>{result.expected_incidents.prob_at_least_one}%</strong>
                </div>
                <div className={styles.hcItem}>
                  <span className={styles.hcLabel}>Daily Rate (λ)</span>
                  <strong className={styles.hcVal}>{result.expected_incidents.lambda}</strong>
                  <span className={styles.hcSub}>expected crimes / day</span>
                </div>
              </div>
            </div>
          )}

          {/* Key Risk Drivers */}
          {result.risk_drivers?.length > 0 && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle}><i className="fas fa-magnifying-glass-chart"></i> Key Risk Drivers</div>
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

          {/* ── Suggested Response ── */}
          {result.suggested_response?.length > 0 && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle} style={{ color: '#22c55e' }}>
                <i className="fas fa-shield-halved"></i> Suggested Response
              </div>
              <div className={styles.driversList}>
                {result.suggested_response.map((s, i) => (
                  <div key={i} className={styles.driverItem}>
                    <i className="fas fa-chevron-right" style={{ color: '#22c55e', fontSize: '0.55rem', marginTop: 5, flexShrink: 0 }}></i>
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7-Day Forecast */}
          {result.seven_day_forecast?.length > 0 && (
            <div className={styles.analyticsBlock}>
              <div className={styles.blockTitle}><i className="fas fa-calendar-days"></i> 7-Day Forecast</div>
              <div className={styles.forecastRows}>
                {result.seven_day_forecast.map((f, i) => (
                  <div key={i} className={styles.forecastRow}>
                    <span className={styles.forecastDay}>{f.day}</span>
                    <span className={styles.forecastDate}>{f.date}</span>
                    <div className={styles.forecastBarTrack}>
                      <div className={styles.forecastBarFill}
                        style={{ width: `${f.risk_percentage}%`, background: RISK_COLORS[f.risk_level] || '#9ca3af' }} />
                    </div>
                    <span className={styles.forecastPct} style={{ color: RISK_COLORS[f.risk_level] || '#9ca3af' }}>{f.risk_percentage}%</span>
                    <span className={styles.forecastBadge} style={{
                      background: (RISK_COLORS[f.risk_level] || '#9ca3af') + '18',
                      color: RISK_COLORS[f.risk_level] || '#9ca3af',
                      border: `1px solid ${(RISK_COLORS[f.risk_level] || '#9ca3af')}35`,
                    }}>{f.risk_level}</span>
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

// ── Tab 2: Multi-Crime Scan ───────────────────────────────────────────────────
const MultiCrimeScan = ({ areas, crimeTypes }) => {
  const [area, setArea] = useState('');
  const [date, setDate] = useState(today());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError]   = useState('');
  const [sortCol, setSortCol] = useState('risk_percentage');
  const [sortAsc, setSortAsc] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const TABLE_LIMIT = 15;

  const run = async () => {
    if (!area) { setError('Select an area.'); return; }
    setError(''); setLoading(true); setResults(null); setShowAll(false);
    try {
      const rows = await Promise.all(
        crimeTypes.map(ct =>
          apiService.predictRisk(area, ct, date)
            .then(r => r ? { crime_type: ct, ...r } : null)
            .catch(() => null)
        )
      );
      setResults(rows.filter(Boolean));
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
        l.includes('mischief') || l.includes('wrongful') || l.includes('conspiracy')) return 'Public Order';
    if (l.includes('drug')  || l.includes('narco') || l.includes('arms') ||
        l.includes('weapon') || l.includes('illegal')) return 'Narcotics & Arms';
    return 'Other Offences';
  };

  const thClick = col => { if (sortCol === col) setSortAsc(p => !p); else { setSortCol(col); setSortAsc(false); } };
  const SortIcon = ({ col }) => sortCol === col
    ? <i className={`fas fa-sort-${sortAsc ? 'up' : 'down'}`} style={{ marginLeft: 4, fontSize: '0.65rem' }} />
    : <i className="fas fa-sort" style={{ marginLeft: 4, fontSize: '0.65rem', opacity: 0.25 }} />;

  const topBar = sorted.slice(0, 10);
  const maxBarPct = Math.max(...topBar.map(r => r.risk_percentage || 0), 1);

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <FormField label="Area">
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </FormField>
        <FormField label="Date">
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </FormField>
      </div>
      {error && <div className={styles.errMsg}><i className="fas fa-triangle-exclamation"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || !area}>
        {loading
          ? <><i className="fas fa-spinner fa-spin"></i> Scanning {crimeTypes.length} types…</>
          : <><i className="fas fa-layer-group"></i> Scan All Crime Types</>}
      </button>

      {sorted.length > 0 && (
        <div className={styles.scanBlock}>
          <div className={styles.scanSummaryRow}>
            {['Critical','High', 'Medium', 'Low'].map(l => (
              <span key={l} className={styles.sumChip} style={{ color: RISK_COLORS[l], background: (RISK_COLORS[l] || '#6b7280') + '15' }}>
                <i className="fas fa-circle" style={{ fontSize: '0.45rem' }}></i> {l}: {sorted.filter(r => r.risk_level === l).length}
              </span>
            ))}
          </div>

          {/* ── Unknown PPC Detection Alert ── */}
          {(() => {
            const unknownPPC = sorted.filter(r =>
              r.crime_type && (
                r.crime_type.toLowerCase().includes('unknown ppc') ||
                r.crime_type.toLowerCase().includes('unknown section') ||
                r.crime_type.toLowerCase() === 'unknown'
              )
            );
            if (!unknownPPC.length) return null;
            return (
              <div className={styles.unknownPPCAlert}>
                <div className={styles.unknownPPCHeader}>
                  <i className="fas fa-circle-exclamation"></i>
                  <strong>Unknown Crime Sections Detected</strong>
                  <span className={styles.unknownPPCCount}>{unknownPPC.length} {unknownPPC.length === 1 ? 'entry requires' : 'entries require'} classification</span>
                </div>
                <div className={styles.unknownPPCList}>
                  {unknownPPC.map(u => (
                    <div key={u.crime_type} className={styles.unknownPPCItem}>
                      <i className="fas fa-tag"></i>
                      <span>{u.crime_type}</span>
                      <span className={styles.unknownPPCRisk}>{u.risk_percentage}% risk</span>
                    </div>
                  ))}
                </div>
                <div className={styles.unknownPPCRec}>
                  <i className="fas fa-lightbulb"></i> Review PPC section classification — these entries may represent Theft, Robbery, or other classified offences.
                </div>
              </div>
            );
          })()}

          {/* Priority Risks */}
          {sorted.slice(0, 3).length > 0 && (
            <div className={styles.prioritySection}>
              <div className={styles.sectionLabel}><i className="fas fa-fire"></i> Priority Risks Today</div>
              <div className={styles.priorityGrid}>
                {sorted.slice(0, 3).map((r, i) => (
                  <div key={r.crime_type} className={styles.priorityCard}
                    style={{ borderColor: (RISK_COLORS[r.risk_level] || '#6b7280') + '40', background: (RISK_COLORS[r.risk_level] || '#6b7280') + '0a' }}>
                    <div className={styles.priorityRank} style={{ color: RISK_COLORS[r.risk_level] }}>#{i + 1}</div>
                    <div className={styles.priorityCrime}>{r.crime_type}</div>
                    <div className={styles.priorityPct} style={{ color: RISK_COLORS[r.risk_level] }}>{r.risk_percentage}%</div>
                    <RiskBadge level={r.risk_level} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bar chart top 10 */}
          {topBar.length > 0 && (
            <div className={styles.barChartSection}>
              <div className={styles.sectionLabel}><i className="fas fa-chart-bar"></i> Crime Risk Distribution (Top 10)</div>
              <div className={styles.barChartList}>
                {topBar.map(r => (
                  <div key={r.crime_type} className={styles.barChartRow}>
                    <span className={styles.barChartLabel}>{r.crime_type}</span>
                    <div className={styles.barChartTrack}>
                      <div className={styles.barChartFill}
                        style={{ width: `${(r.risk_percentage / maxBarPct) * 100}%`, background: RISK_COLORS[r.risk_level] || '#6b7280' }} />
                    </div>
                    <span className={styles.barChartPct} style={{ color: RISK_COLORS[r.risk_level] }}>{r.risk_percentage}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Category breakdown */}
          <div className={styles.categorySection}>
            <div className={styles.sectionLabel}><i className="fas fa-folder-tree"></i> Crime Category Breakdown</div>
            {['Violent Crimes','Property & Financial','Narcotics & Arms','Public Order','Other Offences'].map(cat => {
              const rows = sorted.filter(r => categorize(r.crime_type) === cat);
              if (!rows.length) return null;
              const topR = rows[0];
              return (
                <div key={cat} className={styles.categoryGroup}>
                  <div className={styles.categoryHeader}>
                    {cat} <span className={styles.categoryCount}>{rows.length} types · top: {topR.crime_type} ({topR.risk_percentage}%)</span>
                  </div>
                  <div className={styles.categoryRows}>
                    {rows.slice(0, 5).map(r => (
                      <div key={r.crime_type} className={styles.categoryRow}>
                        <span>{r.crime_type}</span>
                        <RiskBadge level={r.risk_level} pct={r.risk_percentage} />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Table */}
          <div className={styles.tableHeader}>
            <span className={styles.sectionLabel}><i className="fas fa-table"></i> Area Crime Risk Matrix</span>
            <span className={styles.tableCount}>showing {showAll ? sorted.length : Math.min(TABLE_LIMIT, sorted.length)} of {sorted.length}</span>
            <button className={styles.viewAllBtn} onClick={() => setShowAll(p => !p)}>
              {showAll ? <><i className="fas fa-chevron-up"></i> Show Less</> : <><i className="fas fa-expand"></i> View Full Matrix</>}
            </button>
          </div>
          <div className={styles.tableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>#</th>
                  <th onClick={() => thClick('crime_type')} className={styles.thSort}>Crime Type <SortIcon col="crime_type" /></th>
                  <th onClick={() => thClick('risk_level')} className={styles.thSort}>Level <SortIcon col="risk_level" /></th>
                  <th onClick={() => thClick('risk_percentage')} className={styles.thSort}>Risk % <SortIcon col="risk_percentage" /></th>
                  <th onClick={() => thClick('confidence')} className={styles.thSort}>Confidence <SortIcon col="confidence" /></th>
                </tr>
              </thead>
              <tbody>
                {(showAll ? sorted : sorted.slice(0, TABLE_LIMIT)).map((r, i) => (
                  <tr key={r.crime_type}>
                    <td className={styles.rankCell}>#{i + 1}</td>
                    <td><i className="fas fa-tag" style={{ marginRight: 6, opacity: 0.4 }} />{r.crime_type}</td>
                    <td><RiskBadge level={r.risk_level} /></td>
                    <td>
                      <div className={styles.inlineBar}>
                        <div className={styles.inlineBarFill} style={{ width: `${r.risk_percentage}%`, background: RISK_COLORS[r.risk_level] }} />
                        <span>{r.risk_percentage}%</span>
                      </div>
                    </td>
                    <td>{Math.round((r.confidence || 0) * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sorted.length > TABLE_LIMIT && (
            <button className={styles.viewAllBtnBottom} onClick={() => setShowAll(p => !p)}>
              {showAll ? <><i className="fas fa-chevron-up"></i> Show Less</> : <><i className="fas fa-expand"></i> View Full Matrix ({sorted.length} types)</>}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ── Tab 3: Area Safety Intel ──────────────────────────────────────────────────
const AreaSafetyIntel = ({ areas }) => {
  const { settings: systemSettings, loading: settingsLoading } = useSystemSettings();
  const [area, setArea]       = useState('');
  const [months, setMonths]   = useState(3); // will be overridden once settings load
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [error, setError]     = useState('');
  // Sync look-back period from system settings.
  // Runs on first load AND whenever data_retention_days changes (real-time settings updates).
  useEffect(() => {
    if (!settingsLoading) {
      const dm = Math.min(24, Math.max(3, Math.round((systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days) / 30)));
      setMonths(dm);
    }
  }, [settingsLoading, systemSettings?.data_retention_days]);

  // Compute for the dropdown "system default" option label
  const defaultMonths = Math.min(24, Math.max(3, Math.round((systemSettings?.data_retention_days ?? SYSTEM_SETTINGS_DEFAULTS.data_retention_days) / 30)));

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

  const sc = profile
    ? profile.safety_score >= 65 ? '#22c55e' : profile.safety_score >= 50 ? '#eab308' : profile.safety_score >= 35 ? '#f97316' : '#dc2626'
    : '#9ca3af';

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <FormField label="Area">
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map(a => <option key={a.name || a} value={a.name || a}>{a.name || a}</option>)}
          </select>
        </FormField>
        <FormField label="Look-back Period">
          <select value={months} onChange={e => setMonths(Number(e.target.value))}>
            <option value={3}>3 months</option>
            <option value={6}>6 months</option>
            <option value={12}>12 months</option>
            <option value={24}>24 months</option>
            {![3, 6, 12, 24].includes(defaultMonths) && (
              <option value={defaultMonths}>{defaultMonths} months (system default)</option>
            )}
          </select>
        </FormField>
      </div>
      {error && <div className={styles.errMsg}><i className="fas fa-triangle-exclamation"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || !area}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Loading…</> : <><i className="fas fa-shield-halved"></i> Load Area Intel</>}
      </button>

      {profile && (
        <div className={styles.profileCard}>

          {/* Limited data warning */}
          {profile.low_data_warning && (
            <div className={styles.limitedDataWarning}>
              <i className="fas fa-triangle-exclamation"></i> {profile.low_data_warning}
            </div>
          )}

          <div className={styles.profHeader}>
            <div className={styles.profTitle}>
              <i className="fas fa-map-marker-alt"></i> {profile.area}
              <span className={styles.profSub}>
                · {profile.total_crimes?.toLocaleString()} incidents · overall risk profile ({profile.period_months} months)
                {profile.analysis_anchor_date && (
                  <span style={{ fontSize: '0.75rem', opacity: 0.65, marginLeft: 6 }}>
                    (anchored to {profile.analysis_anchor_date})
                  </span>
                )}
              </span>
            </div>
            <div className={styles.profHeaderRight}>
              <MomentumBadge momentum={profile.momentum} />
              {profile.crime_density?.label && <span className={styles.densityTag}>{profile.crime_density.label}</span>}
            </div>
          </div>

          <div className={styles.kpiRow}>
            <KpiCard label="Safety Score" big={`${profile.safety_score}/100`} color={sc} sub={`Grade ${profile.safety_grade}`} />
            <KpiCard label="Risk Level"   val={profile.risk_level}  sub={profile.crime_pressure + ' pressure'} />
            <KpiCard label="City Rank"    big={`#${profile.area_ranking?.rank}`} sub={`Safer than ${profile.safer_than_pct}% of Lahore`} color="#818cf8" />
            <KpiCard
              label="Recent 30 Days"
              big={profile.last_30_days?.toString()}
              sub={profile.last_30_days_ref_date ? `up to ${profile.last_30_days_ref_date}` : 'incidents'}
            />
          </div>

          <div className={styles.visitRow}>
            <VisitBox icon="fa-moon" color="#818cf8" label="Lowest Risk Window"   val={profile.safest_hour_range} />
            <VisitBox icon="fa-sun"  color="#22c55e" label="Recommended Visit"    val={profile.recommended_visit_window} />
            <VisitBox icon="fa-exclamation-triangle" color="#ef4444" label="Higher Risk Window" val={profile.riskiest_hour_range} />
          </div>

          <div className={styles.twoColGrid}>
            {/* Top crimes */}
            <div className={styles.miniCard}>
              <div className={styles.miniTitle}><i className="fas fa-list"></i> Top Crime Types</div>
              {profile.top_crime_types?.slice(0, 5).map((c, i) => (
                <div key={i} className={styles.crimeBarRow}>
                  <span className={styles.crimeRank}>{i + 1}</span>
                  <span className={styles.crimeTypeName}>{c.type}</span>
                  <div className={styles.miniBarTrack}>
                    <div className={styles.miniBarFill} style={{ width: `${Math.max(c.pct, 2)}%`, background: i === 0 ? '#dc2626' : i === 1 ? '#f97316' : '#3b82f6' }} />
                  </div>
                  <span className={styles.crimePct}>{c.pct}%</span>
                </div>
              ))}
            </div>

            {/* Trend */}
            <div className={styles.miniCard}>
              <div className={styles.miniTitle}><i className="fas fa-chart-line"></i> Crime Trend</div>
              <TechRow label={`Recent ${Math.round(profile.period_months / 2)}m`} value={`${profile.trend?.recent_count?.toLocaleString()} (${profile.trend?.recent_monthly_avg}/mo)`} />
              <TechRow label={`Prior ${Math.round(profile.period_months / 2)}m`}  value={`${profile.trend?.older_count?.toLocaleString()} (${profile.trend?.older_monthly_avg}/mo)`} />
              <TechRow label="Change"
                value={`${profile.trend?.direction === 'decreasing' ? '−' : '+'}${profile.trend?.change_pct}%`}
                color={profile.trend?.direction === 'decreasing' ? '#22c55e' : '#dc2626'}
              />
              <div className={styles.dowSummary}>
                <span style={{ color: '#22c55e' }}><i className="fas fa-check-circle"></i> Safest: <strong>{profile.safest_day}</strong>{typeof profile.safest_day_vs_avg === 'number' && ` (${profile.safest_day_vs_avg}%)`}</span>
                <span style={{ color: '#ef4444' }}><i className="fas fa-exclamation-circle"></i> Riskiest: <strong>{profile.riskiest_day}</strong>{typeof profile.riskiest_day_vs_avg === 'number' && ` (+${profile.riskiest_day_vs_avg}%)`}</span>
              </div>
            </div>
          </div>

          {/* Monthly Incident Trend */}
          {profile.monthly_crime_counts?.length > 0 && (
            <div className={styles.monthlyBlock}>
              <div className={styles.sectionLabel}><i className="fas fa-chart-area"></i> Monthly Incident Trend</div>
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

          {/* Locality Crime Hotspots */}
          {profile.sub_area_breakdown?.length > 0 && (
            <div className={styles.localityBlock}>
              <div className={styles.sectionLabel}>
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
                    <tr><th>#</th><th>Sub-Area / Locality</th><th>Incidents</th><th>Share</th><th>Risk</th></tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const maxShare = Math.max(...profile.sub_area_breakdown.map(s => s.pct), 1);
                      return profile.sub_area_breakdown.map((sa, i) => (
                        <tr key={i}>
                          <td className={styles.localityRank}>{i + 1}</td>
                          <td><i className="fas fa-location-dot" style={{ marginRight: 6, opacity: 0.4 }}></i>{sa.name}</td>
                          <td><strong>{sa.count}</strong></td>
                          <td>
                            <div className={styles.localityBarWrap}>
                              <div className={styles.localityBarTrack}>
                                <div className={styles.localityBarFill}
                                  style={{ width: `${(sa.pct / maxShare) * 100}%`, background: RISK_COLORS[sa.risk_level] || '#6b7280' }} />
                              </div>
                              <span>{sa.pct}%</span>
                            </div>
                          </td>
                          <td>
                            <span className={styles.localityRiskTag}
                              style={{ background: (RISK_COLORS[sa.risk_level] || '#6b7280') + '18', color: RISK_COLORS[sa.risk_level] || '#6b7280', border: `1px solid ${(RISK_COLORS[sa.risk_level] || '#6b7280')}30` }}>
                              {sa.risk_level}
                            </span>
                          </td>
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
              <div className={styles.localityDataNote}>
                <i className="fas fa-circle-info"></i> Sub-areas are extracted from Urdu FIR address descriptions (transliterated). Some localities may fall outside traditional area boundaries due to FIR registration practices — only FIRs filed under <strong>{profile.area}</strong> are included.
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          <div className={styles.recommendationsBlock}>
            <div className={styles.sectionLabel}><i className="fas fa-list-check"></i> Recommended Actions</div>
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
                  text: `Prioritise resources on ${profile.top_crime_types[0].type} — ${profile.top_crime_types[0].pct}% of all incidents in this area`,
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

          {/* ── Patrol Strategy ── */}
          {profile.patrol_strategy && Object.keys(profile.patrol_strategy).length > 0 && (
            <div className={styles.patrolBlock}>
              <div className={styles.sectionLabel}><i className="fas fa-shield-halved"></i> Patrol Strategy</div>
              <div className={styles.patrolGrid}>
                <div className={styles.patrolCard} style={{ borderColor: '#dc262635', background: '#dc262608' }}>
                  <div className={styles.patrolLevel} style={{ color: '#dc2626' }}>
                    <i className="fas fa-shield-halved"></i> High Patrol
                  </div>
                  <div className={styles.patrolHours}>{profile.patrol_strategy.high_patrol}</div>
                  <div className={styles.patrolNote}>Peak crime hours — maximum presence required</div>
                </div>
                <div className={styles.patrolCard} style={{ borderColor: '#f9731635', background: '#f9731608' }}>
                  <div className={styles.patrolLevel} style={{ color: '#f97316' }}>
                    <i className="fas fa-eye"></i> Moderate Patrol
                  </div>
                  <div className={styles.patrolHours}>{profile.patrol_strategy.moderate_patrol}</div>
                  <div className={styles.patrolNote}>Adjacent risk window — standard watch</div>
                </div>
                <div className={styles.patrolCard} style={{ borderColor: '#22c55e35', background: '#22c55e08' }}>
                  <div className={styles.patrolLevel} style={{ color: '#22c55e' }}>
                    <i className="fas fa-circle-check"></i> Low Patrol
                  </div>
                  <div className={styles.patrolHours}>{profile.patrol_strategy.low_patrol}</div>
                  <div className={styles.patrolNote}>Historically safest hours</div>
                </div>
              </div>
              <div className={styles.patrolDayRow}>
                <span>
                  <i className="fas fa-calendar-xmark" style={{ color: '#dc2626' }}></i>
                  {' '}Highest Risk Day: <strong>{profile.patrol_strategy.highest_risk_day}</strong>
                </span>
                <span>
                  <i className="fas fa-calendar-check" style={{ color: '#22c55e' }}></i>
                  {' '}Safest Day: <strong>{profile.patrol_strategy.safest_day}</strong>
                </span>
              </div>
            </div>
          )}

          {/* ── FIR Sub-Areas (area_translit localities) ── */}
          {profile.nearby_areas?.length > 0 && (
            <div className={styles.nearbyBlock}>
              <div className={styles.sectionLabel}>
                <i className="fas fa-map-pin"></i> FIR Sub-Areas within {profile.area}
              </div>
              <div className={styles.nearbyList}>
                {profile.nearby_areas.map((nb, i) => (
                  <div key={nb.area} className={styles.nearbyRow}>
                    <span className={styles.nearbyRank}>{i + 1}</span>
                    <span className={styles.nearbyArea}>{nb.area}</span>
                    <div className={styles.nearbyBarWrap}>
                      <div className={styles.nearbyBarTrack}>
                        <div className={styles.nearbyBarFill} style={{
                          width: `${Math.min(100, nb.incident_count / Math.max(...profile.nearby_areas.map(n => n.incident_count), 1) * 100)}%`,
                          background: nb.direction === 'higher' ? '#dc2626' : '#22c55e',
                        }}></div>
                      </div>
                      <span>{nb.incident_count} incidents</span>
                    </div>
                    <span className={styles.nearbyPct} style={{ color: nb.direction === 'higher' ? '#dc2626' : '#9ca3af' }}>
                      {nb.pct_diff}% share
                    </span>
                  </div>
                ))}
              </div>
              <div className={styles.nearbyNote}>
                <i className="fas fa-circle-info"></i> Specific FIR localities (area_translit) recorded under {profile.area} — all-time data
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};

// ── Tab 4: Multi-Area Comparison ──────────────────────────────────────────────
const MAX_AREAS = 5;
const MultiAreaComparison = ({ areas, crimeTypes }) => {
  const [selAreas, setSelAreas] = useState([]);
  const [crimeType, setCrimeType] = useState('');
  const [date, setDate]   = useState(today());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError]   = useState('');

  const toggleArea = a => {
    setSelAreas(prev => prev.includes(a) ? prev.filter(x => x !== a) : prev.length < MAX_AREAS ? [...prev, a] : prev);
  };

  const run = async () => {
    if (selAreas.length < 2) { setError('Select at least 2 areas.'); return; }
    if (!crimeType) { setError('Select a crime type.'); return; }
    setError(''); setLoading(true); setResults([]);
    try {
      const rows = await Promise.all(
        selAreas.map(area =>
          apiService.predictRisk(area, crimeType, date)
            .then(r => r ? { area, ...r } : null)
            .catch(() => ({ area, risk_percentage: null, risk_level: 'N/A', confidence: 0, error: true }))
        )
      );
      setResults(rows.filter(Boolean).sort((a, b) => (b.risk_percentage || 0) - (a.risk_percentage || 0)));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const maxPct = Math.max(...results.map(r => r.risk_percentage || 0), 1);

  return (
    <div className={styles.tabBody}>
      <div className={styles.macForm}>
        <div className={styles.macRow}>
          <FormField label="Crime Type">
            <select value={crimeType} onChange={e => setCrimeType(e.target.value)}>
              <option value="">Select crime type…</option>
              {crimeTypes.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </FormField>
          <FormField label="Date">
            <input type="date" value={date} onChange={e => setDate(e.target.value)} />
          </FormField>
        </div>
        <div className={styles.macAreaPicker}>
          <div className={styles.macAreaLabel}>Select Areas <span className={styles.opt}>(2–{MAX_AREAS})</span></div>
          <div className={styles.macAreaGrid}>
            {(areas || []).map(a => {
              const name = a.name || a;
              const sel  = selAreas.includes(name);
              return (
                <button key={name}
                  className={`${styles.areaChip} ${sel ? styles.areaChipSel : ''}`}
                  onClick={() => toggleArea(name)}
                  disabled={!sel && selAreas.length >= MAX_AREAS}>
                  {sel && <i className="fas fa-check-circle" style={{ marginRight: 5, fontSize: '0.7rem' }}></i>}
                  {name}
                </button>
              );
            })}
          </div>
          {selAreas.length > 0 && <div className={styles.macSelCount}>{selAreas.length}/{MAX_AREAS} areas selected</div>}
        </div>
      </div>

      {error && <div className={styles.errMsg}><i className="fas fa-triangle-exclamation"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || selAreas.length < 2}>
        {loading ? <><i className="fas fa-spinner fa-spin"></i> Comparing {selAreas.length} areas…</> : <><i className="fas fa-chart-bar"></i> Compare Areas</>}
      </button>

      {results.length > 0 && (
        <div className={styles.compBlock}>
          {results.map((r, i) => (
            <div key={r.area} className={styles.compRow}>
              <div className={styles.compRank}>#{i + 1}</div>
              <div className={styles.compArea}>{r.area}</div>
              <RiskBadge level={r.risk_level} />
              <div className={styles.compBarWrap}>
                <div className={styles.compBarTrack}>
                  <div className={styles.compBarFill} style={{
                    width: `${r.risk_percentage != null ? (r.risk_percentage / maxPct) * 100 : 0}%`,
                    background: RISK_COLORS[r.risk_level] || '#6b7280'
                  }} />
                </div>
                <span className={styles.compPct}>{r.risk_percentage ?? '—'}%</span>
              </div>
              <span className={styles.compConf}>{r.confidence != null ? `${Math.round(r.confidence * 100)}% conf` : ''}</span>
            </div>
          ))}

          {/* ── Risk Trend Comparison ── */}
          {results.some(r => r.area_trend) && (
            <div className={styles.trendCompBlock}>
              <div className={styles.sectionLabel}>
                <i className="fas fa-chart-line"></i> Risk Trend (Last 6 Months)
              </div>
              {results.map(r => !r.area_trend ? null : (
                <div key={r.area} className={styles.trendCompRow}>
                  <span className={styles.trendCompArea}>{r.area}</span>
                  <div className={styles.trendCompBarWrap}>
                    <div className={styles.trendCompBarTrack}>
                      <div className={styles.trendCompBarFill} style={{
                        width: `${Math.min(100, Math.abs(r.area_trend.change_pct))}%`,
                        background: r.area_trend.direction === 'increasing' ? '#dc2626'
                                  : r.area_trend.direction === 'decreasing' ? '#22c55e' : '#9ca3af',
                      }}></div>
                    </div>
                  </div>
                  <span className={styles.trendCompPct} style={{
                    color: r.area_trend.direction === 'increasing' ? '#dc2626'
                         : r.area_trend.direction === 'decreasing' ? '#22c55e' : '#9ca3af',
                  }}>
                    <i className={`fas ${r.area_trend.direction === 'increasing' ? 'fa-arrow-trend-up'
                                       : r.area_trend.direction === 'decreasing' ? 'fa-arrow-trend-down' : 'fa-minus'}`}></i>
                    {' '}{r.area_trend.direction === 'increasing' ? '+' : r.area_trend.direction === 'decreasing' ? '\u2212' : ''}{Math.abs(r.area_trend.change_pct)}%
                  </span>
                  <span className={styles.trendCompStatus} style={{
                    background: r.area_trend.direction === 'increasing' ? '#dc262618'
                              : r.area_trend.direction === 'decreasing' ? '#22c55e18' : '#9ca3af18',
                    color: r.area_trend.direction === 'increasing' ? '#dc2626'
                         : r.area_trend.direction === 'decreasing' ? '#22c55e' : '#9ca3af',
                  }}>
                    {r.area_trend.direction === 'increasing' ? 'Rising'
                   : r.area_trend.direction === 'decreasing' ? 'Declining' : 'Stable'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* ── Relative Incident Density ── */}
          {results.some(r => r.area_trend?.recent_count != null) && (
            <div className={styles.trendCompBlock}>
              <div className={styles.sectionLabel}>
                <i className="fas fa-layer-group"></i> Incident Volume (Last 6 Months)
              </div>
              {(() => {
                const maxInc = Math.max(...results.map(r => r.area_trend?.recent_count || 0), 1);
                return results.map(r => (
                  <div key={r.area} className={styles.trendCompRow}>
                    <span className={styles.trendCompArea}>{r.area}</span>
                    <div className={styles.trendCompBarWrap}>
                      <div className={styles.trendCompBarTrack}>
                        <div className={styles.trendCompBarFill} style={{
                          width: `${((r.area_trend?.recent_count || 0) / maxInc) * 100}%`,
                          background: RISK_COLORS[r.risk_level] || '#6b7280',
                        }}></div>
                      </div>
                    </div>
                    <span className={styles.trendCompPct} style={{ color: '#94a3b8' }}>
                      {r.area_trend?.recent_count ?? '—'} incidents
                    </span>
                    <span className={styles.trendCompStatus} style={{ background: 'transparent', color: '#64748b', border: 'none' }}>
                      vs {r.area_trend?.prior_count ?? '—'} prior
                    </span>
                  </div>
                ));
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Tab 5: City Risk Overview ─────────────────────────────────────────────────
const CityRiskOverview = ({ areas, crimeTypes }) => {
  const [crimeType, setCrimeType] = useState('');
  const [date, setDate]   = useState(today());
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError]   = useState('');
  const [sortCol, setSortCol] = useState('risk_percentage');
  const [sortAsc, setSortAsc] = useState(false);
  const [risingCrimes, setRisingCrimes] = useState([]);
  const abortRef = useRef(false);

  // Fetch rising crime types from intelligence dashboard on mount
  useEffect(() => {
    (async () => {
      try {
        const d = await apiService.getIntelligenceDashboard();
        setRisingCrimes(d?.crime_trends?.rising?.slice(0, 5) || []);
      } catch { /* silent */ }
    })();
  }, []);

  const run = async () => {
    if (!crimeType) { setError('Select a crime type.'); return; }
    setError(''); setLoading(true); setResults([]); abortRef.current = false;
    try {
      const rows = await Promise.all(
        (areas || []).map(a => {
          const name = a.name || a;
          return apiService.predictRisk(name, crimeType, date)
            .then(r => r ? { area: name, ...r } : null)
            .catch(() => null);
        })
      );
      if (!abortRef.current) setResults(rows.filter(Boolean));
    } catch (e) { if (!abortRef.current) setError(e.message); }
    finally { if (!abortRef.current) setLoading(false); }
  };

  const sorted = [...results].sort((a, b) => {
    const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0;
    if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    return sortAsc ? va - vb : vb - va;
  });

  const thClick = col => { if (sortCol === col) setSortAsc(p => !p); else { setSortCol(col); setSortAsc(false); } };
  const SortIcon = ({ col }) => sortCol === col
    ? <i className={`fas fa-sort-${sortAsc ? 'up' : 'down'}`} style={{ marginLeft: 4, fontSize: '0.65rem' }} />
    : <i className="fas fa-sort" style={{ marginLeft: 4, fontSize: '0.65rem', opacity: 0.25 }} />;

  const critical = results.filter(r => r.risk_level === 'Critical').length;
  const high = results.filter(r => r.risk_level === 'High').length;
  const lowCount = results.filter(r => r.risk_level === 'Low').length;
  const medCount = results.filter(r => r.risk_level === 'Medium').length;
  const maxPct = Math.max(...results.map(r => r.risk_percentage || 0), 1);

  // City Safety Index: weighted score — Low=100, Medium=60, High=20, Critical=0
  const safetyIndex = results.length > 0
    ? Math.round((lowCount * 100 + medCount * 60 + high * 20 + critical * 0) / results.length)
    : null;
  const safetyStatus = safetyIndex == null ? null
    : safetyIndex >= 70 ? 'Low Risk'
    : safetyIndex >= 50 ? 'Moderate Risk'
    : safetyIndex >= 30 ? 'High Risk' : 'Critical Risk';
  const safetyColor = safetyIndex == null ? '#9ca3af'
    : safetyIndex >= 70 ? '#22c55e'
    : safetyIndex >= 50 ? '#f97316'
    : '#dc2626';

  // Sorted ascending for safest areas
  const safestAreas = [...results]
    .filter(r => r.risk_percentage != null)
    .sort((a, b) => (a.risk_percentage || 0) - (b.risk_percentage || 0))
    .slice(0, 5);

  return (
    <div className={styles.tabBody}>
      <div className={styles.formGrid}>
        <FormField label="Crime Type">
          <select value={crimeType} onChange={e => setCrimeType(e.target.value)}>
            <option value="">Select crime type…</option>
            {crimeTypes.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </FormField>
        <FormField label="Date">
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </FormField>
      </div>
      {error && <div className={styles.errMsg}><i className="fas fa-triangle-exclamation"></i> {error}</div>}
      <button className={styles.runBtn} onClick={run} disabled={loading || !crimeType}>
        {loading
          ? <><i className="fas fa-spinner fa-spin"></i> Scanning all {areas?.length || 0} areas…</>
          : <><i className="fas fa-city"></i> City-Wide Risk Scan</>}
      </button>

      {sorted.length > 0 && (
        <>
          {/* ── City Safety Index ── */}
          <div className={styles.citySafetyRow}>
            <div className={styles.citySafetyCard}>
              <div className={styles.citySafetyTitle}>
                <i className="fas fa-city" style={{ color: safetyColor }}></i> Lahore Safety Index
              </div>
              <div className={styles.citySafetyScore} style={{ color: safetyColor }}>
                {safetyIndex} <span>/100</span>
              </div>
              <div className={styles.citySafetyStatus} style={{
                background: safetyColor + '18', color: safetyColor, border: `1px solid ${safetyColor}35`
              }}>
                {safetyStatus}
              </div>
              <div className={styles.citySafetyNote}>
                Based on {results.length} areas scanned for {crimeType}
              </div>
            </div>

            {/* Risk distribution mini-bars */}
            <div className={styles.cityDistCard}>
              <div className={styles.cityDistTitle}>Risk Distribution</div>
              {[
                { level: 'Critical', count: critical,  color: '#7c3aed' },
                { level: 'High',     count: high,      color: '#dc2626' },
                { level: 'Medium',   count: medCount,  color: '#f97316' },
                { level: 'Low',      count: lowCount,  color: '#22c55e' },
              ].map(l => (
                <div key={l.level} className={styles.cityDistRow}>
                  <span className={styles.cityDistLabel} style={{ color: l.color }}>{l.level}</span>
                  <div className={styles.cityDistTrack}>
                    <div className={styles.cityDistFill} style={{
                      width: `${results.length ? (l.count / results.length) * 100 : 0}%`,
                      background: l.color,
                    }}></div>
                  </div>
                  <span className={styles.cityDistCount}>{l.count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Top 5 Safest + Rising Crimes (side by side) ── */}
          <div className={styles.cityInsightRow}>
            {/* Safest Areas */}
            {safestAreas.length > 0 && (
              <div className={styles.cityInsightCard}>
                <div className={styles.sectionLabel}>
                  <i className="fas fa-shield-halved" style={{ color: '#22c55e' }}></i> Top 5 Safest Areas
                </div>
                {safestAreas.map((r, i) => (
                  <div key={r.area} className={styles.safestRow}>
                    <span className={styles.safestRank}>{i + 1}</span>
                    <span className={styles.safestArea}>{r.area}</span>
                    <span className={styles.safestPct} style={{ color: RISK_COLORS[r.risk_level] || '#22c55e' }}>
                      {r.risk_percentage}%
                    </span>
                    <RiskBadge level={r.risk_level} />
                  </div>
                ))}
              </div>
            )}

            {/* Rising Crime Types */}
            {risingCrimes.length > 0 && (
              <div className={styles.cityInsightCard}>
                <div className={styles.sectionLabel}>
                  <i className="fas fa-arrow-trend-up" style={{ color: '#f97316' }}></i> Fastest Growing Crime Types
                  <span className={styles.cmdSubNote}>city-wide 90-day trend</span>
                </div>
                {risingCrimes.map((r, i) => (
                  <div key={r.crime_type} className={styles.risingRow}>
                    <span className={styles.risingRank}>{i + 1}</span>
                    <span className={styles.risingCrime}>{r.crime_type}</span>
                    <span className={styles.risingPct} style={{ color: '#dc2626' }}>+{r.pct_change}%</span>
                    <span className={styles.risingCounts}>{r.prior}→{r.recent}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.croSummary}>
            {critical > 0 && (
              <div className={styles.croSumCard} style={{ borderColor: '#7c3aed40', background: '#7c3aed10' }}>
                <div className={styles.cscNum} style={{ color: '#7c3aed' }}>{critical}</div>
                <div className={styles.cscLabel}>Critical-Risk Areas</div>
              </div>
            )}
            <div className={styles.croSumCard} style={{ borderColor: '#dc262640', background: '#dc262610' }}>
              <div className={styles.cscNum} style={{ color: '#dc2626' }}>{high}</div>
              <div className={styles.cscLabel}>High-Risk Areas</div>
            </div>
            <div className={styles.croSumCard} style={{ borderColor: '#f9731640', background: '#f9731610' }}>
              <div className={styles.cscNum} style={{ color: '#f97316' }}>{medCount}</div>
              <div className={styles.cscLabel}>Medium-Risk Areas</div>
            </div>
            <div className={styles.croSumCard} style={{ borderColor: '#22c55e40', background: '#22c55e10' }}>
              <div className={styles.cscNum} style={{ color: '#22c55e' }}>{lowCount}</div>
              <div className={styles.cscLabel}>Low-Risk Areas</div>
            </div>
            <div className={styles.croSumCard} style={{ borderColor: '#6366f140', background: '#6366f110' }}>
              <div className={styles.cscNum} style={{ color: '#6366f1' }}>{results.length}</div>
              <div className={styles.cscLabel}>Total Areas Scanned</div>
            </div>
          </div>

          {/* Heatmap-style ranking bars */}
          <div className={styles.croHeatmap}>
            {sorted.slice(0, 15).map((r, i) => (
              <div key={r.area} className={styles.heatRow} title={`${r.area}: ${r.risk_percentage}% ${r.risk_level} risk`}>
                <span className={styles.heatRank}>{i + 1}</span>
                <span className={styles.heatArea}>{r.area}</span>
                <div className={styles.heatBarTrack}>
                  <div className={styles.heatBarFill} style={{
                    width: `${(r.risk_percentage / maxPct) * 100}%`,
                    background: RISK_COLORS[r.risk_level] || '#6b7280'
                  }} />
                </div>
                <span className={styles.heatPct}>{r.risk_percentage}%</span>
                <RiskBadge level={r.risk_level} />
              </div>
            ))}
            {sorted.length > 15 && <div className={styles.moreNote}>+ {sorted.length - 15} more areas — see full table below</div>}
          </div>

          <div className={styles.tableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>#</th>
                  <th onClick={() => thClick('area')} className={styles.thSort}>Area <SortIcon col="area" /></th>
                  <th onClick={() => thClick('risk_level')} className={styles.thSort}>Level <SortIcon col="risk_level" /></th>
                  <th onClick={() => thClick('risk_percentage')} className={styles.thSort}>Risk % <SortIcon col="risk_percentage" /></th>
                  <th onClick={() => thClick('confidence')} className={styles.thSort}>Confidence <SortIcon col="confidence" /></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={r.area}>
                    <td className={styles.rankCell}>#{i + 1}</td>
                    <td><i className="fas fa-map-marker-alt" style={{ marginRight: 7, opacity: 0.4 }} />{r.area}</td>
                    <td><RiskBadge level={r.risk_level} /></td>
                    <td>
                      <div className={styles.inlineBar}>
                        <div className={styles.inlineBarFill} style={{ width: `${r.risk_percentage}%`, background: RISK_COLORS[r.risk_level] }} />
                        <span>{r.risk_percentage}%</span>
                      </div>
                    </td>
                    <td>{Math.round((r.confidence || 0) * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

// ── Shared small components ───────────────────────────────────────────────────
const FormField = ({ label, children }) => (
  <div className={styles.formField}>
    <label>{label}</label>
    {children}
  </div>
);

const TechRow = ({ label, value, color }) => (
  <div className={styles.techRow}>
    <span className={styles.techLabel}>{label}</span>
    <strong style={color ? { color } : {}}>{value}</strong>
  </div>
);

const KpiCard = ({ label, big, val, sub, color }) => (
  <div className={styles.kpiCard}>
    <div className={styles.kpiLabel}>{label}</div>
    {big && <div className={styles.kpiBig} style={color ? { color } : {}}>{big}</div>}
    {val && <div className={styles.kpiVal}>{val}</div>}
    {sub && <div className={styles.kpiSub}>{sub}</div>}
  </div>
);

const VisitBox = ({ icon, color, label, val, type }) => (
  <div className={styles.visitBox} style={{
    borderColor: color + '30',
    background: color + '08'
  }}>
    <i className={`fas ${icon}`} style={{ color, fontSize: '1.1rem', flexShrink: 0 }}></i>
    <div>
      <div className={styles.visitLabel}>{label}</div>
      <strong className={styles.visitVal}>{val}</strong>
    </div>
  </div>
);

// ── Intelligence Command Center ───────────────────────────────────────────────
const DRIFT_COLORS = { High: '#dc2626', Moderate: '#f97316', Low: '#22c55e' };
const SHIFT_ICONS  = { High: 'fa-triangle-exclamation', Moderate: 'fa-circle-exclamation', Low: 'fa-check-circle' };

const IntelCommandCenter = () => {
  const { token } = useAuth();
  const [intel,   setIntel]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState(null);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainMsg(null);
    try {
      const before = await apiService.getModelRetrainStatus(token).catch(() => null);
      const res = await apiService.triggerRetrain(token);
      setRetrainMsg({ ok: true, text: res?.message || 'Retrain launched. Waiting for completion...' });

      const startCount = Number(before?.retrain_count || 0);
      const startTs = Number(before?.last_retrain || 0);
      let completed = false;

      for (let i = 0; i < 80; i += 1) {
        // Poll every 5s for up to ~6m40s
        // eslint-disable-next-line no-await-in-loop
        await new Promise(resolve => setTimeout(resolve, 5000));
        // eslint-disable-next-line no-await-in-loop
        const now = await apiService.getModelRetrainStatus(token).catch(() => null);
        const nowCount = Number(now?.retrain_count || 0);
        const nowTs = Number(now?.last_retrain || 0);
        if (nowCount > startCount || nowTs > startTs) {
          completed = true;
          setRetrainMsg({ ok: true, text: 'Retrain completed successfully. New RF, Poisson, and legacy RF are refreshed.' });
          fetchData();
          break;
        }
      }

      if (!completed) {
        setRetrainMsg({ ok: true, text: 'Retrain is still running in background. Check again shortly.' });
      }
    } catch (e) {
      setRetrainMsg({ ok: false, text: e?.message || 'Failed to trigger retrain.' });
    } finally {
      setRetraining(false);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await apiService.getIntelligenceDashboard();
      setIntel(d);
      setLastFetch(new Date().toLocaleTimeString());
    } catch (e) {
      setError(e?.message || 'Failed to load intelligence data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) return (
    <div className={styles.cmdLoading}>
      <i className="fas fa-satellite-dish fa-spin"></i>
      <span>Loading intelligence snapshot…</span>
    </div>
  );

  if (error) return (
    <div className={styles.cmdError}>
      <i className="fas fa-triangle-exclamation"></i>
      <span>{error}</span>
      <button className={styles.refreshBtn} onClick={fetchData}>Retry</button>
    </div>
  );

  if (!intel) return null;

  const { dataset_health: ds, model_health: mh, drift, crime_trends: ct,
          high_risk_alerts: alerts, forecast_7day: fc } = intel;

  const reliabilityColor = { High: '#22c55e', Moderate: '#f97316', Low: '#dc2626' };
  const driftColor       = DRIFT_COLORS[drift.distribution_shift] || '#9ca3af';
  const reliColor        = reliabilityColor[mh.reliability] || '#9ca3af';
  const maxRising        = Math.max(...(ct.rising.map(r => Math.abs(r.pct_change))), 1);
  const maxFalling       = Math.max(...(ct.falling.map(r => Math.abs(r.pct_change))), 1);

  return (
    <div className={styles.cmdWrap}>

      {/* ── Refresh strip ── */}
      <div className={styles.cmdRefreshRow}>
        <span className={styles.cmdFetchTime}>
          <i className="fas fa-clock"></i> Last updated: {lastFetch || '—'}
        </span>
        <button className={styles.refreshBtn} onClick={fetchData}>
          <i className="fas fa-rotate-right"></i> Refresh
        </button>
      </div>

      {/* ── Hero KPI row ── */}
      <div className={styles.heroKpiRow}>
        <div className={styles.heroKpi}>
          <div className={styles.heroKpiIcon} style={{ background: '#3b82f610', color: '#3b82f6' }}>
            <i className="fas fa-database"></i>
          </div>
          <div>
            <div className={styles.heroKpiVal}>{ds.total_records.toLocaleString()}</div>
            <div className={styles.heroKpiLabel}>Total FIR Records</div>
          </div>
        </div>
        <div className={styles.heroKpi}>
          <div className={styles.heroKpiIcon} style={{ background: '#8b5cf610', color: '#8b5cf6' }}>
            <i className="fas fa-map-location-dot"></i>
          </div>
          <div>
            <div className={styles.heroKpiVal}>{ds.areas_covered}</div>
            <div className={styles.heroKpiLabel}>Areas Covered</div>
          </div>
        </div>
        <div className={styles.heroKpi}>
          <div className={styles.heroKpiIcon} style={{ background: '#f9731610', color: '#f97316' }}>
            <i className="fas fa-tag"></i>
          </div>
          <div>
            <div className={styles.heroKpiVal}>{ds.crime_types_count}</div>
            <div className={styles.heroKpiLabel}>Crime Types</div>
          </div>
        </div>
        <div className={styles.heroKpi}>
          <div className={styles.heroKpiIcon} style={{ background: reliColor + '15', color: reliColor }}>
            <i className="fas fa-microchip"></i>
          </div>
          <div>
            <div className={styles.heroKpiVal} style={{ color: reliColor }}>{mh.reliability}</div>
            <div className={styles.heroKpiLabel}>Model Reliability</div>
          </div>
        </div>
        <div className={styles.heroKpi}>
          <div className={styles.heroKpiIcon} style={{ background: driftColor + '15', color: driftColor }}>
            <i className={`fas ${SHIFT_ICONS[drift.distribution_shift] || 'fa-chart-line'}`}></i>
          </div>
          <div>
            <div className={styles.heroKpiVal} style={{ color: driftColor }}>{drift.distribution_shift}</div>
            <div className={styles.heroKpiLabel}>Distribution Drift</div>
          </div>
        </div>
      </div>

      {/* ── Dataset Health + Model Health ── */}
      <div className={styles.cmdDualRow}>

        {/* Dataset Health */}
        <div className={styles.cmdCard}>
          <div className={styles.cmdCardHeader}>
            <i className="fas fa-database" style={{ color: '#3b82f6' }}></i>
            <span>Dataset Health</span>
          </div>
          <div className={styles.cmdStatGrid}>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal}>{ds.total_records.toLocaleString()}</div>
              <div className={styles.cmdStatLabel}>Total Records</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal}>{ds.areas_covered}</div>
              <div className={styles.cmdStatLabel}>Areas with Data</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal}>{ds.crime_types_count}</div>
              <div className={styles.cmdStatLabel}>Crime Types</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal} style={{ color: ds.unknown_labels > 0 ? '#f97316' : '#22c55e' }}>
                {ds.unknown_labels}
              </div>
              <div className={styles.cmdStatLabel}>Unknown Labels</div>
            </div>
            {ds.records_since_last_train != null && (
              <div className={styles.cmdStat}>
                <div className={styles.cmdStatVal} style={{ color: ds.records_since_last_train > 10 ? '#f97316' : '#22c55e' }}>
                  {ds.records_since_last_train.toLocaleString()}
                </div>
                <div className={styles.cmdStatLabel}>New Since Last Train</div>
              </div>
            )}
          </div>
          {ds.missing_areas_count > 0 && (
            <div className={styles.cmdWarningBox}>
              <i className="fas fa-circle-exclamation"></i>
              <div>
                <strong>{ds.missing_areas_count} crime area{ds.missing_areas_count > 1 ? 's' : ''} missing coordinate data</strong>
                <div className={styles.cmdTagRow}>
                  {ds.missing_areas.map(a => <span key={a} className={styles.cmdTag}>{a}</span>)}
                  {ds.missing_areas_count > 6 && <span className={styles.cmdTagMore}>+{ds.missing_areas_count - 6} more</span>}
                </div>
              </div>
            </div>
          )}
          {ds.sparse_labels.length > 0 && (
            <div className={styles.cmdInfoBox}>
              <i className="fas fa-chart-simple"></i>
              <div>
                <strong>Sparse labels ({"<"}10 records)</strong>
                <div className={styles.cmdTagRow}>
                  {ds.sparse_labels.map(l => <span key={l} className={styles.cmdTag}>{l}</span>)}
                </div>
                <div className={styles.cmdHint}>Collect more data for these crime types to improve model accuracy</div>
              </div>
            </div>
          )}
          {ds.last_update && (
            <div className={styles.cmdMeta}>
              <i className="fas fa-clock"></i> Last record: {new Date(ds.last_update).toLocaleDateString()}
            </div>
          )}
        </div>

        {/* Model Health */}
        <div className={styles.cmdCard}>
          <div className={styles.cmdCardHeader}>
            <i className="fas fa-microchip" style={{ color: '#8b5cf6' }}></i>
            <span>Model Health</span>
          </div>
          <div className={styles.cmdStatGrid}>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal} style={{ color: '#22c55e' }}>{mh.rf_accuracy}%</div>
              <div className={styles.cmdStatLabel}>CV Accuracy</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal} style={{ color: '#3b82f6' }}>{mh.poisson_mae_pct}%</div>
              <div className={styles.cmdStatLabel}>Poisson MAE</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal} style={{ color: reliColor }}>{mh.reliability}</div>
              <div className={styles.cmdStatLabel}>Reliability</div>
            </div>
            <div className={styles.cmdStat}>
              <div className={styles.cmdStatVal} style={{ color: mh.oov_count > 10 ? '#dc2626' : mh.oov_count > 3 ? '#f97316' : '#22c55e' }}>
                {mh.oov_count}
              </div>
              <div className={styles.cmdStatLabel}>OOV Pairs</div>
            </div>
          </div>

          {/* Mini accuracy bars */}
          <div className={styles.cmdBarSection}>
            <div className={styles.cmdBarRow}>
              <div className={styles.cmdBarLabel}>CV Accuracy on generated labels</div>
              <div className={styles.cmdBarTrack}>
                <div className={styles.cmdBarFill} style={{ width: `${mh.rf_accuracy}%`, background: '#22c55e' }}></div>
              </div>
              <div className={styles.cmdBarPct}>{mh.rf_accuracy}%</div>
            </div>
            <div className={styles.cmdBarRow}>
              <div className={styles.cmdBarLabel}>Poisson Error (lower=better)</div>
              <div className={styles.cmdBarTrack}>
                <div className={styles.cmdBarFill} style={{ width: `${mh.poisson_mae_pct}%`, background: '#f97316' }}></div>
              </div>
              <div className={styles.cmdBarPct}>{mh.poisson_mae_pct}%</div>
            </div>
          </div>

          <div className={styles.cmdMetaGrid}>
            <div className={styles.cmdMetaItem}>
              <i className="fas fa-calendar-check"></i> Last trained: <strong>{mh.last_train_date}</strong>
            </div>
            <div className={styles.cmdMetaItem}>
              <i className="fas fa-rotate"></i> Retrain count: <strong>{mh.retrain_count}</strong>
            </div>
            <div className={styles.cmdMetaItem}>
              <i className="fas fa-table"></i> Training size: <strong>{mh.training_size.toLocaleString()}</strong>
            </div>
          </div>

          <div style={{ marginTop: '0.75rem', fontSize: '0.78rem', color: 'rgba(255,255,255,0.55)', lineHeight: 1.5 }}>
            CV Accuracy is computed from 5-fold cross-validation on risk labels generated by the project’s own scoring rules.
            It is useful as an internal training signal, but it is not the same as audited real-world accuracy.
          </div>

          {/* Retrain action */}
          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              onClick={handleRetrain}
              disabled={retraining}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.55rem 1.1rem', borderRadius: '8px', border: 'none',
                background: retraining ? '#4b5563' : '#7c3aed',
                color: '#fff', fontWeight: 600, fontSize: '0.85rem',
                cursor: retraining ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s', width: 'fit-content',
              }}
            >
              <i className={`fas ${retraining ? 'fa-spinner fa-spin' : 'fa-rotate'}`}></i>
              {retraining ? 'Retraining…' : 'Retrain Model Now'}
            </button>
            {retrainMsg && (
              <div style={{
                fontSize: '0.8rem', padding: '0.4rem 0.75rem', borderRadius: '6px',
                background: retrainMsg.ok ? '#22c55e18' : '#dc262618',
                color: retrainMsg.ok ? '#22c55e' : '#dc2626',
                border: `1px solid ${retrainMsg.ok ? '#22c55e40' : '#dc262640'}`,
              }}>
                <i className={`fas ${retrainMsg.ok ? 'fa-check-circle' : 'fa-triangle-exclamation'}`}></i>
                {' '}{retrainMsg.text}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Data Drift Detection ── */}
      <div className={styles.cmdCard}>
        <div className={styles.cmdCardHeader}>
          <i className="fas fa-chart-line" style={{ color: driftColor }}></i>
          <span>Data Drift Detection</span>
          <span className={styles.driftBadge} style={{
            background: driftColor + '18', color: driftColor, border: `1px solid ${driftColor}35`
          }}>
            <i className={`fas ${SHIFT_ICONS[drift.distribution_shift]}`}></i> {drift.distribution_shift} Drift
          </span>
          <span className={styles.driftAction} style={{
            background: drift.recommended_action === 'Retrain Model' ? '#dc262618' : '#22c55e18',
            color: drift.recommended_action === 'Retrain Model' ? '#dc2626' : '#22c55e',
          }}>
            <i className={`fas ${drift.recommended_action === 'Retrain Model' ? 'fa-rotate' : 'fa-eye'}`}></i>
            {drift.recommended_action}
          </span>
        </div>
        <div className={styles.cmdStatGrid}>
          <div className={styles.cmdStat}>
            <div className={styles.cmdStatVal} style={{ color: drift.new_areas_count > 0 ? '#f97316' : '#22c55e' }}>
              {drift.new_areas_count}
            </div>
            <div className={styles.cmdStatLabel}>New Areas (90d)</div>
          </div>
          <div className={styles.cmdStat}>
            <div className={styles.cmdStatVal} style={{ color: drift.new_crime_types_count > 0 ? '#f97316' : '#22c55e' }}>
              {drift.new_crime_types_count}
            </div>
            <div className={styles.cmdStatLabel}>New Crime Types</div>
          </div>
          <div className={styles.cmdStat}>
            <div className={styles.cmdStatVal} style={{ color: driftColor }}>{drift.avg_shift_pct}%</div>
            <div className={styles.cmdStatLabel}>Avg Distribution Shift</div>
          </div>
          <div className={styles.cmdStat}>
            <div className={styles.cmdStatVal} style={{
              color: drift.recommended_action === 'Retrain Model' ? '#dc2626' : '#22c55e'
            }}>
              {drift.recommended_action === 'Retrain Model' ? '⚠' : '✓'}
            </div>
            <div className={styles.cmdStatLabel}>Model Status</div>
          </div>
        </div>
        {drift.new_areas.length > 0 && (
          <div className={styles.cmdInfoBox}>
            <i className="fas fa-map-pin"></i>
            <div>
              <strong>New areas detected in last 90 days:</strong>
              <div className={styles.cmdTagRow}>
                {drift.new_areas.map(a => <span key={a} className={styles.cmdTagNew}>{a}</span>)}
              </div>
            </div>
          </div>
        )}
        {drift.new_crime_types.length > 0 && (
          <div className={styles.cmdInfoBox}>
            <i className="fas fa-tag"></i>
            <div>
              <strong>New crime types detected in last 90 days:</strong>
              <div className={styles.cmdTagRow}>
                {drift.new_crime_types.map(c => <span key={c} className={styles.cmdTagNew}>{c}</span>)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Crime Trends + High-Risk Alerts ── */}
      <div className={styles.cmdDualRow} style={{ alignItems: 'flex-start' }}>

        {/* Crime Trend Intelligence */}
        <div className={styles.cmdCard} style={{ flex: '1.4' }}>
          <div className={styles.cmdCardHeader}>
            <i className="fas fa-arrow-trend-up" style={{ color: '#f97316' }}></i>
            <span>Crime Trend Intelligence</span>
            <span className={styles.cmdSubNote}>90-day vs prior 90-day</span>
          </div>

          {ct.rising.length > 0 && (
            <div className={styles.trendSection}>
              <div className={styles.trendSectionTitle} style={{ color: '#dc2626' }}>
                <i className="fas fa-arrow-trend-up"></i> Rising Trends
              </div>
              {ct.rising.slice(0, 7).map(r => (
                <div key={r.crime_type} className={styles.trendRow}>
                  <div className={styles.trendCrimeType}>{r.crime_type}</div>
                  <div className={styles.trendBarWrap}>
                    <div className={styles.trendBarTrack}>
                      <div className={styles.trendBarFill} style={{
                        width: `${Math.min(100, Math.abs(r.pct_change) / maxRising * 100)}%`,
                        background: r.pct_change >= 40 ? '#dc2626' : r.pct_change >= 20 ? '#f97316' : '#facc15',
                      }}></div>
                    </div>
                  </div>
                  <div className={styles.trendPct} style={{ color: '#dc2626' }}>
                    +{r.pct_change}%
                  </div>
                  <div className={styles.trendCounts}>{r.prior}→{r.recent}</div>
                </div>
              ))}
            </div>
          )}

          {ct.falling.length > 0 && (
            <div className={styles.trendSection}>
              <div className={styles.trendSectionTitle} style={{ color: '#22c55e' }}>
                <i className="fas fa-arrow-trend-down"></i> Falling Trends
              </div>
              {ct.falling.slice(0, 5).map(r => (
                <div key={r.crime_type} className={styles.trendRow}>
                  <div className={styles.trendCrimeType}>{r.crime_type}</div>
                  <div className={styles.trendBarWrap}>
                    <div className={styles.trendBarTrack}>
                      <div className={styles.trendBarFill} style={{
                        width: `${Math.min(100, Math.abs(r.pct_change) / maxFalling * 100)}%`,
                        background: '#22c55e',
                      }}></div>
                    </div>
                  </div>
                  <div className={styles.trendPct} style={{ color: '#22c55e' }}>
                    {r.pct_change}%
                  </div>
                  <div className={styles.trendCounts}>{r.prior}→{r.recent}</div>
                </div>
              ))}
            </div>
          )}

          {ct.rising.length === 0 && ct.falling.length === 0 && (
            <div className={styles.cmdEmpty}>
              <i className="fas fa-check-circle"></i> All crime trends are stable
            </div>
          )}
        </div>

        {/* High-Risk Alerts */}
        <div className={styles.cmdCard} style={{ flex: '1' }}>
          <div className={styles.cmdCardHeader}>
            <i className="fas fa-bell" style={{ color: '#dc2626' }}></i>
            <span>High-Risk Alerts</span>
            <span className={styles.cmdSubNote}>Last 30 days</span>
          </div>
          {alerts.length === 0 ? (
            <div className={styles.cmdEmpty}>
              <i className="fas fa-check-circle" style={{ color: '#22c55e' }}></i> No high-risk alerts
            </div>
          ) : (
            <div className={styles.alertList}>
              {alerts.map((a, i) => (
                <div key={i} className={styles.alertItem} style={{
                  borderLeft: `3px solid ${RISK_COLORS[a.risk_level] || '#9ca3af'}`
                }}>
                  <div className={styles.alertItemTop}>
                    <span className={styles.alertArea}>{a.area}</span>
                    <span className={styles.alertRisk} style={{
                      background: (RISK_COLORS[a.risk_level] || '#9ca3af') + '18',
                      color: RISK_COLORS[a.risk_level] || '#9ca3af',
                    }}>
                      {a.risk_level}
                    </span>
                  </div>
                  <div className={styles.alertCrime}>{a.crime_type}</div>
                  <div className={styles.alertMeta}>
                    <span><i className="fas fa-file-lines"></i> {a.incidents_30d} incidents</span>
                    <span style={{ color: RISK_COLORS[a.risk_level] || '#9ca3af' }}>
                      {a.risk_pct}% risk
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── 7-Day Forecast Timeline ── */}
      {Object.keys(fc).length > 0 && (
        <div className={styles.cmdCard}>
          <div className={styles.cmdCardHeader}>
            <i className="fas fa-calendar-week" style={{ color: '#8b5cf6' }}></i>
            <span>7-Day Risk Forecast</span>
            <span className={styles.cmdSubNote}>Top 5 most active areas · Highest-frequency crime type</span>
          </div>
          <div className={styles.forecastWrap}>
            {/* Header row: day labels */}
            {(() => {
              const areas = Object.keys(fc);
              const firstArea = areas[0];
              const days = fc[firstArea]?.days || [];
              return (
                <>
                  <div className={styles.forecastHeader}>
                    <div className={styles.forecastAreaCol}></div>
                    <div className={styles.forecastCrimeCol}>Top Crime</div>
                    {days.map(d => (
                      <div key={d.day + d.date} className={styles.forecastDayCol}>
                        <div className={styles.forecastDayName}>{d.day}</div>
                        <div className={styles.forecastDayDate}>{d.date}</div>
                      </div>
                    ))}
                  </div>
                  {areas.map(area => (
                    <div key={area} className={styles.forecastRow}>
                      <div className={styles.forecastAreaCol}>{area}</div>
                      <div className={styles.forecastCrimeCol}>{fc[area].crime_type}</div>
                      {(fc[area].days || []).map((d, di) => (
                        <div key={di} className={styles.forecastCell} style={{
                          background: (RISK_COLORS[d.risk] || '#6b7280') + '18',
                          color: RISK_COLORS[d.risk] || '#6b7280',
                          border: `1px solid ${(RISK_COLORS[d.risk] || '#6b7280')}25`,
                        }}>
                          {d.risk}
                        </div>
                      ))}
                    </div>
                  ))}
                </>
              );
            })()}
          </div>
        </div>
      )}

    </div>
  );
};

// ── Main Panel ────────────────────────────────────────────────────────────────
const SuperAdminPredictionPanel = () => {
  const [tab, setTab]                 = useState('command');
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
    { id: 'command', icon: 'fa-satellite-dish', label: 'Command Center'       },
    { id: 'manual',  icon: 'fa-brain',          label: 'Crime Risk Prediction' },
    { id: 'multi',   icon: 'fa-layer-group',    label: 'Area Crime Risk Matrix' },
    { id: 'profile', icon: 'fa-shield-halved',  label: 'Area Risk Intelligence' },
    { id: 'compare', icon: 'fa-chart-bar',      label: 'Area Comparison'        },
    { id: 'city',    icon: 'fa-city',           label: 'City Overview'          },
  ];

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIconWrap}>
            <div className={styles.headerIconBg} />
            <i className="fas fa-brain"></i>
          </div>
          <div>
            <h2 className={styles.headerTitle}>Predictive Intelligence Command Center</h2>
            <p className={styles.headerSub}>
              ML-driven crime forecasting · Poisson + Random Forest ensemble · Lahore Crime Dataset 2024–2025
            </p>
          </div>
        </div>
        <div className={styles.headerMeta}>
          <div className={styles.metaBadge}><i className="fas fa-microchip"></i> Poisson + RF Ensemble</div>
          <div className={styles.metaBadge}><i className="fas fa-database"></i> {totalRecords != null ? totalRecords.toLocaleString() : '—'} FIR Records</div>
          <div className={styles.metaBadge}><i className="fas fa-map"></i> {(areas.length) || '—'} Areas</div>
          <div className={styles.metaBadge}><i className="fas fa-tag"></i> {(crimeTypes.length) || '—'} Crime Types</div>
          {lastTrainDate && (
            <div className={styles.metaBadge} style={{ color: '#a78bfa' }}>
              <i className="fas fa-calendar-check"></i> Last Trained: {lastTrainDate}
            </div>
          )}
        </div>
      </div>

      <div className={styles.tabsRow}>
        {TABS.map(t => (
          <button key={t.id} className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`} onClick={() => setTab(t.id)}>
            <i className={`fas ${t.icon}`}></i>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {loadingMeta ? (
        <div className={styles.metaLoading}><i className="fas fa-spinner fa-spin"></i> Initializing prediction engine…</div>
      ) : (
        <>
          {tab === 'command' && <IntelCommandCenter />}
          {tab === 'manual'  && <ManualPrediction     areas={areas} crimeTypes={crimeTypes} />}
          {tab === 'multi'   && <MultiCrimeScan       areas={areas} crimeTypes={crimeTypes} />}
          {tab === 'profile' && <AreaSafetyIntel      areas={areas} />}
          {tab === 'compare' && <MultiAreaComparison  areas={areas} crimeTypes={crimeTypes} />}
          {tab === 'city'    && <CityRiskOverview     areas={areas} crimeTypes={crimeTypes} />}
        </>
      )}
    </div>
  );
};

export default SuperAdminPredictionPanel;
