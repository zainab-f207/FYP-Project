import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Input, Select, Tag, Modal, Space, message, Spin,
  Row, Col, Statistic, Typography, Tooltip, Badge, Descriptions, Tabs
} from 'antd';
import {
  SearchOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined,
  RobotOutlined, EditOutlined, SafetyCertificateOutlined, DatabaseOutlined,
  ExclamationCircleOutlined, HistoryOutlined, SyncOutlined
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import apiService from '../../services/apiService';
import styles from './SuperAdminDashboard.module.css';
import ppcStyles from './PPCManagement.module.css';

const { Text, Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const PPCManagement = ({ token }) => {
  const { user } = useAuth();
  const [sections, setSections] = useState([]);
  const [stats, setStats] = useState({ total: 0, verified: 0, unverified: 0, law_types: 0 });
  const [lawTypes, setLawTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, per_page: 25, total: 0 });
  const [filters, setFilters] = useState({ law_type: '', is_verified: '', search: '' });
  const [selectedSection, setSelectedSection] = useState(null);
  const [aiResult, setAiResult] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [editForm, setEditForm] = useState({ english_title: '', notes: '', change_reason: '' });
  const [auditTrail, setAuditTrail] = useState([]);
  const [auditModal, setAuditModal] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [rateLimitCountdown, setRateLimitCountdown] = useState(0);
  const rateLimitTimerRef = React.useRef(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [missingModal, setMissingModal] = useState(false);
  const [missingPPCs, setMissingPPCs] = useState([]);
  const [insertingIdx, setInsertingIdx] = useState(new Set());
  const [insertedIdx, setInsertedIdx] = useState(new Set());

  const authToken = token ||
    localStorage.getItem('SafeVision_token') ||
    sessionStorage.getItem('SafeVision_token');

  // Auto-seed once if the law_sections table is empty after first load
  const autoSeededRef = React.useRef(false);

  const fetchSections = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page: pagination.page, per_page: pagination.per_page };
      if (filters.law_type) params.law_type = filters.law_type;
      if (filters.is_verified !== '') params.is_verified = filters.is_verified;
      if (filters.search) params.search = filters.search;

      const data = await apiService.getLawSections(authToken, params);
      setSections(data.sections || []);
      setPagination(prev => ({ ...prev, total: data.pagination?.total || 0 }));
      setStats(data.stats || stats);
    } catch (err) {
      message.error('Failed to load law sections: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [authToken, pagination.page, pagination.per_page, filters]);

  const fetchLawTypes = useCallback(async () => {
    try {
      const data = await apiService.getLawTypes(authToken);
      setLawTypes(data.law_types || []);
    } catch { /* ignore */ }
  }, [authToken]);

  useEffect(() => { fetchSections(); }, [fetchSections]);
  useEffect(() => { fetchLawTypes(); }, [fetchLawTypes]);

  // Countdown ticker for Gemini rate-limit
  useEffect(() => {
    if (rateLimitCountdown <= 0) {
      if (rateLimitTimerRef.current) clearInterval(rateLimitTimerRef.current);
      return;
    }
    rateLimitTimerRef.current = setInterval(() => {
      setRateLimitCountdown(prev => {
        if (prev <= 1) { clearInterval(rateLimitTimerRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(rateLimitTimerRef.current);
  }, [rateLimitCountdown > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-seed from hardcoded data when the table is empty on first load
  useEffect(() => {
    if (!loading && !autoSeededRef.current && stats.total === 0 && sections.length === 0) {
      autoSeededRef.current = true;
      handleSeed();
    }
  }, [loading, stats.total, sections.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const result = await apiService.seedLawSections(authToken);
      message.success(`Seeded ${result.inserted} sections (${result.skipped} already existed)`);
      fetchSections();
      fetchLawTypes();
    } catch (err) {
      message.error('Seed failed: ' + err.message);
    } finally {
      setSeeding(false);
    }
  };

  const handleVerifyAI = async (record) => {
    setSelectedSection(record);
    setAiResult(null);
    setRateLimitCountdown(0);
    setAiLoading(true);
    try {
      const result = await apiService.verifyLawSectionAI(authToken, record.section_number, record.law_type);
      setAiResult(result);
      if (result?.error === 'rate_limit') setRateLimitCountdown(65);
      if (result?.error === 'daily_quota') setRateLimitCountdown(0);
      if (result?.error === 'api_key_error') setRateLimitCountdown(0);
      if (result?.error?.startsWith('http_')) setRateLimitCountdown(0);
    } catch (err) {
      message.error('AI verification failed: ' + err.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleRetryVerify = () => {
    if (selectedSection) handleVerifyAI(selectedSection);
  };

  const handleScanMissing = async () => {
    setScanLoading(true);
    setMissingModal(true);
    setMissingPPCs([]);
    setInsertingIdx(new Set());
    setInsertedIdx(new Set());
    try {
      const result = await apiService.scanMissingPPCs(authToken);
      if (!result.success) throw new Error(result.error || 'Scan failed');
      setMissingPPCs(result.missing || []);
      if ((result.missing || []).length === 0) message.success('No missing important PPC sections found!');
    } catch (err) {
      message.error('Scan failed: ' + err.message);
      setMissingModal(false);
    } finally {
      setScanLoading(false);
    }
  };

  const handleInsertMissing = async (item, idx) => {
    setInsertingIdx(prev => new Set([...prev, idx]));
    try {
      await apiService.insertLawSection(authToken, { law_type: 'PPC', ...item });
      setInsertedIdx(prev => new Set([...prev, idx]));
      message.success(`PPC ${item.section_number} inserted successfully`);
      fetchSections();
    } catch (err) {
      message.error('Insert failed: ' + err.message);
    } finally {
      setInsertingIdx(prev => { const s = new Set(prev); s.delete(idx); return s; });
    }
  };

  const handleApproveAI = async () => {
    if (!selectedSection || !aiResult?.ai_title) return;
    try {
      await apiService.approveAISuggestion(authToken, selectedSection.id, aiResult.ai_title);
      message.success('AI suggestion approved and saved');
      setSelectedSection(null);
      setAiResult(null);
      fetchSections();
    } catch (err) {
      message.error('Approval failed: ' + err.message);
    }
  };

  const handleEdit = (record) => {
    setSelectedSection(record);
    setEditForm({ english_title: record.english_title, notes: record.notes || '', change_reason: '' });
    setEditModal(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedSection) return;
    try {
      await apiService.updateLawSection(authToken, selectedSection.id, {
        english_title: editForm.english_title,
        notes: editForm.notes,
        is_verified: true,
        change_reason: editForm.change_reason,
      });
      message.success('Section updated successfully');
      setEditModal(false);
      setSelectedSection(null);
      fetchSections();
    } catch (err) {
      message.error('Update failed: ' + err.message);
    }
  };

  const handleViewAudit = async (record) => {
    try {
      const data = await apiService.getLawSectionAudit(authToken, record.id);
      setAuditTrail(data.audit || []);
      setAuditModal(true);
    } catch (err) {
      message.error('Failed to load audit trail');
    }
  };

  const columns = [
    {
      title: 'Law', dataIndex: 'law_type', key: 'law_type', width: 80,
      render: (t) => <Tag color={t === 'PPC' ? 'blue' : t === 'ATA' ? 'red' : 'green'}>{t}</Tag>,
    },
    { title: 'Section', dataIndex: 'section_number', key: 'section_number', width: 100 },
    {
      title: 'English Title', dataIndex: 'english_title', key: 'english_title',
      ellipsis: true,
    },
    {
      title: 'Status', dataIndex: 'is_verified', key: 'is_verified', width: 110,
      render: (v) => v
        ? <Tag icon={<CheckCircleOutlined />} color="success">Verified</Tag>
        : <Tag icon={<CloseCircleOutlined />} color="warning">Unverified</Tag>,
    },
    { title: 'Source', dataIndex: 'source', key: 'source', width: 130,
      render: (s) => <Text type="secondary" style={{ fontSize: 12 }}>{s}</Text>,
    },
    {
      title: 'Actions', key: 'actions', width: 200, fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Verify with AI">
            <Button size="small" icon={<RobotOutlined />} onClick={() => handleVerifyAI(record)}
              style={{ color: '#00a6a6' }} />
          </Tooltip>
          <Tooltip title="Edit">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="Audit Trail">
            <Button size="small" icon={<HistoryOutlined />} onClick={() => handleViewAudit(record)} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className={ppcStyles.ppcWrapper}>
      {/* Stats Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #1a3a5f, #2d5a8e)', border: 'none' }}>
            <Statistic title={<span style={{ color: '#ccc' }}>Total Sections</span>}
              value={stats.total} valueStyle={{ color: '#fff' }}
              prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #0d6e3a, #14a05e)', border: 'none' }}>
            <Statistic title={<span style={{ color: '#ccc' }}>Verified</span>}
              value={stats.verified} valueStyle={{ color: '#fff' }}
              prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #b45309, #d97706)', border: 'none' }}>
            <Statistic title={<span style={{ color: '#ccc' }}>Unverified</span>}
              value={stats.unverified} valueStyle={{ color: '#fff' }}
              prefix={<ExclamationCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #6b21a8, #9333ea)', border: 'none' }}>
            <Statistic title={<span style={{ color: '#ccc' }}>Law Types</span>}
              value={stats.law_types} valueStyle={{ color: '#fff' }}
              prefix={<SafetyCertificateOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Controls */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={6}>
            <Input placeholder="Search sections..." prefix={<SearchOutlined />}
              value={filters.search}
              onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
              onPressEnter={() => { setPagination(p => ({ ...p, page: 1 })); fetchSections(); }}
              allowClear />
          </Col>
          <Col xs={12} sm={4}>
            <Select placeholder="Law Type" style={{ width: '100%' }} allowClear
              value={filters.law_type || undefined}
              onChange={(v) => { setFilters(f => ({ ...f, law_type: v || '' })); setPagination(p => ({ ...p, page: 1 })); }}>
              {lawTypes.map(lt => <Option key={lt} value={lt}>{lt}</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={4}>
            <Select placeholder="Status" style={{ width: '100%' }} allowClear
              value={filters.is_verified !== '' ? filters.is_verified : undefined}
              onChange={(v) => { setFilters(f => ({ ...f, is_verified: v ?? '' })); setPagination(p => ({ ...p, page: 1 })); }}>
              <Option value={true}>Verified</Option>
              <Option value={false}>Unverified</Option>
            </Select>
          </Col>
          <Col xs={24} sm={10} style={{ textAlign: 'right' }}>
            <Space wrap>
              <Button
                size="small"
                type={filters.law_type === 'PPC' ? 'primary' : 'default'}
                style={filters.law_type === 'PPC' ? { background: '#1a3a5f', borderColor: '#00a6a6' } : {}}
                onClick={() => {
                  const next = filters.law_type === 'PPC' ? '' : 'PPC';
                  setFilters(f => ({ ...f, law_type: next }));
                  setPagination(p => ({ ...p, page: 1 }));
                }}
              >
                {filters.law_type === 'PPC' ? '✓ PPC Only' : 'Show PPC'}
              </Button>
              <Button icon={<ReloadOutlined />} onClick={fetchSections}>Refresh</Button>
              <Button
                icon={<RobotOutlined />}
                loading={scanLoading}
                onClick={handleScanMissing}
                style={{ background: '#1a1a3f', borderColor: '#00a6a6', color: '#00a6a6' }}
              >
                Scan Missing PPCs
              </Button>
              <Button type="primary" icon={<DatabaseOutlined />} loading={seeding}
                onClick={() => Modal.confirm({
                  title: 'Seed Database from Hardcoded Data?',
                  content: 'This will import all hardcoded PPC/ATA/CNSA sections into the database. Existing entries will be skipped.',
                  onOk: handleSeed,
                })}
                style={{ background: '#1a3a5f' }}>
                Seed from Code
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* PPC Quick-Jump */}
      {filters.law_type === 'PPC' && (
        <div style={{ marginBottom: 10, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginRight: 4 }}>Jump to:</span>
          {['299','302','304-A','320','324','354','365-B','370','376','392','420','489-C'].map(sec => (
            <Tag key={sec}
              color="blue"
              style={{ cursor: 'pointer', fontWeight: 600, fontSize: 12 }}
              onClick={() => {
                setFilters(f => ({ ...f, search: sec }));
                setPagination(p => ({ ...p, page: 1 }));
              }}>
              {sec}
            </Tag>
          ))}
          {filters.search && (
            <Tag color="default" style={{ cursor: 'pointer' }}
              onClick={() => { setFilters(f => ({ ...f, search: '' })); setPagination(p => ({ ...p, page: 1 })); }}>
              ✕ Clear
            </Tag>
          )}
        </div>
      )}

      {/* Table */}
      <Card size="small">
        <Table
          columns={columns}
          dataSource={sections}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 900 }}
          pagination={{
            current: pagination.page,
            pageSize: pagination.per_page,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} sections`,
            onChange: (page, pageSize) => setPagination({ page, per_page: pageSize, total: pagination.total }),
          }}
        />
      </Card>

      {/* AI Verification Modal */}
      <Modal
        title={<span style={{ color: '#e2e8f0' }}><RobotOutlined style={{ color: '#00a6a6', marginRight: 8 }} />AI Verification</span>}
        open={!!selectedSection && !editModal}
        onCancel={() => { setSelectedSection(null); setAiResult(null); setRateLimitCountdown(0); }}
        styles={{
          content: { background: '#0f1d35', border: '1px solid rgba(0,166,166,0.3)' },
          header: { background: '#0f1d35', borderBottom: '1px solid rgba(255,255,255,0.1)' },
          body: { background: '#0f1d35', paddingTop: 12, paddingBottom: 12 },
          footer: { background: '#0f1d35', borderTop: '1px solid rgba(255,255,255,0.08)' },
          mask: { backdropFilter: 'blur(4px)' },
        }}
        footer={aiResult ? [
          <Button key="close" onClick={() => { setSelectedSection(null); setAiResult(null); }}>Close</Button>,
          aiResult.ai_title && aiResult.confidence !== 'none' && !aiResult.error && (
            <Button key="approve" type="primary" icon={<CheckCircleOutlined />}
              onClick={handleApproveAI} style={{ background: '#0d6e3a' }}>
              Approve AI Suggestion
            </Button>
          ),
        ] : null}
        width={650}
      >
        {selectedSection && (
          <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 8, padding: '10px 14px', marginBottom: 14, border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 16px', fontSize: 13 }}>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Law Type</span>
              <span><Tag color={selectedSection.law_type === 'PPC' ? 'blue' : selectedSection.law_type === 'ATA' ? 'red' : 'green'} style={{ fontWeight: 700 }}>{selectedSection.law_type}</Tag></span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Section</span>
              <span style={{ color: '#fff', fontWeight: 700 }}>{selectedSection.section_number}</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Current Title</span>
              <span style={{ color: '#e2e8f0' }}>{selectedSection.english_title}</span>
            </div>
          </div>
        )}
        {aiLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <p style={{ marginTop: 16, color: 'rgba(255,255,255,0.6)' }}>Consulting AI...</p>
          </div>
        ) : aiResult ? (
          <div>
            {/* Rate-limit / error banner */}
            {(aiResult.confidence === 'none' || aiResult.error) ? (
              <div style={{
                background: aiResult.error === 'daily_quota' ? 'rgba(220,38,38,0.15)' : 'rgba(234,179,8,0.12)',
                border: `1px solid ${aiResult.error === 'daily_quota' ? 'rgba(220,38,38,0.4)' : 'rgba(234,179,8,0.35)'}`,
                borderRadius: 10, padding: '16px 18px',
              }}>
                <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8,
                  color: aiResult.error === 'daily_quota' || aiResult.error === 'api_key_error' ? '#f87171' : '#facc15' }}>
                  {aiResult.error === 'daily_quota' ? '🚫 Quota / Billing Issue'
                    : aiResult.error === 'api_key_error' ? '🔑 API Key Error'
                    : aiResult.error === 'rate_limit' ? '⏱ Rate Limit (per minute)'
                    : '⚠ AI Verification Failed'}
                </div>
                <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: 13, lineHeight: 1.6, marginBottom: 12,
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {aiResult.explanation}
                </div>
                {aiResult.error === 'daily_quota' && (
                  <div style={{ background: 'rgba(220,38,38,0.1)', borderRadius: 6, padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    <div style={{ marginBottom: 6, color: '#f87171', fontWeight: 600 }}>How to fix this:</div>
                    <div>Option A — New Groq key: <a href="https://console.groq.com" target="_blank" rel="noreferrer" style={{ color: '#60a5fa' }}>console.groq.com</a> → API Keys → Create</div>
                    <div>Option B — OpenRouter key (fallback): <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" style={{ color: '#60a5fa' }}>openrouter.ai/keys</a> → Create key</div>
                    <div>2. Paste in <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>backend/.env</code> → <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>GROQ_API_KEY=...</code> or <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>OPENROUTER_API_KEY=...</code></div>
                    <div>3. Restart the backend server (Ctrl+C → uvicorn main:app --reload)</div>
                  </div>
                )}
                {aiResult.error === 'api_key_error' && (
                  <div style={{ background: 'rgba(220,38,38,0.1)', borderRadius: 6, padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                    <div style={{ marginBottom: 6, color: '#f87171', fontWeight: 600 }}>API key is invalid or rejected:</div>
                    <div>1. Get a new Groq key at <a href="https://console.groq.com" target="_blank" rel="noreferrer" style={{ color: '#60a5fa' }}>console.groq.com</a> (free, no billing)</div>
                    <div>2. Or get an OpenRouter key at <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" style={{ color: '#60a5fa' }}>openrouter.ai/keys</a> (free tier available)</div>
                    <div>3. Update <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>GROQ_API_KEY</code> or <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>OPENROUTER_API_KEY</code> in <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>backend/.env</code></div>
                    <div>4. Restart the backend (Ctrl+C → uvicorn main:app --reload)</div>
                  </div>
                )}
                {aiResult.error === 'rate_limit' && (
                  <div>
                    {rateLimitCountdown > 0 ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
                        <div style={{ position: 'relative', width: 54, height: 54, flexShrink: 0 }}>
                          <svg width="54" height="54" style={{ transform: 'rotate(-90deg)' }}>
                            <circle cx="27" cy="27" r="23" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="4" />
                            <circle cx="27" cy="27" r="23" fill="none"
                              stroke="#facc15" strokeWidth="4"
                              strokeDasharray={`${2 * Math.PI * 23}`}
                              strokeDashoffset={`${2 * Math.PI * 23 * (rateLimitCountdown / 65)}`}
                              strokeLinecap="round"
                              style={{ transition: 'stroke-dashoffset 1s linear' }}
                            />
                          </svg>
                          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 14, fontWeight: 700, color: '#facc15' }}>{rateLimitCountdown}</div>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>Cooling down — {rateLimitCountdown}s remaining</div>
                          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 3 }}>Retry button activates automatically</div>
                        </div>
                        <Button disabled size="small" icon={<SyncOutlined spin />} style={{ opacity: 0.4 }}>
                          Wait {rateLimitCountdown}s
                        </Button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ color: '#4ade80', fontSize: 13, fontWeight: 600 }}>✓ Ready to retry</span>
                        <Button type="primary" size="small" icon={<RobotOutlined />}
                          onClick={handleRetryVerify} loading={aiLoading}
                          style={{ background: '#00a6a6', borderColor: '#00a6a6' }}>
                          Retry Verification
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {/* Status badge row */}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 2 }}>
                  {aiResult.status === 'correct' && <Tag color="success" style={{ fontWeight: 700, fontSize: 12 }}>✓ CORRECT</Tag>}
                  {aiResult.status === 'incorrect' && <Tag color="error" style={{ fontWeight: 700, fontSize: 12 }}>✗ INCORRECT TITLE</Tag>}
                  {aiResult.status === 'not_found' && <Tag color="warning" style={{ fontWeight: 700, fontSize: 12 }}>⚠ NOT FOUND</Tag>}
                  {aiResult.suggested_action === 'keep' && <Tag color="cyan" style={{ fontSize: 11 }}>Suggested: Keep as-is</Tag>}
                  {aiResult.suggested_action === 'update_title' && <Tag color="orange" style={{ fontSize: 11 }}>Suggested: Update Title</Tag>}
                  {aiResult.suggested_action === 'review' && <Tag color="purple" style={{ fontSize: 11 }}>Suggested: Manual Review</Tag>}
                </div>
                {/* AI result rows */}
                {[
                  ['AI Title', <span style={{ color: '#34d399', fontWeight: 700 }}>
                    {aiResult.ai_title || 'Not found'}
                    {aiResult._from_cache && <Tag style={{ marginLeft: 8, fontSize: 10 }} color="default">Cached · {aiResult._cache_age_minutes}m ago</Tag>}
                  </span>],
                  ['Confidence', <Tag color={aiResult.confidence === 'high' ? 'green' : aiResult.confidence === 'medium' ? 'orange' : 'red'} style={{ fontWeight: 700 }}>
                    {aiResult.confidence?.toUpperCase()}
                  </Tag>],
                  ['Matches Current', aiResult.matches_current
                    ? <Tag color="success" icon={<CheckCircleOutlined />}>Yes — Title Matches</Tag>
                    : <Tag color="warning" icon={<ExclamationCircleOutlined />}>Different — Review Suggested</Tag>],
                  ['Explanation', <span style={{ color: 'rgba(255,255,255,0.85)', lineHeight: 1.6 }}>{aiResult.explanation}</span>],
                  ...(aiResult.punishment ? [['Punishment', <span style={{ color: '#fbbf24', fontWeight: 600, lineHeight: 1.6 }}>{aiResult.punishment}</span>]] : []),
                  ...(aiResult.purpose ? [['Purpose / Rationale', <span style={{ color: 'rgba(200,220,255,0.85)', lineHeight: 1.6, fontStyle: 'italic' }}>{aiResult.purpose}</span>]] : []),
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: 8,
                    padding: '9px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.07)' }}>
                    <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12, paddingTop: 2 }}>{label}</span>
                    <span>{value}</span>
                  </div>
                ))}
                {aiResult.related_ppc && aiResult.related_ppc.length > 0 && (
                  <div style={{ padding: '9px 12px', borderRadius: 6, background: 'rgba(59,130,246,0.08)',
                    border: '1px solid rgba(59,130,246,0.2)' }}>
                    <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12, marginBottom: 6 }}>Related PPC Sections</div>
                    <Space wrap size={4}>
                      {aiResult.related_ppc.map(sec => (
                        <Tag key={sec} color="blue"
                          style={{ cursor: 'pointer', fontWeight: 700, fontSize: 13 }}
                          onClick={() => {
                            setSelectedSection(null); setAiResult(null);
                            setFilters(f => ({ ...f, law_type: 'PPC', search: sec }));
                            setPagination(p => ({ ...p, page: 1 }));
                          }}>
                          PPC {sec}
                        </Tag>
                      ))}
                    </Space>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 6 }}>
                      Click any tag to jump to that PPC section in the table
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      {/* Missing PPCs Scan Modal */}
      <Modal
        title={<span style={{ color: '#e2e8f0' }}><RobotOutlined style={{ color: '#00a6a6', marginRight: 8 }} />AI: Missing PPC Sections</span>}
        open={missingModal}
        onCancel={() => setMissingModal(false)}
        footer={<Button onClick={() => setMissingModal(false)}>Close</Button>}
        width={750}
        styles={{
          content: { background: '#0f1d35', border: '1px solid rgba(0,166,166,0.3)' },
          header: { background: '#0f1d35', borderBottom: '1px solid rgba(255,255,255,0.1)' },
          body: { background: '#0f1d35', paddingTop: 12, paddingBottom: 12 },
          footer: { background: '#0f1d35', borderTop: '1px solid rgba(255,255,255,0.08)' },
        }}
      >
        {scanLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <p style={{ marginTop: 16, color: 'rgba(255,255,255,0.6)' }}>AI is scanning all PPC sections... (may take 10-20s)</p>
          </div>
        ) : missingPPCs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#4ade80', fontSize: 16, fontWeight: 600 }}>
            ✓ No important missing PPC sections found!
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: 12, color: 'rgba(255,255,255,0.55)', fontSize: 13 }}>
              AI found <strong style={{ color: '#facc15' }}>{missingPPCs.length}</strong> important PPC sections not in your database. Click <strong>Insert</strong> to add each one.
            </div>
            {missingPPCs.map((item, idx) => (
              <div key={idx} style={{
                background: insertedIdx.has(idx) ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${insertedIdx.has(idx) ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.1)'}`,
                borderRadius: 8, padding: '10px 14px', marginBottom: 8,
                display: 'flex', alignItems: 'flex-start', gap: 12,
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <Tag color="blue" style={{ fontWeight: 700, fontSize: 13 }}>PPC {item.section_number}</Tag>
                    {item.chapter && <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11 }}>{item.chapter}</span>}
                  </div>
                  <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{item.english_title}</div>
                  {item.punishment_summary && (
                    <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>⚖ {item.punishment_summary}</div>
                  )}
                </div>
                <div style={{ flexShrink: 0 }}>
                  {insertedIdx.has(idx) ? (
                    <Tag color="success" style={{ fontWeight: 700 }}>✓ Inserted</Tag>
                  ) : (
                    <Button
                      type="primary"
                      size="small"
                      loading={insertingIdx.has(idx)}
                      onClick={() => handleInsertMissing(item, idx)}
                      style={{ background: '#00a6a6', borderColor: '#00a6a6' }}
                    >
                      Insert
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal title="Edit Law Section" open={editModal}
        onCancel={() => { setEditModal(false); setSelectedSection(null); }}
        onOk={handleSaveEdit} okText="Save & Verify">
        {selectedSection && (
          <>
            <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Law Type">
                <Tag>{selectedSection.law_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Section">{selectedSection.section_number}</Descriptions.Item>
            </Descriptions>
            <div style={{ marginBottom: 12 }}>
              <Text strong>English Title:</Text>
              <Input value={editForm.english_title}
                onChange={e => setEditForm(f => ({ ...f, english_title: e.target.value }))}
                style={{ marginTop: 4 }} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>Notes:</Text>
              <TextArea rows={2} value={editForm.notes}
                onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))}
                style={{ marginTop: 4 }} />
            </div>
            <div>
              <Text strong>Reason for Change:</Text>
              <Input value={editForm.change_reason}
                onChange={e => setEditForm(f => ({ ...f, change_reason: e.target.value }))}
                placeholder="e.g., Verified from official gazette"
                style={{ marginTop: 4 }} />
            </div>
          </>
        )}
      </Modal>

      {/* Audit Trail Modal */}
      <Modal
        title={<span style={{ color: '#e2e8f0' }}><HistoryOutlined style={{ color: '#00a6a6', marginRight: 8 }} />Change History</span>}
        open={auditModal}
        onCancel={() => setAuditModal(false)}
        footer={<Button onClick={() => setAuditModal(false)}>Close</Button>}
        width={750}
        styles={{
          content: { background: '#0f1d35', border: '1px solid rgba(0,166,166,0.3)' },
          header: { background: '#0f1d35', borderBottom: '1px solid rgba(255,255,255,0.1)' },
          body: { background: '#0f1d35', paddingTop: 12, paddingBottom: 4 },
          footer: { background: '#0f1d35', borderTop: '1px solid rgba(255,255,255,0.08)' },
        }}
      >
        {auditTrail.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 32, color: 'rgba(255,255,255,0.4)', fontSize: 14 }}>
            No change history recorded yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {auditTrail.map((entry, i) => {
              const actionMap = {
                update: { label: 'Title Updated', color: '#facc15' },
                ai_approve: { label: 'AI Suggestion Approved', color: '#34d399' },
                insert: { label: 'Section Inserted', color: '#60a5fa' },
                delete: { label: 'Section Deleted', color: '#f87171' },
              };
              const action = actionMap[entry.action] || { label: entry.action, color: '#a78bfa' };
              return (
                <div key={entry.id || i} style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderLeft: `3px solid ${action.color}`,
                  borderRadius: 8, padding: '10px 14px',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <Tag style={{ background: 'rgba(0,0,0,0.3)', borderColor: action.color, color: action.color, fontWeight: 700 }}>
                      {action.label}
                    </Tag>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ color: '#00a6a6', fontSize: 12, fontWeight: 600 }}>{entry.changed_by}</span>
                      <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11 }}>
                        {entry.created_at ? new Date(entry.created_at).toLocaleString('en-PK', { dateStyle: 'medium', timeStyle: 'short' }) : '-'}
                      </span>
                    </div>
                  </div>
                  {(entry.old_title || entry.new_title) && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: entry.change_reason ? 6 : 0 }}>
                      {entry.old_title && (
                        <div style={{ background: 'rgba(239,68,68,0.08)', borderRadius: 4, padding: '5px 8px' }}>
                          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 2 }}>BEFORE</div>
                          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{entry.old_title}</div>
                        </div>
                      )}
                      {entry.new_title && (
                        <div style={{ background: 'rgba(16,185,129,0.08)', borderRadius: 4, padding: '5px 8px' }}>
                          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 2 }}>AFTER</div>
                          <div style={{ fontSize: 12, color: '#e2e8f0' }}>{entry.new_title}</div>
                        </div>
                      )}
                    </div>
                  )}
                  {entry.change_reason && (
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4, fontStyle: 'italic' }}>
                      Reason: {entry.change_reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PPCManagement;

