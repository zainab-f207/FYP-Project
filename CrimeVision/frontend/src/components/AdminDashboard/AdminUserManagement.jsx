import React, { useCallback, useMemo, useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
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
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiService from '../../services/apiService_updated';
import usePaginatedResource from '../SuperAdminDashboard/hooks/usePaginatedResource';
import styles from '../SuperAdminDashboard/SuperAdminDashboard.module.css';

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

const AdminUserManagement = ({ token, user: currentUser }) => {
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionModal, setActionModal] = useState({ visible: false, user: null, action: null });
  const [actionReason, setActionReason] = useState('');
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

  const fetchUsers = useCallback(
    async (params) => {
      // Restrict to non-admin users
      const safeParams = { ...params };
      if (!safeParams.role || safeParams.role === 'admin' || safeParams.role === 'superadmin' || safeParams.role === 'super_admin') {
        safeParams.role = 'user';
      }
      console.log('[AdminUserManagement] Fetching users with params:', safeParams);
      const response = await apiService.getUsers(token, safeParams);
      console.log('[AdminUserManagement] API Raw Response:', response);
      console.log('[AdminUserManagement] First user raw:', response.users?.[0]);
      console.log('[AdminUserManagement] First user has keys:', Object.keys(response.users?.[0] || {}));
      
      // API already normalizes to camelCase via normalizeUser
      const filtered = (response.users || []).filter(
        (u) => u && u.role !== 'admin' && u.role !== 'superadmin' && u.role !== 'super_admin'
      );
      console.log('[AdminUserManagement] Filtered users (already normalized):', filtered);
      return {
        data: filtered,
        total: filtered.length,
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

  // Debug logging
  useEffect(() => {
    const currentPage = pagination?.limit ? Math.max(1, Math.floor(pagination.offset / pagination.limit) + 1) : 1;
    console.log('[AdminUserManagement] Component state:', {
      token: !!token,
      usersCount: users?.length || 0,      firstUserSample: users?.[0],      isLoading,
      error: error?.message || null,
      pagination,
      calculatedCurrentPage: currentPage,
    });
  }, [token, users, isLoading, error, pagination]);

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

  const openActionModal = (user, action) => {
    setActionModal({ visible: true, user, action });
    setActionReason('');
  };

  const submitAction = async () => {
    if (!actionReason.trim()) {
      message.error('Please provide a reason for this action');
      return;
    }

    try {
      setIsSubmittingAction(true);
      const actionType = actionModal.action;
      const targetId = actionModal.user.id;

      // Create approval request
      const response = await apiService.submitUserActionForApproval(token, {
        action_type: actionType,
        target_id: targetId,
        reason: actionReason,
        target_username: actionModal.user.username,
        target_email: actionModal.user.email,
      });

      message.success(`Action submitted to superadmin for approval. Request ID: ${response.request_id}`);
      setActionModal({ visible: false, user: null, action: null });
      setActionReason('');
      loadData();
    } catch (err) {
      message.error(err.message || 'Failed to submit action for approval');
    } finally {
      setIsSubmittingAction(false);
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
        width: 200,
        render: (_, record) => (
          <Space size={4}>
            <Tooltip title="View details">
              <Button size="small" icon={<EyeOutlined />} type="text" style={{ color: '#2d7fb8' }} onClick={() => setSelectedUser(record)} />
            </Tooltip>
            {record.isLocked && (
              <Tooltip title="Unlock account (direct action)">
                <Button size="small" icon={<UnlockOutlined />} type="text" style={{ color: '#1dd1a1' }} onClick={() => handleUnlock(record)} />
              </Tooltip>
            )}
            {record.role === 'inactive' ? (
              <Tooltip title="Activate (requires approval)">
                <Button 
                  size="small" 
                  icon={<CheckCircleOutlined />} 
                  type="text" 
                  style={{ color: '#1dd1a1' }} 
                  onClick={() => openActionModal(record, 'activate_user_admin')} 
                />
              </Tooltip>
            ) : (
              <Tooltip title="Suspend (requires approval)">
                <Button 
                  size="small" 
                  icon={<LockOutlined />} 
                  type="text" 
                  style={{ color: '#ff6b6b' }} 
                  onClick={() => openActionModal(record, 'suspend_user_admin')} 
                />
              </Tooltip>
            )}
            <Tooltip title="Delete (requires approval)">
              <Button 
                size="small" 
                icon={<UserDeleteOutlined />} 
                type="text" 
                danger 
                onClick={() => openActionModal(record, 'delete_user_admin')} 
              />
            </Tooltip>
          </Space>
        ),
      },
    ],
    []
  );

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
  };

  return (
    <div className={styles.sectionContainer}>
      <div className={styles.sectionHeader}>
        <div>
          <h2>User Management</h2>
          <p className={styles.sectionDescription}>
            Manage regular user accounts. Actions require superadmin approval.
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
              placeholder="Search user by name or email"
              style={{ width: 240, background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: 10, color: '#e0e0e0' }}
            />
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
      </div>

      <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
        {error && (
          <div style={{ padding: 16, background: 'rgba(255,107,107,0.1)', color: '#ff6b6b', marginBottom: 12, borderRadius: 8 }}>
            <strong>Error loading users:</strong> {error}
          </div>
        )}
        <Table
          dataSource={users}
          columns={columns}
          loading={isLoading}
          pagination={{
            pageSize: pagination?.limit || 10,
            current: Math.max(1, pagination?.limit ? Math.floor(pagination.offset / pagination.limit) + 1 : 1),
            total: pagination?.total || 0,
            onChange: (page, pageSize) =>
              handleTableChange(
                { current: page, pageSize },
                { limit: pageSize, offset: (page - 1) * pageSize }
              ),
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            style: { color: '#e0e0e0' },
          }}
          rowKey="id"
          size="small"
          style={{ background: 'transparent', color: '#e0e0e0' }}
          className={styles.darkTable}
        />
      </div>

      {/* User Details Drawer */}
      <Drawer
        title={selectedUser ? `${selectedUser.username} - Details` : 'User Details'}
        placement="right"
        onClose={() => setSelectedUser(null)}
        open={!!selectedUser}
        width={500}
        bodyStyle={{ background: '#1a1a1a', color: '#e0e0e0' }}
        headerStyle={{ background: '#0f0f0f', borderBottom: '1px solid rgba(255,255,255,0.1)' }}
      >
        {selectedUser && (
          <>
            <Descriptions column={1} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="Username">{selectedUser.username}</Descriptions.Item>
              <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
              <Descriptions.Item label="Name">
                {`${selectedUser.firstName || ''} ${selectedUser.lastName || ''}`.trim() || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Role">
                <Tag color="blue">{selectedUser.role?.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Badge 
                  status={selectedUser.role === 'inactive' ? 'default' : 'success'} 
                  text={selectedUser.role === 'inactive' ? 'Inactive' : 'Active'} 
                />
              </Descriptions.Item>
              <Descriptions.Item label="Verified">
                {selectedUser.isVerified ? (
                  <Tag color="green">VERIFIED</Tag>
                ) : (
                  <Tag color="orange">UNVERIFIED</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Locked">
                {selectedUser.isLocked ? (
                  <Tag color="red" icon={<LockOutlined />}>LOCKED</Tag>
                ) : (
                  <span style={{ color: 'rgba(255,255,255,0.35)' }}>—</span>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Home Area">
                {selectedUser.home_area || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Work Area">
                {selectedUser.work_area || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Alert Radius">
                {selectedUser.alert_radius ? `${selectedUser.alert_radius} km` : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {selectedUser.createdAt ? dayjs(selectedUser.createdAt).format('DD MMM YYYY HH:mm') : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Last Login">
                {selectedUser.last_login ? dayjs(selectedUser.last_login).format('DD MMM YYYY HH:mm') : 'Never'}
              </Descriptions.Item>
            </Descriptions>

            <Space style={{ width: '100%', justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setSelectedUser(null)}>Close</Button>
              <Button 
                type="primary" 
                onClick={() => handleUnlock(selectedUser)}
                style={{ background: 'linear-gradient(135deg, #1a4f72, #2d7fb8)' }}
              >
                Unlock Account
              </Button>
            </Space>
          </>
        )}
      </Drawer>

      {/* Action Modal */}
      <Modal
        title={`${actionModal.action === 'suspend_user_admin' ? 'Suspend' : actionModal.action === 'activate_user_admin' ? 'Activate' : 'Delete'} User - Approval Required`}
        open={actionModal.visible}
        onCancel={() => setActionModal({ visible: false, user: null, action: null })}
        onOk={submitAction}
        okText="Submit for Approval"
        cancelText="Cancel"
        confirmLoading={isSubmittingAction}
        bodyStyle={{ background: '#1a1a1a', color: '#e0e0e0' }}
        headerStyle={{ background: '#0f0f0f', borderBottom: '1px solid rgba(255,255,255,0.1)' }}
        width={500}
      >
        {actionModal.user && (
          <>
            <div style={{ marginBottom: 24, padding: 12, background: 'rgba(45,127,184,0.1)', borderLeft: '4px solid #2d7fb8', borderRadius: 4 }}>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', marginBottom: 4 }}>Selected User</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0', marginBottom: 4 }}>{actionModal.user.username}</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{actionModal.user.email}</div>
            </div>

            <Form layout="vertical">
              <Form.Item label="Action">
                <span style={{ color: '#e0e0e0', fontSize: 14 }}>
                  {actionModal.action === 'suspend_user_admin' && 'Suspend User Account'}
                  {actionModal.action === 'activate_user_admin' && 'Activate User Account'}
                  {actionModal.action === 'delete_user_admin' && 'Delete User Account'}
                </span>
              </Form.Item>
              <Form.Item label="Reason for Action *">
                <Input.TextArea
                  placeholder="Provide a detailed reason for this action..."
                  rows={4}
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    borderColor: 'rgba(255,255,255,0.1)',
                    color: '#e0e0e0',
                  }}
                />
              </Form.Item>
            </Form>

            <div style={{ padding: 12, background: 'rgba(252,211,77,0.1)', borderLeft: '4px solid #f9a826', borderRadius: 4, fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
              <strong>Note:</strong> This action requires superadmin approval. The superadmin will review your request and reason before executing this action.
            </div>
          </>
        )}
      </Modal>
    </div>
  );
};

AdminUserManagement.propTypes = {
  token: PropTypes.string.isRequired,
  user: PropTypes.object,
};

export default AdminUserManagement;
