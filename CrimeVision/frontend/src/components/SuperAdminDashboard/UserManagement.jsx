import React, { useCallback, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Badge,
  Button,
  Checkbox,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  message,
} from 'antd';
import {
  ExclamationCircleOutlined,
  EyeOutlined,
  FilterOutlined,
  LockOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  UnlockOutlined,
  UserDeleteOutlined,
  EditOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiService from '../../services/apiService';
import usePaginatedResource from './hooks/usePaginatedResource';
import { USER_BULK_ACTIONS, USER_PERMISSIONS, USER_ROLES } from './constants/permissions';
import styles from './SuperAdminDashboard.module.css';

const { confirm } = Modal;

const ROLE_COLORS = {
  super_admin: 'magenta',
  admin: 'geekblue',
  user: 'cyan',
  inactive: 'volcano',
};

const STATUS_COLORS = {
  active: 'green',
  pending: 'gold',
  inactive: 'default',
};

const UserManagement = ({ token }) => {
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [editModal, setEditModal] = useState({ visible: false, user: null });
  const [editForm] = Form.useForm();
  const [permissionsModal, setPermissionsModal] = useState({ visible: false, user: null });
  const [isPerformingBulkAction, setIsPerformingBulkAction] = useState(false);

  const fetchUsers = useCallback(
    async (params) => {
      // Always restrict to non-admin users — Admins/SuperAdmins live in Admin Management
      const safeParams = { ...params };
      if (!safeParams.role || safeParams.role === 'admin' || safeParams.role === 'superadmin' || safeParams.role === 'super_admin') {
        safeParams.role = 'user';
      }
      const response = await apiService.getUsers(token, safeParams);
      // Defense in depth: filter client-side too in case backend ignores role param
      const filtered = (response.users || []).filter(
        (u) => u && u.role !== 'admin' && u.role !== 'superadmin' && u.role !== 'super_admin'
      );
      return {
        data: filtered,
        total: response.total,
        limit: response.limit,
        offset: response.offset,
      };
    },
    [token]
  );

  const {
    data: users,
    isLoading,
    error,
    pagination,
    handleTableChange,
    applyFilters,
    resetFilters,
    loadData,
  } = usePaginatedResource({
    fetcher: fetchUsers,
    initialFilters: {
      limit: 10,
      offset: 0,
      role: 'user',
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

  const handleBulkAction = (action, userIdsOverride) => {
    const targetIds = userIdsOverride ?? selectedRowKeys;

    if (!targetIds.length) {
      message.warning('Please select at least one user');
      return;
    }

    confirm({
      title: 'Confirm Bulk Action',
      icon: <ExclamationCircleOutlined />,
      content: `Are you sure you want to ${action} the selected ${targetIds.length} users?`,
      okText: 'Yes',
      cancelText: 'No',
      onOk: async () => {
        try {
          setIsPerformingBulkAction(true);
          await apiService.bulkUserActions(token, action, targetIds);
          message.success(`Successfully executed bulk ${action}`);
          setSelectedRowKeys([]);
          loadData();
        } catch (bulkError) {
          message.error(bulkError.message || `Failed to ${action} users`);
        } finally {
          setIsPerformingBulkAction(false);
        }
      },
    });
  };

  const openPermissionsModal = (user) => {
    setPermissionsModal({ visible: true, user });
  };

  const handlePermissionsSubmit = async (values) => {
    try {
      await apiService.updateUserPermissions(token, permissionsModal.user.id, values.permissions);
      message.success('Permissions updated successfully');
      setPermissionsModal({ visible: false, user: null });
      loadData();
    } catch (permissionsError) {
      message.error(permissionsError.message || 'Failed to update permissions');
    }
  };

  const handleEdit = (user) => {
    setEditModal({ visible: true, user });
    editForm.setFieldsValue({
      username: user.username || '',
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      role: user.role || '',
      homeArea: user.homeArea || '',
      workArea: user.workArea || '',
      alertRadius: user.alertRadius || '',
      password: '',
    });
  };

  const handleEditSubmit = async (values) => {
    try {
      await apiService.updateUser(token, editModal.user.id, values);
      message.success('User updated successfully');
      setEditModal({ visible: false, user: null });
      loadData();
    } catch (error) {
      message.error(error.message || 'Failed to update user');
    }
  };

  const handleUnlock = (user) => {
    confirm({
      title: 'Unlock account?',
      icon: <ExclamationCircleOutlined />,
      content: `This will clear all failed login attempts for ${user.username || user.email} so they can sign in again.`,
      okText: 'Unlock',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await apiService.unlockUser(token, user.id);
          message.success(`Unlocked ${user.username || user.email}`);
          loadData();
        } catch (err) {
          message.error(err.message || 'Failed to unlock user');
        }
      },
    });
  };

  const columns = useMemo(
    () => [
      {
        title: 'User',
        dataIndex: 'username',
        key: 'username',
        fixed: 'left',
        width: 220,
        render: (username, record) => (
          <Space direction="vertical" size={0}>
            <Space>
              <TeamOutlined style={{ color: '#2d7fb8' }} />
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
        title: 'Role',
        dataIndex: 'role',
        key: 'role',
        width: 110,
        filters: USER_ROLES.map((role) => ({ text: role.label, value: role.value })),
        render: (role) => <Tag color={ROLE_COLORS[role] || 'default'}>{role?.toUpperCase()}</Tag>,
      },
      {
        title: 'Status',
        key: 'status',
        width: 100,
        render: (_, record) => (
          <Badge
            status={record.role === 'inactive' ? 'default' : 'success'}
            text={<span style={{ color: record.role === 'inactive' ? '#ff6b6b' : '#1dd1a1', fontSize: 13 }}>{record.role === 'inactive' ? 'Inactive' : 'Active'}</span>}
          />
        ),
      },
      {
        title: 'Verified',
        key: 'verified',
        width: 110,
        render: (_, record) => (
          record.isVerified
            ? <Tag color="green" style={{ fontSize: 11 }}>VERIFIED</Tag>
            : <Tag color="orange" style={{ fontSize: 11 }}>UNVERIFIED</Tag>
        ),
      },
      {
        title: 'Lock',
        key: 'locked',
        width: 110,
        render: (_, record) => (
          record.isLocked
            ? <Tag color="red" icon={<LockOutlined />} style={{ fontSize: 11 }}>LOCKED</Tag>
            : <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>—</span>
        ),
      },
      {
        title: 'Created',
        dataIndex: 'createdAt',
        key: 'createdAt',
        width: 140,
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
        width: 230,
        render: (_, record) => (
          <Space size={4}>
            <Tooltip title="View details">
              <Button size="small" icon={<EyeOutlined />} type="text" style={{ color: '#2d7fb8' }} onClick={() => setSelectedUser(record)} />
            </Tooltip>
            <Tooltip title="Edit user">
              <Button size="small" icon={<EditOutlined />} type="text" style={{ color: '#f9a826' }} onClick={() => handleEdit(record)} />
            </Tooltip>
            <Tooltip title="Permissions">
              <Button size="small" icon={<UnlockOutlined />} type="text" style={{ color: '#1dd1a1' }} onClick={() => openPermissionsModal(record)} />
            </Tooltip>
            {record.isLocked && (
              <Tooltip title="Unlock account (clear failed attempts)">
                <Button size="small" icon={<UnlockOutlined />} type="text" style={{ color: '#fbbf24' }} onClick={() => handleUnlock(record)} />
              </Tooltip>
            )}
            {record.role === 'inactive' ? (
              <Tooltip title="Activate">
                <Button size="small" icon={<UnlockOutlined />} type="text" style={{ color: '#1dd1a1' }} onClick={() => handleBulkAction('activate', [record.id])} />
              </Tooltip>
            ) : (
              <Tooltip title="Suspend">
                <Button size="small" icon={<LockOutlined />} type="text" style={{ color: '#ff6b6b' }} onClick={() => handleBulkAction('suspend', [record.id])} />
              </Tooltip>
            )}
            <Tooltip title="Delete">
              <Button size="small" icon={<UserDeleteOutlined />} type="text" danger onClick={() => handleBulkAction('delete', [record.id])} />
            </Tooltip>
          </Space>
        ),
      },
    ],
    [openPermissionsModal]
  );

  return (
    <div className={styles.sectionContainer}>
      <div className={styles.sectionHeader}>
        <div>
          <h2>User Management</h2>
          <p className={styles.sectionDescription}>
            View, filter, and manage all platform users. Use bulk actions for quick operations.
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
              placeholder="Search by name or email"
              style={{ width: 230, background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: 10, color: '#e0e0e0' }}
            />
          </Form.Item>
          <Form.Item name="role" style={{ marginBottom: 0 }}>
            <Select
              allowClear
              placeholder="Filter status"
              style={{ width: 160 }}
              classNames={{ popup: { root: 'dark-select-dropdown' } }}
            >
              {/* Hide Admin / Super Admin filter options — they belong to Admin Management */}
              {USER_ROLES
                .filter((role) => role.value !== 'admin' && role.value !== 'super_admin' && role.value !== 'superadmin')
                .map((role) => (
                  <Select.Option key={role.value} value={role.value}>
                    {role.label}
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>
          <Form.Item name="verification" style={{ marginBottom: 0 }}>
            <Select
              allowClear
              placeholder="Verification"
              style={{ width: 150 }}
              classNames={{ popup: { root: 'dark-select-dropdown' } }}
            >
              <Select.Option value="verified">Verified</Select.Option>
              <Select.Option value="unverified">Unverified</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="locked" style={{ marginBottom: 0 }}>
            <Select
              allowClear
              placeholder="Lock state"
              style={{ width: 140 }}
              classNames={{ popup: { root: 'dark-select-dropdown' } }}
            >
              <Select.Option value={true}>Locked</Select.Option>
              <Select.Option value={false}>Not locked</Select.Option>
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
          {selectedRowKeys.length > 0 && (
            <span className={styles.selectionCount}>{selectedRowKeys.length} selected</span>
          )}
          <Tooltip title="Suspend selected accounts">
            <Button
              size="small"
              icon={<LockOutlined />}
              onClick={() => handleBulkAction('suspend')}
              disabled={selectedRowKeys.length === 0}
              loading={isPerformingBulkAction}
              style={{ borderRadius: 8, background: selectedRowKeys.length > 0 ? 'rgba(249,168,38,0.12)' : undefined, borderColor: selectedRowKeys.length > 0 ? 'rgba(249,168,38,0.3)' : undefined, color: selectedRowKeys.length > 0 ? '#f9a826' : undefined }}
            >
              Suspend
            </Button>
          </Tooltip>
          <Tooltip title="Activate selected accounts">
            <Button
              size="small"
              icon={<UnlockOutlined />}
              onClick={() => handleBulkAction('activate')}
              disabled={selectedRowKeys.length === 0}
              loading={isPerformingBulkAction}
              style={{ borderRadius: 8, background: selectedRowKeys.length > 0 ? 'rgba(29,209,161,0.12)' : undefined, borderColor: selectedRowKeys.length > 0 ? 'rgba(29,209,161,0.3)' : undefined, color: selectedRowKeys.length > 0 ? '#1dd1a1' : undefined }}
            >
              Activate
            </Button>
          </Tooltip>
          <Tooltip title="Delete selected accounts">
            <Button
              size="small"
              icon={<UserDeleteOutlined />}
              danger
              onClick={() => handleBulkAction('delete')}
              disabled={selectedRowKeys.length === 0}
              loading={isPerformingBulkAction}
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
          dataSource={users}
          scroll={{ x: 1000 }}
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
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          locale={{
            emptyText: error ? 'Failed to load users' : 'No users found',
          }}
        />
      </div>

      {/* ── View User Details Drawer ── */}
      <Drawer
        width={480}
        title={<span style={{ color: '#e0e0e0', fontWeight: 600 }}>User Details</span>}
        open={!!selectedUser}
        onClose={() => setSelectedUser(null)}
        styles={{
          header: { background: 'rgba(10,10,15,0.98)', borderBottom: '1px solid rgba(255,255,255,0.08)' },
          body: { background: 'rgba(10,10,15,0.98)', padding: '20px 24px' },
        }}
      >
        {selectedUser && (
          <Descriptions
            bordered
            column={1}
            size="small"
            styles={{ label: { color: '#f9a826', background: 'rgba(255,255,255,0.04)', fontWeight: 500, width: 130 }, content: { color: '#d0d0d0', background: 'rgba(255,255,255,0.02)' } }}
          >
            <Descriptions.Item label="Username">{selectedUser.username}</Descriptions.Item>
            <Descriptions.Item label="Full Name">
              {`${selectedUser.firstName || ''} ${selectedUser.lastName || ''}`.trim() || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="Role"><Tag color={ROLE_COLORS[selectedUser.role] || 'default'}>{selectedUser.role?.toUpperCase()}</Tag></Descriptions.Item>
            <Descriptions.Item label="Verification">
              {selectedUser.isVerified
                ? <Tag color="green">VERIFIED{selectedUser.verifiedAt ? ` · ${dayjs(selectedUser.verifiedAt).format('DD MMM YYYY')}` : ''}</Tag>
                : <Tag color="orange">UNVERIFIED</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="Lock State">
              {selectedUser.isLocked
                ? <Tag color="red" icon={<LockOutlined />}>LOCKED — clear failed attempts to unlock</Tag>
                : <span style={{ color: 'rgba(255,255,255,0.5)' }}>Not locked</span>}
            </Descriptions.Item>
            <Descriptions.Item label="Last Login">
              {selectedUser.lastLogin ? dayjs(selectedUser.lastLogin).format('DD MMM YYYY HH:mm') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Home Area">{selectedUser.homeArea || '—'}</Descriptions.Item>
            <Descriptions.Item label="Work Area">{selectedUser.workArea || '—'}</Descriptions.Item>
            <Descriptions.Item label="Alert Radius">{selectedUser.alertRadius ? `${selectedUser.alertRadius} km` : '—'}</Descriptions.Item>
            <Descriptions.Item label="Created At">
              {selectedUser.createdAt ? dayjs(selectedUser.createdAt).format('DD MMM YYYY HH:mm') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Permissions">
              <Space wrap>
                {(selectedUser.permissions || []).length > 0
                  ? selectedUser.permissions.map((p) => <Tag key={p} color="blue">{p}</Tag>)
                  : <span style={{ color: 'rgba(255,255,255,0.3)' }}>No permissions</span>}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      {/* ── Edit User Modal ── */}
      <Modal
        title={<span style={{ color: '#e0e0e0' }}>Edit User Details</span>}
        open={editModal.visible}
        onCancel={() => setEditModal({ visible: false, user: null })}
        footer={null}
        destroyOnHidden
        styles={{
          content: { background: 'rgba(13,20,30,0.98)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12 },
          header: { background: 'transparent', borderBottom: '1px solid rgba(255,255,255,0.08)' },
        }}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
          style={{ marginTop: 8 }}
        >
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
              { type: 'email', message: 'Enter a valid email' }
            ]}
          >
            <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
          </Form.Item>
          <Form.Item
            name="password"
            label={<span style={{ color: '#d0d0d0' }}>New Password <span style={{ color: 'rgba(255,255,255,0.35)', fontWeight: 400, fontSize: 12 }}>(leave blank to keep current)</span></span>}
          >
            <Input.Password
              placeholder="Enter new password"
              style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }}
            />
          </Form.Item>
          <Form.Item
            name="role"
            label={<span style={{ color: '#d0d0d0' }}>Role</span>}
            rules={[{ required: true, message: 'Required' }]}
          >
            <Select
              classNames={{ popup: { root: 'dark-select-dropdown' } }}
              style={{ background: 'transparent' }}
            >
              {USER_ROLES.map((role) => (
                <Select.Option key={role.value} value={role.value}>
                  {role.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item
              name="homeArea"
              label={<span style={{ color: '#d0d0d0' }}>Home Area</span>}
            >
              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
            </Form.Item>
            <Form.Item
              name="workArea"
              label={<span style={{ color: '#d0d0d0' }}>Work Area</span>}
            >
              <Input style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
            </Form.Item>
          </div>
          <Form.Item
            name="alertRadius"
            label={<span style={{ color: '#d0d0d0' }}>Alert Radius (km)</span>}
          >
            <Input type="number" style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.12)', color: '#e0e0e0' }} />
          </Form.Item>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <Button onClick={() => setEditModal({ visible: false, user: null })}>Cancel</Button>
            <Button type="primary" htmlType="submit" style={{ background: '#2d7fb8', borderColor: '#2d7fb8' }}>
              Save Changes
            </Button>
          </div>
        </Form>
      </Modal>

      {/* ── Permissions Modal ── */}
      <Modal
        title={<span style={{ color: '#e0e0e0' }}>{`Manage Permissions${permissionsModal.user ? ` — ${permissionsModal.user.username}` : ''}`}</span>}
        open={permissionsModal.visible}
        onCancel={() => setPermissionsModal({ visible: false, user: null })}
        footer={null}
        destroyOnHidden
        styles={{
          content: { background: 'rgba(13,20,30,0.98)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12 },
          header: { background: 'transparent', borderBottom: '1px solid rgba(255,255,255,0.08)' },
        }}
      >
        <Form
          initialValues={{
            permissions: permissionsModal.user?.permissions || [],
          }}
          onFinish={handlePermissionsSubmit}
          layout="vertical"
        >
          <Form.Item name="permissions" label={<span style={{ color: '#d0d0d0' }}>Permissions</span>}>
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical">
                {USER_PERMISSIONS.map((permission) => (
                  <Checkbox key={permission.value} value={permission.value} style={{ color: '#d0d0d0' }}>
                    {permission.label}
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={() => setPermissionsModal({ visible: false, user: null })}>Cancel</Button>
            <Button type="primary" htmlType="submit" style={{ background: '#2d7fb8', borderColor: '#2d7fb8' }}>
              Save Changes
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

UserManagement.propTypes = {
  token: PropTypes.string.isRequired,
};

export default UserManagement;
