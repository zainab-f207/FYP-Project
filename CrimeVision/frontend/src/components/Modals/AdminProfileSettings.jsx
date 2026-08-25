import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Alert,
  Avatar,
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  Progress,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CrownOutlined,
  KeyOutlined,
  LockOutlined,
  MailOutlined,
  PhoneOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import apiService from '../../services/apiService';
import { useAuth } from '../../contexts/AuthContext';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';

const { Text, Title } = Typography;

const evaluate = (pw, minLen) => {
  if (!pw) return 0;
  let s = 0;
  if (pw.length >= minLen) s += 25;
  if (/[a-z]/.test(pw)) s += 15;
  if (/[A-Z]/.test(pw)) s += 20;
  if (/[0-9]/.test(pw)) s += 15;
  if (/[^A-Za-z0-9]/.test(pw)) s += 25;
  return Math.min(100, s);
};

const AdminProfileSettings = ({ open, onClose }) => {
  const { token, user, updateUser, logout } = useAuth();
  const { settings } = useSystemSettings();
  const [pwForm] = Form.useForm();
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [pwStrength, setPwStrength] = useState(0);

  const role = user?.role || 'admin';
  const minLen = useMemo(() => {
    if (role === 'superadmin') return settings?.superadmin_password_min_length ?? 12;
    return settings?.admin_password_min_length ?? 10;
  }, [role, settings]);

  useEffect(() => {
    if (!open) {
      pwForm.resetFields();
      setPwStrength(0);
    }
  }, [open, pwForm]);

  const handleChangePassword = async (values) => {
    setPwSubmitting(true);
    try {
      await apiService.forceChangePassword(token, values.newPassword, values.confirmPassword);
      message.success('Password updated successfully');
      pwForm.resetFields();
      setPwStrength(0);
      if (user && updateUser) {
        updateUser({ ...user, password_must_change: false });
      }
    } catch (err) {
      message.error(err?.message || 'Failed to update password');
    } finally {
      setPwSubmitting(false);
    }
  };

  const fullName = `${user?.first_name || user?.firstName || ''} ${user?.last_name || user?.lastName || ''}`.trim() || user?.username || '—';
  const initials = (fullName || 'A').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();
  const avatarBg = role === 'superadmin' ? '#8B4513' : '#1a4f72';
  const isSuperAdmin = role === 'superadmin';

  const strengthColor =
    pwStrength >= 90 ? '#1dd1a1' : pwStrength >= 70 ? '#3b82f6' : pwStrength >= 50 ? '#f9a826' : '#ff6b6b';

  return (
    <Drawer
      title={
        <Space>
          <UserOutlined style={{ color: '#f9a826' }} />
          <span style={{ color: '#e0e0e0', fontWeight: 600 }}>Profile Settings</span>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={520}
      styles={{
        header: { background: 'rgba(10,10,15,0.98)', borderBottom: '1px solid rgba(255,255,255,0.08)' },
        body: { background: 'rgba(10,10,15,0.98)', padding: '20px 24px' },
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: 16,
          alignItems: 'center',
          padding: '16px 18px',
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.08)',
          background: 'linear-gradient(135deg, rgba(26,79,114,0.18), rgba(45,127,184,0.08))',
          marginBottom: 18,
        }}
      >
        <Avatar size={64} style={{ background: avatarBg, color: '#fff', fontSize: 24, fontWeight: 700 }}>
          {initials}
        </Avatar>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Title level={5} style={{ color: '#e0e0e0', margin: 0, lineHeight: 1.2 }}>
            {fullName}
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.55)', fontSize: 13 }}>
            @{user?.username || '—'}
          </Text>
          <div style={{ marginTop: 6 }}>
            <Tag
              color={isSuperAdmin ? 'gold' : 'blue'}
              icon={isSuperAdmin ? <CrownOutlined /> : <SafetyCertificateOutlined />}
            >
              {isSuperAdmin ? 'Super Administrator' : 'Administrator'}
            </Tag>
            {user?.password_must_change && (
              <Tag color="orange" style={{ marginLeft: 4 }}>
                Password change pending
              </Tag>
            )}
          </div>
        </div>
      </div>

      <Tabs
        defaultActiveKey="info"
        items={[
          {
            key: 'info',
            label: (
              <span>
                <UserOutlined /> Profile
              </span>
            ),
            children: (
              <Descriptions
                bordered
                column={1}
                size="small"
                styles={{
                  label: { color: '#f9a826', background: 'rgba(255,255,255,0.04)', fontWeight: 500, width: 130 },
                  content: { color: '#d0d0d0', background: 'rgba(255,255,255,0.02)' },
                }}
              >
                <Descriptions.Item label={<><UserOutlined /> Username</>}>
                  {user?.username || '—'}
                </Descriptions.Item>
                <Descriptions.Item label={<><MailOutlined /> Email</>}>
                  {user?.email || '—'}
                </Descriptions.Item>
                <Descriptions.Item label={<><PhoneOutlined /> Phone</>}>
                  {user?.phone_number || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Role">
                  <Tag color={isSuperAdmin ? 'gold' : 'blue'}>{role.toUpperCase()}</Tag>
                </Descriptions.Item>
                {user?.department && (
                  <Descriptions.Item label="Department">
                    <Tag color="cyan">{user.department}</Tag>
                  </Descriptions.Item>
                )}
                {Array.isArray(user?.permissions) && user.permissions.length > 0 && (
                  <Descriptions.Item label="Permissions">
                    <Space wrap>
                      {user.permissions.map((p) => (
                        <Tag key={p} color="blue" style={{ fontSize: 11 }}>{p}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                )}
              </Descriptions>
            ),
          },
          {
            key: 'security',
            label: (
              <span>
                <KeyOutlined /> Change Password
              </span>
            ),
            children: (
              <div>
                {user?.password_must_change && (
                  <Alert
                    type="warning"
                    showIcon
                    message="Temporary password in use"
                    description="Please change your password to a private one — your current password was set by SuperAdmin during registration."
                    style={{
                      background: 'rgba(249,168,38,0.08)',
                      border: '1px solid rgba(249,168,38,0.25)',
                      borderRadius: 12,
                      marginBottom: 14,
                    }}
                  />
                )}
                <Form form={pwForm} layout="vertical" onFinish={handleChangePassword}>
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
                      onChange={(e) => setPwStrength(evaluate(e.target.value, minLen))}
                    />
                  </Form.Item>
                  <div style={{ marginTop: -8, marginBottom: 14 }}>
                    <Progress
                      percent={pwStrength}
                      showInfo={false}
                      strokeColor={strengthColor}
                      trailColor="rgba(255,255,255,0.08)"
                      size="small"
                    />
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
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<LockOutlined />}
                    loading={pwSubmitting}
                    block
                    size="large"
                    style={{ background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)', border: 'none', fontWeight: 600 }}
                  >
                    Update Password
                  </Button>
                </Form>
              </div>
            ),
          },
          {
            key: 'session',
            label: (
              <span>
                <SafetyCertificateOutlined /> Session
              </span>
            ),
            children: (
              <div>
                <Alert
                  type="info"
                  showIcon
                  message="Active session"
                  description="Sign out from this drawer to end your current session immediately. You will be redirected to the login page."
                  style={{
                    background: 'rgba(45,127,184,0.08)',
                    border: '1px solid rgba(45,127,184,0.25)',
                    borderRadius: 12,
                    marginBottom: 14,
                  }}
                />
                <Button danger block size="large" onClick={() => logout()}>
                  Sign out of this session
                </Button>
              </div>
            ),
          },
        ]}
      />
    </Drawer>
  );
};

AdminProfileSettings.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default AdminProfileSettings;
