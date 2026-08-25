import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Alert, Button, Form, Input, Modal, Progress, Space, Typography, message } from 'antd';
import {
  ClockCircleOutlined,
  KeyOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import apiService from '../../services/apiService';
import { useAuth } from '../../contexts/AuthContext';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';

const { Text } = Typography;

const SNOOZE_KEY = 'safevision.pwChangeSnoozed';

const evaluateStrength = (pw, minLen) => {
  if (!pw) return { score: 0, label: 'Empty' };
  let score = 0;
  if (pw.length >= minLen) score += 25;
  if (/[a-z]/.test(pw)) score += 15;
  if (/[A-Z]/.test(pw)) score += 20;
  if (/[0-9]/.test(pw)) score += 15;
  if (/[^A-Za-z0-9]/.test(pw)) score += 25;
  let label = 'Weak';
  if (score >= 90) label = 'Excellent';
  else if (score >= 70) label = 'Strong';
  else if (score >= 50) label = 'Fair';
  return { score: Math.min(100, score), label };
};

/**
 * Non-blocking password change modal that surfaces on first login.
 * - "Change Now" → opens password fields, validates, calls /auth/force-change-password.
 * - "Remind Me Later" → snoozes for the current session (sessionStorage).
 * The reminder will not appear again on subsequent logins once the password has been changed
 * (the backend clears `password_must_change`).
 */
const AdminPasswordChangeReminder = ({ open, onClose, onChanged }) => {
  const { token, user, updateUser } = useAuth();
  const { settings } = useSystemSettings();
  const [form] = Form.useForm();
  const [stage, setStage] = useState('intro'); // 'intro' | 'change'
  const [submitting, setSubmitting] = useState(false);
  const [strength, setStrength] = useState({ score: 0, label: 'Empty' });

  const role = user?.role || 'admin';
  const minLen = useMemo(() => {
    if (role === 'superadmin') return settings?.superadmin_password_min_length ?? 12;
    return settings?.admin_password_min_length ?? 10;
  }, [role, settings]);

  useEffect(() => {
    if (!open) {
      setStage('intro');
      form.resetFields();
      setStrength({ score: 0, label: 'Empty' });
    }
  }, [open, form]);

  const handleSnooze = () => {
    sessionStorage.setItem(SNOOZE_KEY, '1');
    onClose?.();
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      await apiService.forceChangePassword(token, values.newPassword, values.confirmPassword);
      message.success('Password updated. You will not see this prompt on future logins.');
      sessionStorage.removeItem(SNOOZE_KEY);
      if (user && updateUser) {
        updateUser({ ...user, password_must_change: false });
      }
      onChanged?.();
      onClose?.();
    } catch (err) {
      message.error(err?.message || 'Failed to update password');
    } finally {
      setSubmitting(false);
    }
  };

  const strengthColor =
    strength.score >= 90 ? '#1dd1a1' : strength.score >= 70 ? '#3b82f6' : strength.score >= 50 ? '#f9a826' : '#ff6b6b';

  return (
    <Modal
      title={
        <Space>
          <SafetyCertificateOutlined style={{ color: '#f9a826' }} />
          <span style={{ color: '#e0e0e0', fontWeight: 600 }}>
            {stage === 'intro' ? 'Secure your account' : 'Choose a new password'}
          </span>
        </Space>
      }
      open={open}
      onCancel={handleSnooze}
      maskClosable={false}
      footer={null}
      destroyOnHidden
      width={520}
      styles={{
        content: { background: 'rgba(13,20,30,0.98)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 16 },
        header: { background: 'transparent', borderBottom: '1px solid rgba(255,255,255,0.08)' },
        body: { padding: 24 },
      }}
    >
      {stage === 'intro' ? (
        <div>
          <Alert
            message="Temporary password detected"
            description={
              <Text style={{ color: 'rgba(255,255,255,0.75)' }}>
                Your account is using the password set by your SuperAdmin during registration. For your security, please
                change it to a private password that only you know. You can also do this later from your profile menu.
              </Text>
            }
            type="warning"
            showIcon
            style={{
              background: 'rgba(249,168,38,0.08)',
              border: '1px solid rgba(249,168,38,0.25)',
              borderRadius: 12,
              marginBottom: 20,
            }}
          />

          <div
            style={{
              display: 'flex',
              gap: 12,
              padding: '12px 14px',
              borderRadius: 12,
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.03)',
              marginBottom: 12,
            }}
          >
            <KeyOutlined style={{ color: '#2d7fb8', fontSize: 18, marginTop: 2 }} />
            <div>
              <Text strong style={{ color: '#e0e0e0', display: 'block' }}>Why this matters</Text>
              <Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
                The temporary password may have been seen by whoever set up your account. Changing it ensures only you
                can authenticate as {user?.username || 'this admin'}.
              </Text>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
            <Button onClick={handleSnooze} icon={<ClockCircleOutlined />}>
              Remind Me Later
            </Button>
            <Button
              type="primary"
              icon={<LockOutlined />}
              onClick={() => setStage('change')}
              style={{ background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)', border: 'none' }}
            >
              Change Now
            </Button>
          </div>
        </div>
      ) : (
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="newPassword"
            label={<span style={{ color: '#d0d0d0' }}>New Password</span>}
            rules={[
              { required: true, message: 'Please enter a new password' },
              { min: minLen, message: `Must be at least ${minLen} characters` },
              {
                validator(_, value) {
                  if (!value) return Promise.resolve();
                  const re = new RegExp(`^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{${minLen},}$`);
                  return re.test(value)
                    ? Promise.resolve()
                    : Promise.reject(new Error('Must include uppercase, lowercase, number and special character'));
                },
              },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Enter new password"
              size="large"
              onChange={(e) => setStrength(evaluateStrength(e.target.value, minLen))}
            />
          </Form.Item>

          <div style={{ marginTop: -8, marginBottom: 14 }}>
            <Progress
              percent={strength.score}
              showInfo={false}
              strokeColor={strengthColor}
              trailColor="rgba(255,255,255,0.08)"
              size="small"
            />
            <Text style={{ color: 'rgba(255,255,255,0.55)', fontSize: 12 }}>
              Strength: <span style={{ color: strengthColor, fontWeight: 600 }}>{strength.label}</span>
            </Text>
          </div>

          <Form.Item
            name="confirmPassword"
            label={<span style={{ color: '#d0d0d0' }}>Confirm Password</span>}
            dependencies={['newPassword']}
            rules={[
              { required: true, message: 'Please confirm your new password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) return Promise.resolve();
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Re-enter password" size="large" />
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
            <Button onClick={() => setStage('intro')}>Back</Button>
            <Space wrap>
              <Button onClick={handleSnooze} icon={<ClockCircleOutlined />} disabled={submitting}>
                Remind Me Later
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                icon={<LockOutlined />}
                loading={submitting}
                style={{ background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)', border: 'none' }}
              >
                Update Password
              </Button>
            </Space>
          </div>
        </Form>
      )}
    </Modal>
  );
};

AdminPasswordChangeReminder.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onChanged: PropTypes.func,
};

export const isPwChangeSnoozed = () => sessionStorage.getItem(SNOOZE_KEY) === '1';
export const clearPwSnooze = () => sessionStorage.removeItem(SNOOZE_KEY);

export default AdminPasswordChangeReminder;
