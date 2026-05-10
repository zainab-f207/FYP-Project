import React, { useState, useEffect, useCallback } from 'react';
import { Card, Row, Col, Form, Select, Switch, Button, message, Spin, Tabs, Input, InputNumber, Slider, Tag, Tooltip, Badge, Radio } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  LockOutlined,
  SaveOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  EnvironmentOutlined,
  AlertOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext_updated';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import apiService from '../../services/apiService_updated';
import styles from './SuperAdminDashboard.module.css';

const { Option } = Select;

// Map backend key → frontend state key and parse type
const KEY_MAP = {
  session_timeout: { state: 'sessionTimeout', type: 'number' },
  user_session_timeout: { state: 'userSessionTimeout', type: 'number' },
  admin_session_timeout: { state: 'adminSessionTimeout', type: 'number' },
  superadmin_session_timeout: { state: 'superadminSessionTimeout', type: 'number' },
  max_login_attempts: { state: 'maxLoginAttempts', type: 'number' },
  lockout_duration: { state: 'lockoutDuration', type: 'number' },
  unverified_warning_after_days: { state: 'unverifiedWarningAfterDays', type: 'number' },
  unverified_delete_after_days: { state: 'unverifiedDeleteAfterDays', type: 'number' },
  password_min_length: { state: 'passwordMinLength', type: 'number' },
  admin_password_min_length: { state: 'adminPasswordMinLength', type: 'number' },
  superadmin_password_min_length: { state: 'superadminPasswordMinLength', type: 'number' },
  require_two_factor: { state: 'requireTwoFactor', type: 'bool' },
  alert_threshold: { state: 'alertThreshold', type: 'string' },
  notification_radius: { state: 'notificationRadius', type: 'number' },
  auto_alert_generation: { state: 'autoAlertGeneration', type: 'bool' },
  alert_cooldown_minutes: { state: 'alertCooldownMinutes', type: 'number' },
  high_risk_threshold: { state: 'highRiskThreshold', type: 'number' },
  medium_risk_threshold: { state: 'mediumRiskThreshold', type: 'number' },
  alert_last_30_window_days: { state: 'alertLast30WindowDays', type: 'number' },
  alert_last_90_window_days: { state: 'alertLast90WindowDays', type: 'number' },
  alert_recent_half_window_days: { state: 'alertRecentHalfWindowDays', type: 'number' },
  alert_history_window_days: { state: 'alertHistoryWindowDays', type: 'number' },
  default_map_zoom: { state: 'defaultMapZoom', type: 'number' },
  map_min_zoom: { state: 'mapMinZoom', type: 'number' },
  map_max_zoom: { state: 'mapMaxZoom', type: 'number' },
  map_default_center_lat: { state: 'mapDefaultCenterLat', type: 'float' },
  map_default_center_lng: { state: 'mapDefaultCenterLng', type: 'float' },
  map_bounds_south: { state: 'mapBoundsSouth', type: 'float' },
  map_bounds_west: { state: 'mapBoundsWest', type: 'float' },
  map_bounds_north: { state: 'mapBoundsNorth', type: 'float' },
  map_bounds_east: { state: 'mapBoundsEast', type: 'float' },
  map_bounds_viscosity: { state: 'mapBoundsViscosity', type: 'float' },
  map_fitbounds_padding_px: { state: 'mapFitBoundsPaddingPx', type: 'number' },
  map_fitbounds_max_zoom: { state: 'mapFitBoundsMaxZoom', type: 'number' },
  map_provider_default: { state: 'mapProviderDefault', type: 'string' },
  maptiler_enabled: { state: 'maptilerEnabled', type: 'bool' },
  maptiler_api_key: { state: 'maptilerApiKey', type: 'string' },
  map_default_style: { state: 'mapDefaultStyle', type: 'string' },
  heatmap_radius: { state: 'heatmapRadius', type: 'number' },
  heatmap_intensity: { state: 'heatmapIntensity', type: 'float' },
  heatmap_blur_multiplier: { state: 'heatmapBlurMultiplier', type: 'number' },
  heatmap_layer_max_zoom: { state: 'heatmapLayerMaxZoom', type: 'number' },
  map_default_record_limit: { state: 'mapDefaultRecordLimit', type: 'number' },
  map_hotspot_min_incidents: { state: 'mapHotspotMinIncidents', type: 'number' },
  map_alert_visibility_threshold: { state: 'mapAlertVisibilityThreshold', type: 'string' },
  monitor_saved_locations_interval_minutes: { state: 'monitorSavedLocationsIntervalMinutes', type: 'number' },
  monitor_job_max_instances: { state: 'monitorJobMaxInstances', type: 'number' },
  incident_poll_interval_minutes: { state: 'incidentPollIntervalMinutes', type: 'number' },
  incident_poll_job_max_instances: { state: 'incidentPollJobMaxInstances', type: 'number' },
  model_watcher_retrain_threshold_new_crimes: { state: 'modelWatcherRetrainThresholdNewCrimes', type: 'number' },
  model_watcher_retrain_threshold_new_areas: { state: 'modelWatcherRetrainThresholdNewAreas', type: 'number' },
  model_watcher_retrain_threshold_new_crime_types: { state: 'modelWatcherRetrainThresholdNewCrimeTypes', type: 'number' },
  model_watcher_check_interval_seconds: { state: 'modelWatcherCheckIntervalSeconds', type: 'number' },
  model_watcher_retrain_timeout_seconds: { state: 'modelWatcherRetrainTimeoutSeconds', type: 'number' },
  auto_retrain_oov_pair_threshold: { state: 'autoRetrainOovPairThreshold', type: 'number' },
  auto_retrain_new_record_threshold: { state: 'autoRetrainNewRecordThreshold', type: 'number' },
  auto_retrain_min_interval_seconds: { state: 'autoRetrainMinIntervalSeconds', type: 'number' },
  run_initial_monitor_on_startup: { state: 'runInitialMonitorOnStartup', type: 'bool' },
  weekly_reports_enabled: { state: 'weeklyReportsEnabled', type: 'bool' },
  weekly_reports_day_of_week: { state: 'weeklyReportsDayOfWeek', type: 'string' },
  weekly_reports_hour: { state: 'weeklyReportsHour', type: 'number' },
  weekly_reports_minute: { state: 'weeklyReportsMinute', type: 'number' },
  weekly_reports_timezone: { state: 'weeklyReportsTimezone', type: 'string' },
  location_accuracy_threshold_meters: { state: 'locationAccuracyThresholdMeters', type: 'number' },
  low_accuracy_location_policy: { state: 'lowAccuracyLocationPolicy', type: 'string' },
  ocr_transliteration_timeout_seconds: { state: 'ocrTransliterationTimeoutSeconds', type: 'number' },
  data_retention_days: { state: 'dataRetentionDays', type: 'number' },
  log_level: { state: 'logLevel', type: 'string' },
  maintenance_mode: { state: 'maintenanceMode', type: 'bool' },
};

const parseVal = (raw, type) => {
  if (type === 'number') return parseInt(raw, 10) || 0;
  if (type === 'float') return parseFloat(raw) || 0;
  if (type === 'bool') return raw === 'true' || raw === true;
  return raw;
};

const DEFAULTS = {
  sessionTimeout: 15,
  userSessionTimeout: 43200,
  adminSessionTimeout: 60,
  superadminSessionTimeout: 60,
  maxLoginAttempts: 5,
  lockoutDuration: 30,
  unverifiedWarningAfterDays: 6,
  unverifiedDeleteAfterDays: 7,
  passwordMinLength: 8,
  adminPasswordMinLength: 10,
  superadminPasswordMinLength: 12,
  requireTwoFactor: false,
  alertThreshold: 'medium',
  notificationRadius: 5,
  autoAlertGeneration: true,
  alertCooldownMinutes: 60,
  highRiskThreshold: 70,
  mediumRiskThreshold: 40,
  alertLast30WindowDays: 30,
  alertLast90WindowDays: 90,
  alertRecentHalfWindowDays: 182,
  alertHistoryWindowDays: 365,
  defaultMapZoom: 12,
  mapMinZoom: 11,
  mapMaxZoom: 18,
  mapDefaultCenterLat: 31.5204,
  mapDefaultCenterLng: 74.3587,
  mapBoundsSouth: 31.30,
  mapBoundsWest: 74.15,
  mapBoundsNorth: 31.75,
  mapBoundsEast: 74.60,
  mapBoundsViscosity: 1.0,
  mapFitBoundsPaddingPx: 20,
  mapFitBoundsMaxZoom: 14,
  mapProviderDefault: 'maptiler',
  maptilerEnabled: true,
  maptilerApiKey: 'JKSv1djb3YWDL4sjZtTB',
  mapDefaultStyle: 'streets',
  heatmapRadius: 20,
  heatmapIntensity: 0.5,
  heatmapBlurMultiplier: 25,
  heatmapLayerMaxZoom: 17,
  mapDefaultRecordLimit: 1000,
  mapHotspotMinIncidents: 2,
  mapAlertVisibilityThreshold: 'low',
  monitorSavedLocationsIntervalMinutes: 1,
  monitorJobMaxInstances: 1,
  incidentPollIntervalMinutes: 1,
  incidentPollJobMaxInstances: 1,
  modelWatcherRetrainThresholdNewCrimes: 10,
  modelWatcherRetrainThresholdNewAreas: 5,
  modelWatcherRetrainThresholdNewCrimeTypes: 10,
  modelWatcherCheckIntervalSeconds: 3600,
  modelWatcherRetrainTimeoutSeconds: 600,
  autoRetrainOovPairThreshold: 10,
  autoRetrainNewRecordThreshold: 10,
  autoRetrainMinIntervalSeconds: 3600,
  runInitialMonitorOnStartup: true,
  weeklyReportsEnabled: true,
  weeklyReportsDayOfWeek: 'sun',
  weeklyReportsHour: 17,
  weeklyReportsMinute: 5,
  weeklyReportsTimezone: 'Asia/Karachi',
  locationAccuracyThresholdMeters: 50000,
  lowAccuracyLocationPolicy: 'accept_warn',
  ocrTransliterationTimeoutSeconds: 8,
  dataRetentionDays: 90,
  logLevel: 'info',
  maintenanceMode: false,
};

const SystemSettings = () => {
  const { token } = useAuth();
  const { refreshSettings } = useSystemSettings();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [applyingRuntime, setApplyingRuntime] = useState(false);
  const [settings, setSettings] = useState({ ...DEFAULTS });
  const [lastSaved, setLastSaved] = useState(null);
  const [lastSavedBy, setLastSavedBy] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [savedSettings, setSavedSettings] = useState({ ...DEFAULTS });
  const [modelMeta, setModelMeta]       = useState(null);
  const [retraining, setRetraining]     = useState(false);
  const [retrainMsg, setRetrainMsg]     = useState(null);
  const [cleanupRunning, setCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult]   = useState(null);
  const [cleanupTestMode, setCleanupTestMode] = useState(false);

  const loadSettings = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const response = await apiService.get('/admin/system-settings', token);
      if (response && response.settings) {
        const parsed = { ...DEFAULTS };
        for (const [backendKey, meta] of Object.entries(KEY_MAP)) {
          if (response.settings[backendKey] !== undefined) {
            parsed[meta.state] = parseVal(response.settings[backendKey], meta.type);
          }
        }
        setSettings(parsed);
        setSavedSettings(parsed);
        setLastSaved(response.lastUpdated || null);
        setLastSavedBy(response.lastUpdatedBy || null);
      }
    } catch (error) {
      console.error('Error loading system settings:', error);
      message.warning('Using default settings — configure and save to persist');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  // Load ML model metadata for the Model Management card
  useEffect(() => {
    if (!token) return;
    apiService.getIntelligenceDashboard()
      .then(data => {
        if (data) {
          setModelMeta({
            last_train_date: data?.model_health?.last_train_date || null,
            total_records:   data?.dataset_health?.total_records ?? null,
            records_since_last_train: data?.dataset_health?.records_since_last_train ?? null,
          });
        }
      })
      .catch(() => {});
  }, [token]);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainMsg(null);
    try {
      const before = await apiService.getModelRetrainStatus(token).catch(() => null);
      const res = await apiService.triggerRetrain(token);
      setRetrainMsg({ type: 'success', text: res?.message || 'Retrain launched. Waiting for completion...' });

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
          const doneDate = nowTs > 0
            ? new Date(nowTs * 1000).toISOString().slice(0, 10)
            : new Date().toISOString().slice(0, 10);
          setModelMeta(prev => ({ ...prev, last_train_date: doneDate, records_since_last_train: 0 }));
          setRetrainMsg({ type: 'success', text: 'Retrain completed successfully. New RF, Poisson, and legacy RF are refreshed.' });
          message.success('Model retrain completed successfully');
          break;
        }
      }

      if (!completed) {
        setRetrainMsg({
          type: 'success',
          text: 'Retrain is still running in background. Check again in a minute.',
        });
      }
    } catch (err) {
      setRetrainMsg({ type: 'error', text: err?.message || 'Retraining failed. Check backend logs.' });
    } finally {
      setRetraining(false);
    }
  };

  const handleRunCleanup = async () => {
    setCleanupRunning(true);
    setCleanupResult(null);
    try {
      const res = await apiService.runUnverifiedCleanup(token, cleanupTestMode
        ? { warningAfterDays: 0, deleteAfterDays: 0, notifyAdmins: false }
        : { notifyAdmins: true });
      setCleanupResult(res);
      message.success(`Cleanup ran — warned ${res.warned_count}, deleted ${res.deleted_count}`);
    } catch (err) {
      message.error(err?.message || 'Cleanup failed — check backend logs');
      setCleanupResult({ error: err?.message || 'Cleanup failed' });
    } finally {
      setCleanupRunning(false);
    }
  };

  useEffect(() => {
    setHasChanges(JSON.stringify(settings) !== JSON.stringify(savedSettings));
  }, [settings, savedSettings]);

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      const payload = {};
      for (const [backendKey, meta] of Object.entries(KEY_MAP)) {
        payload[backendKey] = String(settings[meta.state]);
      }
      const res = await apiService.post('/admin/system-settings', payload, token);
      message.success(res?.message || 'Settings saved successfully');
      setSavedSettings({ ...settings });
      setHasChanges(false);
      setLastSaved(new Date().toISOString());
      // Refresh the global SystemSettingsContext so all components get the new values immediately
      refreshSettings();
      return true;
    } catch (error) {
      console.error('Error saving system settings:', error);
      message.error('Failed to save system settings');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleApplyRuntimeNow = async () => {
    try {
      setApplyingRuntime(true);

      if (hasChanges) {
        const saved = await handleSaveSettings();
        if (!saved) return;
      }

      const res = await apiService.post('/admin/system-settings/apply-runtime', {}, token);
      message.success(res?.message || 'Runtime settings applied successfully');
      refreshSettings();
    } catch (error) {
      console.error('Error applying runtime settings:', error);
      message.error('Failed to apply runtime settings');
    } finally {
      setApplyingRuntime(false);
    }
  };

  const deriveWatcherThresholds = (newCrimeReports) => {
    const n = Math.max(1, Number(newCrimeReports) || 1);
    const minIntervalSeconds = n <= 10 ? 900 : (n <= 50 ? 1800 : 3600);
    return {
      modelWatcherRetrainThresholdNewAreas: Math.max(1, Math.round(n / 100)),
      modelWatcherRetrainThresholdNewCrimeTypes: Math.max(1, Math.round(n / 50)),
      autoRetrainOovPairThreshold: n,
      autoRetrainNewRecordThreshold: n,
      autoRetrainMinIntervalSeconds: minIntervalSeconds,
    };
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value };
      if (key === 'modelWatcherRetrainThresholdNewCrimes') {
        const derived = deriveWatcherThresholds(value);
        next.modelWatcherRetrainThresholdNewAreas = derived.modelWatcherRetrainThresholdNewAreas;
        next.modelWatcherRetrainThresholdNewCrimeTypes = derived.modelWatcherRetrainThresholdNewCrimeTypes;
        next.autoRetrainOovPairThreshold = derived.autoRetrainOovPairThreshold;
        next.autoRetrainNewRecordThreshold = derived.autoRetrainNewRecordThreshold;
        next.autoRetrainMinIntervalSeconds = derived.autoRetrainMinIntervalSeconds;
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <Spin size="large" />
        <p>Loading system settings...</p>
      </div>
    );
  }

  const formatDate = (iso) => {
    if (!iso) return null;
    try { return new Date(iso).toLocaleString(); } catch { return iso; }
  };

  const tabItems = [
    {
      key: 'security',
      label: (<span><LockOutlined style={{ marginRight: 8 }} />Security &amp; Access</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><LockOutlined style={{ color: '#f9a826' }} /> Authentication</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <div style={{ marginBottom: 12, color: 'rgba(255,255,255,0.72)', fontSize: 13 }}>
                  Authentication settings are now separated by role to reflect the actual backend login flow.
                </div>

                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#93c5fd' }}>Regular User Authentication</div>
                  <Form.Item label={<span>User Session Timeout (minutes) <Tooltip title="How long a normal user stays signed in. Common: 43200 = 30 days, 525600 = 1 year"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={30} max={525600} value={settings.userSessionTimeout} onChange={(v) => handleSettingChange('userSessionTimeout', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label={<span>User Password Length <Tooltip title="Minimum characters required for regular users"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={6} max={20} value={settings.passwordMinLength} onChange={(v) => handleSettingChange('passwordMinLength', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    Optional OTP app verification.
                  </div>
                </div>

                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#fbbf24' }}>Admin Authentication</div>
                  <Form.Item label={<span>Admin Session Timeout (minutes) <Tooltip title="How long an admin stays signed in"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={5} max={1440} value={settings.adminSessionTimeout} onChange={(v) => handleSettingChange('adminSessionTimeout', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label={<span>Admin Password Length <Tooltip title="Minimum password length for admin accounts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={8} max={32} value={settings.adminPasswordMinLength} onChange={(v) => handleSettingChange('adminPasswordMinLength', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    Email OTP required on every login.
                  </div>
                </div>

                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#c4b5fd' }}>SuperAdmin Authentication</div>
                  <Form.Item label={<span>SuperAdmin Session Timeout (minutes) <Tooltip title="How long a superadmin stays signed in"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={5} max={1440} value={settings.superadminSessionTimeout} onChange={(v) => handleSettingChange('superadminSessionTimeout', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label={<span>SuperAdmin Password Length <Tooltip title="Minimum password length for superadmins"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={10} max={32} value={settings.superadminPasswordMinLength} onChange={(v) => handleSettingChange('superadminPasswordMinLength', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    Email OTP required on every login.
                  </div>
                </div>

                <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#86efac' }}>Shared Login Protection</div>
                  <Form.Item label={<span>Max Login Attempts <Tooltip title="How many failed logins before the account is locked"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={3} max={10} value={settings.maxLoginAttempts} onChange={(v) => handleSettingChange('maxLoginAttempts', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label={<span>Lockout Duration (minutes) <Tooltip title="How long the lock stays active"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={5} max={120} value={settings.lockoutDuration} onChange={(v) => handleSettingChange('lockoutDuration', v)} style={{ width: '100%' }} />
                  </Form.Item>
                </div>

                <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 12, marginTop: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#fca5a5' }}>Unverified Account Cleanup</div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginBottom: 10 }}>
                    Background job runs every 6 hours. Users who don't verify their email get a warning email at "Warn after", then are deleted at "Delete after".
                  </div>
                  <Form.Item label={<span>Warn After (days) <Tooltip title="Send a 'your account will be deleted soon' warning email when an unverified account is older than this many days"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={1} max={30} value={settings.unverifiedWarningAfterDays} onChange={(v) => handleSettingChange('unverifiedWarningAfterDays', v)} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item label={<span>Delete After (days) <Tooltip title="Permanently delete unverified accounts older than this many days. Must be greater than Warn After"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                    <InputNumber min={2} max={60} value={settings.unverifiedDeleteAfterDays} onChange={(v) => handleSettingChange('unverifiedDeleteAfterDays', v)} style={{ width: '100%' }} />
                  </Form.Item>

                  <div style={{ background: 'rgba(0,0,0,0.18)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, marginTop: 8 }}>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', marginBottom: 8 }}>
                      Run the cleanup job manually for testing. Normally fires every 6 hours.
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
                      <Tooltip title="When ON, this run uses 0 days for both thresholds — every unverified account gets warned + deleted regardless of age. Use only for end-to-end testing.">
                        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                          <Switch size="small" checked={cleanupTestMode} onChange={setCleanupTestMode} />
                          <span style={{ fontSize: 12, color: cleanupTestMode ? '#fca5a5' : 'rgba(255,255,255,0.7)' }}>
                            Test mode (ignore TTL — process every unverified user)
                          </span>
                        </label>
                      </Tooltip>
                    </div>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={handleRunCleanup}
                      loading={cleanupRunning}
                      danger={cleanupTestMode}
                      type={cleanupTestMode ? 'primary' : 'default'}
                    >
                      {cleanupTestMode ? 'Run cleanup NOW (test mode)' : 'Run cleanup now'}
                    </Button>

                    {cleanupResult && (
                      <div style={{ marginTop: 10, fontSize: 12 }}>
                        {cleanupResult.error ? (
                          <div style={{ color: '#ef4444' }}>Error: {cleanupResult.error}</div>
                        ) : (
                          <>
                            <div style={{ color: 'rgba(255,255,255,0.75)', marginBottom: 6 }}>
                              <Tag color="orange">Warned {cleanupResult.warned_count ?? 0}</Tag>
                              <Tag color="red">Deleted {cleanupResult.deleted_count ?? 0}</Tag>
                              <span style={{ color: 'rgba(255,255,255,0.45)' }}>
                                · warn_after={cleanupResult.warning_after_days}d
                                · delete_after={cleanupResult.delete_after_days}d
                              </span>
                            </div>
                            {Array.isArray(cleanupResult.warned) && cleanupResult.warned.length > 0 && (
                              <div style={{ marginBottom: 4 }}>
                                <span style={{ color: '#fbbf24' }}>Warned:</span>{' '}
                                <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                                  {cleanupResult.warned.map((u) => u.email).join(', ')}
                                </span>
                              </div>
                            )}
                            {Array.isArray(cleanupResult.deleted) && cleanupResult.deleted.length > 0 && (
                              <div>
                                <span style={{ color: '#ef4444' }}>Deleted:</span>{' '}
                                <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                                  {cleanupResult.deleted.map((u) => u.email).join(', ')}
                                </span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'alerts',
      label: (<span><AlertOutlined style={{ marginRight: 8 }} />Alerts</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><AlertOutlined style={{ color: '#f9a826' }} /> Alert Rules</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <div style={{ marginBottom: 12, color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>Choose when the system should send alerts.</div>
                <Form.Item label={<span>When to Send Alerts <Tooltip title="Pick how early the system should warn staff"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <Radio.Group value={settings.alertThreshold} onChange={(e) => handleSettingChange('alertThreshold', e.target.value)} style={{ width: '100%' }}>
                    <div style={{ display: 'grid', gap: 12 }}>
                      <label style={{ padding: 12, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, cursor: 'pointer' }}><Radio value="low">Show alerts for moderate, high, and critical risk</Radio></label>
                      <label style={{ padding: 12, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, cursor: 'pointer' }}><Radio value="medium">Show alerts for high and critical risk</Radio></label>
                      <label style={{ padding: 12, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, cursor: 'pointer' }}><Radio value="high">Show alerts only for critical risk</Radio></label>
                    </div>
                  </Radio.Group>
                </Form.Item>
                <div style={{ marginTop: -4, marginBottom: 12, color: 'rgba(255,255,255,0.75)', fontSize: 12 }}>Current rule: alert when risk is at least {settings.alertThreshold === 'low' ? 'Moderate' : settings.alertThreshold === 'medium' ? 'High' : 'Critical'}, within {settings.notificationRadius} km.</div>
                <Form.Item label={<span>Alert Area Size (km) <Tooltip title="How wide the alert area should be"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <Slider min={1} max={20} value={settings.notificationRadius} onChange={(v) => handleSettingChange('notificationRadius', v)} marks={{ 1: '1 km', 5: '5 km', 10: '10 km', 20: '20 km' }} />
                </Form.Item>
                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginTop: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#86efac' }}>Alert Analytics Windows (Days)</div>
                  <div style={{ marginBottom: 10, color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>These values tell the alert system how far back to look for recent and past activity.</div>
                  <Row gutter={12}>
                    <Col span={12}><Form.Item label="Recent activity (days)"><InputNumber min={1} max={3650} value={settings.alertLast30WindowDays} onChange={(v) => handleSettingChange('alertLast30WindowDays', v)} style={{ width: '100%' }} /></Form.Item></Col>
                    <Col span={12}><Form.Item label="Recent risk check (days)"><InputNumber min={1} max={3650} value={settings.alertLast90WindowDays} onChange={(v) => handleSettingChange('alertLast90WindowDays', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  </Row>
                  <Row gutter={12}>
                    <Col span={12}><Form.Item label="Recent half split (days)"><InputNumber min={1} max={3650} value={settings.alertRecentHalfWindowDays} onChange={(v) => handleSettingChange('alertRecentHalfWindowDays', v)} style={{ width: '100%' }} /></Form.Item></Col>
                    <Col span={12}><Form.Item label="History window (days)"><InputNumber min={30} max={3650} value={settings.alertHistoryWindowDays} onChange={(v) => handleSettingChange('alertHistoryWindowDays', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  </Row>
                </div>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'map-basic',
      label: (<span><EnvironmentOutlined style={{ marginRight: 8 }} />Map Basics</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><EnvironmentOutlined style={{ color: '#f9a826' }} /> Map Start Point</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label={<span>Starting Zoom <Tooltip title="How close the map opens"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <Slider min={8} max={18} value={settings.defaultMapZoom} onChange={(v) => handleSettingChange('defaultMapZoom', v)} marks={{ 8: 'City', 12: 'District', 15: 'Street', 18: 'Block' }} />
                </Form.Item>
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Zoom out limit"><InputNumber min={3} max={20} value={settings.mapMinZoom} onChange={(v) => handleSettingChange('mapMinZoom', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Zoom in limit"><InputNumber min={3} max={22} value={settings.mapMaxZoom} onChange={(v) => handleSettingChange('mapMaxZoom', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Map center latitude"><InputNumber min={20} max={40} step={0.0001} value={settings.mapDefaultCenterLat} onChange={(v) => handleSettingChange('mapDefaultCenterLat', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Map center longitude"><InputNumber min={60} max={80} step={0.0001} value={settings.mapDefaultCenterLng} onChange={(v) => handleSettingChange('mapDefaultCenterLng', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Form.Item label="Map style"><Select value={settings.mapDefaultStyle} onChange={(v) => handleSettingChange('mapDefaultStyle', v)} style={{ width: '100%' }}><Option value="streets">Streets</Option><Option value="dark">Dark</Option><Option value="satellite">Satellite</Option><Option value="hybrid">Hybrid</Option><Option value="basic">Basic</Option><Option value="outdoor">Outdoor</Option></Select></Form.Item>
                <Form.Item label="Map source"><Select value={settings.mapProviderDefault} onChange={(v) => handleSettingChange('mapProviderDefault', v)} style={{ width: '100%' }}><Option value="maptiler">MapTiler</Option><Option value="osm">OpenStreetMap</Option></Select></Form.Item>
                <Form.Item label={<span>Use MapTiler <Tooltip title="Turn off to use OpenStreetMap instead"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><Switch checked={settings.maptilerEnabled} onChange={(v) => handleSettingChange('maptilerEnabled', v)} /></Form.Item>
                <Form.Item label="Map source key"><Input value={settings.maptilerApiKey} onChange={(e) => handleSettingChange('maptilerApiKey', e.target.value)} /></Form.Item>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'map-layers',
      label: (<span><EnvironmentOutlined style={{ marginRight: 8 }} />Map Layers</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><EnvironmentOutlined style={{ color: '#f9a826' }} /> Map Area</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Map area south"><InputNumber min={20} max={40} step={0.0001} value={settings.mapBoundsSouth} onChange={(v) => handleSettingChange('mapBoundsSouth', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Map area west"><InputNumber min={60} max={80} step={0.0001} value={settings.mapBoundsWest} onChange={(v) => handleSettingChange('mapBoundsWest', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Map area north"><InputNumber min={20} max={40} step={0.0001} value={settings.mapBoundsNorth} onChange={(v) => handleSettingChange('mapBoundsNorth', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Map area east"><InputNumber min={60} max={80} step={0.0001} value={settings.mapBoundsEast} onChange={(v) => handleSettingChange('mapBoundsEast', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Form.Item label="Edge lock strength"><Slider min={0} max={1} step={0.1} value={settings.mapBoundsViscosity} onChange={(v) => handleSettingChange('mapBoundsViscosity', v)} marks={{ 0: 'Free', 0.5: 'Soft', 1: 'Locked' }} /></Form.Item>
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Auto-fit padding"><InputNumber min={0} max={200} value={settings.mapFitBoundsPaddingPx} onChange={(v) => handleSettingChange('mapFitBoundsPaddingPx', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Auto-fit zoom limit"><InputNumber min={8} max={22} value={settings.mapFitBoundsMaxZoom} onChange={(v) => handleSettingChange('mapFitBoundsMaxZoom', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
              </Form>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><ThunderboltOutlined style={{ color: '#f9a826' }} /> Heatmap</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <div style={{ marginBottom: 12, color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>Control how much data the heatmap shows and how strong it looks.</div>
                <Form.Item label="Heatmap size"><Slider min={10} max={50} value={settings.heatmapRadius} onChange={(v) => handleSettingChange('heatmapRadius', v)} marks={{ 10: '10', 20: '20', 30: '30', 50: '50' }} /></Form.Item>
                <Form.Item label="Heatmap strength"><Slider min={0.1} max={1} step={0.1} value={settings.heatmapIntensity} onChange={(v) => handleSettingChange('heatmapIntensity', v)} marks={{ 0.1: 'Low', 0.5: 'Med', 1: 'High' }} /></Form.Item>
                <Row gutter={12}>
                  <Col span={12}><Form.Item label="Heatmap softness"><InputNumber min={5} max={60} value={settings.heatmapBlurMultiplier} onChange={(v) => handleSettingChange('heatmapBlurMultiplier', v)} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item label="Heatmap zoom limit"><InputNumber min={10} max={22} value={settings.heatmapLayerMaxZoom} onChange={(v) => handleSettingChange('heatmapLayerMaxZoom', v)} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Form.Item label="Records to load"><InputNumber min={100} max={5000} step={100} value={settings.mapDefaultRecordLimit} onChange={(v) => handleSettingChange('mapDefaultRecordLimit', v)} style={{ width: '100%' }} /></Form.Item>
                <Form.Item label="Hotspot minimum"><InputNumber min={1} max={20} value={settings.mapHotspotMinIncidents} onChange={(v) => handleSettingChange('mapHotspotMinIncidents', v)} style={{ width: '100%' }} /></Form.Item>
                <Form.Item label="Which risks to show"><Radio.Group value={settings.mapAlertVisibilityThreshold} onChange={(e) => handleSettingChange('mapAlertVisibilityThreshold', e.target.value)} style={{ width: '100%' }}><div style={{ display: 'grid', gap: 10 }}><label style={{ padding: 10, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10, cursor: 'pointer' }}><Radio value="low">Show All Levels (Low, Moderate, High, Critical)</Radio></label><label style={{ padding: 10, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10, cursor: 'pointer' }}><Radio value="medium">Show Moderate and above</Radio></label><label style={{ padding: 10, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10, cursor: 'pointer' }}><Radio value="high">Show High and Critical only</Radio></label><label style={{ padding: 10, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10, cursor: 'pointer' }}><Radio value="critical">Show Critical only</Radio></label></div></Radio.Group></Form.Item>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'jobs',
      label: (<span><ThunderboltOutlined style={{ marginRight: 8 }} />Jobs &amp; Reports</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><ThunderboltOutlined style={{ color: '#f9a826' }} /> Background Jobs</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <div style={{ marginBottom: 12, color: 'rgba(255,255,255,0.72)', fontSize: 13 }}>Control how often the system checks locations and sends reports.</div>
                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#93c5fd' }}>Location Checks</div>
                  <Form.Item label={<span>Check saved locations every (minutes) <Tooltip title="How often the system checks saved places like home and work"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={1} max={60} value={settings.monitorSavedLocationsIntervalMinutes} onChange={(v) => handleSettingChange('monitorSavedLocationsIntervalMinutes', v)} style={{ width: '100%' }} /></Form.Item>
                  <Form.Item label={<span>Max parallel checks <Tooltip title="How many checks can run at the same time"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={1} max={5} value={settings.monitorJobMaxInstances} onChange={(v) => handleSettingChange('monitorJobMaxInstances', v)} style={{ width: '100%' }} /></Form.Item>
                  <Form.Item label={<span>Check new incidents every (minutes) <Tooltip title="How often the system checks for new reports to send alerts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={1} max={60} value={settings.incidentPollIntervalMinutes} onChange={(v) => handleSettingChange('incidentPollIntervalMinutes', v)} style={{ width: '100%' }} /></Form.Item>
                  <Form.Item label={<span>Max parallel incident checks <Tooltip title="How many incident checks can run at the same time"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={1} max={5} value={settings.incidentPollJobMaxInstances} onChange={(v) => handleSettingChange('incidentPollJobMaxInstances', v)} style={{ width: '100%' }} /></Form.Item>
                  <Form.Item label={<span>Run location check on startup <Tooltip title="Do one check when the backend starts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><Switch checked={settings.runInitialMonitorOnStartup} onChange={(c) => handleSettingChange('runInitialMonitorOnStartup', c)} /></Form.Item>
                </div>
                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#fde68a' }}>Weekly Reports</div>
                  <Form.Item label={<span>Send weekly report <Tooltip title="Turn weekly reports on or off"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Switch checked={settings.weeklyReportsEnabled} onChange={(c) => handleSettingChange('weeklyReportsEnabled', c)} /><Tag color={settings.weeklyReportsEnabled ? 'green' : 'default'}>{settings.weeklyReportsEnabled ? 'Enabled' : 'Disabled'}</Tag></div></Form.Item>
                  <Form.Item label="Report day"><Select value={settings.weeklyReportsDayOfWeek} onChange={(v) => handleSettingChange('weeklyReportsDayOfWeek', v)} style={{ width: '100%' }}><Option value="mon">Monday</Option><Option value="tue">Tuesday</Option><Option value="wed">Wednesday</Option><Option value="thu">Thursday</Option><Option value="fri">Friday</Option><Option value="sat">Saturday</Option><Option value="sun">Sunday</Option></Select></Form.Item>
                  <Row gutter={12}><Col span={12}><Form.Item label="Hour"><InputNumber min={0} max={23} value={settings.weeklyReportsHour} onChange={(v) => handleSettingChange('weeklyReportsHour', v)} style={{ width: '100%' }} /></Form.Item></Col><Col span={12}><Form.Item label="Minute"><InputNumber min={0} max={59} value={settings.weeklyReportsMinute} onChange={(v) => handleSettingChange('weeklyReportsMinute', v)} style={{ width: '100%' }} /></Form.Item></Col></Row>
                  <Form.Item label="Time zone"><Select value={settings.weeklyReportsTimezone} onChange={(v) => handleSettingChange('weeklyReportsTimezone', v)} style={{ width: '100%' }}><Option value="Asia/Karachi">Asia/Karachi</Option><Option value="UTC">UTC</Option></Select></Form.Item>
                </div>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'model',
      label: (<span><ThunderboltOutlined style={{ marginRight: 8 }} />Model &amp; OCR</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><ThunderboltOutlined style={{ color: '#a78bfa' }} /> Model Management</div>} className={styles.settingsCard}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div style={{ background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: 8, padding: '10px 14px' }}><div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>Last trained</div><div style={{ fontWeight: 700, color: '#a78bfa', fontSize: '0.92rem' }}>{modelMeta?.last_train_date || '—'}</div></div>
                <div style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: '10px 14px' }}><div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>Total records</div><div style={{ fontWeight: 700, color: '#3b82f6', fontSize: '0.92rem' }}>{modelMeta?.total_records != null ? modelMeta.total_records.toLocaleString() : '—'}</div></div>
                <div style={{ background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: 8, padding: '10px 14px' }}><div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>Records since retrain</div><div style={{ fontWeight: 700, color: modelMeta?.records_since_last_train > 10 ? '#f97316' : '#22c55e', fontSize: '0.92rem' }}>{modelMeta?.records_since_last_train != null ? modelMeta.records_since_last_train.toLocaleString() : '—'}{modelMeta?.records_since_last_train > 10 && (<Tag color="orange" style={{ marginLeft: 8, fontSize: '0.7rem' }}>Retrain recommended</Tag>)}</div></div>
              </div>
              <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: '#c4b5fd' }}>Automatic model check</div>
                <div style={{ marginBottom: 10, color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>These values control when the system checks if the model should be updated.</div>
                <Row gutter={12}><Col xs={24} md={12}><Form.Item label="New crime reports needed"><InputNumber min={1} max={100000} value={settings.modelWatcherRetrainThresholdNewCrimes} onChange={(v) => handleSettingChange('modelWatcherRetrainThresholdNewCrimes', v)} style={{ width: '100%' }} /></Form.Item></Col><Col xs={24} md={12}><Form.Item label="New areas needed"><InputNumber min={1} max={10000} value={settings.modelWatcherRetrainThresholdNewAreas} onChange={(v) => handleSettingChange('modelWatcherRetrainThresholdNewAreas', v)} style={{ width: '100%' }} /></Form.Item></Col></Row>
                <Row gutter={12}><Col xs={24} md={12}><Form.Item label="New crime types needed"><InputNumber min={1} max={10000} value={settings.modelWatcherRetrainThresholdNewCrimeTypes} onChange={(v) => handleSettingChange('modelWatcherRetrainThresholdNewCrimeTypes', v)} style={{ width: '100%' }} /></Form.Item></Col><Col xs={24} md={12}><Form.Item label="Check every (seconds)"><InputNumber min={10} max={86400} value={settings.modelWatcherCheckIntervalSeconds} onChange={(v) => handleSettingChange('modelWatcherCheckIntervalSeconds', v)} style={{ width: '100%' }} /></Form.Item></Col></Row>
                <Form.Item label="Maximum training time (seconds)"><InputNumber min={30} max={7200} value={settings.modelWatcherRetrainTimeoutSeconds} onChange={(v) => handleSettingChange('modelWatcherRetrainTimeoutSeconds', v)} style={{ width: '100%' }} /></Form.Item>
              </div>
              <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: '#93c5fd' }}>Auto-retrain rules</div>
                <div style={{ marginBottom: 10, color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>These values control when the system retrains automatically after new records arrive.</div>
                <Row gutter={12}><Col xs={24} md={12}><Form.Item label="Unknown area + crime pairs"><InputNumber min={1} max={10000} value={settings.autoRetrainOovPairThreshold} onChange={(v) => handleSettingChange('autoRetrainOovPairThreshold', v)} style={{ width: '100%' }} /></Form.Item></Col><Col xs={24} md={12}><Form.Item label="New records needed"><InputNumber min={1} max={100000} value={settings.autoRetrainNewRecordThreshold} onChange={(v) => handleSettingChange('autoRetrainNewRecordThreshold', v)} style={{ width: '100%' }} /></Form.Item></Col></Row>
                <Form.Item label="Minimum time between retrains (seconds)"><InputNumber min={30} max={86400} value={settings.autoRetrainMinIntervalSeconds} onChange={(v) => handleSettingChange('autoRetrainMinIntervalSeconds', v)} style={{ width: '100%' }} /></Form.Item>
              </div>
              <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: '#fca5a5' }}>OCR</div>
                <Form.Item label={<span>OCR translation timeout (seconds) <Tooltip title="How long the system waits for the language helper before stopping"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={1} max={60} value={settings.ocrTransliterationTimeoutSeconds} onChange={(v) => handleSettingChange('ocrTransliterationTimeoutSeconds', v)} style={{ width: '100%' }} /></Form.Item>
              </div>
              {retrainMsg && (<div style={{ marginTop: 12, marginBottom: 12, padding: '8px 12px', borderRadius: 8, fontSize: '0.83rem', background: retrainMsg.type === 'success' ? 'rgba(34,197,94,0.1)' : 'rgba(220,38,38,0.1)', border: `1px solid ${retrainMsg.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(220,38,38,0.3)'}`, color: retrainMsg.type === 'success' ? '#22c55e' : '#ef4444' }}><i className={`fas ${retrainMsg.type === 'success' ? 'fa-circle-check' : 'fa-circle-xmark'}`} style={{ marginRight: 6 }}></i>{retrainMsg.text}</div>)}
              <Button type="primary" loading={retraining} onClick={handleRetrain} icon={<ReloadOutlined />} style={{ width: '100%', borderRadius: 8, background: '#7c3aed', borderColor: '#7c3aed' }}>{retraining ? 'Retraining Model…' : 'Retrain Model Now'}</Button>
              <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', textAlign: 'center' }}>Triggers a fresh Poisson + Random Forest ensemble training run on all current FIR data.</div>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'system',
      label: (<span><SettingOutlined style={{ marginRight: 8 }} />System State</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={24}>
            <Card title={<div className={styles.cardTitle}><SettingOutlined style={{ color: '#f9a826' }} /> System State</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <div style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#86efac' }}>Maintenance</div>
                  <Form.Item label={<span>Maintenance mode <Tooltip title="Pause the system for normal users"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><Switch checked={settings.maintenanceMode} onChange={(c) => handleSettingChange('maintenanceMode', c)} checkedChildren="ON" unCheckedChildren="OFF" /><Tag color={settings.maintenanceMode ? 'orange' : 'green'}>{settings.maintenanceMode ? 'Maintenance on' : 'System on'}</Tag></div></Form.Item>
                  <Form.Item label="Logging detail"><Select value={settings.logLevel} onChange={(v) => handleSettingChange('logLevel', v)} style={{ width: '100%' }}><Option value="debug">Debug</Option><Option value="info">Normal</Option><Option value="warning">Warnings</Option><Option value="error">Errors only</Option></Select></Form.Item>
                  <Form.Item label={<span>Keep old records for (days) <Tooltip title="Older crime data and logs are removed after this many days"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}><InputNumber min={30} max={365} value={settings.dataRetentionDays} onChange={(v) => handleSettingChange('dataRetentionDays', v)} style={{ width: '100%' }} /></Form.Item>
                </div>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
  ];
  return (
    <div className={styles.sectionContainer}>
      {/* Header */}
      <div className={styles.sectionHeader} style={{ flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h2><SettingOutlined style={{ marginRight: 10 }} />System Settings</h2>
          <p className={styles.sectionDescription} style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 6 }}>
            Configure security, alerts, map, and system parameters
            <Tag icon={<CheckCircleOutlined />} color="success" style={{ marginLeft: 4 }}>Connected</Tag>
            {lastSaved && (
              <span style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.45)' }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                Last saved {formatDate(lastSaved)}{lastSavedBy ? ` by ${lastSavedBy}` : ''}
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Button
            icon={<ThunderboltOutlined />}
            loading={applyingRuntime}
            disabled={saving}
            onClick={handleApplyRuntimeNow}
            style={{ borderRadius: 10 }}
          >
            Apply Runtime Now
          </Button>
          {hasChanges && (
            <Badge dot color="#f9a826" offset={[0, 0]}>
              <Button icon={<ReloadOutlined />} onClick={() => { setSettings({ ...savedSettings }); }} style={{ borderRadius: 10 }}>
                Discard
              </Button>
            </Badge>
          )}
          <Button
            type="primary"
            size="large"
            loading={saving}
            disabled={!hasChanges}
            onClick={handleSaveSettings}
            icon={<SaveOutlined />}
            style={{ borderRadius: 10, minWidth: 160 }}
          >
            {hasChanges ? 'Save Changes' : 'All Saved'}
          </Button>
        </div>
      </div>

      {hasChanges && (
        <div style={{ background: 'rgba(249,168,38,0.08)', border: '1px solid rgba(249,168,38,0.25)', borderRadius: 10, padding: '8px 16px', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.88rem', color: '#f9a826' }}>
          <InfoCircleOutlined /> You have unsaved changes
        </div>
      )}

      <Tabs defaultActiveKey="security" size="large" items={tabItems} />

      {/* Bottom save */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Button
          icon={<ThunderboltOutlined />}
          loading={applyingRuntime}
          disabled={saving}
          onClick={handleApplyRuntimeNow}
          style={{ borderRadius: 10, marginRight: 10 }}
        >
          Apply Runtime Now
        </Button>
        <Button
          type="primary"
          size="large"
          loading={saving}
          disabled={!hasChanges}
          onClick={handleSaveSettings}
          icon={<SaveOutlined />}
          style={{ borderRadius: 10, minWidth: 160 }}
        >
          {hasChanges ? 'Save Changes' : 'All Saved'}
        </Button>
      </div>
    </div>
  );
};

export default SystemSettings;
