import React, { useCallback, useMemo, useState } from 'react';
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
  ApartmentOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  LockOutlined,
  ReloadOutlined,
  UnlockOutlined,
  UserAddOutlined,
  UserDeleteOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiService from '../../services/apiService';
import usePaginatedResource from './hooks/usePaginatedResource';
import { USER_BULK_ACTIONS, USER_PERMISSIONS, USER_ROLES } from './constants/permissions';
import styles from './SuperAdminDashboard.module.css';

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
          await apiService.bulkUserActions(token, action, targetIds);
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
        render: (username, record) => (
          <Space direction="vertical" size={0}>
            <Space>
              <UserAddOutlined />
              <strong>{username}</strong>
              <Tag color="default">ID {record.id}</Tag>
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
        render: (role) => <Tag color="geekblue">{role}</Tag>,
      },
      {
        title: 'Department',
        dataIndex: 'department',
        key: 'department',
        render: (department) => department || '—',
      },
      {
        title: 'Last Login',
        dataIndex: 'lastLogin',
        key: 'lastLogin',
        render: (lastLogin) => (lastLogin ? dayjs(lastLogin).format('DD MMM YYYY HH:mm') : '—'),
      },
      {
        title: 'Status',
        dataIndex: 'role',
        key: 'status',
        render: (role) => (
          <Badge
            status={role === 'inactive' ? 'default' : 'processing'}
            text={role === 'inactive' ? 'Inactive' : 'Active'}
          />
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        render: (_, record) => (
          <Space>
            <Tooltip title="View details">
              <Button type="link" icon={<EyeOutlined />} onClick={() => setSelectedAdmin(record)}>
                View
              </Button>
            </Tooltip>
            {record.role === 'inactive' ? (
              <Tooltip title="Activate admin">
                <Button type="link" icon={<UnlockOutlined />} onClick={() => handleAdminAction('activate', [record.id])}>
                  Activate
                </Button>
              </Tooltip>
            ) : (
              <Tooltip title="Suspend admin">
                <Button
                  type="link"
                  danger
                  icon={<LockOutlined />}
                  onClick={() => handleAdminAction('suspend', [record.id])}
                >
                  Suspend
                </Button>
              </Tooltip>
            )}
            <Tooltip title="Delete admin">
              <Button
                type="link"
                danger
                icon={<UserDeleteOutlined />}
                onClick={() => handleAdminAction('delete', [record.id])}
              />
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
            <Input.Search allowClear placeholder="Search admin" style={{ width: 220 }} />
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

        <div className={styles.actionBar}>
          <Space>
            <Button
              icon={<UnlockOutlined />}
              onClick={() => handleAdminAction('activate')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
            >
              Activate
            </Button>
            <Button
              icon={<LockOutlined />}
              onClick={() => handleAdminAction('suspend')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
            >
              Suspend
            </Button>
            <Button
              icon={<UserDeleteOutlined />}
              danger
              onClick={() => handleAdminAction('delete')}
              disabled={selectedAdmins.length === 0}
              loading={isPerformingAction}
            >
              Delete
            </Button>
          </Space>
        </div>
      </div>

      <div className={styles.tableCard}>
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={admins}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
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

      <Drawer
        width={460}
        title="Admin Details"
        open={!!selectedAdmin}
        onClose={() => setSelectedAdmin(null)}
      >
        {selectedAdmin && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Username">{selectedAdmin.username}</Descriptions.Item>
            <Descriptions.Item label="Full Name">
              {`${selectedAdmin.firstName || ''} ${selectedAdmin.lastName || ''}`.trim() || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">{selectedAdmin.email || '—'}</Descriptions.Item>
            <Descriptions.Item label="Role">{selectedAdmin.role || '—'}</Descriptions.Item>
            <Descriptions.Item label="Department">{selectedAdmin.department || '—'}</Descriptions.Item>
            <Descriptions.Item label="Last Login">
              {selectedAdmin.lastLogin ? dayjs(selectedAdmin.lastLogin).format('DD MMM YYYY HH:mm') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Permissions">
              <Space wrap>
                {(selectedAdmin.permissions || []).map((permission) => (
                  <Tag key={permission}>{permission}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

AdminManagement.propTypes = {
  token: PropTypes.string.isRequired,
};

export default AdminManagement;