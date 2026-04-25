import React, { useCallback, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Alert,
  Badge,
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  ApartmentOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  LockOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  UnlockOutlined,
  UserAddOutlined,
  UserDeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiService from '../../services/apiService_updated';
import usePaginatedResource from './hooks/usePaginatedResource';
import { USER_BULK_ACTIONS, USER_PERMISSIONS, USER_ROLES } from './constants/permissions';
import {
  DEPARTMENTS,
  DEPARTMENT_PERMISSIONS,
} from './constants/adminPermissions';
import PermissionMatrix from './PermissionMatrix';
import styles from './SuperAdminDashboard.module.css';

const { Text } = Typography;
const { confirm } = Modal;

/**
 * @typedef {Object} AdminRecord
 * @property {number} id
 * @property {string} username
 * @property {string} [firstName]
 * @property {string} [lastName]
 * @property {string} [email]
 * @property {string} [role]
 * @property {string} [department]
 * @property {string} [lastLogin]
 * @property {string[]} [permissions]
 */

const AdminManagement = ({ token }) => {
  const [form] = Form.useForm();
  const [selectedAdmins, setSelectedAdmins] = useState([]);
  const [selectedAdmin, setSelectedAdmin] = useState(null);
  const [editModal, setEditModal] = useState({ visible: false, admin: null });
  const [editForm] = Form.useForm();
  const [isPerformingAction, setIsPerformingAction] = useState(false);

  const fetchAdmins = useCallback(
    async (params) => {
      const response = await apiService.getAdmins(token, params);
      return {
        data: response.admins,
        total: response.total,
        limit: response.limit,
        offset: response.offset,
      };
    },
    [token]
  );

  const {
    data: admins,
    isLoading,
    error,
    pagination,
    handleTableChange,
    applyFilters,
    resetFilters,
    loadData,
  } = usePaginatedResource({
    fetcher: fetchAdmins,
    initialFilters: {
      limit: 10,
      offset: 0,
    },
    enabled: !!token,
  });

  const handleApplyFilters = (values) => {
    applyFilters({
      ...values,
      offset: 0,
    });
  };

  const handleResetFilters = () => {
    form.resetFields();
    resetFilters();
  };

  const handleEdit = (admin) => {
    setEditModal({ visible: true, admin });
    editForm.setFieldsValue({
      username: admin.username || '',
      firstName: admin.firstName || '',
      lastName: admin.lastName || '',
      email: admin.email || '',
      role: admin.role || '',
      department: admin.department || '',
      password: '',
      permissions: Array.isArray(admin.permissions) ? admin.permissions : [],
    });
  };

  const handleEditSubmit = async (values) => {
    try {
      const payload = {
        firstName: values.firstName,
        lastName: values.lastName,
        username: values.username,
        email: values.email,
        role: values.role,
        department: values.department,
        permissions: values.permissions || [],
      };
      if (values.password) payload.password = values.password;

      await apiService.updateAdmin(token, editModal.admin.id, payload);
      message.success('Admin updated successfully');
      setEditModal({ visible: false, admin: null });
      loadData();
    } catch (error) {
      message.error(error.message || 'Failed to update admin');
    }
  };

  const handleAdminAction = (action, adminIdsOverride) => {
    const targetIds = adminIdsOverride ?? selectedAdmins;

    if (!targetIds.length) {
      message.warning('Please select at least one admin');
      return;
    }

    const actionVerb = action === 'activate' ? 'activate' : action === 'suspend' ? 'suspend' : 'delete';

    confirm({
      title: 'Confirm Action',
      icon: <ExclamationCircleOutlined />,
      content: `Are you sure you want to ${actionVerb} ${targetIds.length} admin(s)?`,
      okText: 'Yes',
      cancelText: 'No',
      onOk: async () => {
        try {
          setIsPerformingAction(true);
          await apiService.bulkAdminActions(token, action, targetIds);
          message.success(`Successfully executed ${actionVerb} action`);
          setSelectedAdmins([]);
          loadData();
        } catch (actionError) {
          message.error(actionError.message || 'Action failed');
        } finally {
          setIsPerformingAction(false);
        }
      },
    });
  };

  const columns = useMemo(
    () => [
      {
        title: 'Admin',
        dataIndex: 'username',
        key: 'username',
        fixed: 'left',
        width: 220,
        render: (username, record) => (
          <Space direction="vertical" size={0}>
            <Space>
              <UserAddOutlined style={{ color: '#f9a826' }} />
              <strong style={{ color: '#e0e0e0' }}>{username}</strong>
            </Space>
            <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>{record.email}</span>
          </Space>
        ),
      },
      {
        title: 'Name',
        key: 'fullName',
        width: 160,
        render: (_, record) => (
          <span style={{ color: '#d0d0d0' }}>
            {`${record.firstName || ''} ${record.lastName || ''}`.trim() || '—'}
          </span>
        ),
      },
      {
        title: 'Department',
        dataIndex: 'department',
        key: 'department',
        width: 180,
        render: (department) => (
          <Tag color="cyan" style={{ fontSize: 12 }}>{department || '—'}</Tag>
        ),
      },
      {
        title: 'Role',
        dataIndex: 'role',
        key: 'role',
        width: 100,
        filters: USER_ROLES.map((role) => ({ text: role.label, value: role.value })),
        render: (role) => {
          const effective = (role && String(role).trim()) || 'admin';
          const isSuper = effective === 'superadmin' || effective === 'super_admin';
          return <Tag color={isSuper ? 'magenta' : 'geekblue'}>{effective.toUpperCase()}</Tag>;
        },
      },
      {
        title: 'Status',
        key: 'status',
        width: 100,
        render: (_, record) => {
          const isActive = record.status === 'active' || (record.status !== 'inactive' && record.role !== 'inactive');
          return (
            <Badge
              status={isActive ? 'success' : 'default'}
              text={<span style={{ color: isActive ? '#1dd1a1' : '#ff6b6b', fontSize: 13 }}>{isActive ? 'Active' : 'Inactive'}</span>}
            />
          );
        },
      },
      {
        title: 'Created',
        dataIndex: 'createdAt',
        key: 'createdAt',
        width: 130,
        render: (createdAt) => (
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            {createdAt ? dayjs(createdAt).format('DD MMM YYYY') : '—'}
          </span>
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        fixed: 'right',
        width: 180,
        render: (_, record) => (
          <Space size={4}>
            <Tooltip title="View details">
              <Button size="small" icon={<EyeOutlined />} type="text" style={{ color: '#2d7fb8' }} onClick={() => setSelectedAdmin(record)} />
            </Tooltip>
            <Tooltip title="Edit admin">
              <Button size="small" icon={<EditOutlined />} type="text" style={{ color: '#f9a826' }} onClick={() => handleEdit(record)} />
            </Tooltip>
            {record.status === 'inactive' || record.role === 'inactive' ? (
              <Tooltip title="Activate">
                <Button size="small" icon={<UnlockOutlined />} type="text" style={{ color: '#1dd1a1' }} onClick={() => handleAdminAction('activate', [record.id])} />
              </Tooltip>
            ) : (
              <Tooltip title="Suspend">
                <Button size="small" icon={<LockOutlined />} type="text" style={{ color: '#ff6b6b' }} onClick={() => handleAdminAction('suspend', [record.id])} />
              </Tooltip>
            )}
            <Tooltip title="Delete">
              <Button size="small" icon={<UserDeleteOutlined />} type="text" danger onClick={() => handleAdminAction('delete', [record.id])} />
            </Tooltip>
          </Space>
        ),
      },
    ],
    [handleAdminAction]
  );

  return (
    <div className={styles.sectionContainer}>
      <div className={styles.sectionHeader}>
        <div>
          <h2>Admin Management</h2>
          <p className={styles.sectionDescription}>
            Manage admin accounts and permissions. Use filters to quickly locate specific administrators.
          </p>
        </div>
        <Tooltip title="Refresh data">
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadData()}
            style={{ background: 'rgba(45,127,184,0.15)', border: '1px solid rgba(45,127,184,0.3)', color: '#2d7fb8', borderRadius: 10 }}
          >
            Refresh
          </Button>
        </Tooltip>
      </div>

      <div className={styles.filtersRow}>
        <Form
          form={form}
          layout="inline"
          onFinish={handleApplyFilters}
          onReset={handleResetFilters}
          className={styles.filtersForm}
        >
          <Form.Item name="search" style={{ marginBottom: 0 }}>
            <Input
              prefix={<SearchOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
              allowClear
              placeholder="Search admin by name or email"
              style={{ width: 240, background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: 10, color: '#e0e0e0' }}
            />
          </Form.Item>
          <Form.Item name="role" style={{ marginBottom: 0 }}>
            <Select
              allowClear
              placeholder="Filter by role"
              style={{ width: 160 }}
              classNames={{ popup: { root: 'dark-select-dropdown' } }}
            >
              {USER_ROLES.map((role) => (
                <Select.Option key={role.value} value={role.value}>
                  {role.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Space size={6}>
              <Button
                type="primary"
                htmlType="submit"
                icon={<FilterOutlined />}
                style={{ borderRadius: 10, background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)', border: 'none', fontWeight: 500 }}
              >
                Apply
              </Button>
              <Button
                htmlType="reset"
                icon={<CloseCircleOutlined />}
                style={{ borderRadius: 10, background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.1)', color: '#d0d0d0' }}
              >
                Reset
              </Button>
            </Space>
          </Form.Item>
        </Form>

        <div className={styles.actionBar}>
          {selectedAdmins.length > 0 && (
            <span className={styles.selectionCount}>{selectedAdmins.length} selected</span>
          )}
          <Tooltip title="Activate selected admins">
            <Button
              size="small"
              icon={<UnlockOutlined />}
              onClick={() => handleAdminAction('activate')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
              style={{ borderRadius: 8, background: selectedAdmins.length > 0 ? 'rgba(29,209,161,0.12)' : undefined, borderColor: selectedAdmins.length > 0 ? 'rgba(29,209,161,0.3)' : undefined, color: selectedAdmins.length > 0 ? '#1dd1a1' : undefined }}
            >
              Activate
            </Button>
          </Tooltip>
          <Tooltip title="Suspend selected admins">
            <Button
              size="small"
              icon={<LockOutlined />}
              onClick={() => handleAdminAction('suspend')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
              style={{ borderRadius: 8, background: selectedAdmins.length > 0 ? 'rgba(249,168,38,0.12)' : undefined, borderColor: selectedAdmins.length > 0 ? 'rgba(249,168,38,0.3)' : undefined, color: selectedAdmins.length > 0 ? '#f9a826' : undefined }}
            >
              Suspend
            </Button>
          </Tooltip>
          <Tooltip title="Delete selected admins">
            <Button
              size="small"
              icon={<UserDeleteOutlined />}
              danger
              onClick={() => handleAdminAction('delete')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
              style={{ borderRadius: 8 }}
            >
              Delete
            </Button>
          </Tooltip>
        </div>
      </div>

      <div className={styles.tableCard}>
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={admins}
          scroll={{ x: 1100 }}
          size="middle"
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            style: { marginRight: 16 },
          }}
          onChange={handleTableChange}
          rowSelection={{
            selectedRowKeys: selectedAdmins,
            onChange: setSelectedAdmins,
          }}
          locale={{
            emptyText: error ? 'Failed to load admins' : 'No admins found',
          }}
        />
      </div>

      {/* ── View Admin Details Drawer ── */}
      <Drawer
        width={480}
        title={<span style={{ color: '#e0e0e0', fontWeight: 600 }}>Admin Details</span>}
        open={!!selectedAdmin}
        onClose={() => setSelectedAdmin(null)}
        styles={{
          header: { background: 'rgba(10,10,15,0.98)', borderBottom: '1px solid rgba(255,255,255,0.08)' },
          body: { background: 'rgba(10,10,15,0.98)', padding: '20px 24px' },
        }}
      >
        {selectedAdmin && (
          <Descriptions
            bordered
            column={1}
            size="small"
            styles={{ label: { color: '#f9a826', background: 'rgba(255,255,255,0.04)', fontWeight: 500, width: 130 }, content: { color: '#d0d0d0', background: 'rgba(255,255,255,0.02)' } }}
          >
            <Descriptions.Item label="Username">{selectedAdmin.username}</Descriptions.Item>
            <Descriptions.Item label="Full Name">
              {`${selectedAdmin.firstName || ''} ${selectedAdmin.lastName || ''}`.trim() || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">{selectedAdmin.email || '—'}</Descriptions.Item>
            <Descriptions.Item label="Role"><Tag color="geekblue">{selectedAdmin.role?.toUpperCase()}</Tag></Descriptions.Item>
            <Descriptions.Item label="Department"><Tag color="cyan">{selectedAdmin.department || '—'}</Tag></Descriptions.Item>
            <Descriptions.Item label="Phone">{selectedAdmin.phone || '—'}</Descriptions.Item>
            <Descriptions.Item label="Address">{selectedAdmin.address || '—'}</Descriptions.Item>
            <Descriptions.Item label="Created At">
              {selectedAdmin.createdAt ? dayjs(selectedAdmin.createdAt).format('DD MMM YYYY HH:mm') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Permissions">
              <Space wrap>
                {(selectedAdmin.permissions || []).length > 0
                  ? selectedAdmin.permissions.map((p) => <Tag key={p} color="blue">{p}</Tag>)
                  : <span style={{ color: 'rgba(255,255,255,0.3)' }}>No permissions</span>}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      {/* ── Edit Admin Modal (Profile + Department & Permissions tabs) ── */}
      <Modal
        title={
          <Space>
            <EditOutlined style={{ color: '#f9a826' }} />
            <span style={{ color: '#e0e0e0', fontWeight: 600 }}>
              Edit Administrator
              {editModal.admin?.username ? (
                <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13, marginLeft: 8 }}>
                  · {editModal.admin.username}
                </Text>
              ) : null}
            </span>
          </Space>
        }
        open={editModal.visible}
        onCancel={() => setEditModal({ visible: false, admin: null })}
        footer={null}
        destroyOnHidden
        width={920}
        styles={{
          content: { background: 'rgba(13,20,30,0.98)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 16 },
          header: { background: 'transparent', borderBottom: '1px solid rgba(255,255,255,0.08)' },
          body: { padding: '20px 24px 24px' },
        }}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
          initialValues={{ permissions: [] }}
        >
          <Form.Item dependencies={['department']} noStyle>
            {() => {
              const dept = editForm.getFieldValue('department');
              const recommendedPerms = (dept && DEPARTMENT_PERMISSIONS[dept]) || [];
              return (
                <Tabs
                  defaultActiveKey="profile"
                  items={[
                    {
                      key: 'profile',
                      label: (
                        <span>
                          <UserAddOutlined /> Profile Info
                        </span>
                      ),
                      children: (
                        <div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
                            <Form.Item
                              name="firstName"
                              label={<span style={{ color: '#d0d0d0' }}>First Name</span>}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
                            </Form.Item>
                            <Form.Item
                              name="lastName"
                              label={<span style={{ color: '#d0d0d0' }}>Last Name</span>}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
                            </Form.Item>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
                            <Form.Item
                              name="username"
                              label={<span style={{ color: '#d0d0d0' }}>Username</span>}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
                            </Form.Item>
                            <Form.Item
                              name="email"
                              label={<span style={{ color: '#d0d0d0' }}>Email</span>}
                              rules={[
                                { required: true, message: 'Required' },
                                { type: 'email', message: 'Enter a valid email' },
                              ]}
                            >
                              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
                            </Form.Item>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
                            <Form.Item
                              name="role"
                              label={<span style={{ color: '#d0d0d0' }}>Role</span>}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Select classNames={{ popup: { root: 'dark-select-dropdown' } }} style={{ background: 'transparent' }}>
                                {USER_ROLES.map((role) => (
                                  <Select.Option key={role.value} value={role.value}>
                                    {role.label}
                                  </Select.Option>
                                ))}
                              </Select>
                            </Form.Item>
                            <Form.Item
                              name="password"
                              label={
                                <span style={{ color: '#d0d0d0' }}>
                                  New Password{' '}
                                  <span style={{ color: 'rgba(255,255,255,0.35)', fontWeight: 400, fontSize: 12 }}>
                                    (leave blank to keep current)
                                  </span>
                                </span>
                              }
                            >
                              <Input.Password
                                placeholder="Enter new password"
                                style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }}
                              />
                            </Form.Item>
                          </div>
                        </div>
                      ),
                    },
                    {
                      key: 'access',
                      label: (
                        <span>
                          <SafetyCertificateOutlined /> Department & Permissions
                        </span>
                      ),
                      children: (
                        <div>
                          <Form.Item
                            name="department"
                            label={
                              <span style={{ color: '#d0d0d0' }}>
                                Department <Text style={{ color: 'rgba(255,255,255,0.4)', fontWeight: 400, fontSize: 12 }}>· choosing a department adds its recommended permissions</Text>
                              </span>
                            }
                            rules={[{ required: true, message: 'Please select a department' }]}
                          >
                            <Select
                              showSearch
                              optionLabelProp="label"
                              placeholder="Select department"
                              classNames={{ popup: { root: 'dark-select-dropdown' } }}
                              filterOption={(input, option) =>
                                (option?.label ?? '').toString().toLowerCase().includes(input.toLowerCase())
                              }
                              onChange={(newDept) => {
                                const suggested = DEPARTMENT_PERMISSIONS[newDept] || [];
                                const current = editForm.getFieldValue('permissions') || [];
                                const merged = Array.from(new Set([...current, ...suggested]));
                                editForm.setFieldsValue({ permissions: merged });
                              }}
                            >
                              {DEPARTMENTS.map((d) => (
                                <Select.Option key={d.value} value={d.value} label={d.label}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
                                    <span style={{ fontSize: 18 }}>{d.icon}</span>
                                    <div>
                                      <div style={{ fontWeight: 600, color: '#e0e0e0' }}>{d.label}</div>
                                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>{d.desc}</div>
                                    </div>
                                  </div>
                                </Select.Option>
                              ))}
                            </Select>
                          </Form.Item>

                          <Alert
                            message="All permissions are freely selectable"
                            description="Recommendations highlighted with a gold tag are based on the chosen department, but you can check or uncheck ANY permission across ALL categories — independent of the recommendation."
                            type="success"
                            showIcon
                            icon={<InfoCircleOutlined />}
                            style={{
                              marginBottom: 16,
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
                            <PermissionMatrix recommendedPerms={recommendedPerms} compact />
                          </Form.Item>
                        </div>
                      ),
                    },
                  ]}
                />
              );
            }}
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <Button onClick={() => setEditModal({ visible: false, admin: null })}>Cancel</Button>
            <Button type="primary" htmlType="submit" style={{ background: '#2d7fb8', borderColor: '#2d7fb8' }}>
              Save Changes
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

AdminManagement.propTypes = {
  token: PropTypes.string.isRequired,
};

export default AdminManagement;
