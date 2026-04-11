import React, { useState, useEffect } from 'react';
import {
  DatePicker,
  Button,
  Select,
  message,
  Card,
  Row,
  Col,
  Form,
  Input,
  Checkbox,
  Divider,
  Space,
  List,
  Typography,
  Tag,
  Empty,
  Descriptions,
  Popconfirm,
} from 'antd';
import {
  DownloadOutlined,
  FileTextOutlined,
  ScheduleOutlined,
  BarChartOutlined,
  HistoryOutlined,
  ClockCircleOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  FileUnknownOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext_updated';
import { apiService } from '../services/apiService_updated';
import styles from './ReportingDashboard.module.css';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TextArea } = Input;
const { Title, Text } = Typography;

const ReportingDashboard = () => {
  const { token } = useAuth();
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()]);
  const [reportType, setReportType] = useState('crime_summary');
  const [exportFormat, setExportFormat] = useState('pdf');
  const [loading, setLoading] = useState(false);
  const [scheduledReports, setScheduledReports] = useState([]);
  const [reportHistory, setReportHistory] = useState([]);

  // Report builder state
  const [customReport, setCustomReport] = useState({
    title: '',
    description: '',
    includeCharts: true,
    includeStatistics: true,
    includeRawData: false,
    recipients: [],
    schedule: 'manual',
  });

  useEffect(() => {
    if (token) {
      loadReportHistory();
      loadScheduledReports();
    }
  }, [token]);

  const loadReportHistory = async () => {
    try {
      const history = await apiService.getReportHistory(token);
      setReportHistory(history);
    } catch (error) {
      console.error('Failed to load report history:', error);
    }
  };

  const loadScheduledReports = async () => {
    try {
      const schedules = await apiService.getScheduledReports(token);
      setScheduledReports(schedules);
    } catch (error) {
      console.error('Failed to load scheduled reports:', error);
    }
  };

  const handleGenerateReport = async () => {
    if (!token) {
      message.error('Authentication required');
      return;
    }

    setLoading(true);
    try {
      const filters = {
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
        report_type: reportType,
        format: exportFormat,
        title: customReport.title?.trim() || null,
        ...customReport,
      };

      const response = await apiService.generateCustomReport(token, filters);
      message.success(`Report generated: ${response?.report_name || 'Success'}`);
      loadReportHistory();
    } catch (error) {
      console.error('Failed to generate report:', error);
      message.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleReport = async () => {
    try {
      const scheduleData = {
        ...customReport,
        date_range: {
          start: dateRange[0].format('YYYY-MM-DD'),
          end: dateRange[1].format('YYYY-MM-DD'),
        },
        report_type: reportType,
        format: exportFormat,
      };

      await apiService.scheduleReport(token, scheduleData);
      message.success('Report scheduled successfully');
      loadScheduledReports();
    } catch (error) {
      console.error('Failed to schedule report:', error);
      message.error('Failed to schedule report');
    }
  };

  const handleDownloadReport = async (reportId) => {
    try {
      // First, get the report details to know the filename
      const reportItem = reportHistory.find(r => r.id === reportId);
      const filename = reportItem?.report_name || `report_${reportId}.pdf`;
      
      // Call the download API
      const response = await fetch(`${apiService.API_BASE_URL}/admin/reports/download/${reportId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const contentDisposition = response.headers.get('content-disposition') || '';
      const serverFilenameMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      const serverFilename = decodeURIComponent(serverFilenameMatch?.[1] || serverFilenameMatch?.[2] || '');
      const a = document.createElement('a');
      a.href = url;
      a.download = serverFilename || filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success('Report downloaded successfully');
    } catch (error) {
      console.error('Failed to download report:', error);
      message.error('Failed to download report');
    }
  };

  const handleClearHistory = async () => {
    try {
      const result = await apiService.clearReportHistory(token);
      message.success(result?.message || 'Previous reports cleared');
      setReportHistory([]);
    } catch (error) {
      console.error('Failed to clear report history:', error);
      message.error(error.message || 'Failed to clear report history');
    }
  };

  const getReportTypeDescription = (type) => {
    switch (type) {
      case 'crime_summary':
        return 'Comprehensive crime statistics, trends, and area analysis';
      case 'user_activity':
        return 'User registration, activity patterns, and engagement metrics';
      case 'system_health':
        return 'System performance, uptime, and maintenance reports';
      default:
        return 'Custom report configuration';
    }
  };

  const getFormatIcon = (format) => {
    switch (format) {
      case 'pdf':
        return <FilePdfOutlined style={{ color: '#ff4d4f' }} />;
      case 'excel':
      case 'csv':
        return <FileExcelOutlined style={{ color: '#52c41a' }} />;
      default:
        return <FileUnknownOutlined />;
    }
  };

  return (
    <div className={styles.reportingDashboard}>
      <div className={styles.header}>
        <Title level={2}>
          <FileTextOutlined /> Comprehensive Reporting System
        </Title>
        <div className={styles.headerActionsRow}>
          <Text type="secondary">Generate, schedule, and manage detailed reports for analysis.</Text>
          <Popconfirm
            title="Clear previous reports?"
            description="This removes all report history entries and generated report files."
            okText="Clear"
            cancelText="Cancel"
            onConfirm={handleClearHistory}
          >
            <Button danger size="middle">Clear Previous Reports</Button>
          </Popconfirm>
        </div>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          {/* Report Builder */}
          <Card
            title={
              <Space>
                <BarChartOutlined />
                Report Builder
              </Space>
            }
            className={styles.reportBuilder}
            hoverable
          >
            <Form layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Report Type" required>
                    <Select
                      value={reportType}
                      onChange={setReportType}
                      placeholder="Select report type"
                      size="large"
                    >
                      <Option value="crime_summary">Crime Summary Report</Option>
                      <Option value="user_activity">User Activity Report</Option>
                      <Option value="system_health">System Health Report</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Export Format" required>
                    <Select
                      value={exportFormat}
                      onChange={setExportFormat}
                      placeholder="Select format"
                      size="large"
                    >
                      <Option value="pdf">PDF Document</Option>
                      <Option value="csv">CSV Spreadsheet</Option>
                      <Option value="excel">Excel Workbook</Option>
                      <Option value="json">JSON Data</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item label="Date Range" required>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates)}
                  style={{ width: '100%' }}
                  size="large"
                />
              </Form.Item>

              <Divider orientation="left">Report Configuration</Divider>

              <Form.Item label="Report Title">
                <Input
                  value={customReport.title}
                  onChange={(e) => setCustomReport({ ...customReport, title: e.target.value })}
                  placeholder="Enter report title"
                  size="large"
                />
              </Form.Item>

              <Form.Item label="Description">
                <TextArea
                  value={customReport.description}
                  onChange={(e) => setCustomReport({ ...customReport, description: e.target.value })}
                  placeholder="Describe the report purpose and scope"
                  rows={3}
                />
              </Form.Item>

              <Form.Item label="Include Sections">
                <Space direction="vertical">
                  <Checkbox
                    checked={customReport.includeCharts}
                    onChange={(e) => setCustomReport({ ...customReport, includeCharts: e.target.checked })}
                  >
                    Charts and Visualizations
                  </Checkbox>
                  <Checkbox
                    checked={customReport.includeStatistics}
                    onChange={(e) => setCustomReport({ ...customReport, includeStatistics: e.target.checked })}
                  >
                    Statistical Analysis
                  </Checkbox>
                  <Checkbox
                    checked={customReport.includeRawData}
                    onChange={(e) => setCustomReport({ ...customReport, includeRawData: e.target.checked })}
                  >
                    Raw Data Tables
                  </Checkbox>
                </Space>
              </Form.Item>

              <Form.Item label="Schedule">
                <Select
                  value={customReport.schedule}
                  onChange={(value) => setCustomReport({ ...customReport, schedule: value })}
                  size="large"
                >
                  <Option value="manual">Manual Generation</Option>
                  <Option value="daily">Daily</Option>
                  <Option value="weekly">Weekly</Option>
                  <Option value="monthly">Monthly</Option>
                </Select>
              </Form.Item>

              <Form.Item style={{ marginTop: 24 }}>
                <Space size="large">
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    onClick={handleGenerateReport}
                    loading={loading}
                    size="large"
                  >
                    Generate Report
                  </Button>
                  {customReport.schedule !== 'manual' && (
                    <Button
                      icon={<ScheduleOutlined />}
                      onClick={handleScheduleReport}
                      size="large"
                    >
                      Schedule Report
                    </Button>
                  )}
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {/* Report Preview */}
          <Card
            title="Report Preview"
            className={styles.reportPreview}
            style={{ marginTop: 24 }}
            hoverable
          >
            <div className={styles.previewContent}>
              <Title level={4}>{customReport.title || 'Untitled Report'}</Title>
              <Text type="secondary" display="block" style={{ marginBottom: 16 }}>
                {getReportTypeDescription(reportType)}
              </Text>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="Date Range">
                  {dateRange[0].format('MMM DD, YYYY')} - {dateRange[1].format('MMM DD, YYYY')}
                </Descriptions.Item>
                <Descriptions.Item label="Format">
                  <Space>
                    {getFormatIcon(exportFormat)}
                    {exportFormat.toUpperCase()}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="Sections">
                  {[
                    customReport.includeCharts && 'Charts',
                    customReport.includeStatistics && 'Statistics',
                    customReport.includeRawData && 'Raw Data',
                  ]
                    .filter(Boolean)
                    .join(', ') || 'None selected'}
                </Descriptions.Item>
              </Descriptions>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {/* Scheduled Reports */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                Scheduled Reports
              </Space>
            }
            className={styles.scheduledReports}
            hoverable
          >
            <List
              itemLayout="horizontal"
              dataSource={scheduledReports}
              locale={{ emptyText: <Empty description="No scheduled reports" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<ScheduleOutlined />}
                    title={item.report_name || 'Scheduled Report'}
                    description={
                      <Space direction="vertical" size={0}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {item.schedule_frequency || 'N/A'} • {item.format?.toUpperCase() || 'PDF'}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          Next: {item.next_run_at ? new Date(item.next_run_at).toLocaleString() : 'Not scheduled'}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>

          {/* Recent Reports */}
          <Card
            title={
              <Space>
                <HistoryOutlined />
                Recent Reports
              </Space>
            }
            className={styles.recentReports}
            style={{ marginTop: 24 }}
            hoverable
          >
            <List
              itemLayout="horizontal"
              dataSource={reportHistory.slice(0, 5)}
              locale={{ emptyText: <Empty description="No recent reports" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownloadReport(item.id)}
                      key="download"
                    />,
                  ]}
                >
                  <List.Item.Meta
                    avatar={getFormatIcon(item.format)}
                    title={item.report_name || 'Untitled Report'}
                    description={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.generated_at ? new Date(item.generated_at).toLocaleString() : 'Unknown date'}
                      </Text>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ReportingDashboard;
