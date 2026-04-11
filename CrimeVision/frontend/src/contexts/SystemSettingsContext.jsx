import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiService from '../services/apiService_updated';

// Default values matching backend SYSTEM_SETTINGS_DEFAULTS
const DEFAULTS = {
  session_timeout: 15,
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
  default_map_zoom: 12,
  heatmap_radius: 20,
  heatmap_intensity: 0.5,
  data_retention_days: 90,
  log_level: 'info',
  maintenance_mode: false,
};

const PARSE_MAP = {
  session_timeout: Number,
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
  default_map_zoom: Number,
  heatmap_radius: Number,
  heatmap_intensity: parseFloat,
  data_retention_days: Number,
  maintenance_mode: (v) => v === 'true' || v === true,
};

const SystemSettingsContext = createContext({
  settings: DEFAULTS,
  loading: true,
  refreshSettings: () => {},
});

export function SystemSettingsProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULTS);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    try {
      const response = await apiService.getPublicSettings();
      if (response && response.settings) {
        const parsed = { ...DEFAULTS };
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

