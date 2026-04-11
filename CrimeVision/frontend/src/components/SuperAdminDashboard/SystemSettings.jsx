import React, { useState, useEffect, useCallback } from 'react';
import { Card, Row, Col, Form, Select, Switch, Button, message, Spin, Tabs, InputNumber, Slider, Tag, Tooltip, Badge } from 'antd';
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
  max_login_attempts: { state: 'maxLoginAttempts', type: 'number' },
  lockout_duration: { state: 'lockoutDuration', type: 'number' },
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
  default_map_zoom: { state: 'defaultMapZoom', type: 'number' },
  heatmap_radius: { state: 'heatmapRadius', type: 'number' },
  heatmap_intensity: { state: 'heatmapIntensity', type: 'float' },
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
  maxLoginAttempts: 5,
  lockoutDuration: 30,
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
  defaultMapZoom: 12,
  heatmapRadius: 20,
  heatmapIntensity: 0.5,
  dataRetentionDays: 90,
  logLevel: 'info',
  maintenanceMode: false,
};

const SystemSettings = () => {
  const { token } = useAuth();
  const { refreshSettings } = useSystemSettings();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({ ...DEFAULTS });
  const [lastSaved, setLastSaved] = useState(null);
  const [lastSavedBy, setLastSavedBy] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [savedSettings, setSavedSettings] = useState({ ...DEFAULTS });
  const [modelMeta, setModelMeta]       = useState(null);
  const [retraining, setRetraining]     = useState(false);
  const [retrainMsg, setRetrainMsg]     = useState(null);

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
      const res = await apiService.triggerRetrain(token);
      const newDate = res?.last_train_date || new Date().toISOString().slice(0, 10);
      setModelMeta(prev => ({ ...prev, last_train_date: newDate, records_since_last_train: 0 }));
      setRetrainMsg({ type: 'success', text: res?.message || 'Model retrained successfully.' });
    } catch (err) {
      setRetrainMsg({ type: 'error', text: err?.message || 'Retraining failed. Check backend logs.' });
    } finally {
      setRetraining(false);
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
    } catch (error) {
      console.error('Error saving system settings:', error);
      message.error('Failed to save system settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
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
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><LockOutlined style={{ color: '#f9a826' }} /> Authentication</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label={<span>Session Timeout (minutes) <Tooltip title="Admin sessions expire after this many minutes of inactivity"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={5} max={120} value={settings.sessionTimeout} onChange={(v) => handleSettingChange('sessionTimeout', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Max Login Attempts <Tooltip title="Lock the account after this many consecutive failed login attempts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={3} max={10} value={settings.maxLoginAttempts} onChange={(v) => handleSettingChange('maxLoginAttempts', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Lockout Duration (minutes) <Tooltip title="How long to lock an account after exceeding max failed attempts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={5} max={120} value={settings.lockoutDuration} onChange={(v) => handleSettingChange('lockoutDuration', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>User Min Password Length <Tooltip title="Minimum characters required when a regular user registers or resets their password"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={6} max={20} value={settings.passwordMinLength} onChange={(v) => handleSettingChange('passwordMinLength', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Admin Min Password Length <Tooltip title="Minimum characters required when an Admin account is created or password is changed"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={8} max={32} value={settings.adminPasswordMinLength} onChange={(v) => handleSettingChange('adminPasswordMinLength', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>SuperAdmin Min Password Length <Tooltip title="Minimum characters required for SuperAdmin passwords (must also include special character)"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={10} max={32} value={settings.superadminPasswordMinLength} onChange={(v) => handleSettingChange('superadminPasswordMinLength', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Require Two-Factor Authentication <Tooltip title="Force all admin users to enable TOTP-based 2FA"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Switch checked={settings.requireTwoFactor} onChange={(c) => handleSettingChange('requireTwoFactor', c)} />
                    <Tag color={settings.requireTwoFactor ? 'green' : 'default'}>{settings.requireTwoFactor ? 'Enforced' : 'Optional'}</Tag>
                  </div>
                </Form.Item>
              </Form>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><AlertOutlined style={{ color: '#f9a826' }} /> Notification Preferences</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label="Alert Threshold">
                  <Select value={settings.alertThreshold} onChange={(v) => handleSettingChange('alertThreshold', v)} style={{ width: '100%' }}>
                    <Option value="low">Low — All Alerts</Option>
                    <Option value="medium">Medium — Important Only</Option>
                    <Option value="high">High — Critical Only</Option>
                  </Select>
                </Form.Item>
                <Form.Item label={<span>Notification Radius (km) <Tooltip title="Radius around a point of interest for triggering alerts"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <Slider min={1} max={20} value={settings.notificationRadius} onChange={(v) => handleSettingChange('notificationRadius', v)} marks={{ 1: '1 km', 5: '5 km', 10: '10 km', 20: '20 km' }} />
                </Form.Item>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },

    {
      key: 'map',
      label: (<span><EnvironmentOutlined style={{ marginRight: 8 }} />Map &amp; Visualization</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><EnvironmentOutlined style={{ color: '#f9a826' }} /> Map Defaults</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label={<span>Default Map Zoom <Tooltip title="Initial zoom level when the crime map loads"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <Slider min={8} max={18} value={settings.defaultMapZoom} onChange={(v) => handleSettingChange('defaultMapZoom', v)} marks={{ 8: 'City', 12: 'District', 15: 'Street', 18: 'Block' }} />
                </Form.Item>
                <Form.Item label="Heatmap Radius (px)">
                  <Slider min={10} max={50} value={settings.heatmapRadius} onChange={(v) => handleSettingChange('heatmapRadius', v)} marks={{ 10: '10', 20: '20', 30: '30', 50: '50' }} />
                </Form.Item>
                <Form.Item label="Heatmap Intensity">
                  <Slider min={0.1} max={1} step={0.1} value={settings.heatmapIntensity} onChange={(v) => handleSettingChange('heatmapIntensity', v)} marks={{ 0.1: 'Low', 0.5: 'Med', 1: 'High' }} />
                </Form.Item>
              </Form>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><AlertOutlined style={{ color: '#f9a826' }} /> Alert Thresholds</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label={<span>High Risk Threshold (%) <Tooltip title="Crime prediction score above this value is flagged as High Risk"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={50} max={100} value={settings.highRiskThreshold} onChange={(v) => handleSettingChange('highRiskThreshold', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Medium Risk Threshold (%) <Tooltip title="Score above this value but below high risk is flagged Medium"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={20} max={70} value={settings.mediumRiskThreshold} onChange={(v) => handleSettingChange('mediumRiskThreshold', v)} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label={<span>Auto Alert Generation <Tooltip title="Automatically create alerts when crime predictions exceed thresholds"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Switch checked={settings.autoAlertGeneration} onChange={(c) => handleSettingChange('autoAlertGeneration', c)} />
                    <Tag color={settings.autoAlertGeneration ? 'green' : 'default'}>{settings.autoAlertGeneration ? 'Active' : 'Disabled'}</Tag>
                  </div>
                </Form.Item>
                <Form.Item label={<span>Alert Cooldown (minutes) <Tooltip title="Minimum interval before a new alert can be generated for the same area"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={15} max={180} value={settings.alertCooldownMinutes} onChange={(v) => handleSettingChange('alertCooldownMinutes', v)} style={{ width: '100%' }} />
                </Form.Item>
              </Form>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'system',
      label: (<span><SettingOutlined style={{ marginRight: 8 }} />System &amp; Maintenance</span>),
      children: (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={12}>
            <Card title={<div className={styles.cardTitle}><ThunderboltOutlined style={{ color: '#f9a826' }} /> Operational</div>} className={styles.settingsCard}>
              <Form layout="vertical">
                <Form.Item label={<span>Maintenance Mode <Tooltip title="Restrict system access to admins only — users will see a maintenance page"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Switch checked={settings.maintenanceMode} onChange={(c) => handleSettingChange('maintenanceMode', c)} checkedChildren="ON" unCheckedChildren="OFF" />
                    <Tag color={settings.maintenanceMode ? 'orange' : 'green'}>{settings.maintenanceMode ? 'Maintenance Active' : 'System Online'}</Tag>
                  </div>
                </Form.Item>
                <Form.Item label="Log Level">
                  <Select value={settings.logLevel} onChange={(v) => handleSettingChange('logLevel', v)} style={{ width: '100%' }}>
                    <Option value="debug">Debug — All Logs</Option>
                    <Option value="info">Info — Standard Logs</Option>
                    <Option value="warning">Warning — Warnings &amp; Errors</Option>
                    <Option value="error">Error — Errors Only</Option>
                  </Select>
                </Form.Item>
                <Form.Item label={<span>Data Retention (days) <Tooltip title="Historical crime data and audit logs older than this will be purged"><InfoCircleOutlined style={{ marginLeft: 6, color: 'rgba(255,255,255,0.35)' }} /></Tooltip></span>}>
                  <InputNumber min={30} max={365} value={settings.dataRetentionDays} onChange={(v) => handleSettingChange('dataRetentionDays', v)} style={{ width: '100%' }} />
                </Form.Item>
              </Form>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              title={<div className={styles.cardTitle}><ThunderboltOutlined style={{ color: '#a78bfa' }} /> Model Management</div>}
              className={styles.settingsCard}
            >
              {/* Stats row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div style={{ background: 'rgba(167,139,250,0.08)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: 8, padding: '10px 14px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>Last Trained</div>
                  <div style={{ fontWeight: 700, color: '#a78bfa', fontSize: '0.92rem' }}>
                    {modelMeta?.last_train_date || '—'}
                  </div>
                </div>
                <div style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: '10px 14px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>Total FIR Records</div>
                  <div style={{ fontWeight: 700, color: '#3b82f6', fontSize: '0.92rem' }}>
                    {modelMeta?.total_records != null ? modelMeta.total_records.toLocaleString() : '—'}
                  </div>
                </div>
                <div style={{ background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: 8, padding: '10px 14px', gridColumn: '1 / -1' }}>
                  <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', marginBottom: 4 }}>New Records Since Last Train</div>
                  <div style={{ fontWeight: 700, color: modelMeta?.records_since_last_train > 500 ? '#f97316' : '#22c55e', fontSize: '0.92rem' }}>
                    {modelMeta?.records_since_last_train != null ? modelMeta.records_since_last_train.toLocaleString() : '—'}
                    {modelMeta?.records_since_last_train > 500 && (
                      <Tag color="orange" style={{ marginLeft: 8, fontSize: '0.7rem' }}>Retrain Recommended</Tag>
                    )}
                  </div>
                </div>
              </div>

              {/* Retrain button + feedback */}
              {retrainMsg && (
                <div style={{
                  marginBottom: 12, padding: '8px 12px', borderRadius: 8, fontSize: '0.83rem',
                  background: retrainMsg.type === 'success' ? 'rgba(34,197,94,0.1)' : 'rgba(220,38,38,0.1)',
                  border: `1px solid ${retrainMsg.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(220,38,38,0.3)'}`,
                  color: retrainMsg.type === 'success' ? '#22c55e' : '#ef4444',
                }}>
                  <i className={`fas ${retrainMsg.type === 'success' ? 'fa-circle-check' : 'fa-circle-xmark'}`} style={{ marginRight: 6 }}></i>
                  {retrainMsg.text}
                </div>
              )}
              <Button
                type="primary"
                loading={retraining}
                onClick={handleRetrain}
                icon={<ReloadOutlined />}
                style={{ width: '100%', borderRadius: 8, background: '#7c3aed', borderColor: '#7c3aed' }}
              >
                {retraining ? 'Retraining Model…' : 'Retrain Model Now'}
              </Button>
              <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', textAlign: 'center' }}>
                Triggers a fresh Poisson + Random Forest ensemble training run on all current FIR data.
              </div>
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
