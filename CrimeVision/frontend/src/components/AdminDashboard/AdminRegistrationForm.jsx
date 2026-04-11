import React, { useState, useMemo, useCallback } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Row,
  Select,
  Space,
  Typography,
  message,
  Divider,
  Tooltip,
  Tag,
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

const { Text } = Typography;
const { Option } = Select;

// ── Government-relevant departments for SafeVision ──
const DEPARTMENTS = [
  { value: 'Law Enforcement Operations', label: 'Law Enforcement Operations', icon: '🛡️', desc: 'Police liaison, crime investigation coordination & field enforcement' },
  { value: 'Crime Analytics & Intelligence', label: 'Crime Analytics & Intelligence', icon: '📊', desc: 'Data analysis, crime pattern recognition & prediction models' },
  { value: 'Emergency Response & Dispatch', label: 'Emergency Response & Dispatch', icon: '🚨', desc: 'Crisis management, emergency coordination & rapid response' },
  { value: 'IT & Cybersecurity', label: 'IT & Cybersecurity', icon: '🔒', desc: 'System administration, network security & technical support' },
  { value: 'Public Safety Communications', label: 'Public Safety Communications', icon: '📡', desc: 'Public outreach, media relations & community alerts' },
  { value: 'Forensics & Evidence Management', label: 'Forensics & Evidence Management', icon: '🔬', desc: 'Evidence handling, forensic analysis & case documentation' },
  { value: 'Strategic Planning & Policy', label: 'Strategic Planning & Policy', icon: '📋', desc: 'Policy development, resource allocation & strategic oversight' },
  { value: 'Community Policing & Outreach', label: 'Community Policing & Outreach', icon: '🤝', desc: 'Community engagement, neighborhood watch & public awareness' },
];

// ── Grouped permissions with categories, icons, and descriptions ──
const PERMISSION_CATEGORIES = [
  {
    category: 'User Management',
    icon: <TeamOutlined />,
    color: '#1a4f72',
    permissions: [
      { value: 'view_users', label: 'View Users', desc: 'View all registered user profiles and details' },
      { value: 'manage_users', label: 'Manage User Accounts', desc: 'Edit user information and account settings' },
      { value: 'suspend_users', label: 'Suspend / Activate Users', desc: 'Temporarily suspend or reactivate user accounts' },
      { value: 'assign_roles', label: 'Assign Roles', desc: 'Change user roles and access levels (requires approval)' },
      { value: 'view_community', label: 'View Community Reports', desc: 'View community-submitted incident reports and posts' },
    ],
  },
  {
    category: 'Crime Data',
    icon: <SafetyCertificateOutlined />,
    color: '#ff6b6b',
    permissions: [
      { value: 'view_crime_data', label: 'View Crime Reports', desc: 'Access all crime reports, incidents & case files' },
      { value: 'manage_crime_data', label: 'Manage Crime Data', desc: 'Create, edit and organize crime records' },
      { value: 'verify_crime_reports', label: 'Verify Crime Reports', desc: 'Review and approve submitted crime reports' },
      { value: 'approve_firs', label: 'Approve FIR Reports', desc: 'Review and approve or reject submitted FIR applications' },
      { value: 'export_crime_data', label: 'Export Crime Data', desc: 'Download crime data in various formats (CSV, PDF)' },
    ],
  },
  {
    category: 'Analytics & Predictions',
    icon: <InfoCircleOutlined />,
    color: '#f9a826',
    permissions: [
      { value: 'view_analytics', label: 'View Analytics', desc: 'Access crime analytics dashboards and visualizations' },
      { value: 'access_predictions', label: 'Access Prediction Models', desc: 'Use AI-based crime prediction and hotspot models' },
      { value: 'generate_reports', label: 'Generate Reports', desc: 'Create custom analytical and summary reports' },
      { value: 'manage_reports', label: 'Manage Reports Dashboard', desc: 'Access and manage the system reports and analytics exports' },
      { value: 'view_heatmaps', label: 'View Crime Heatmaps', desc: 'Access geographic crime heatmap overlays' },
    ],
  },
  {
    category: 'Alerts & Emergency',
    icon: <CheckCircleOutlined />,
    color: '#1dd1a1',
    permissions: [
      { value: 'manage_alerts', label: 'Manage Alerts', desc: 'Configure and send crime alerts to users' },
      { value: 'emergency_dispatch', label: 'Emergency Dispatch', desc: 'Coordinate emergency response dispatches' },
      { value: 'priority_alerts', label: 'Priority Alerts', desc: 'Issue high-priority public safety alerts' },
      { value: 'manage_emergency_contacts', label: 'Manage Emergency Contacts', desc: 'Maintain emergency contact directories' },
    ],
  },
  {
    category: 'System Administration',
    icon: <LockOutlined />,
    color: '#2d7fb8',
    permissions: [
      { value: 'manage_settings', label: 'System Settings', desc: 'Configure platform settings and parameters' },
      { value: 'view_audit_logs', label: 'View Audit Logs', desc: 'Access system audit trails and activity logs' },
      { value: 'manage_integrations', label: 'Manage Integrations', desc: 'Configure third-party integrations and APIs' },
      { value: 'api_access', label: 'API Access', desc: 'Direct access to SafeVision REST APIs' },
      { value: 'manage_law_sections', label: 'Manage Law Sections', desc: 'Add, edit and manage PPC/ATA/CNSA law section database' },
    ],
  },
];

// ── Department → Recommended permissions mapping ──
const DEPARTMENT_PERMISSIONS = {
  'Law Enforcement Operations': ['view_users', 'view_crime_data', 'verify_crime_reports', 'approve_firs', 'manage_crime_data', 'view_analytics', 'view_heatmaps', 'manage_alerts', 'emergency_dispatch'],
  'Crime Analytics & Intelligence': ['view_crime_data', 'export_crime_data', 'view_analytics', 'access_predictions', 'generate_reports', 'manage_reports', 'view_heatmaps', 'view_audit_logs'],
  'Emergency Response & Dispatch': ['view_crime_data', 'view_heatmaps', 'manage_alerts', 'emergency_dispatch', 'priority_alerts', 'manage_emergency_contacts'],
  'IT & Cybersecurity': ['view_users', 'manage_settings', 'view_audit_logs', 'manage_integrations', 'api_access', 'manage_law_sections'],
  'Public Safety Communications': ['view_crime_data', 'view_analytics', 'view_heatmaps', 'manage_alerts', 'priority_alerts', 'generate_reports', 'view_community'],
  'Forensics & Evidence Management': ['view_crime_data', 'manage_crime_data', 'verify_crime_reports', 'approve_firs', 'export_crime_data', 'generate_reports'],
  'Strategic Planning & Policy': ['view_users', 'view_crime_data', 'view_analytics', 'access_predictions', 'generate_reports', 'manage_reports', 'view_heatmaps', 'view_audit_logs'],
  'Community Policing & Outreach': ['view_users', 'view_crime_data', 'view_analytics', 'view_heatmaps', 'manage_alerts', 'view_community'],
};

const AdminRegistrationForm = () => {
  const [form] = Form.useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedDept, setSelectedDept] = useState(null);
  const { token } = useAuth();
  const { settings: sysSettings } = useSystemSettings();
  const adminMinLen = sysSettings?.admin_password_min_length ?? 10;

  // Get all permission values as flat array
  const allPermissionValues = useMemo(
    () => PERMISSION_CATEGORIES.flatMap((cat) => cat.permissions.map((p) => p.value)),
    []
  );

  // Recommended permissions for currently selected department
  const recommendedPerms = useMemo(
    () => (selectedDept ? DEPARTMENT_PERMISSIONS[selectedDept] || [] : []),
    [selectedDept]
  );

  // Handle department change — auto-suggest recommended permissions
  const handleDepartmentChange = useCallback(
    (dept) => {
      setSelectedDept(dept);
      const suggested = DEPARTMENT_PERMISSIONS[dept] || [];
      form.setFieldsValue({ permissions: suggested });
      message.info(`Recommended permissions for ${dept} have been auto-selected. You can adjust them below.`);
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

  // Select / deselect all permissions in a category
  const toggleCategory = useCallback(
    (categoryPerms, checked) => {
      const current = form.getFieldValue('permissions') || [];
      const categoryValues = categoryPerms.map((p) => p.value);
      let updated;
      if (checked) {
        updated = [...new Set([...current, ...categoryValues])];
      } else {
        updated = current.filter((v) => !categoryValues.includes(v));
      }
      form.setFieldsValue({ permissions: updated });
    },
    [form]
  );

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

      <Card className={styles.formCard} bordered={false}>
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

          <Form.Item
            name="permissions"
            rules={[{
              required: true,
              message: 'Please select at least one permission',
              type: 'array',
              min: 1,
            }]}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <Row gutter={[20, 20]}>
                {PERMISSION_CATEGORIES.map((cat) => {
                  const catValues = cat.permissions.map((p) => p.value);
                  const currentPerms = form.getFieldValue('permissions') || [];
                  const allChecked = catValues.every((v) => currentPerms.includes(v));
                  const someChecked = catValues.some((v) => currentPerms.includes(v)) && !allChecked;

                  return (
                    <Col xs={24} lg={12} key={cat.category}>
                      <div
                        style={{
                          background: 'rgba(255,255,255,0.03)',
                          border: `1px solid rgba(255,255,255,0.08)`,
                          borderRadius: 16,
                          padding: '18px 20px',
                          height: '100%',
                          transition: 'all 0.3s ease',
                        }}
                      >
                        {/* Category Header */}
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: 14,
                            paddingBottom: 10,
                            borderBottom: '1px solid rgba(255,255,255,0.06)',
                          }}
                        >
                          <Space>
                            <span style={{ color: cat.color, fontSize: 18 }}>{cat.icon}</span>
                            <Text strong style={{ color: '#e0e0e0', fontSize: 15 }}>
                              {cat.category}
                            </Text>
                            <Tag
                              color={cat.color}
                              style={{ borderRadius: 10, fontSize: 11, marginLeft: 4 }}
                            >
                              {catValues.filter((v) => currentPerms.includes(v)).length}/{catValues.length}
                            </Tag>
                          </Space>
                          <Checkbox
                            checked={allChecked}
                            indeterminate={someChecked}
                            onChange={(e) => toggleCategory(cat.permissions, e.target.checked)}
                            style={{ marginRight: 0 }}
                          >
                            <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>All</Text>
                          </Checkbox>
                        </div>

                        {/* Permission Items */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {cat.permissions.map((perm) => (
                            <div
                              key={perm.value}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <Checkbox value={perm.value}>
                                <span style={{ color: '#d0d0d0' }}>{perm.label}</span>
                                {recommendedPerms.includes(perm.value) && (
                                  <Tag
                                    color="gold"
                                    style={{ marginLeft: 6, fontSize: 10, borderRadius: 8, lineHeight: '16px', padding: '0 5px' }}
                                  >
                                    Recommended
                                  </Tag>
                                )}
                              </Checkbox>
                              <Tooltip title={perm.desc} placement="left">
                                <InfoCircleOutlined style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer' }} />
                              </Tooltip>
                            </div>
                          ))}
                        </div>
                      </div>
                    </Col>
                  );
                })}
              </Row>
            </Checkbox.Group>
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
