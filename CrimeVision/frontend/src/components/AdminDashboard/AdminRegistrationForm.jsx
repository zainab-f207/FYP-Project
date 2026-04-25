import React, { useState, useMemo, useCallback } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Select,
  Space,
  Typography,
  message,
  Divider,
  Alert,
} from 'antd';
import {
  UserAddOutlined,
  MailOutlined,
  LockOutlined,
  PhoneOutlined,
  HomeOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import styles from '../SuperAdminDashboard/SuperAdminDashboard.module.css';
import { useSystemSettings } from '../../contexts/SystemSettingsContext';
import PermissionMatrix from '../SuperAdminDashboard/PermissionMatrix';
import {
  DEPARTMENTS as SHARED_DEPARTMENTS,
  DEPARTMENT_PERMISSIONS as SHARED_DEPARTMENT_PERMISSIONS,
} from '../SuperAdminDashboard/constants/adminPermissions';

const { Text } = Typography;
const { Option } = Select;

const DEPARTMENTS = SHARED_DEPARTMENTS;
const DEPARTMENT_PERMISSIONS = SHARED_DEPARTMENT_PERMISSIONS;

const AdminRegistrationForm = () => {
  const [form] = Form.useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedDept, setSelectedDept] = useState(null);
  const { token } = useAuth();
  const { settings: sysSettings } = useSystemSettings();
  const adminMinLen = sysSettings?.admin_password_min_length ?? 10;

  // Recommended permissions for currently selected department
  const recommendedPerms = useMemo(
    () => (selectedDept ? DEPARTMENT_PERMISSIONS[selectedDept] || [] : []),
    [selectedDept]
  );

  // Handle department change — merge recommended into current selection (does not erase existing picks)
  const handleDepartmentChange = useCallback(
    (dept) => {
      setSelectedDept(dept);
      const suggested = DEPARTMENT_PERMISSIONS[dept] || [];
      const current = form.getFieldValue('permissions') || [];
      const merged = Array.from(new Set([...current, ...suggested]));
      form.setFieldsValue({ permissions: merged });
      message.info(`Recommended permissions for ${dept} added. Feel free to add or remove any permission below — recommendations are only suggestions.`);
    },
    [form]
  );

  // Handle form submission
  const onFinish = async (values) => {
    setIsSubmitting(true);
    try {
      const adminData = {
        name: values.name,
        email: values.email,
        password: values.password,
        department: values.department,
        permissions: values.permissions || [],
        phone: values.phone,
        address: values.address,
      };

      await apiService.registerAdmin(adminData, token);
      message.success('Admin registered successfully! They can now log in with the provided credentials.');
      form.resetFields();
      setSelectedDept(null);
    } catch (err) {
      console.error('Admin registration error:', err);
      message.error(err.message || 'Failed to register admin. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.sectionContainer}>
      <div className={styles.sectionHeader}>
        <div>
          <h2>Register New Administrator</h2>
          <p className={styles.sectionDescription}>
            Create a new administrator account with department-specific permissions and access control.
          </p>
        </div>
      </div>

      <Card className={styles.formCard} variant="borderless">
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          requiredMark="optional"
          initialValues={{ permissions: [] }}
        >
          {/* ── Section 1: Personal Information ── */}
          <Divider orientation="left" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
            <Space>
              <UserAddOutlined style={{ color: '#f9a826' }} />
              <span style={{ color: '#e0e0e0', fontWeight: 600 }}>Personal Information</span>
            </Space>
          </Divider>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item
                name="name"
                label="Full Name"
                rules={[{ required: true, message: 'Please enter full name' }]}
              >
                <Input prefix={<UserAddOutlined />} placeholder="Enter full name" size="large" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="email"
                label="Official Email Address"
                rules={[
                  { required: true, message: 'Please enter email' },
                  { type: 'email', message: 'Please enter a valid email' },
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder="admin@SafeVision.gov.pk" size="large" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item
                name="password"
                label="Password"
                rules={[
                  { required: true, message: 'Please enter password' },
                  { min: adminMinLen, message: `Admin password must be at least ${adminMinLen} characters` },
                  {
                    validator(_, value) {
                      if (!value) return Promise.resolve();
                      const re = new RegExp(`^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{${adminMinLen},}$`);
                      return re.test(value)
                        ? Promise.resolve()
                        : Promise.reject(new Error('Must include uppercase, lowercase, number & special character'));
                    },
                  },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Create strong password" size="large" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="confirmPassword"
                label="Confirm Password"
                dependencies={['password']}
                rules={[
                  { required: true, message: 'Please confirm password' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Passwords do not match'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Confirm password" size="large" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item
                name="phone"
                label="Phone Number"
                rules={[{ required: true, message: 'Please enter phone number' }]}
              >
                <Input prefix={<PhoneOutlined />} placeholder="+92 XXX XXXXXXX" size="large" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="address" label="Office Address (Optional)">
                <Input prefix={<HomeOutlined />} placeholder="Enter office address" size="large" />
              </Form.Item>
            </Col>
          </Row>

          {/* ── Section 2: Department Assignment ── */}
          <Divider orientation="left" style={{ borderColor: 'rgba(255,255,255,0.1)', marginTop: 32 }}>
            <Space>
              <TeamOutlined style={{ color: '#f9a826' }} />
              <span style={{ color: '#e0e0e0', fontWeight: 600 }}>Department Assignment</span>
            </Space>
          </Divider>

          <Form.Item
            name="department"
            label="Department"
            rules={[{ required: true, message: 'Please select a department' }]}
            extra={
              <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
                Selecting a department will auto-suggest relevant permissions based on the role.
              </Text>
            }
          >
            <Select
              placeholder="Select Department"
              size="large"
              onChange={handleDepartmentChange}
              optionLabelProp="label"
            >
              {DEPARTMENTS.map((dept) => (
                <Option key={dept.value} value={dept.value} label={dept.label}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
                    <span style={{ fontSize: 20 }}>{dept.icon}</span>
                    <div>
                      <div style={{ fontWeight: 600, color: '#e0e0e0' }}>{dept.label}</div>
                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>{dept.desc}</div>
                    </div>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          {selectedDept && (
            <Alert
              message={`Department: ${selectedDept}`}
              description={`${(DEPARTMENT_PERMISSIONS[selectedDept] || []).length} recommended permissions have been auto-selected for this department. Review and adjust as needed in the permissions section below.`}
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
              style={{
                marginBottom: 24,
                background: 'rgba(26, 79, 114, 0.15)',
                border: '1px solid rgba(45, 127, 184, 0.3)',
                borderRadius: 12,
              }}
            />
          )}

          {/* ── Section 3: Permissions & Access Control ── */}
          <Divider orientation="left" style={{ borderColor: 'rgba(255,255,255,0.1)', marginTop: 32 }}>
            <Space>
              <SafetyCertificateOutlined style={{ color: '#f9a826' }} />
              <span style={{ color: '#e0e0e0', fontWeight: 600 }}>Permissions & Access Control</span>
            </Space>
          </Divider>

          <Alert
            message="All permissions are freely selectable"
            description="Recommendations highlighted with a gold tag are based on the chosen department, but you can check or uncheck ANY permission across ALL categories — independent of the recommendation. Mix and match to build the exact role you need."
            type="success"
            showIcon
            style={{
              marginBottom: 20,
              background: 'rgba(29,209,161,0.08)',
              border: '1px solid rgba(29,209,161,0.25)',
              borderRadius: 12,
            }}
          />

          <Form.Item
            name="permissions"
            rules={[{
              required: true,
              message: 'Please select at least one permission',
              type: 'array',
              min: 1,
            }]}
          >
            <PermissionMatrix recommendedPerms={recommendedPerms} />
          </Form.Item>

          {/* ── Security Notice ── */}
          <Alert
            message="Security Notice"
            description="The new administrator will be required to enable Two-Factor Authentication (2FA) on first login. All admin actions are logged in the audit trail and sensitive operations require SuperAdmin approval."
            type="warning"
            showIcon
            style={{
              marginTop: 16,
              marginBottom: 24,
              background: 'rgba(249, 168, 38, 0.08)',
              border: '1px solid rgba(249, 168, 38, 0.25)',
              borderRadius: 12,
            }}
          />

          {/* ── Submit Button ── */}
          <Form.Item style={{ marginTop: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<CheckCircleOutlined />}
              loading={isSubmitting}
              size="large"
              block
              className={styles.submitButton}
            >
              {isSubmitting ? 'Registering Administrator...' : 'Register Administrator'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default AdminRegistrationForm;
