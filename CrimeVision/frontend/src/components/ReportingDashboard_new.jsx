import React, { useState, useEffect } from 'react';
import { DatePicker, Button, Select, message, Card, Row, Col, Form, Input, Checkbox, Divider, Space } from 'antd';
import { DownloadOutlined, FileTextOutlined, MailOutlined, ScheduleOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext_updated';
import apiService from '../services/apiService';
import styles from './ReportingDashboard.module.css';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TextArea } = Input;

const ReportingDashboard = () => {
  const { token } = useAuth();
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()]);
  const [reportType, setReportType] = useState('crime-summary');
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
    schedule: 'manual'
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
        ...customReport
      };

      await apiService.generateCustomReport(token, filters);
      message.success('Report generated successfully');
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
          end: dateRange[1].format('YYYY-MM-DD')
        },
        report_type: reportType,
        format: exportFormat
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
      await apiService.downloadReport(token, reportId);
      message.success('Report downloaded successfully');
    } catch (error) {
      console.error('Failed to download report:', error);
      message.error('Failed to download report');
    }
  };

  const getReportTypeDescription = (type) => {
    switch (type) {
      case 'crime-summary':
        return 'Comprehensive crime statistics, trends, and area analysis';
      case 'user-activity':
        return 'User registration, activity patterns, and engagement metrics';
      case 'system-health':
        return 'System performance, uptime, and maintenance reports';
      default:
        return 'Custom report configuration';
    }
  };

  return (
    <div className={styles.reportingDashboard}>
      <div className={styles.header}>
        <h2><FileTextOutlined /> Comprehensive Reporting System</h2>
        <p>Generate, schedule, and manage detailed reports</p>
      </div>

      <Row gutter={[24, 24]}>
        <Col span={16}>
          {/* Report Builder */}
          <Card title="Report Builder" className={styles.reportBuilder}>
            <Form layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Report Type">
                    <Select
                      value={reportType}
                      onChange={setReportType}
                      placeholder="Select report type"
                    >
                      <Option value="crime-summary">Crime Summary Report</Option>
                      <Option value="user-activity">User Activity Report</Option>
                      <Option value="system-health">System Health Report</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Export Format">
                    <Select
                      value={exportFormat}
                      onChange={setExportFormat}
                      placeholder="Select format"
                    >
                      <Option value="pdf">PDF Document</Option>
                      <Option value="csv">CSV Spreadsheet</Option>
                      <Option value="excel">Excel Workbook</Option>
                      <Option value="json">JSON Data</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item label="Date Range">
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates)}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Divider>Report Configuration</Divider>

              <Form.Item label="Report Title">
                <Input
                  value={customReport.title}
                  onChange={(e) => setCustomReport({...customReport, title: e.target.value})}
                  placeholder="Enter report title"
                />
              </Form.Item>

              <Form.Item label="Description">
                <TextArea
                  value={customReport.description}
                  onChange={(e) => setCustomReport({...customReport, description: e.target.value})}
                  placeholder="Describe the report purpose and scope"
                  rows={3}
                />
              </Form.Item>

              <Form.Item label="Include Sections">
                <Space direction="vertical">
                  <Checkbox
                    checked={customReport.includeCharts}
                    onChange={(e) => setCustomReport({...customReport, includeCharts: e.target.checked})}
                  >
                    Charts and Visualizations
                  </Checkbox>
                  <Checkbox
                    checked={customReport.includeStatistics}
                    onChange={(e) => setCustomReport({...customReport, includeStatistics: e.target.checked})}
                  >
                    Statistical Analysis
                  </Checkbox>
                  <Checkbox
                    checked={customReport.includeRawData}
                    onChange={(e) => setCustomReport({...customReport, includeRawData: e.target.checked})}
                  >
                    Raw Data Tables
                  </Checkbox>
                </Space>
              </Form.Item>

              <Form.Item label="Schedule">
                <Select
                  value={customReport.schedule}
                  onChange={(value) => setCustomReport({...customReport, schedule: value})}
                >
                  <Option value="manual">Manual Generation</Option>
                  <Option value="daily">Daily</Option>
                  <Option value="weekly">Weekly</Option>
                  <Option value="monthly">Monthly</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    onClick={handleGenerateReport}
                    loading={loading}
                  >
                    Generate Report
                  </Button>
                  {customReport.schedule !== 'manual' && (
                    <Button
                      icon={<ScheduleOutlined />}
                      onClick={handleScheduleReport}
                    >
                      Schedule Report
                    </Button>
                  )}
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {/* Report Preview */}
          <Card title="Report Preview" className={styles.reportPreview}>
            <div className={styles.previewContent}>
              <h3>{customReport.title || 'Untitled Report'}</h3>
              <p className={styles.reportType}>{getReportTypeDescription(reportType)}</p>
              <div className={styles.previewDetails}>
                <p><strong>Date Range:</strong> {dateRange[0].format('MMM DD, YYYY')} - {dateRange[1].format('MMM DD, YYYY')}</p>
                <p><strong>Format:</strong> {exportFormat.toUpperCase()}</p>
                <p><strong>Sections:</strong> {
                  [
                    customReport.includeCharts && 'Charts',
                    customReport.includeStatistics && 'Statistics',
                    customReport.includeRawData && 'Raw Data'
                  ].filter(Boolean).join(', ') || 'None selected'
                }</p>
              </div>
            </div>
          </Card>
        </Col>

        <Col span={8}>
          {/* Scheduled Reports */}
          <Card title="Scheduled Reports" className={styles.scheduledReports}>
            {scheduledReports.length > 0 ? (
              <div className={styles.scheduleList}>
                {scheduledReports.map((schedule) => (
                  <div key={schedule.id} className={styles.scheduleItem}>
                    <h4>{schedule.title}</h4>
                    <p>{schedule.schedule} • {schedule.format}</p>
                    <small>Next: {new Date(schedule.next_run).toLocaleDateString()}</small>
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptyState}>No scheduled reports</p>
            )}
          </Card>

          {/* Recent Reports */}
          <Card title="Recent Reports" className={styles.recentReports}>
            {reportHistory.length > 0 ? (
              <div className={styles.historyList}>
                {reportHistory.slice(0, 5).map((report) => (
                  <div key={report.id} className={styles.historyItem}>
                    <div className={styles.historyInfo}>
                      <h4>{report.title}</h4>
                      <p>{report.type} • {new Date(report.created_at).toLocaleDateString()}</p>
                    </div>
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownloadReport(report.id)}
                    >
                      Download
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptyState}>No reports generated yet</p>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ReportingDashboard;
