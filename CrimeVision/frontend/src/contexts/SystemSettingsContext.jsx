import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiService from '../services/apiService_updated';

// Default values matching backend SYSTEM_SETTINGS_DEFAULTS
export const SYSTEM_SETTINGS_DEFAULTS = {
  session_timeout: 15,
  user_session_timeout: 43200,
  admin_session_timeout: 60,
  superadmin_session_timeout: 60,
  max_login_attempts: 5,
  lockout_duration: 30,
  password_min_length: 8,
  admin_password_min_length: 10,
  superadmin_password_min_length: 12,
  require_two_factor: false,
  alert_threshold: 'medium',
  notification_radius: 5,
  auto_alert_generation: true,
  alert_cooldown_minutes: 60,
  high_risk_threshold: 70,
  medium_risk_threshold: 40,
  alert_last_30_window_days: 30,
  alert_last_90_window_days: 90,
  alert_recent_half_window_days: 182,
  alert_history_window_days: 365,
  default_map_zoom: 12,
  map_min_zoom: 11,
  map_max_zoom: 18,
  map_default_center_lat: 31.5204,
  map_default_center_lng: 74.3587,
  map_bounds_south: 31.30,
  map_bounds_west: 74.15,
  map_bounds_north: 31.75,
  map_bounds_east: 74.60,
  map_bounds_viscosity: 1.0,
  map_fitbounds_padding_px: 20,
  map_fitbounds_max_zoom: 14,
  map_provider_default: 'maptiler',
  maptiler_enabled: true,
  maptiler_api_key: 'JKSv1djb3YWDL4sjZtTB',
  map_default_style: 'streets',
  heatmap_radius: 35,
  heatmap_intensity: 0.5,
  heatmap_blur_multiplier: 25,
  heatmap_layer_max_zoom: 12,
  map_default_record_limit: 1000,
  map_hotspot_min_incidents: 2,
  map_alert_visibility_threshold: 'low',
  monitor_saved_locations_interval_minutes: 1,
  monitor_job_max_instances: 1,
  incident_poll_interval_minutes: 1,
  incident_poll_job_max_instances: 1,
  model_watcher_retrain_threshold_new_crimes: 500,
  model_watcher_retrain_threshold_new_areas: 5,
  model_watcher_retrain_threshold_new_crime_types: 10,
  model_watcher_check_interval_seconds: 3600,
  model_watcher_retrain_timeout_seconds: 600,
  auto_retrain_oov_pair_threshold: 20,
  auto_retrain_new_record_threshold: 50,
  auto_retrain_min_interval_seconds: 3600,
  run_initial_monitor_on_startup: true,
  weekly_reports_enabled: true,
  weekly_reports_day_of_week: 'sun',
  weekly_reports_hour: 17,
  weekly_reports_minute: 5,
  weekly_reports_timezone: 'Asia/Karachi',
  location_accuracy_threshold_meters: 50000,
  low_accuracy_location_policy: 'accept_warn',
  ocr_transliteration_timeout_seconds: 8,
  data_retention_days: 180,
  log_level: 'info',
  maintenance_mode: false,
};

const PARSE_MAP = {
  session_timeout: Number,
  user_session_timeout: Number,
  admin_session_timeout: Number,
  superadmin_session_timeout: Number,
  max_login_attempts: Number,
  lockout_duration: Number,
  password_min_length: Number,
  admin_password_min_length: Number,
  superadmin_password_min_length: Number,
  require_two_factor: (v) => v === 'true' || v === true,
  notification_radius: Number,
  auto_alert_generation: (v) => v === 'true' || v === true,
  alert_cooldown_minutes: Number,
  high_risk_threshold: Number,
  medium_risk_threshold: Number,
  alert_last_30_window_days: Number,
  alert_last_90_window_days: Number,
  alert_recent_half_window_days: Number,
  alert_history_window_days: Number,
  default_map_zoom: Number,
  map_min_zoom: Number,
  map_max_zoom: Number,
  map_default_center_lat: Number,
  map_default_center_lng: Number,
  map_bounds_south: Number,
  map_bounds_west: Number,
  map_bounds_north: Number,
  map_bounds_east: Number,
  map_bounds_viscosity: parseFloat,
  map_fitbounds_padding_px: Number,
  map_fitbounds_max_zoom: Number,
  maptiler_enabled: (v) => v === 'true' || v === true,
  heatmap_radius: Number,
  heatmap_intensity: parseFloat,
  heatmap_blur_multiplier: Number,
  heatmap_layer_max_zoom: Number,
  map_default_record_limit: Number,
  map_hotspot_min_incidents: Number,
  monitor_job_max_instances: Number,
  monitor_saved_locations_interval_minutes: Number,
  incident_poll_job_max_instances: Number,
  incident_poll_interval_minutes: Number,
  model_watcher_retrain_threshold_new_crimes: Number,
  model_watcher_retrain_threshold_new_areas: Number,
  model_watcher_retrain_threshold_new_crime_types: Number,
  model_watcher_check_interval_seconds: Number,
  model_watcher_retrain_timeout_seconds: Number,
  auto_retrain_oov_pair_threshold: Number,
  auto_retrain_new_record_threshold: Number,
  auto_retrain_min_interval_seconds: Number,
  run_initial_monitor_on_startup: (v) => v === 'true' || v === true,
  weekly_reports_enabled: (v) => v === 'true' || v === true,
  weekly_reports_hour: Number,
  weekly_reports_minute: Number,
  location_accuracy_threshold_meters: Number,
  ocr_transliteration_timeout_seconds: Number,
  data_retention_days: Number,
  maintenance_mode: (v) => v === 'true' || v === true,
};

const SystemSettingsContext = createContext({
  settings: SYSTEM_SETTINGS_DEFAULTS,
  loading: true,
  refreshSettings: () => {},
});

export function SystemSettingsProvider({ children }) {
  const [settings, setSettings] = useState(SYSTEM_SETTINGS_DEFAULTS);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    try {
      const response = await apiService.getPublicSettings();
      if (response && response.settings) {
        const parsed = { ...SYSTEM_SETTINGS_DEFAULTS };
        for (const [key, raw] of Object.entries(response.settings)) {
          const parser = PARSE_MAP[key];
          if (parser) {
            parsed[key] = parser(raw);
          } else {
            parsed[key] = raw;
          }
        }
        setSettings(parsed);
      }
    } catch (err) {
      console.warn('SystemSettingsContext: using defaults', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return (
    <SystemSettingsContext.Provider value={{ settings, loading, refreshSettings: fetchSettings }}>
      {children}
    </SystemSettingsContext.Provider>
  );
}

export function useSystemSettings() {
  return useContext(SystemSettingsContext);
}

export default SystemSettingsContext;

