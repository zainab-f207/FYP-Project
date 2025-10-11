import React, { useState } from 'react';
import { Form, Input, Button, Select, DatePicker, message } from 'antd';
import styles from './ReportBuilder.module.css';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

const ReportBuilder = ({ onGenerate }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const onFinish = (values) => {
    if (!values.dateRange || values.dateRange.length !== 2) {
      message.error('Please select a valid date range');
      return;
    }
    setLoading(true);
    onGenerate({
      startDate: values.dateRange[0].format('YYYY-MM-DD'),
      endDate: values.dateRange[1].format('YYYY-MM-DD'),
      reportType: values.reportType,
      filters: values.filters || {},
      title: values.title,
    });
    setLoading(false);
  };

  return (
    <div className={styles.reportBuilder}>
      <h3>Custom Report Builder</h3>
      <Form form={form} onFinish={onFinish} layout="vertical">
        <Form.Item
          name="title"
          label="Report Title"
          rules={[{ required: true, message: 'Please enter a report title' }]}
        >
          <Input placeholder="Enter report title" />
        </Form.Item>
        <Form.Item
          name="reportType"
          label="Report Type"
          rules={[{ required: true, message: 'Please select a report type' }]}
        >
          <Select placeholder="Select report type">
            <Option value="crime_trends">Crime Trends</Option>
            <Option value="risk_distribution">Risk Distribution</Option>
            <Option value="area_analysis">Area Analysis</Option>
            <Option value="comparative">Comparative Analysis</Option>
          </Select>
        </Form.Item>
        <Form.Item
          name="dateRange"
          label="Date Range"
          rules={[{ required: true, message: 'Please select a date range' }]}
        >
          <RangePicker />
        </Form.Item>
        <Form.Item name="filters" label="Filters">
          <Select mode="multiple" placeholder="Select filters">
            <Option value="high_risk">High Risk Only</Option>
            <Option value="recent">Recent Crimes</Option>
            <Option value="by_area">By Area</Option>
          </Select>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            Generate Report
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default ReportBuilder;
