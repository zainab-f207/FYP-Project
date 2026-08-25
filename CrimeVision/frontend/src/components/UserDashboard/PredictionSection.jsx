// src/components/PredictionSection/PredictionSection.jsx
import React, { useState, useEffect } from 'react';
import styles from './PredictionSection.module.css';
import apiService from '../../services/apiService';
import PredictionMapView from './PredictionMapView';
import PredictionVisual from './PredictionVisual';

const PredictionSection = ({ onPredictionComplete, initialArea = null }) => {
  const [area, setArea] = useState('');
  const [date, setDate] = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [time, setTime] = useState('');
  const [areas, setAreas] = useState([]); // Array of {name, coordinates}
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [message, setMessage] = useState('');
  const [lastPrediction, setLastPrediction] = useState(null);
  const [showMapView, setShowMapView] = useState(false);
  const [areaProfile, setAreaProfile]       = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        console.log('🔄 Fetching areas and crime types...');
        
        const areasResponse = await apiService.getAreas();
        const crimeTypesResponse = await apiService.getCrimeTypes();

        console.log('📊 Areas response:', areasResponse);
        console.log('📊 Crime types response:', crimeTypesResponse);

        // Handle the API response structure
        // Backend now returns [{name: "Area", coordinates: {...}}, ...]
        const areasData = areasResponse?.areas || areasResponse || [];
        const crimeTypesData = crimeTypesResponse?.crime_types || crimeTypesResponse || [];

        setAreas(areasData);
        setCrimeTypes(crimeTypesData);

        console.log(`✅ Loaded ${areasData.length} areas and ${crimeTypesData.length} crime types`);

      } catch (error) {
        console.error('❌ Error fetching prediction data:', error);
        setMessage('Unable to load areas and crime types. Please check if the backend server is running.');
        
        setAreas([]);
        setCrimeTypes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Handle initialArea selection from dashboard/email links
  useEffect(() => {
    if (initialArea && areas.length > 0) {
      const slugToName = initialArea.replace(/-/g, ' ').toLowerCase();
      const areaObj = areas.find(a => Number.isNaN(Number(a.name)) ? a.name.toLowerCase() === slugToName : false);
      
      // If direct name match fails, try splitting if name has commas or details (though backend usually sends clean names)
      const targetArea = areaObj || areas.find(a => a.name.toLowerCase().includes(slugToName));

      if (targetArea) {
        setArea(targetArea.name);
        // Auto-calculate risk for THE WHOLE AREA (all crime types) if we have the area
        // We'll call calculateRisk with default crimeType empty string which handles general prediction
        calculateRisk(targetArea.name, '', date, '');
        console.log(`✅ Pre-selected area for prediction from email: ${targetArea.name}`);
      }
    }
  }, [initialArea, areas]);

  // Set default date to today
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setDate(today);
  }, []);

  const handleReset = () => {
    setArea('');
    setCrimeType('');
    setTime('');
    const today = new Date().toISOString().split('T')[0];
    setDate(today);
    setLastPrediction(null);
    setMessage('');
    setShowMapView(false);
    setAreaProfile(null);
    setProfileLoading(false);
  };

  const fmtHour = (h) => {
    const ampm = h < 12 ? 'AM' : 'PM';
    return `${h % 12 || 12} ${ampm}`;
  };

  const formatConfidenceLabel = (value) => {
    if (!value) return 'Unknown';
    return String(value).replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
  };

  const handleAreaOverview = async () => {
    if (!area) return;
    setLastPrediction(null);
    setShowMapView(false);
    setAreaProfile(null);
    setProfileLoading(true);
    try {
      const selectedAreaObj = areas.find((a) => (a?.name || a) === area);
      const scopeLat = selectedAreaObj?.coordinates?.lat;
      const scopeLng = selectedAreaObj?.coordinates?.lng;
      const profile = await apiService.getAreaSafetyProfile(area, 12, {
        crimeType: crimeType || undefined,
        date: date || undefined,
        visitTime: time || undefined,
        lat: typeof scopeLat === 'number' ? scopeLat : undefined,
        lng: typeof scopeLng === 'number' ? scopeLng : undefined,
        radiusKm: 1.0,
      });
      setAreaProfile(profile);
    } catch (e) {
      console.error('Area profile error:', e);
    } finally {
      setProfileLoading(false);
    }
  };

  const calculateRisk = async (areaParam = area, crimeTypeParam = crimeType, dateParam = date, timeParam = time) => {
    setPredicting(true);
    setMessage('');
    setLastPrediction(null);
    setShowMapView(false);

    try {
      console.log('📡 Sending prediction request with:', {
        area: areaParam,
        crimeType: crimeTypeParam,
        date: dateParam
      });

      // Get prediction
      const prediction = await apiService.predictRisk(areaParam, crimeTypeParam, dateParam, timeParam || null);
      console.log('📊 Raw prediction response:', prediction);

      // Get coordinates from local state (Real data from DB)
      let coordinates = null;
      const selectedAreaObj = areas.find(a => a.name === areaParam);
      
      if (selectedAreaObj && selectedAreaObj.coordinates) {
        coordinates = selectedAreaObj.coordinates;
        console.log('🗺️ Found coordinates in database:', coordinates);
      } else {
        // Try API as backup (only if not in DB list)
        try {
          console.log('⚠️ Coordinates not in DB, trying external API...');
          const areaCoords = await apiService.getAreaCoordinates(areaParam);
          if (areaCoords && areaCoords.coordinates) {
            coordinates = areaCoords.coordinates;
          }
        } catch (coordError) {
          console.warn('External API coordinate fetch failed:', coordError);
        }
      }

      // Format coordinates if available
      const formattedCoordinates = coordinates ? 
        (Array.isArray(coordinates) ? coordinates : [coordinates.lat, coordinates.lng]) 
        : null;

      const normalizedPrediction = {
        model: prediction?.model || 'unknown',
        model_label: prediction?.model_label || null,
        risk_level: prediction?.risk_level || prediction?.risk || 'Medium',
        risk_percentage: prediction?.risk_percentage !== undefined ? prediction.risk_percentage : 50,
        confidence: prediction?.confidence || 0.8,
        model_confidence: prediction?.model_confidence,
        reliability_basis: prediction?.reliability_basis || null,
        reliability_note: prediction?.reliability_note || null,
        comparability_note: prediction?.comparability_note || null,
        effective_hour: prediction?.effective_hour,
        time_was_provided: prediction?.time_was_provided,
        time_used_by_model: prediction?.time_used_by_model,
        message: prediction?.message || 'Prediction completed',
        // Poisson advisory fields
        probability:           prediction?.probability,
        safest_days_of_week:   prediction?.safest_days_of_week   || [],
        riskiest_day_of_week:  prediction?.riskiest_day_of_week  || null,
        safest_months:         prediction?.safest_months         || [],
        safest_upcoming_dates: prediction?.safest_upcoming_dates || [],
        is_estimated:          prediction?.is_estimated          || false,
        // New insight fields
        riskiest_hours:        prediction?.riskiest_hours        || [],
        hourly_risk_profile:   prediction?.hourly_risk_profile   || null,
        visit_time_comparison: prediction?.visit_time_comparison || [],
        area_trend:            prediction?.area_trend            || null,
        dataset_stats:         prediction?.dataset_stats         || null,
        monthly_crime_counts:  prediction?.monthly_crime_counts  || [],
        time_period:           prediction?.time_period           || null,
      };

      const predictionResult = {
        area: areaParam,
        crimeType: crimeTypeParam,
        date: dateParam,
        model: normalizedPrediction.model,
        modelLabel: normalizedPrediction.model_label,
        riskPercentageLabel: prediction?.risk_percentage_label || null,
        riskLevel: normalizedPrediction.risk_level,
        riskPercentage: normalizedPrediction.risk_percentage,
        confidence: normalizedPrediction.confidence,
        modelConfidence: normalizedPrediction.model_confidence,
        reliabilityBasis: normalizedPrediction.reliability_basis,
        reliabilityNote: normalizedPrediction.reliability_note,
        comparabilityNote: normalizedPrediction.comparability_note,
        effectiveHour: normalizedPrediction.effective_hour,
        timeWasProvided: normalizedPrediction.time_was_provided,
        timeUsedByModel: normalizedPrediction.time_used_by_model,
        coordinates: formattedCoordinates,
        // Advisory fields
        probability:           normalizedPrediction.probability,
        safestDays:            normalizedPrediction.safest_days_of_week,
        riskiestDay:           normalizedPrediction.riskiest_day_of_week,
        safestMonths:          normalizedPrediction.safest_months,
        safestUpcomingDates:   normalizedPrediction.safest_upcoming_dates,
        isEstimated:           normalizedPrediction.is_estimated,
        // New insight fields
        riskiestHours:         normalizedPrediction.riskiest_hours,
        hourlyProfile:         normalizedPrediction.hourly_risk_profile,
        visitComparison:       normalizedPrediction.visit_time_comparison,
        areaTrend:             normalizedPrediction.area_trend,
        datasetStats:          normalizedPrediction.dataset_stats,
        monthlyCrimeStats:     normalizedPrediction.monthly_crime_counts,
        timePeriod:            normalizedPrediction.time_period,
      };

      setLastPrediction(predictionResult);

      if (normalizedPrediction.message) {
        setMessage(normalizedPrediction.message);
      } else {
        const coordMessage = formattedCoordinates ? '' : ' (Map unavailable - no coordinates)';
        setMessage(`Prediction completed: ${normalizedPrediction.risk_level} risk (${normalizedPrediction.risk_percentage}%)${coordMessage}`);
      }

      if (onPredictionComplete) {
        onPredictionComplete(predictionResult);
      }

      console.log('✅ Prediction completed successfully:', predictionResult);

    } catch (error) {
      console.error('❌ Error calculating risk:', error);
      setMessage('Error connecting to prediction service. Please try again.');
    } finally {
      setPredicting(false);
    }
  };

  const formatAreaName = (name) => {
    if (!name) return '';
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const normalizeRiskBandLabel = (value) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized.includes('critical') || normalized.includes('avoid')) return 'Avoid';
    if (normalized.includes('high') || normalized.includes('warning')) return 'Warning';
    if (normalized.includes('moderate') || normalized.includes('medium') || normalized.includes('caution')) return 'Caution';
    if (normalized.includes('low') || normalized.includes('safe')) return 'Safe';
    return 'Caution';
  };

  const handleViewOnMap = () => {
    if (lastPrediction && lastPrediction.coordinates) {
      setShowMapView(true);
    } else {
      setMessage('No coordinates available for this area to display on map.');
    }
  };

  const handleBackToResults = () => {
    setShowMapView(false);
  };

  const renderAreaProfile = () => {
    if (!areaProfile && !profileLoading) return null;
    if (profileLoading && !areaProfile) {
      return (
        <div className={styles.areaProfilePanel}>
          <div className={styles.apLoading}>
            <i className="fas fa-spinner fa-spin"></i> Building safety profile for {formatAreaName(area)}…
          </div>
        </div>
      );
    }
    if (!areaProfile) return null;

    const p = areaProfile;
    const trendDir = p.trend?.direction || 'stable';
    const trendCap = trendDir.charAt(0).toUpperCase() + trendDir.slice(1);
    const normalizedBand = normalizeRiskBandLabel(p.risk_level);
    const riskLevelDisplay = normalizedBand === 'Warning' && trendDir === 'decreasing'
      ? 'Warning (Improving)'
      : normalizedBand;
    const overallSummary = p.overall_summary || null;
    const overallBand = normalizeRiskBandLabel(overallSummary?.risk_level);
    const overallDateRange = overallSummary?.date_range?.start && overallSummary?.date_range?.end
      ? `${overallSummary.date_range.start} to ${overallSummary.date_range.end}`
      : 'Not available';

    return (
      <div className={styles.areaProfilePanel}>
        {/* Header */}
        <div className={styles.apHeader}>
          <div className={styles.apHeaderLeft}>
            <i className={`fas fa-shield-alt ${styles.apShieldIcon}`}></i>
            <div>
              <div className={styles.apTitle}>Area Safety Profile</div>
              <div className={styles.apSubtitle}>
                {formatAreaName(p.area)} · Overall risk view (last {p.period_months} months)
              </div>
              <div className={styles.apSubtitle} style={{ fontSize: '0.78rem', opacity: 0.9 }}>
                Profile window: {p.period_months} months
              </div>
            </div>
          </div>
          <div className={styles.apHeaderMeta}>
            Based on <strong>{p.total_crimes.toLocaleString()}</strong> FIR records ·
            City avg: <strong>{p.city_avg_crimes}</strong>/area ·
            Data Confidence: <strong>{formatConfidenceLabel(p.data_confidence)}</strong>
          </div>
        </div>

        {/* Crime Pressure Bar */}
        <div className={styles.apPressureBar}>
          <div className={styles.apPressureItem}>
            <span className={styles.apPressureLabel}>Crime Pressure</span>
            <span className={`${styles.apPressureValue} ${styles[`apPressure${p.crime_pressure || 'Moderate'}`]}`}>
              {p.crime_pressure || '—'}
            </span>
          </div>
          <div className={styles.apPressureDivider} />
          <div className={styles.apPressureItem}>
            <span className={styles.apPressureLabel}>Crime Density</span>
            <span className={styles.apPressureValue}>{p.crime_density?.label || '—'}</span>
          </div>
          <div className={styles.apPressureDivider} />
          <div className={styles.apPressureItem}>
            <span className={styles.apPressureLabel}>Trend</span>
            <span className={styles.apPressureValue}>
              {trendDir === 'decreasing' ? '↓ Decreasing'
               : trendDir === 'increasing' ? '↑ Increasing'
               : '→ Stable'}
            </span>
          </div>
          <div className={styles.apPressureDivider} />
          <div className={styles.apPressureItem}>
            <span className={styles.apPressureLabel}>Last 30 Days</span>
            <span className={styles.apPressureValue}>{p.last_30_days ?? '—'} incidents</span>
          </div>
          <div className={styles.apPressureDivider} />
          <div className={styles.apPressureItem}>
            <span className={styles.apPressureLabel}>Crime Momentum</span>
            <span className={`${styles.apPressureValue} ${styles[`apMomentum${p.momentum?.direction === 'rising' ? 'Rising' : p.momentum?.direction === 'declining' ? 'Declining' : 'Stable'}`]}`}>
              {p.momentum?.direction === 'rising'    ? '↑ Rising'   :
               p.momentum?.direction === 'declining' ? '↓ Declining' : '→ Stable'}
              {p.momentum?.pct_change > 0 && (
                <span> ({p.momentum.direction === 'declining' ? '-' : '+'}{p.momentum.pct_change}%)</span>
              )}
              <span className={styles.apMomentumSub}> last 90 days</span>
            </span>
          </div>
        </div>

        {/* Main grid: score + top crimes */}
        <div className={styles.apMainGrid}>
          <div className={styles.apScoreCard}>
            <div className={styles.apScoreLabel}>Safety Score</div>
            <div className={styles.apScoreNumber}>
              <span className={styles.apScoreVal}>{p.safety_score}</span>
              <span className={styles.apScoreDenom}>&thinsp;/ 100</span>
            </div>
            <div className={styles.apScoreBarTrack}>
              <div className={styles.apScoreBarFill} style={{
                width: `${p.safety_score}%`,
                background: p.safety_score >= 65 ? '#22c55e'
                          : p.safety_score >= 50 ? '#eab308'
                          : p.safety_score >= 35 ? '#f97316'
                          : '#dc2626'
              }} />
            </div>
            <div className={`${styles.apRiskLevelBadge} ${styles[`apRisk${p.safety_grade}`]}`}>
              {riskLevelDisplay}
            </div>
            <div className={styles.apRankingText}>
              City Rank: <strong>#{p.area_ranking?.rank} / {p.area_ranking?.total_areas}</strong>
            </div>
            <div className={styles.apSaferThan}>
              Safer than <strong>{p.safer_than_pct}%</strong> of Lahore
            </div>
            {overallSummary && (
              <div className={styles.apVisitTimes} style={{ marginTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.12)', paddingTop: '0.65rem' }}>
                <div className={styles.apVisitRow} style={{ fontWeight: 700 }}>
                  <i className="fas fa-globe-asia" style={{ color: '#60a5fa' }}></i>
                  <span>Overall (Complete History)</span>
                </div>
                <div className={styles.apVisitRow}>
                  <i className="fas fa-shield-alt" style={{ color: '#22c55e' }}></i>
                  <span>
                    Safety: <strong>{overallSummary.safety_score}</strong>/100 ·
                    Level: <strong>{overallBand}</strong>
                  </span>
                </div>
                <div className={styles.apVisitRow}>
                  <i className="fas fa-database" style={{ color: '#f59e0b' }}></i>
                  <span>
                    Records: <strong>{(overallSummary.total_crimes ?? 0).toLocaleString()}</strong> ·
                    Range: <strong>{overallDateRange}</strong>
                  </span>
                </div>
              </div>
            )}
            {p.safest_hour_range && (
              <div className={styles.apVisitTimes}>
                <div className={styles.apVisitRow}>
                  <i className="fas fa-moon" style={{color:'#818cf8'}}></i>
                  <span>Lowest Risk Window: <strong>{p.safest_hour_range}</strong></span>
                </div>
                {p.recommended_visit_window && p.recommended_visit_window !== p.safest_hour_range && (
                  <div className={styles.apVisitRow}>
                    <i className="fas fa-sun" style={{color:'#22c55e'}}></i>
                    <span>Recommended Visit Time: <strong>{p.recommended_visit_window}</strong></span>
                  </div>
                )}
                <div className={styles.apVisitRow}>
                  <i className="fas fa-exclamation-triangle" style={{color:'#ef4444'}}></i>
                  <span>Higher Risk Window: <strong>{p.riskiest_hour_range}</strong></span>
                </div>
              </div>
            )}
          </div>

          <div className={styles.apCrimesCard}>
            <div className={styles.apCardTitle}><i className="fas fa-list"></i> Top Crime Types</div>
            {p.top_crime_types?.slice(0, 5).map((c, i) => (
              <div key={i} className={styles.apCrimeRow}>
                <span className={styles.apCrimeRank}>{i + 1}</span>
                <span className={styles.apCrimeType}>{c.display_type || c.type}</span>
                <div className={styles.apCrimeBarTrack}>
                  <div
                    className={styles.apCrimeBarFill}
                    style={{
                      width: `${Math.max(c.pct, 2)}%`,
                      background: i === 0 ? '#dc2626' : i === 1 ? '#f97316' : i === 2 ? '#eab308' : '#6b7280'
                    }}
                  />
                </div>
                <span className={styles.apCrimePct}>{c.pct}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* 24-hour pattern */}
        <div className={styles.apSection}>
          <div className={styles.apSectionTitle}>
            <i className="fas fa-clock"></i> 24-Hour Crime Pattern
          </div>
          <div className={styles.apHourlyChart}>
            {p.hourly_distribution?.map((h) => {
              const isRiskiest = p.riskiest_hours?.includes(h.hour);
              const isSafest   = p.safest_hours?.includes(h.hour);
              const barColor   = isRiskiest ? '#dc2626' : isSafest ? '#16a34a' : h.pct > 70 ? '#f97316' : '#3b82f6';
              return (
                <div key={h.hour} className={styles.apHourCol}
                  title={`${fmtHour(h.hour)}: ${h.count} incidents`}>
                  <div className={styles.apHourBarTrack}>
                    <div
                      className={styles.apHourBarFill}
                      style={{ height: `${Math.max(h.pct, 2)}%`, background: barColor }}
                    />
                  </div>
                  {h.hour % 6 === 0 && (
                    <div className={styles.apHourLabel}>{fmtHour(h.hour)}</div>
                  )}
                </div>
              );
            })}
          </div>
          <div className={styles.apHourlyLegend}>
            <span className={styles.apLegendSafe}>
              <i className="fas fa-check-circle"></i>
              Lowest Risk Window: {p.safest_hour_range || p.safest_hours?.map(h => fmtHour(h)).join(', ')}
            </span>
            <span className={styles.apLegendRisk}>
              <i className="fas fa-exclamation-circle"></i>
              Higher Risk Window: {p.riskiest_hour_range || p.riskiest_hours?.map(h => fmtHour(h)).join(', ')}
            </span>
          </div>
        </div>

        {/* Day of week + Trend */}
        <div className={styles.apBottomGrid}>
          <div className={styles.apSection}>
            <div className={styles.apSectionTitle}>
              <i className="fas fa-calendar-week"></i> Day of Week
            </div>
            <div className={styles.apDowChart}>
              {p.day_of_week?.map((d, i) => (
                <div key={i} className={styles.apDowCol}
                  title={`${d.day}: ${d.count} incidents`}>
                  <div className={styles.apDowBarTrack}>
                    <div
                      className={styles.apDowBarFill}
                      style={{
                        height: `${Math.max(d.pct, 4)}%`,
                        background: d.day === p.riskiest_day ? '#dc2626'
                                  : d.day === p.safest_day   ? '#16a34a'
                                  : '#3b82f6'
                      }}
                    />
                  </div>
                  <div className={styles.apDowLabel}>{d.day?.slice(0, 3)}</div>
                </div>
              ))}
            </div>
            <div className={styles.apDowSummary}>
              <span>
                <i className="fas fa-check-circle" style={{color:'#16a34a'}}></i>
                Safest: <strong>{p.safest_day}</strong>
                {typeof p.safest_day_vs_avg === 'number' && (
                  <span className={styles.apDowVs} style={{color:'#16a34a'}}>
                    {' '}({p.safest_day_vs_avg}% vs avg)
                  </span>
                )}
              </span>
              <span>
                <i className="fas fa-exclamation-circle" style={{color:'#dc2626'}}></i>
                Riskiest: <strong>{p.riskiest_day}</strong>
                {typeof p.riskiest_day_vs_avg === 'number' && (
                  <span className={styles.apDowVs} style={{color:'#dc2626'}}>
                    {' '}(+{p.riskiest_day_vs_avg}% vs avg)
                  </span>
                )}
              </span>
            </div>
          </div>

          <div className={styles.apSection}>
            <div className={styles.apSectionTitle}>
              <i className="fas fa-chart-line"></i> Crime Trend
            </div>
            <div className={`${styles.apTrendBadge} ${styles[`apTrend${trendCap}`]}`}>
              {trendDir === 'increasing' && <>📈 Crime <strong>up {p.trend.change_pct}%</strong> vs prior period</>}
              {trendDir === 'decreasing' && <>📉 Crime <strong>down {p.trend.change_pct}%</strong> vs prior period</>}
              {trendDir === 'stable'     && <>➡️ Crime is <strong>stable</strong> vs prior period</>}
            </div>
            <div className={styles.apTrendCounts}>
              <div className={styles.apTcRow}>
                <span>Recent {Math.round(p.period_months / 2)} months:</span>
                <strong>{p.trend?.recent_count?.toLocaleString() ?? '—'} incidents</strong>
              </div>
              {typeof p.trend?.recent_monthly_avg === 'number' && (
                <div className={`${styles.apTcRow} ${styles.apTcSub}`}>
                  <span>Monthly avg:</span>
                  <strong>{p.trend.recent_monthly_avg} / month</strong>
                </div>
              )}
              <div className={styles.apTcRow}>
                <span>Previous {Math.round(p.period_months / 2)} months:</span>
                <strong>{p.trend?.older_count?.toLocaleString() ?? '—'} incidents</strong>
              </div>
              {typeof p.trend?.older_monthly_avg === 'number' && (
                <div className={`${styles.apTcRow} ${styles.apTcSub}`}>
                  <span>Monthly avg:</span>
                  <strong>{p.trend.older_monthly_avg} / month</strong>
                </div>
              )}
              {typeof p.trend?.older_count === 'number' && p.trend.older_count > 0 && (
                <div className={styles.apTcRow}>
                  <span>Change:</span>
                  <strong style={{color: trendDir === 'decreasing' ? '#22c55e' : trendDir === 'increasing' ? '#dc2626' : '#9ca3af'}}>
                    {trendDir === 'decreasing' ? '−' : trendDir === 'increasing' ? '+' : '±'}{p.trend.change_pct}%
                  </strong>
                </div>
              )}
            </div>
          </div>
        </div>
        {/* Safety Insights */}
        <div className={`${styles.apSection} ${styles.apInsightsSection}`}>
          <div className={styles.apSectionTitle}>
            <i className="fas fa-lightbulb"></i> Safety Insights
          </div>
          <ul className={styles.apInsightList}>
            {p.riskiest_hour_range && (
              <li>
                <i className="fas fa-exclamation-circle" style={{color:'#f97316'}}></i>
                Crime activity peaks during <strong>{p.riskiest_hour_range}</strong>
              </li>
            )}
            {p.riskiest_day && (
              <li>
                <i className="fas fa-calendar-times" style={{color:'#f97316'}}></i>
                <strong>{p.riskiest_day}s</strong> historically show higher crime frequency
                {typeof p.riskiest_day_vs_avg === 'number' && (
                  <> (+{p.riskiest_day_vs_avg}% above weekly average)</>
                )}
              </li>
            )}
            {p.top_crime_types?.[0] && (
              <li>
                <i className="fas fa-tag" style={{color:'#f97316'}}></i>
                <strong>{p.top_crime_types[0].display_type || p.top_crime_types[0].type}</strong> is the most reported incident ({p.top_crime_types[0].pct}%)
              </li>
            )}
            <li>
              <i className="fas fa-sun" style={{color:'#22c55e'}}></i>
              Visits during <strong>{p.recommended_visit_window || '10 AM–5 PM'}</strong> tend to be relatively safer
            </li>
            {p.trend?.direction === 'decreasing' && (
              <li>
                <i className="fas fa-chart-line" style={{color:'#22c55e'}}></i>
                Crime is trending <strong>down {p.trend.change_pct}%</strong> compared to the prior period
              </li>
            )}
            {p.trend?.direction === 'increasing' && (
              <li>
                <i className="fas fa-chart-line" style={{color:'#dc2626'}}></i>
                Crime is trending <strong>up {p.trend.change_pct}%</strong> — exercise extra caution
              </li>
            )}
          </ul>
        </div>
      </div>
    );
  };

  const renderPredictionResult = () => {
    if (!lastPrediction) return null;

    const RISK_INFO = {
      Low:    { description: "Historical data indicates a relatively low likelihood of this crime occurring in the selected area and time.", precautions: ["Stay aware of your surroundings.", "Keep your valuables secure.", "Report any suspicious activity.", "Follow normal safety precautions."], color: "#22c55e", icon: "✅" },
      Medium: { description: "Historical data suggests a moderate likelihood of this type of crime occurring in the selected area and time.", precautions: ["Stay in well-lit areas after dark.", "Avoid walking alone at night.", "Keep valuables out of sight.", "Remain aware of your surroundings.", "Use trusted transportation services."], color: "#f59e0b", icon: "⚠️" },
      High:   { description: "Historical data indicates a higher likelihood of this type of crime occurring in this area during similar time periods.", precautions: ["Avoid unnecessary travel after dark.", "Travel in groups if possible.", "Keep emergency contacts handy.", "Stay alert and avoid distractions.", "Consider alternative routes if possible."], color: "#dc2626", icon: "🚨" },
    };
    const PERIOD_ICONS = { Morning: '🌅', Afternoon: '☀️', Evening: '🌆', Night: '🌙' };

    const riskInfo      = RISK_INFO[lastPrediction.riskLevel] || RISK_INFO.Medium;
    const hasCoords     = !!lastPrediction.coordinates;
    const riskPct       = parseFloat(lastPrediction.riskPercentage) || 0;
    const riskColor     = riskPct < 20 ? '#22c55e' : riskPct < 60 ? '#f59e0b' : '#dc2626';
    const reliabilityPct = Math.round((parseFloat(lastPrediction.confidence) || 0) * 100);
    const reliabilityBasis = lastPrediction.reliabilityBasis || 'generic';
    const reliabilityLabel = reliabilityBasis === 'data_volume'
      ? 'Data Coverage (Area × Crime)'
      : reliabilityBasis === 'legacy_model_prob'
        ? 'Model Confidence (Legacy)'
        : reliabilityBasis === 'fallback_default'
          ? 'Fallback Reliability'
          : 'Prediction Reliability';
    const reliabilityNote = lastPrediction.reliabilityNote
      || (reliabilityBasis === 'data_volume'
        ? 'Coverage score based on historical FIR volume for this area and crime type.'
        : 'Confidence is estimated from historical model behavior.');
    const isRFComposite = lastPrediction.model === 'rf_composite';
    const metricLabel = lastPrediction.riskPercentageLabel || (isRFComposite ? 'RISK INDEX' : 'EST. RISK');
    const r = 44, circ  = +(2 * Math.PI * r).toFixed(1);
    const dashOff       = +(circ - (Math.min(riskPct, 100) / 100) * circ).toFixed(1);
    const fmtTime       = (t) => { if (!t) return ''; const [h, m] = t.split(':').map(Number); if (isNaN(h)) return t; return `${h % 12 || 12}:${String(m || 0).padStart(2,'0')} ${h >= 12 ? 'PM' : 'AM'}`; };

    return (
      <div className={styles.predictionResult}>

        {/* ── Header row ── */}
        <div className={styles.resultHeader}>
          <h4>Prediction Result</h4>
          <div className={styles.resultActions}>
            {hasCoords
              ? <button className={styles.mapViewBtn} onClick={handleViewOnMap}><i className="fas fa-map-marked-alt"></i> View on Map</button>
              : <button className={`${styles.mapViewBtn} ${styles.disabled}`} disabled title="No geographic data"><i className="fas fa-map-marked-alt"></i> Map Unavailable</button>
            }
            <div className={styles.riskBadge} style={{ backgroundColor: riskColor }}>{riskInfo.icon} {lastPrediction.riskLevel}</div>
          </div>
        </div>

        {/* ── Main metric row: SVG ring + stats ── */}
        <div className={styles.metricRow}>
          {/* Ring gauge */}
          <div className={styles.ringWrap}>
            <svg width="140" height="140" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="11"/>
              <circle cx="60" cy="60" r={r} fill="none" stroke={riskColor} strokeWidth="11"
                strokeLinecap="round"
                strokeDasharray={circ} strokeDashoffset={dashOff}
                transform="rotate(-90 60 60)"
                style={{ transition: 'stroke-dashoffset 1.2s ease, stroke 0.4s' }}
              />
              <text x="60" y="54" textAnchor="middle" fontSize="21" fill="white" fontWeight="800">{riskPct}%</text>
              <text x="60" y="69" textAnchor="middle" fontSize="7.5" fill="rgba(255,255,255,0.42)" fontWeight="600" letterSpacing="1.2">{metricLabel}</text>
            </svg>
            <div className={styles.ringMeta}>
              <div className={styles.ringRiskLevel} style={{ color: riskColor }}>{lastPrediction.riskLevel}</div>
              <div className={styles.ringAreaName}>{formatAreaName(lastPrediction.area)}</div>
              {lastPrediction.areaTrend && (
                <div className={`${styles.trendBadge} ${
                  lastPrediction.areaTrend.direction === 'decreasing' ? styles.trendDecreasing :
                  lastPrediction.areaTrend.direction === 'increasing' ? styles.trendIncreasing : styles.trendStable
                }`}>
                  {lastPrediction.areaTrend.direction === 'decreasing' ? '↓' : lastPrediction.areaTrend.direction === 'increasing' ? '↑' : '→'}
                  {' '}Trend (12 mo): {lastPrediction.areaTrend.direction}
                </div>
              )}
            </div>
          </div>

          {/* Stats column */}
          <div className={styles.statsCol}>
            <div className={styles.statBlock}>
              <div className={styles.statHeader}>
                <span className={styles.statLabel}>{reliabilityLabel}</span>
                <span className={styles.statValue} style={{ color: riskColor }}>{reliabilityPct}%</span>
              </div>
              <div className={styles.statBarWrap}>
                <div className={styles.statBar} style={{ width: `${reliabilityPct}%`, background: riskColor }}/>
              </div>
              <p className={styles.statNote}>{reliabilityNote}</p>
              {isRFComposite && (
                <p className={styles.statNote}>
                  RF result is a composite risk score, not a direct probability of an incident.
                </p>
              )}
              {lastPrediction.comparabilityNote && (
                <p className={styles.statNote}>{lastPrediction.comparabilityNote}</p>
              )}
              {isRFComposite && lastPrediction.modelConfidence != null && (
                <p className={styles.statNote}>RF Class Confidence: {Math.round(lastPrediction.modelConfidence * 100)}%</p>
              )}
            </div>

            <div className={styles.contextChips}>
              <span className={styles.contextChip}><i className="fas fa-shield-alt"></i>{lastPrediction.crimeType}</span>
              <span className={styles.contextChip}><i className="fas fa-calendar"></i>{new Date(lastPrediction.date + 'T12:00:00').toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' })}</span>
              {time && <span className={styles.contextChip}><i className="fas fa-clock"></i>{fmtTime(time)}</span>}
            </div>

            {lastPrediction.datasetStats && (
              <div className={styles.datasetBadge}>
                <i className="fas fa-database"></i>
                <span>Based on <strong>{lastPrediction.datasetStats.total_records?.toLocaleString()}</strong> FIRs ({lastPrediction.datasetStats.date_range})</span>
              </div>
            )}

            {!hasCoords && <div className={styles.coordinateWarning}><i className="fas fa-exclamation-triangle"></i> No geographic data available</div>}
          </div>
        </div>

        {/* ── Selected Visit Time Banner ── */}
        {time && lastPrediction.timePeriod && (() => {
          const PERIOD_HOURS   = { Morning: '6 AM – 12 PM', Afternoon: '12 PM – 6 PM', Evening: '6 PM – 12 AM', Night: '12 AM – 6 AM' };
          const PERIOD_CONTEXT = { Morning: 'morning', Afternoon: 'afternoon', Evening: 'evening', Night: 'late-night' };
          const periodShare    = lastPrediction.hourlyProfile?.[lastPrediction.timePeriod];
          const activityLevel  = periodShare == null ? '' : periodShare < 20 ? 'lower-activity' : periodShare < 40 ? 'moderate-activity' : 'higher-activity';
          return (
            <>
                    {/* Visit time advisory for legacy model */}
                    {lastPrediction.timeWasProvided && lastPrediction.timeUsedByModel === false && (
                      <div className={styles.visitTimeAdvisory}>
                        <i className="fas fa-circle-info"></i> Selected visit time was provided but not used by this legacy model — it is advisory only.
                      </div>
                    )}

                    {/* Visit time risk card */}
                    <div className={styles.visitTimeRiskCard} style={{ borderLeftColor: riskColor }}>
                <div className={styles.visitTimeRiskHeader}>
                  <span className={styles.visitTimeRiskIconBox}>{PERIOD_ICONS[lastPrediction.timePeriod]}</span>
                  <div className={styles.visitTimeRiskTitleCol}>
                    <span className={styles.visitTimeRiskLabel}>Your Visit Time Risk</span>
                    <span className={styles.visitTimeRiskSub}>{lastPrediction.timePeriod} · {fmtTime(time)}</span>
                  </div>
                  <span className={styles.visitTimeRiskPct} style={{ color: riskColor }}>{riskPct}%</span>
                </div>
                <p className={styles.visitTimeRiskDesc}>
                  This estimate reflects historical crime patterns observed during{' '}
                  <strong>{PERIOD_CONTEXT[lastPrediction.timePeriod]}</strong> hours in this area.
                  {periodShare != null && (
                    <> Historically, <strong>{periodShare}%</strong> of daily crime risk falls during {lastPrediction.timePeriod.toLowerCase()} hours ({PERIOD_HOURS[lastPrediction.timePeriod]}).</>
                  )}
                </p>
              </div>

              {/* Hourly risk context */}
              {periodShare != null && (
                <div className={styles.hourlyRiskContext}>
                  <div className={styles.hourlyRiskContextTitle}><i className="fas fa-clock"></i> Hourly Risk Context</div>
                  <p className={styles.hourlyRiskContextBody}>
                    <strong>{fmtTime(time)}</strong> falls within the <strong>{lastPrediction.timePeriod}</strong> window ({PERIOD_HOURS[lastPrediction.timePeriod]}), a{' '}
                    <strong>{activityLevel}</strong> period based on historical FIR records.
                  </p>
                  <div className={styles.hourlyRiskContextStat}>
                    <span className={styles.hourlyRiskContextStatLabel}>Average crime share · {lastPrediction.timePeriod} ({PERIOD_HOURS[lastPrediction.timePeriod]})</span>
                    <div className={styles.hourlyRiskContextBarRow}>
                      <div className={styles.hourlyRiskContextBarTrack}>
                        <div className={styles.hourlyRiskContextBarFill} style={{ width: `${periodShare}%`, background: riskColor }}/>
                      </div>
                      <span className={styles.hourlyRiskContextPct} style={{ color: riskColor }}>{periodShare}%</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          );
        })()}

        {/* ── Risk Interpretation ── */}
        <div className={styles.riskInterpBlock}>
          <div className={styles.riskInterpTitle}><i className="fas fa-info-circle"></i> Risk Interpretation</div>
          <p className={styles.riskInterpText}>{riskInfo.description}</p>
        </div>

        {/* ── Time of Day Profile (with active period highlight) ── */}
        {lastPrediction.hourlyProfile && (
          <div className={styles.insightsCard}>
            <div className={styles.insightsCardTitle}>
              <i className="fas fa-chart-bar"></i> Risk by Time of Day
              {time && lastPrediction.timePeriod && (
                <span className={styles.insightsSubtag}>{PERIOD_ICONS[lastPrediction.timePeriod]} {lastPrediction.timePeriod} selected</span>
              )}
            </div>
            <div className={styles.periodBars}>
              {['Morning','Afternoon','Evening','Night'].map(period => {
                const pct = lastPrediction.hourlyProfile[period] || 0;
                const maxPct = Math.max(...Object.values(lastPrediction.hourlyProfile).filter(v => v > 0), 0.01);
                const barPct = (pct / maxPct) * 100;
                const color = pct < 20 ? '#22c55e' : pct < 60 ? '#f59e0b' : '#dc2626';
                const isActive = !!(time && lastPrediction.timePeriod === period);
                return (
                  <div key={period} className={`${styles.periodBarRow} ${isActive ? styles.periodBarRowActive : ''}`}>
                    <span className={styles.periodIcon}>{PERIOD_ICONS[period]}</span>
                    <span className={styles.periodName}>{period}</span>
                    <div className={styles.periodBarTrack}>
                      <div className={styles.periodBarFill} style={{ width: `${barPct}%`, background: color }}/>
                    </div>
                    <span className={styles.periodPct} style={{ color }}>{pct.toFixed(2)}%</span>
                    {isActive && <span className={styles.activeTag}>← now</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Visit Time Comparison (with active cell) ── */}
        {lastPrediction.visitComparison?.length > 0 && (
          <div className={styles.insightsCard}>
            <div className={styles.insightsCardTitle}>
              <i className="fas fa-clock"></i> Risk Comparison by Visit Time
            </div>
            <div className={styles.visitGrid}>
              {lastPrediction.visitComparison.map((v, i) => {
                const color = v.risk_percentage < 20 ? '#22c55e' : v.risk_percentage < 60 ? '#f59e0b' : '#dc2626';
                const isActive = !!(time && lastPrediction.timePeriod === v.period);
                return (
                  <div key={i} className={`${styles.visitCell} ${isActive ? styles.visitCellActive : ''}`} style={{ borderLeftColor: color }}>
                    <span className={styles.visitTime}>{v.label}</span>
                    <span className={styles.visitPeriod}>{PERIOD_ICONS[v.period]} {v.period}</span>
                    <span className={styles.visitPct} style={{ color }}>{v.risk_percentage.toFixed(2)}%</span>
                    <div className={styles.visitBarWrap}>
                      <div className={styles.visitBar} style={{ width: `${Math.min(v.risk_percentage, 100)}%`, background: color }}/>
                    </div>
                    {isActive && <span className={styles.visitActiveTag}>← your visit</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Safety Advisory ── */}
        {(lastPrediction.safestDays?.length > 0 || lastPrediction.safestUpcomingDates?.length > 0) && (
          <div className={styles.safetyAdvisory}>
            <h5><i className="fas fa-calendar-check"></i> When Is It Safest?</h5>
            {lastPrediction.safestDays?.length > 0 && (
              <div className={styles.advisoryRow}>
                <span className={styles.advisoryLabel}><i className="fas fa-thumbs-up"></i> Safest days:</span>
                <span className={styles.advisoryValue}>{lastPrediction.safestDays.join(', ')}</span>
              </div>
            )}
            {lastPrediction.riskiestDay && (
              <div className={styles.advisoryRow}>
                <span className={styles.advisoryLabel}><i className="fas fa-exclamation-triangle"></i> Higher risk historically:</span>
                <span className={styles.advisoryValueWarn}>{lastPrediction.riskiestDay}</span>
              </div>
            )}
            {lastPrediction.safestMonths?.length > 0 && (
              <div className={styles.advisoryRow}>
                <span className={styles.advisoryLabel}><i className="fas fa-sun"></i> Safest months:</span>
                <span className={styles.advisoryValue}>{lastPrediction.safestMonths.join(', ')}</span>
              </div>
            )}
            {lastPrediction.safestUpcomingDates?.length > 0 && (
              <div className={styles.advisoryUpcoming}>
                <p className={styles.advisoryUpcomingLabel}><i className="fas fa-calendar-alt"></i> Lowest estimated risk dates within the next 30 days:</p>
                <div className={styles.upcomingDates}>
                  {lastPrediction.safestUpcomingDates.map((d, i) => (
                    <div key={i} className={styles.upcomingDateCard}>
                      <span className={styles.upcomingDay}>{d.day}</span>
                      <span className={styles.upcomingDate}>{d.date}</span>
                      <span className={styles.upcomingPct} style={{ color: d.risk_percentage < 30 ? '#22c55e' : '#f59e0b' }}>{d.risk_percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {lastPrediction.isEstimated && (
              <p className={styles.estimatedNote}><i className="fas fa-info-circle"></i> This prediction is based on similar historical patterns because this exact combination was rare in the dataset.</p>
            )}
          </div>
        )}

        {/* ── Riskiest Hours ── */}
        {lastPrediction.riskiestHours?.length > 0 && (
          <div className={styles.insightsCard}>
            <div className={styles.insightsCardTitle}><i className="fas fa-exclamation-circle"></i> Highest Historical Risk Hours</div>
            <p className={styles.insightSubtitle}>Crime peaks at these hours based on historical data</p>
            <div className={styles.chipsRow}>
              {lastPrediction.riskiestHours.map((h, i) => (
                <span key={h?.hour ?? i} className={styles.chipRed}>🕐 {h?.label ?? h}</span>
              ))}
            </div>
          </div>
        )}

        {/* ── Safety Precautions ── */}
        <div className={styles.precautionsBlock}>
          <div className={styles.precautionsTitle}><i className="fas fa-exclamation-triangle"></i> Safety Precautions</div>
          <ul className={styles.precautionsList}>
            {riskInfo.precautions.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>

        {/* ── Monthly Crime Frequency Chart ── */}
        {lastPrediction.monthlyCrimeStats?.length > 0 && (() => {
          const maxCount = Math.max(...lastPrediction.monthlyCrimeStats.map(m => m.count));
          return (
            <div className={styles.insightsCard}>
              <div className={styles.insightsCardTitle}><i className="fas fa-chart-bar"></i> Crime Frequency — Last 12 Months</div>
              <p className={styles.insightSubtitle}>{formatAreaName(lastPrediction.area)} — FIR incidents per month (data through latest available)</p>
              <div className={styles.monthlyHbarChart}>
                {lastPrediction.monthlyCrimeStats.map(m => (
                  <div key={m.month} className={styles.monthlyHbarRow}>
                    <span className={styles.monthlyHbarLabel}>{m.label}</span>
                    <div className={styles.monthlyHbarTrack}>
                      <div className={styles.monthlyHbarFill} style={{ width: `${Math.round((m.count / maxCount) * 100)}%` }} title={`${m.month}: ${m.count} incidents`}/>
                    </div>
                    <span className={styles.monthlyHbarCount}>{m.count}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* ── Disclaimer ── */}
        <div className={styles.disclaimerBlock}>
          <i className="fas fa-info-circle"></i>
          <p><strong>Statistical Disclaimer:</strong> Predictions are based on historical FIR data and statistical models. They represent probabilities, not certainties. Do not use this as a substitute for official law-enforcement advice.</p>
        </div>
      </div>
    );
  };
  if (showMapView && lastPrediction) {
    return (
      <PredictionMapView
        prediction={lastPrediction}
        onBack={handleBackToResults}
      />
    );
  }

  return (
    <div className={`${styles.predictionSection} ${styles.fadeIn}`} id="risk-prediction">
      <PredictionVisual />
      
      <div className={styles.sectionHeader}>
        <div className={styles.headerIcon}>
          <i className="fas fa-robot"></i>
        </div>
        <h3 className={styles.sectionTitle}>AI Risk Prediction Tool</h3>
        <p className={styles.sectionSubtitle}>Get real-time crime risk predictions powered by machine learning</p>
      </div>

      <div className={styles.predictionContainer}>
        <div className={styles.predictionForm}>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label htmlFor="prediction-area">
                <i className="fas fa-map-marker-alt"></i>
                Select Area
              </label>
              <select
                id="prediction-area"
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className={area ? styles.hasValue : ''}
                disabled={loading}
              >
                <option value="">
                  {loading ? "Loading areas..." : areas.length > 0 ? "Choose an area in Lahore" : "No areas available"}
                </option>
                {areas.map((areaObj, index) => (
                  <option key={index} value={areaObj.name}>
                    {formatAreaName(areaObj.name)}
                  </option>
                ))}
              </select>
              {areas.length === 0 && !loading && (
                <div className={styles.warningText}>
                  <i className="fas fa-exclamation-triangle"></i>
                  No areas found in database
                </div>
              )}
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="prediction-crime-type">
                <i className="fas fa-shield-alt"></i>
                Crime Type
              </label>
              <select
                id="prediction-crime-type"
                value={crimeType}
                onChange={(e) => setCrimeType(e.target.value)}
                className={crimeType ? styles.hasValue : ''}
                disabled={loading}
              >
                <option value="">
                  {loading ? "Loading crime types..." : crimeTypes.length > 0 ? "Select crime type" : "No crime types available"}
                </option>
                {crimeTypes.map((crime, index) => (
                  <option key={index} value={crime}>
                    {crime}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="prediction-date">
                <i className="fas fa-calendar"></i>
                Date
              </label>
              <input
                type="date"
                id="prediction-date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className={date ? styles.hasValue : ''}
              />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="prediction-time">
                <i className="fas fa-clock"></i>
                Visit Time <span style={{ fontSize: '0.75em', opacity: 0.65 }}>(optional)</span>
              </label>
              <input
                type="time"
                id="prediction-time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className={time ? styles.hasValue : ''}
              />
            </div>

            <p className={styles.formHelper}>
              Select a date and optional visit time to estimate crime risk based on historical patterns.
            </p>

            <div className={styles.formActions}>
              <button
                className={`${styles.predictBtn} ${predicting ? styles.loading : ''} ${
                  !area || !crimeType ? styles.disabled : ''
                }`}
                onClick={() => { setAreaProfile(null); calculateRisk(area, crimeType, date, time); }}
                disabled={predicting || profileLoading || !area || !crimeType || areas.length === 0}
              >
                {predicting ? (
                  <>
                    <i className="fas fa-spinner fa-spin"></i>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <i className="fas fa-bolt"></i>
                    Predict Risk
                  </>
                )}
              </button>

              {area && !crimeType && (
                <button
                  className={`${styles.areaProfileBtn}${profileLoading ? ` ${styles.loading}` : ''}`}
                  onClick={handleAreaOverview}
                  disabled={profileLoading || predicting}
                >
                  {profileLoading ? (
                    <><i className="fas fa-spinner fa-spin"></i> Loading…</>
                  ) : (
                    <><i className="fas fa-shield-alt"></i> Area Safety Profile</>
                  )}
                </button>
              )}
              
              <button
                className={styles.resetBtn}
                onClick={handleReset}
                disabled={predicting || (!area && !crimeType && !lastPrediction && !areaProfile)}
                title="Reset form"
              >
                <i className="fas fa-redo-alt"></i>
                Reset
              </button>
            </div>
          </div>

          {message && (
            <div className={`${styles.infoMessage} ${
              message.includes('Error') || message.includes('Unable') ? styles.error : styles.success
            }`}>
              <i className={`fas ${
                message.includes('Error') || message.includes('Unable') ? 'fa-exclamation-triangle' : 'fa-info-circle'
              }`}></i> 
              {message}
            </div>
          )}

          {renderPredictionResult()}
          {renderAreaProfile()}
        </div>
      </div>
    </div>
  );
};

export default PredictionSection;


