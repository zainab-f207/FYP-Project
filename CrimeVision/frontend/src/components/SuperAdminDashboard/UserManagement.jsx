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
  LockOutlined,
  ReloadOutlined,
  TeamOutlined,
  UnlockOutlined,
  UserDeleteOutlined,
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
  const [permissionsModal, setPermissionsModal] = useState({ visible: false, user: null });
  const [isPerformingBulkAction, setIsPerformingBulkAction] = useState(false);

  const fetchUsers = useCallback(
    async (params) => {
      const response = await apiService.getUsers(token, params);
      return {
        data: response.users,
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

  const columns = useMemo(
    () => [
      {
        title: 'User',
        dataIndex: 'username',
        key: 'username',
        render: (username, record) => (
          <Space direction="vertical" size={0}>
            <Space>
              <TeamOutlined />
              <strong>{username}</strong>
              <Tooltip title={`User ID: ${record.id}`}>
                <Tag color="default">ID {record.id}</Tag>
              </Tooltip>
            </Space>
            <span className={styles.tableMetaText}>{record.email}</span>
          </Space>
        ),
      },
      {
        title: 'Name',
        dataIndex: 'fullName',
        key: 'fullName',
        render: (_, record) => `${record.firstName || ''} ${record.lastName || ''}`.trim() || '—',
      },
      {
        title: 'Role',
        dataIndex: 'role',
        key: 'role',
        filters: USER_ROLES.map((role) => ({ text: role.label, value: role.value })),
        render: (role) => <Tag color={ROLE_COLORS[role] || 'default'}>{role}</Tag>,
      },
      {
        title: 'Permissions',
        key: 'permissions',
        render: (_, record) => (
          <Space wrap>
            {(record.permissions || []).slice(0, 3).map((permission) => (
              <Tag key={permission}>{permission}</Tag>
            ))}
            {(record.permissions || []).length > 3 && <Tag>+{record.permissions.length - 3}</Tag>}
            <Button
              size="small"
              type="link"
              onClick={() => openPermissionsModal(record)}
            >
              Manage
            </Button>
          </Space>
        ),
      },
      {
        title: 'Created At',
        dataIndex: 'createdAt',
        key: 'createdAt',
        render: (createdAt) => (createdAt ? dayjs(createdAt).format('DD MMM YYYY HH:mm') : '—'),
      },
      {
        title: 'Status',
        dataIndex: 'role',
        key: 'status',
        render: (role) => (
          <Badge status={STATUS_COLORS[role] ? 'success' : 'default'} text={role === 'inactive' ? 'Inactive' : 'Active'} />
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        render: (_, record) => (
          <Space>
            <Tooltip title="View details">
              <Button icon={<EyeOutlined />} type="link" onClick={() => setSelectedUser(record)}>
                View
              </Button>
            </Tooltip>
            <Tooltip title="Edit permissions">
              <Button icon={<UnlockOutlined />} type="link" onClick={() => openPermissionsModal(record)}>
                Edit Permissions
              </Button>
            </Tooltip>
            {record.role === 'inactive' ? (
              <Tooltip title="Activate user">
                <Button
                  icon={<UnlockOutlined />}
                  type="link"
                  onClick={() => handleBulkAction('activate', [record.id])}
                >
                  Activate
                </Button>
              </Tooltip>
            ) : (
              <Tooltip title="Suspend user">
                <Button
                  icon={<LockOutlined />}
                  danger
                  type="link"
                  onClick={() => handleBulkAction('suspend', [record.id])}
                >
                  Suspend
                </Button>
              </Tooltip>
            )}
            <Tooltip title="Delete user">
              <Button icon={<UserDeleteOutlined />} danger type="link" onClick={() => handleBulkAction('delete', [record.id])} />
            </Tooltip>
          </Space>
        ),
      },
    ],
    [openPermissionsModal]
  );

  const bulkActionMenu = (
    <Space>
      {USER_BULK_ACTIONS.map((action) => (
        <Button
          key={action.value}
          onClick={() => handleBulkAction(action.value)}
          disabled={selectedRowKeys.length === 0}
          loading={isPerformingBulkAction}
        >
          {action.label}
        </Button>
      ))}
    </Space>
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
        <Space>
          <Tooltip title="Refresh">
            <Button icon={<ReloadOutlined />} onClick={() => loadData()}>
              Refresh
            </Button>
          </Tooltip>
        </Space>
      </div>

      <div className={styles.filtersRow}>
        <Form
          form={form}
          layout="inline"
          onFinish={handleApplyFilters}
          onReset={handleResetFilters}
          className={styles.filtersForm}
        >
          <Form.Item name="search">
            <Input.Search allowClear placeholder="Search by name or email" style={{ width: 220 }} />
          </Form.Item>
          <Form.Item name="role">
            <Select allowClear placeholder="Role" style={{ width: 160 }}>
              {USER_ROLES.map((role) => (
                <Select.Option key={role.value} value={role.value}>
                  {role.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Apply Filters
              </Button>
              <Button htmlType="reset">Reset</Button>
            </Space>
          </Form.Item>
        </Form>

        <div className={styles.actionBar}>{bulkActionMenu}</div>
      </div>

      <div className={styles.tableCard}>
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={users}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
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

      <Drawer
        width={460}
        title="User Details"
        open={!!selectedUser}
        onClose={() => setSelectedUser(null)}
      >
        {selectedUser && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Username">{selectedUser.username}</Descriptions.Item>
            <Descriptions.Item label="Full Name">
              {`${selectedUser.firstName || ''} ${selectedUser.lastName || ''}`.trim() || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="Role">{selectedUser.role}</Descriptions.Item>
            <Descriptions.Item label="Home Area">{selectedUser.homeArea || '—'}</Descriptions.Item>
            <Descriptions.Item label="Work Area">{selectedUser.workArea || '—'}</Descriptions.Item>
            <Descriptions.Item label="Alert Radius">{selectedUser.alertRadius || '—'}</Descriptions.Item>
            <Descriptions.Item label="Created At">
              {selectedUser.createdAt ? dayjs(selectedUser.createdAt).format('DD MMM YYYY HH:mm') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Permissions">
              <Space wrap>
                {(selectedUser.permissions || []).map((permission) => (
                  <Tag key={permission}>{permission}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <Modal
        title={`Manage Permissions${permissionsModal.user ? ` - ${permissionsModal.user.username}` : ''}`}
        open={permissionsModal.visible}
        onCancel={() => setPermissionsModal({ visible: false, user: null })}
        footer={null}
        destroyOnClose
      >
        <Form
          initialValues={{
            permissions: permissionsModal.user?.permissions || [],
          }}
          onFinish={handlePermissionsSubmit}
          layout="vertical"
        >
          <Form.Item name="permissions" label="Permissions">
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical">
                {USER_PERMISSIONS.map((permission) => (
                  <Checkbox key={permission.value} value={permission.value}>
                    {permission.label}
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
            <Button onClick={() => setPermissionsModal({ visible: false, user: null })}>Cancel</Button>
            <Button type="primary" htmlType="submit">
              Save Changes
            </Button>
          </Space>
        </Form>
      </Modal>
    </div>
  );
};

UserManagement.propTypes = {
  token: PropTypes.string.isRequired,
};

export default UserManagement;