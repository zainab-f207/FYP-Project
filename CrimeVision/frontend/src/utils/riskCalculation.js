/**
 * Unified Risk Calculation - Frontend implementation matching backend
 * Ensures consistent risk scoring across all interfaces
 */

const UNIFIED_WEIGHTS = {
  volume: 0.35,
  severity: 0.15,
  recency: 0.30,
  trend: 0.10,
  time: 0.10,
};

const _clamp = (value, low = 0.0, high = 100.0) => {
  return Math.max(low, Math.min(high, value));
};

const risk_label_from_risk_score = (risk_score) => {
  const rs = parseFloat(_clamp(risk_score));
  if (rs <= 20) return "Low";
  if (rs <= 50) return "Moderate";
  if (rs <= 80) return "High";
  return "Critical";
};

const risk_action_label_from_score = (risk_score) => {
  const rs = parseFloat(_clamp(risk_score));
  if (rs <= 20) return "Safe";
  if (rs <= 50) return "Caution";
  if (rs <= 80) return "Warning";
  return "Avoid";
};

const safety_grade_from_score = (safety_score) => {
  const ss = parseFloat(_clamp(safety_score));
  if (ss >= 80) return "A";
  if (ss >= 65) return "B";
  if (ss >= 50) return "C";
  if (ss >= 35) return "D";
  return "F";
};

const _confidence_from_volume = (total_crimes) => {
  const n = parseFloat(Math.max(0.0, total_crimes));
  if (n >= 120) return "high";
  if (n >= 30) return "medium";
  return "low";
};

const _stabilize_for_sparse_data = (risk_score, total_crimes, observation_days = 365) => {
  const n = parseFloat(Math.max(0.0, total_crimes));
  const required_sample = Math.max(3.0, (30.0 / 365.0) * Math.max(1, observation_days));

  if (n >= required_sample) {
    return parseFloat(_clamp(risk_score));
  }

  const alpha = n / required_sample;
  const stabilized = alpha * parseFloat(risk_score) + (1.0 - alpha) * 0.0;
  return parseFloat(_clamp(stabilized));
};

const _volume_score = (total_crimes, observation_days = 365, baseline_daily = 0.35) => {
  const tc = parseFloat(Math.max(0.0, total_crimes));
  const days = Math.max(1, parseInt(observation_days));

  // Poisson probability
  const lam = tc / parseFloat(days);
  const poisson_score = 100.0 * (1.0 - Math.exp(-Math.max(lam, 1e-9)));

  // Log-scaled count ratio
  const volume_ref = Math.max(3000.0, parseFloat(days) * 30.0);
  const count_scale = 100.0 * (Math.log1p(tc) / Math.log1p(volume_ref));

  const score = 0.6 * poisson_score + 0.4 * count_scale;
  return parseFloat(_clamp(score));
};

const _severity_score = (high_risk_count, medium_risk_count, total_crimes) => {
  const tc = parseFloat(Math.max(0.0, total_crimes));
  if (tc <= 0.0) return 0.0;

  const hc = parseFloat(Math.max(0.0, high_risk_count));
  const mc = parseFloat(Math.max(0.0, medium_risk_count));
  const lc = parseFloat(Math.max(0.0, tc - hc - mc));

  const weighted = hc * 8.0 + mc * 5.0 + lc * 2.0;
  const avg = weighted / tc;
  const score = ((avg - 2.0) / 6.0) * 100.0;
  return parseFloat(_clamp(score));
};

const _trend_from_recent_vs_older = (recent_count, older_count) => {
  const recent = parseFloat(Math.max(0.0, recent_count));
  const older = parseFloat(Math.max(0.0, older_count));
  if (older <= 0.0) {
    return recent <= 0.0 ? 50.0 : 5.0;
  }
  const diff_pct = ((recent - older) / older) * 100.0;
  return parseFloat(_clamp(50.0 - diff_pct * 0.5));
};

const _recency_from_last_30 = (last_30_days, expected_30_days) => {
  const obs = parseFloat(Math.max(0.0, last_30_days));
  const exp = parseFloat(Math.max(0.0, expected_30_days));
  if (exp <= 0.0) {
    return obs <= 0.0 ? 50.0 : 95.0;
  }
  return parseFloat(_clamp((obs / exp) * 100.0));
};

const _recency_from_recent_windows = (last_30_days, last_90_days) => {
  const l30 = parseFloat(Math.max(0.0, last_30_days));
  const l90 = parseFloat(Math.max(0.0, last_90_days));
  if (l90 <= 0.0) {
    return 50.0;
  }
  const expected_30_from_90 = l90 / 3.0;
  if (expected_30_from_90 <= 0.0) {
    return 50.0;
  }
  return parseFloat(_clamp((l30 / expected_30_from_90) * 100.0));
};

/**
 * Calculate unified risk summary - matches backend calculation exactly
 * @param {Object} stats - Statistics object with crime counts and timing data
 * @param {number} observation_days - Lookback period in days (default 365)
 * @returns {Object} Risk summary with score, level, and components
 */
export const calculate_unified_risk_summary = (stats, observation_days = 365) => {
  if (!stats) {
    return {
      risk_score: 5.0,
      safety_score: 95.0,
      risk_level: "Low",
      risk_label: "Safe",
      safety_grade: "A",
      score_components: { volume: 5.0, severity: 5.0, recency: 5.0, trend: 5.0, time: 5.0 },
      data_confidence: "low",
      weights: UNIFIED_WEIGHTS,
    };
  }

  const total_crimes = parseFloat(stats.total_crimes || 0);
  const high_risk_count = parseFloat(stats.high_risk_count || 0);
  const medium_risk_count = parseFloat(stats.medium_risk_count || 0);

  // Handle zero-crime areas
  if (total_crimes === 0) {
    return {
      risk_score: 5.0,
      safety_score: 95.0,
      risk_level: "Low",
      risk_label: "Safe",
      safety_grade: "A",
      score_components: { volume: 5.0, severity: 5.0, recency: 5.0, trend: 5.0, time: 5.0 },
      data_confidence: _confidence_from_volume(total_crimes),
      weights: UNIFIED_WEIGHTS,
    };
  }

  // Component scores
  const pre_volume = stats.volume_score;
  const pre_severity = stats.severity_score;
  const pre_recency = stats.recency_score;
  const pre_trend = stats.trend_score;
  const pre_time = stats.time_risk_score;

  const volume_score = pre_volume !== undefined ? parseFloat(pre_volume) : _volume_score(total_crimes, observation_days);
  const severity_score = pre_severity !== undefined ? parseFloat(pre_severity) : _severity_score(high_risk_count, medium_risk_count, total_crimes);

  let recency_score;
  if (pre_recency !== undefined) {
    recency_score = parseFloat(pre_recency);
  } else {
    const last_30 = parseFloat(stats.last_30_days || 0);
    const last_90 = parseFloat(stats.last_90_days || 0);
    if (last_90 > 0) {
      recency_score = _recency_from_recent_windows(last_30, last_90);
    } else {
      const expected_30 = parseFloat(stats.expected_30_days || (total_crimes / Math.max(1, observation_days)) * 30.0);
      recency_score = _recency_from_last_30(last_30, expected_30);
    }
  }

  let trend_score;
  if (pre_trend !== undefined) {
    trend_score = parseFloat(pre_trend);
  } else {
    const recent_count = parseFloat(stats.recent_count || stats.recent_half || 0);
    const older_count = parseFloat(stats.older_count || stats.older_half || 0);
    trend_score = _trend_from_recent_vs_older(recent_count, older_count);
  }

  const time_risk_score = pre_time !== undefined ? parseFloat(pre_time) : parseFloat(_clamp(parseFloat(stats.time_risk_score || 50.0)));

  // Weighted risk calculation
  const raw_risk =
    UNIFIED_WEIGHTS.volume * volume_score +
    UNIFIED_WEIGHTS.severity * severity_score +
    UNIFIED_WEIGHTS.recency * recency_score +
    UNIFIED_WEIGHTS.trend * trend_score +
    UNIFIED_WEIGHTS.time * time_risk_score;

  // Decay for stale data
  let risk_score_before_stabilize = raw_risk;
  const last_90 = parseFloat(stats.last_90_days || 0);
  if (last_90 === 0) {
    let decay_factor;
    if (total_crimes >= 1000 || high_risk_count >= 50) {
      decay_factor = 0.85;
    } else if (total_crimes >= 100) {
      decay_factor = 0.7;
    } else {
      decay_factor = 0.6;
    }
    risk_score_before_stabilize = raw_risk * decay_factor;
  }

  const risk_score = _stabilize_for_sparse_data(risk_score_before_stabilize, total_crimes, observation_days);
  const safety_score = parseFloat(_clamp(100.0 - risk_score));
  const risk_level = risk_label_from_risk_score(risk_score);

  return {
    risk_score: parseFloat(Math.round(risk_score * 10) / 10),
    safety_score: parseFloat(Math.round(safety_score * 10) / 10),
    risk_level: risk_level,
    risk_label: risk_action_label_from_score(risk_score),
    safety_grade: safety_grade_from_score(safety_score),
    score_components: {
      volume: parseFloat(Math.round(_clamp(volume_score) * 10) / 10),
      severity: parseFloat(Math.round(_clamp(severity_score) * 10) / 10),
      recency: parseFloat(Math.round(_clamp(recency_score) * 10) / 10),
      trend: parseFloat(Math.round(_clamp(trend_score) * 10) / 10),
      time: parseFloat(Math.round(_clamp(time_risk_score) * 10) / 10),
    },
    data_confidence: _confidence_from_volume(total_crimes),
    weights: UNIFIED_WEIGHTS,
  };
};

export default { calculate_unified_risk_summary };
