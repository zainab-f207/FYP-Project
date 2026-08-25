import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import apiService from '../../services/apiService';
import styles from './ApprovalRequests.module.css';

const actionLabels = {
  delete_user: 'Delete User',
  bulk_delete: 'Bulk Delete Users',
  bulk_suspend: 'Bulk Suspend Users',
  change_role_to_admin: 'Promote to Admin',
  change_role_to_superadmin: 'Promote to Super Admin',
  fir_ocr_submission: 'FIR OCR Submission',
};

const actionIcons = {
  delete_user: 'fa-user-minus',
  bulk_delete: 'fa-users-slash',
  bulk_suspend: 'fa-user-lock',
  change_role_to_admin: 'fa-user-shield',
  change_role_to_superadmin: 'fa-crown',
  fir_ocr_submission: 'fa-file-image',
};

const APPROVAL_CATEGORIES = {
  fir: {
    label: 'FIR Approvals',
    color: '#8b5cf6',
    actions: ['fir_ocr_submission'],
  },
  admin: {
    label: 'Admin Approvals',
    color: '#2d7fb8',
    actions: ['delete_user', 'bulk_delete', 'bulk_suspend', 'change_role_to_admin', 'change_role_to_superadmin'],
  },
};

const getApprovalCategory = (actionType) => (
  actionType === 'fir_ocr_submission' ? APPROVAL_CATEGORIES.fir : APPROVAL_CATEGORIES.admin
);

const statusColors = {
  pending: { color: '#f9a826', bg: '#f9a82615', icon: 'fa-clock' },
  approved: { color: '#1dd1a1', bg: '#1dd1a115', icon: 'fa-check-circle' },
  rejected: { color: '#ff6b6b', bg: '#ff6b6b15', icon: 'fa-times-circle' },
};

const normalizeRiskLevel = (value) => {
  const v = String(value || '').toLowerCase();
  if (v.includes('critical') || v.includes('avoid')) return 'Critical';
  if (v.includes('high') || v.includes('warning')) return 'High';
  if (v.includes('moderate') || v.includes('medium') || v.includes('caution')) return 'Moderate';
  return 'Low';
};

const riskColor = (level) => ({ Critical: '#7c3aed', High: '#dc2626', Moderate: '#f97316', Low: '#22c55e' }[level] || '#22c55e');
const riskIcon = (level) => ({ Critical: 'fa-skull-crossbones', High: 'fa-exclamation-circle', Moderate: 'fa-info-circle', Low: 'fa-check-circle' }[level] || 'fa-check-circle');
const actionLabel = (level) => ({ Critical: 'Avoid', High: 'Warning', Moderate: 'Caution', Low: 'Safe' }[level] || 'Safe');

/**
 * Normalize various OCR date formats to YYYY-MM-DD.
 * Returns null if conversion is not possible (backend will use today).
 */
const normalizeToISO = (raw) => {
  if (!raw) return null;
  const s = String(raw).trim();
  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  // DD-MM-YYYY or DD/MM/YYYY
  const dmy = s.match(/^(\d{1,2})[\-\/](\d{1,2})[\-\/](\d{4})$/);
  if (dmy) return `${dmy[3]}-${dmy[2].padStart(2,'0')}-${dmy[1].padStart(2,'0')}`;
  // MM/DD/YYYY
  const mdy = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (mdy) {
    // Disambiguate: if first group > 12 it must be DD
    if (parseInt(mdy[1]) > 12)
      return `${mdy[3]}-${mdy[2].padStart(2,'0')}-${mdy[1].padStart(2,'0')}`;
    return `${mdy[3]}-${mdy[1].padStart(2,'0')}-${mdy[2].padStart(2,'0')}`;
  }
  // YYYY/MM/DD
  const ymd = s.match(/^(\d{4})\/(\d{2})\/(\d{2})$/);
  if (ymd) return `${ymd[1]}-${ymd[2]}-${ymd[3]}`;
  // Try native Date parse as last resort
  const ts = Date.parse(s);
  if (!isNaN(ts)) {
    const d = new Date(ts);
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }
  return null; // backend will use today's date
};

const PendingApprovalsPanel = () => {
  const { user, token, refreshAuthToken } = useAuth();
  const [requests, setRequests] = useState([]);
  const [myRequests, setMyRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reviewNotes, setReviewNotes] = useState({});
  const [processing, setProcessing] = useState(null);
  const [showInfo, setShowInfo] = useState(true);

  // FIR edit state – keyed by request id
  const [firEdits, setFirEdits] = useState({});
  const [editingFir, setEditingFir] = useState({});   // { [reqId]: true/false }
  const [sectionMeanings, setSectionMeanings] = useState({}); // { [reqId]: { [section]: { lawType, crimeName } } }

  // Auto-prediction results after FIR approval: { [reqId]: { loading, result, area, crimeType } }
  const [autoPredictions, setAutoPredictions] = useState({});
  // FIR image state: lazy-loaded from the detail endpoint (keyed by request id)
  const [loadedImages, setLoadedImages] = useState({});
  // Lightbox: null = closed, string = base64 image to display
  const [lightboxImage, setLightboxImage] = useState(null);

  // Submit form state (for admins)
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [submitForm, setSubmitForm] = useState({ action_type: '', target_type: 'user', target_id: '', notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState('');

  const isSuperAdmin = user?.role === 'superadmin';

  const refreshAttemptedRef = React.useRef(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      if (isSuperAdmin) {
        const data = await apiService.getPendingApprovals(token);
        setRequests(data.requests || []);
      }
      const myData = await apiService.getMyApprovalRequests(token);
      setMyRequests(myData.requests || []);
      refreshAttemptedRef.current = false; // reset on success
    } catch (err) {
      // If token expired, try to refresh once — new token triggers re-fetch via dependency
      if (err.message === 'Invalid token' && !refreshAttemptedRef.current) {
        refreshAttemptedRef.current = true;
        const refreshed = await refreshAuthToken();
        if (refreshed) return; // token state update → useEffect re-runs fetchData
      }
      console.error('Failed to fetch approvals:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, isSuperAdmin, refreshAuthToken]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Lazy-load FIR images for SuperAdmin: fetch full request (with base64 image) per card
  useEffect(() => {
    if (!isSuperAdmin || !token) return;
    const firRequests = requests.filter(r => r.action_type === 'fir_ocr_submission');
    firRequests.forEach(async (req) => {
      if (loadedImages[req.id] !== undefined) return; // already loaded or attempted
      // Mark as loading to prevent duplicate fetches
      setLoadedImages(prev => ({ ...prev, [req.id]: null }));
      try {
        const full = await apiService.getApprovalRequest(token, req.id);
        const img = full?.request_data?.fir_image_base64 || null;
        setLoadedImages(prev => ({ ...prev, [req.id]: img }));
      } catch {
        setLoadedImages(prev => ({ ...prev, [req.id]: null }));
      }
    });
  }, [requests, isSuperAdmin, token]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── helpers for FIR edit mode ───────────────────────────────────
  const startEditingFir = async (req) => {
    const rd = req.request_data || {};
    const ef = rd.extracted_fields || {};
    const sectionCrimeMap = {};
    (ef.section_crimes || []).forEach(sc => {
      if (sc?.section) {
        sectionCrimeMap[String(sc.section)] = {
          lawType: sc.law_type || 'PPC',
          crimeName: sc.crime_name || `Section ${sc.section}`,
        };
      }
    });

    setFirEdits(prev => ({
      ...prev,
      [req.id]: {
        crime_date: ef.crime_date || '',
        crime_time: ef.crime_time || '',
        crime_area: ef.crime_area || '',
        sections: [...(rd.extracted_sections || [])],
        newSection: '',
      },
    }));
    setEditingFir(prev => ({ ...prev, [req.id]: true }));

    // Resolve meanings for sections not already present in extracted section_crimes
    const sections = rd.extracted_sections || [];
    if (sections.length > 0) {
      const resolved = { ...sectionCrimeMap };
      await Promise.all(sections.map(async (secRaw) => {
        const sec = String(secRaw);
        if (resolved[sec]) return;
        let lawType = 'PPC';
        let sectionNumber = sec;
        if (sec.includes('-')) {
          const [maybeLaw, maybeSection] = sec.split('-', 2);
          if (maybeLaw && maybeSection) {
            lawType = maybeLaw.toUpperCase();
            sectionNumber = maybeSection;
          }
        }
        try {
          const lookup = await apiService.lookupLawSection(sectionNumber, lawType);
          if (lookup?.found && lookup?.section?.english_title) {
            resolved[sec] = {
              lawType: lookup.section.law_type || lawType,
              crimeName: lookup.section.english_title,
            };
            return;
          }
          if (lookup?.crime_name) {
            resolved[sec] = {
              lawType: lookup.law_type || lawType,
              crimeName: lookup.crime_name,
            };
            return;
          }
        } catch {
          // Ignore lookup failures and keep fallback below
        }
        resolved[sec] = {
          lawType,
          crimeName: `Section ${sec}`,
        };
      }));
      setSectionMeanings(prev => ({ ...prev, [req.id]: resolved }));
    } else {
      setSectionMeanings(prev => ({ ...prev, [req.id]: sectionCrimeMap }));
    }
  };

  const cancelEditingFir = (reqId) => {
    setEditingFir(prev => ({ ...prev, [reqId]: false }));
  };

  const updateFirEdit = (reqId, field, value) => {
    setFirEdits(prev => ({
      ...prev,
      [reqId]: { ...prev[reqId], [field]: value },
    }));
  };

  const addSection = async (reqId) => {
    const sec = (firEdits[reqId]?.newSection || '').trim();
    if (!sec) return;
    const normalized = sec.toUpperCase().replace(/\s+/g, '');
    if ((firEdits[reqId]?.sections || []).includes(normalized)) {
      setFirEdits(prev => ({
        ...prev,
        [reqId]: { ...prev[reqId], newSection: '' },
      }));
      return;
    }

    let lawType = 'PPC';
    let sectionNumber = normalized;
    if (normalized.includes('-')) {
      const [maybeLaw, maybeSection] = normalized.split('-', 2);
      if (maybeLaw && maybeSection && ['PPC', 'ATA', 'CNSA', 'CRPC'].includes(maybeLaw)) {
        lawType = maybeLaw;
        sectionNumber = maybeSection;
      }
    }

    let resolvedSection = lawType === 'PPC' ? sectionNumber : `${lawType}-${sectionNumber}`;
    let crimeName = `Section ${resolvedSection}`;
    try {
      const lookup = await apiService.lookupLawSection(sectionNumber, lawType);
      if (lookup?.found && lookup?.section?.english_title) {
        const lt = lookup.section.law_type || lawType;
        const sn = lookup.section.section_number || sectionNumber;
        resolvedSection = lt === 'PPC' ? sn : `${lt}-${sn}`;
        crimeName = lookup.section.english_title;
        lawType = lt;
      } else if (lookup?.crime_name) {
        crimeName = lookup.crime_name;
        lawType = lookup.law_type || lawType;
        resolvedSection = lawType === 'PPC' ? sectionNumber : `${lawType}-${sectionNumber}`;
      }
    } catch {
      // Keep fallback labels
    }

    setFirEdits(prev => ({
      ...prev,
      [reqId]: {
        ...prev[reqId],
        sections: [...(prev[reqId]?.sections || []), resolvedSection],
        newSection: '',
      },
    }));
    setSectionMeanings(prev => ({
      ...prev,
      [reqId]: {
        ...(prev[reqId] || {}),
        [resolvedSection]: {
          lawType,
          crimeName,
        },
      },
    }));
  };

  const removeSection = (reqId, idx) => {
    setFirEdits(prev => ({
      ...prev,
      [reqId]: {
        ...prev[reqId],
        sections: prev[reqId].sections.filter((_, i) => i !== idx),
      },
    }));
  };

  const handleReview = async (requestId, approved) => {
    setProcessing(requestId);
    try {
      let editedData = null;
      // If FIR was in edit mode and we're approving, send edited data
      if (approved && editingFir[requestId] && firEdits[requestId]) {
        const e = firEdits[requestId];
        editedData = {
          extracted_fields: {
            crime_date: e.crime_date,
            crime_time: e.crime_time || '',
            crime_area: e.crime_area,
          },
          extracted_sections: e.sections,
        };
      }
      await apiService.reviewApproval(token, requestId, approved, reviewNotes[requestId] || '', editedData);

      // Auto-predict risk for approved FIR OCR submissions
      if (approved) {
        const req = requests.find(r => r.id === requestId);
        if (req?.action_type === 'fir_ocr_submission') {
          const ef  = req.request_data?.extracted_fields || {};
          const loc = ef.location || {};
          // Prefer transliterated / English area; fall back to raw OCR text
          const apArea      = ef.area_english || ef.area_translit || ef.crime_area || null;
          const apCrimeType = ef.crime_type   || null;
          // Normalize date — OCR may produce DD-MM-YYYY, DD/MM/YYYY, etc.
          const apDate      = normalizeToISO(ef.crime_date);  // null → backend uses today
          const apTime      = ef.crime_time   || null;
          if (apArea && apCrimeType) {
            const predKey = `${requestId}_pred`;
            setAutoPredictions(prev => ({ ...prev, [predKey]: { loading: true, result: null, area: apArea, crimeType: apCrimeType } }));
            apiService.predictRisk(apArea, apCrimeType, apDate, apTime)
              .then(r => setAutoPredictions(prev => ({ ...prev, [predKey]: { loading: false, result: r, area: apArea, crimeType: apCrimeType } })))
              .catch(() => setAutoPredictions(prev => ({ ...prev, [predKey]: { loading: false, result: null, area: apArea, crimeType: apCrimeType } })));
          }
        }
      }

      setRequests(prev => prev.filter(r => r.id !== requestId));
      setReviewNotes(prev => { const copy = { ...prev }; delete copy[requestId]; return copy; });
      setEditingFir(prev => { const copy = { ...prev }; delete copy[requestId]; return copy; });
      setFirEdits(prev => { const copy = { ...prev }; delete copy[requestId]; return copy; });
    } catch (err) {
      console.error('Failed to review approval:', err);
      alert(`Failed to ${approved ? 'approve' : 'reject'} request: ${err.message}`);
    } finally {
      setProcessing(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const getStatusInfo = (status) => statusColors[status] || statusColors.pending;

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    if (!submitForm.action_type) { alert('Please select an action type.'); return; }
    setSubmitting(true);
    setSubmitSuccess('');
    try {
      await apiService.submitApprovalRequest(
        token,
        submitForm.action_type,
        submitForm.target_type || 'user',
        submitForm.target_id || null,
        { notes: submitForm.notes || '' }
      );
      setSubmitSuccess('Approval request submitted successfully!');
      setSubmitForm({ action_type: '', target_type: 'user', target_id: '', notes: '' });
      setShowSubmitForm(false);
      fetchData(); // refresh lists
      setTimeout(() => setSubmitSuccess(''), 4000);
    } catch (err) {
      console.error('Failed to submit approval request:', err);
      alert(`Failed to submit: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
    <div className={styles.approvalPanel}>
      {/* Header */}
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon} style={{ background: 'linear-gradient(135deg, #8b5cf6, #00d4ff)' }}>
            <i className="fas fa-gavel"></i>
          </div>
          <div>
            <h3>{isSuperAdmin ? 'Approval Management' : 'My Approval Requests'}</h3>
            <p className={styles.headerSub}>
              {isSuperAdmin
                ? `${requests.length} pending · ${myRequests.length} total submitted`
                : `${myRequests.length} request${myRequests.length !== 1 ? 's' : ''} submitted`}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!isSuperAdmin && (
            <button className={styles.refreshBtn} onClick={() => setShowSubmitForm(!showSubmitForm)}
              title={showSubmitForm ? 'Cancel' : 'New Request'}
              style={{ background: showSubmitForm ? '#ff6b6b15' : '#8b5cf615', color: showSubmitForm ? '#ff6b6b' : '#8b5cf6' }}>
              <i className={`fas fa-${showSubmitForm ? 'times' : 'plus'}`}></i>
            </button>
          )}
          <button className={styles.refreshBtn} onClick={() => setShowInfo(!showInfo)}
            title={showInfo ? 'Hide info' : 'How it works'}>
            <i className={`fas fa-${showInfo ? 'chevron-up' : 'question-circle'}`}></i>
          </button>
          <button className={styles.refreshBtn} onClick={fetchData} disabled={loading}>
            <i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i>
          </button>
        </div>
      </div>

      {/* Info Section */}
      {showInfo && (
        <div className={styles.infoSection}>
          <div className={styles.infoHeader}>
            <i className="fas fa-shield-alt"></i>
            <h4>How the Approval System Works</h4>
          </div>
          <p className={styles.infoDesc}>
            Certain sensitive actions require <strong>Super Admin approval</strong> before they can be executed.
            This ensures critical operations are reviewed and authorized, maintaining system security and accountability.
          </p>
          <div className={styles.workflowSteps}>
            <div className={styles.workflowStep}>
              <div className={styles.stepIcon} style={{ background: '#00d4ff20', color: '#00d4ff' }}>
                <i className="fas fa-paper-plane"></i>
              </div>
              <div className={styles.stepText}>
                <strong>1. Admin Submits</strong>
                <span>Admin initiates a sensitive action</span>
              </div>
            </div>
            <div className={styles.stepArrow}><i className="fas fa-arrow-right"></i></div>
            <div className={styles.workflowStep}>
              <div className={styles.stepIcon} style={{ background: '#f9a82620', color: '#f9a826' }}>
                <i className="fas fa-hourglass-half"></i>
              </div>
              <div className={styles.stepText}>
                <strong>2. Awaits Review</strong>
                <span>Request queued for super admin</span>
              </div>
            </div>
            <div className={styles.stepArrow}><i className="fas fa-arrow-right"></i></div>
            <div className={styles.workflowStep}>
              <div className={styles.stepIcon} style={{ background: '#1dd1a120', color: '#1dd1a1' }}>
                <i className="fas fa-check-double"></i>
              </div>
              <div className={styles.stepText}>
                <strong>3. Approved/Rejected</strong>
                <span>Action executed or denied</span>
              </div>
            </div>
          </div>
          <div className={styles.actionsList}>
            <span className={styles.actionsTitle}><i className="fas fa-list"></i> Actions Requiring Approval:</span>
            <div className={styles.actionsGrid} style={{ gridTemplateColumns: '1fr' }}>
              {Object.values(APPROVAL_CATEGORIES).map((category) => (
                <div key={category.label} style={{ marginBottom: 8 }}>
                  <div style={{ marginBottom: 8, color: category.color, fontSize: '0.76rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {category.label}
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {category.actions.map((key) => (
                      <div key={key} className={styles.actionItem}>
                        <i className={`fas ${actionIcons[key] || 'fa-gavel'}`}></i>
                        <span>{actionLabels[key]}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Success Message */}
      {submitSuccess && (
        <div className={styles.successMsg}>
          <i className="fas fa-check-circle"></i> {submitSuccess}
        </div>
      )}

      {/* Admin: Submit Approval Request Form */}
      {!isSuperAdmin && showSubmitForm && (
        <div className={styles.submitFormSection}>
          <h4 className={styles.sectionTitle} style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
            <i className="fas fa-paper-plane"></i> Submit New Approval Request
          </h4>
          <form onSubmit={handleSubmitRequest} className={styles.submitForm}>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label><i className="fas fa-bolt"></i> Action Type <span style={{ color: '#ff6b6b' }}>*</span></label>
                <select value={submitForm.action_type}
                  onChange={e => setSubmitForm(p => ({ ...p, action_type: e.target.value }))} required>
                  <option value="">Select action...</option>
                  <option value="fir_ocr_submission">{actionLabels.fir_ocr_submission}</option>
                  <optgroup label="Admin Approvals">
                    <option value="delete_user">{actionLabels.delete_user}</option>
                    <option value="bulk_delete">{actionLabels.bulk_delete}</option>
                    <option value="bulk_suspend">{actionLabels.bulk_suspend}</option>
                    <option value="change_role_to_admin">{actionLabels.change_role_to_admin}</option>
                    <option value="change_role_to_superadmin">{actionLabels.change_role_to_superadmin}</option>
                  </optgroup>
                </select>
              </div>
              {/* Target Type & Target ID — only relevant for user-targeted actions */}
              {submitForm.action_type !== 'fir_ocr_submission' && (
                <>
                  <div className={styles.formGroup}>
                    <label><i className="fas fa-bullseye"></i> Target Type</label>
                    <select value={submitForm.target_type}
                      onChange={e => setSubmitForm(p => ({ ...p, target_type: e.target.value }))}>
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label><i className="fas fa-hashtag"></i> Target ID</label>
                    <input type="number" placeholder="User/Admin ID"
                      value={submitForm.target_id}
                      onChange={e => setSubmitForm(p => ({ ...p, target_id: e.target.value }))} />
                  </div>
                </>
              )}
            </div>
            {/* FIR OCR Submission info banner */}
            {submitForm.action_type === 'fir_ocr_submission' && (
              <div style={{
                background: '#8b5cf615', border: '1px solid #8b5cf640', borderRadius: '10px',
                padding: '12px 16px', marginTop: '4px', display: 'flex', gap: '10px', alignItems: 'flex-start',
              }}>
                <i className="fas fa-info-circle" style={{ color: '#8b5cf6', marginTop: '2px', flexShrink: 0 }}></i>
                <div style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--text-primary)' }}>FIR OCR Submission</strong> must be done from the
                  {' '}<strong>FIR OCR Panel</strong> (in Crime Data Management). Upload the FIR image there, extract
                  the data, then click <em>"Submit for SuperAdmin Approval"</em> — the request will appear here
                  automatically with the full extracted data and document preview.
                </div>
              </div>
            )}
            <div className={styles.formGroup} style={{ marginTop: '10px' }}>
              <label><i className="fas fa-sticky-note"></i> Notes (optional)</label>
              <textarea placeholder="Explain why this action is needed..."
                value={submitForm.notes}
                onChange={e => setSubmitForm(p => ({ ...p, notes: e.target.value }))}
                rows={3} />
            </div>
            <div className={styles.formActions}>
              <button type="button" className={styles.cancelFormBtn}
                onClick={() => { setShowSubmitForm(false); setSubmitForm({ action_type: '', target_type: 'user', target_id: '', notes: '' }); }}>
                Cancel
              </button>
              <button type="submit" className={styles.submitFormBtn} disabled={submitting || !submitForm.action_type}>
                {submitting ? <><i className={`fas fa-spinner ${styles.spin}`}></i> Submitting...</> : <><i className="fas fa-paper-plane"></i> Submit Request</>}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Superadmin: Pending Requests */}
      {isSuperAdmin && (
        <>
          <h4 className={styles.sectionTitle}><i className="fas fa-hourglass-half"></i> Pending Requests</h4>
          <div className={styles.requestsList}>
            {loading ? (
              <div className={styles.loadingState}>
                <div className={styles.spinner}></div>
                <p>Loading pending requests...</p>
              </div>
            ) : error ? (
              <div className={styles.errorState}>
                <i className="fas fa-exclamation-triangle"></i>
                <p>{error}</p>
                <button onClick={fetchData}>Retry</button>
              </div>
            ) : requests.length === 0 ? (
              <div className={styles.emptyState}>
                <i className="fas fa-check-double"></i>
                <h4>All Clear</h4>
                <p>No pending approval requests at the moment.</p>
              </div>
            ) : (
              requests.map((req) => {
                const sInfo = getStatusInfo(req.status || 'pending');
                return (
                  <div key={req.id} className={`${styles.requestCard} ${styles[`status_${req.status || 'pending'}`]}`}>
                    <div className={styles.requestTop}>
                      <div className={styles.actionBadge}>
                        <i className={`fas ${actionIcons[req.action_type] || 'fa-gavel'}`}></i>
                        {actionLabels[req.action_type] || req.action_type}
                      </div>
                      <div className={styles.statusBadge} style={{ color: getApprovalCategory(req.action_type).color, borderColor: getApprovalCategory(req.action_type).color, background: `${getApprovalCategory(req.action_type).color}15` }}>
                        {getApprovalCategory(req.action_type).label}
                      </div>
                      <div className={styles.statusBadge} style={{ color: sInfo.color, borderColor: sInfo.color, background: sInfo.bg }}>
                        <i className={`fas ${sInfo.icon}`}></i> {(req.status || 'pending').charAt(0).toUpperCase() + (req.status || 'pending').slice(1)}
                      </div>
                    </div>
                    <div className={styles.requestBody}>
                      {req.duplicate_candidate && req.action_type === 'fir_ocr_submission' && (
                        <div className={styles.duplicateBadge}>
                          <div className={styles.duplicateBadgeTitle}>
                            <i className="fas fa-copy"></i> Duplicate Candidate
                          </div>
                          <div className={styles.duplicateBadgeReason}>
                            {req.duplicate_reason || 'This FIR appears to already exist in the crimes database.'}
                          </div>
                        </div>
                      )}
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}><i className="fas fa-user"></i> Requested By</span>
                        <span>{req.admin_username || req.admin_id || '—'}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}><i className="fas fa-crosshairs"></i> Target</span>
                        <span>{req.target_type} {req.target_id ? `#${req.target_id}` : ''}</span>
                      </div>
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}><i className="far fa-calendar-alt"></i> Submitted</span>
                        <span>{formatDate(req.requested_at || req.created_at)}</span>
                      </div>
                      {/* FIR OCR Submission: Show image + extracted data (editable) */}
                      {req.action_type === 'fir_ocr_submission' && req.request_data ? (
                        <div className={styles.firPreviewSection}>
                          {loadedImages[req.id] ? (
                            <div
                              className={styles.firImagePreview}
                              onClick={() => setLightboxImage(loadedImages[req.id])}
                              title="Click to enlarge"
                            >
                              <img src={loadedImages[req.id]} alt="FIR Document" style={{ maxWidth: '100%', borderRadius: '8px' }} />
                            </div>
                          ) : loadedImages[req.id] === undefined ? (
                            <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                              <i className="fas fa-spinner fa-spin"></i> Loading FIR image...
                            </div>
                          ) : null}
                          <div className={styles.firExtractedData}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <h5 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '0.82rem' }}>
                                <i className="fas fa-database"></i> Extracted Data
                              </h5>
                              {isSuperAdmin && req.status === 'pending' && !editingFir[req.id] && (
                                <button
                                  onClick={() => startEditingFir(req)}
                                  style={{ background: 'none', border: '1px solid #8b5cf6', color: '#8b5cf6', borderRadius: '6px', padding: '3px 10px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                                >
                                  <i className="fas fa-pen"></i> Edit
                                </button>
                              )}
                              {editingFir[req.id] && (
                                <button
                                  onClick={() => cancelEditingFir(req.id)}
                                  style={{ background: 'none', border: '1px solid #ff6b6b', color: '#ff6b6b', borderRadius: '6px', padding: '3px 10px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                                >
                                  <i className="fas fa-times"></i> Cancel Edit
                                </button>
                              )}
                            </div>

                            {/* ── READ-ONLY or EDIT mode ── */}
                            {editingFir[req.id] && firEdits[req.id] ? (
                              <div className={styles.firFieldsGrid}>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Date</span>
                                  <input type="date" value={firEdits[req.id].crime_date}
                                    onChange={(e) => updateFirEdit(req.id, 'crime_date', e.target.value)}
                                    style={{ width: '100%', padding: '4px 8px', borderRadius: '6px', border: '1px solid #8b5cf640', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.8rem' }}
                                  />
                                </div>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Time</span>
                                  <input type="text" placeholder="e.g. 09:30 AM"
                                    value={firEdits[req.id].crime_time || ''}
                                    onChange={(e) => updateFirEdit(req.id, 'crime_time', e.target.value)}
                                    style={{ width: '100%', padding: '4px 8px', borderRadius: '6px', border: '1px solid #8b5cf640', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.8rem' }}
                                  />
                                </div>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Area (Urdu)</span>
                                  <input type="text" value={firEdits[req.id].crime_area}
                                    onChange={(e) => updateFirEdit(req.id, 'crime_area', e.target.value)}
                                    style={{ width: '100%', padding: '4px 8px', borderRadius: '6px', border: '1px solid #8b5cf640', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.8rem', fontFamily: "'Noto Nastaliq Urdu', serif", direction: 'rtl' }}
                                  />
                                </div>
                                <div className={styles.firField} style={{ gridColumn: '1 / -1' }}>
                                  <span className={styles.firFieldLabel}>Sections</span>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
                                    {firEdits[req.id].sections.map((s, i) => (
                                      <span key={i} style={{ padding: '2px 8px', borderRadius: '6px', background: '#8b5cf620', color: '#8b5cf6', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                        §{s}
                                        <i className="fas fa-times-circle" style={{ cursor: 'pointer', fontSize: '0.7rem', opacity: 0.7 }}
                                          onClick={() => removeSection(req.id, i)}></i>
                                      </span>
                                    ))}
                                  </div>
                                  {firEdits[req.id].sections.length > 0 && (
                                    <div style={{ marginBottom: '8px' }}>
                                      <ul style={{ margin: 0, paddingLeft: '18px' }}>
                                        {firEdits[req.id].sections.map((s, i) => (
                                          <li key={`m-${i}`} style={{ color: 'var(--text-secondary)', fontSize: '0.76rem', marginBottom: '2px' }}>
                                            <strong style={{ color: '#8b5cf6' }}>§{s}</strong>
                                            {' — '}
                                            {sectionMeanings[req.id]?.[s]?.crimeName || `Section ${s}`}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                  <div style={{ display: 'flex', gap: '4px' }}>
                                    <input type="text" placeholder="Add section (e.g. 302)"
                                      value={firEdits[req.id].newSection || ''}
                                      onChange={(e) => updateFirEdit(req.id, 'newSection', e.target.value)}
                                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSection(req.id); } }}
                                      style={{ flex: 1, padding: '4px 8px', borderRadius: '6px', border: '1px solid #8b5cf640', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.78rem' }}
                                    />
                                    <button onClick={() => addSection(req.id)}
                                      style={{ background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer' }}>
                                      <i className="fas fa-plus"></i>
                                    </button>
                                  </div>
                                </div>
                                {req.request_data.extracted_fields?.location?.latitude && (
                                  <div className={styles.firField}>
                                    <span className={styles.firFieldLabel}>Location</span>
                                    <span style={{ fontSize: '0.78rem' }}>{Number(req.request_data.extracted_fields.location.latitude).toFixed(4)}, {Number(req.request_data.extracted_fields.location.longitude).toFixed(4)}</span>
                                  </div>
                                )}
                              </div>
                            ) : req.request_data.extracted_fields && (
                              <div className={styles.firFieldsGrid}>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Date</span>
                                  <span>{req.request_data.extracted_fields.crime_date || '—'}</span>
                                </div>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Time</span>
                                  <span>{req.request_data.extracted_fields.crime_time || '—'}</span>
                                </div>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Area</span>
                                  <span style={{ fontFamily: "'Noto Nastaliq Urdu', serif" }}>
                                    {req.request_data.extracted_fields.crime_area || '—'}
                                  </span>
                                </div>
                                <div className={styles.firField}>
                                  <span className={styles.firFieldLabel}>Crime Type</span>
                                  <span>{req.request_data.extracted_fields.crime_type || '—'}</span>
                                </div>
                                {req.request_data.extracted_fields.location?.latitude && (
                                  <div className={styles.firField}>
                                    <span className={styles.firFieldLabel}>Location</span>
                                    <span>{Number(req.request_data.extracted_fields.location.latitude).toFixed(4)}, {Number(req.request_data.extracted_fields.location.longitude).toFixed(4)}</span>
                                  </div>
                                )}
                              </div>
                            )}
                            {!editingFir[req.id] && req.request_data.extracted_sections?.length > 0 && (
                              <div style={{ marginTop: '6px' }}>
                                <ul style={{ margin: 0, paddingLeft: '18px' }}>
                                  {req.request_data.extracted_sections.map((s, i) => {
                                    const sc = (req.request_data.extracted_fields?.section_crimes || []).find(x => String(x.section) === String(s));
                                    return (
                                      <li key={i} style={{ color: 'var(--text-secondary)', fontSize: '0.76rem', marginBottom: '2px' }}>
                                        <strong style={{ color: '#8b5cf6' }}>§{s}</strong>
                                        {' — '}
                                        {sc?.crime_name || `Section ${s}`}
                                      </li>
                                    );
                                  })}
                                </ul>
                              </div>
                            )}
                            {req.request_data.confidence && (
                              <div style={{ marginTop: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                <i className="fas fa-chart-line"></i> Confidence: {req.request_data.confidence}%
                              </div>
                            )}
                          </div>
                        </div>
                      ) : req.request_data && Object.keys(req.request_data).length > 0 && (
                        <div className={styles.reviewNotes}>
                          <i className="fas fa-info-circle"></i>
                          <span>{JSON.stringify(req.request_data)}</span>
                        </div>
                      )}
                      <div style={{ marginTop: '10px' }}>
                        <textarea
                          placeholder="Add review notes (optional)..."
                          value={reviewNotes[req.id] || ''}
                          onChange={(e) => setReviewNotes(prev => ({ ...prev, [req.id]: e.target.value }))}
                          className={styles.reviewTextarea}
                        />
                      </div>
                      <div className={styles.reviewActions}>
                        <button className={styles.rejectBtn} onClick={() => handleReview(req.id, false)}
                          disabled={processing === req.id}>
                          <i className="fas fa-times"></i> Reject
                        </button>
                        <button className={styles.approveBtn} onClick={() => handleReview(req.id, true)}
                          disabled={processing === req.id}>
                          <i className="fas fa-check"></i> {editingFir[req.id] ? 'Save & Approve' : 'Approve'}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}

      {/* My Requests History (both admin and superadmin) */}
      {myRequests.length > 0 && (
        <>
          <h4 className={styles.sectionTitle}><i className="fas fa-history"></i> My Request History</h4>
          <div className={styles.requestsList}>
            {myRequests.map((req) => {
              const sInfo = getStatusInfo(req.status || 'pending');
              return (
                <div key={req.id} className={`${styles.requestCard} ${styles[`status_${req.status || 'pending'}`]}`}>
                  <div className={styles.requestTop}>
                    <div className={styles.actionBadge}>
                      <i className={`fas ${actionIcons[req.action_type] || 'fa-gavel'}`}></i>
                      {actionLabels[req.action_type] || req.action_type}
                    </div>
                    <div className={styles.statusBadge} style={{ color: getApprovalCategory(req.action_type).color, borderColor: getApprovalCategory(req.action_type).color, background: `${getApprovalCategory(req.action_type).color}15` }}>
                      {getApprovalCategory(req.action_type).label}
                    </div>
                    <div className={styles.statusBadge} style={{ color: sInfo.color, borderColor: sInfo.color, background: sInfo.bg }}>
                      <i className={`fas ${sInfo.icon}`}></i> {(req.status || 'pending').charAt(0).toUpperCase() + (req.status || 'pending').slice(1)}
                    </div>
                  </div>
                  <div className={styles.requestBody}>
                    {req.action_type === 'fir_ocr_submission' ? (
                      // FIR-specific info
                      <>
                        {req.request_data?.extracted_fields?.crime_date && (
                          <div className={styles.detailRow}>
                            <span className={styles.detailLabel}><i className="fas fa-calendar-day"></i> Crime Date</span>
                            <span>{req.request_data.extracted_fields.crime_date}</span>
                          </div>
                        )}
                        {req.request_data?.extracted_fields?.crime_time && (
                          <div className={styles.detailRow}>
                            <span className={styles.detailLabel}><i className="fas fa-clock"></i> Crime Time</span>
                            <span>{req.request_data.extracted_fields.crime_time}</span>
                          </div>
                        )}
                        {req.request_data?.extracted_fields?.crime_area && (
                          <div className={styles.detailRow}>
                            <span className={styles.detailLabel}><i className="fas fa-map-marker-alt"></i> Area</span>
                            <span style={{ fontFamily: "'Noto Nastaliq Urdu', serif" }}>
                              {req.request_data.extracted_fields.crime_area}
                            </span>
                          </div>
                        )}
                        {req.request_data?.extracted_sections?.length > 0 && (
                          <div className={styles.detailRow}>
                            <span className={styles.detailLabel}><i className="fas fa-balance-scale"></i> Sections</span>
                            <span>{req.request_data.extracted_sections.map(s => `§${s}`).join(', ')}</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}><i className="fas fa-crosshairs"></i> Target</span>
                        <span>{req.target_type} {req.target_id ? `#${req.target_id}` : ''}</span>
                      </div>
                    )}
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}><i className="far fa-calendar-alt"></i> Submitted</span>
                      <span>{formatDate(req.requested_at || req.created_at)}</span>
                    </div>
                    {req.reviewed_by && (
                      <div className={styles.detailRow}>
                        <span className={styles.detailLabel}><i className="fas fa-user-check"></i> Reviewed By</span>
                        <span>{req.reviewed_by}</span>
                      </div>
                    )}
    {req.review_notes && (
                      <div className={styles.reviewNotes}>
                        <i className="fas fa-comment-alt"></i>
                        <span>{req.review_notes}</span>
                      </div>
                    )}

                    {/* Auto-prediction result for approved FIR */}
                    {req.action_type === 'fir_ocr_submission' && req.status === 'approved' && (() => {
                      const predKey = `${req.id}_pred`;
                      const ap = autoPredictions[predKey];
                      if (!ap) return null;
                      if (ap.loading) return (
                        <div style={{ marginTop: 10, padding: '10px 14px', borderRadius: 8, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', fontSize: '0.8rem', color: '#a5b4fc', display: 'flex', alignItems: 'center', gap: 8 }}>
                          <i className="fas fa-spinner fa-spin"></i> Running ML risk prediction…
                        </div>
                      );
                      if (!ap.result) return null;
                      const r = ap.result;
                      const level = normalizeRiskLevel(r.risk_level);
                      const rc = riskColor(level);
                      return (
                        <div style={{ marginTop: 10, padding: '12px 16px', borderRadius: 10, background: rc + '0d', border: `1px solid ${rc}30` }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                            <span style={{ fontSize: '0.73rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              <i className="fas fa-brain" style={{ marginRight: 5 }}></i>AI Risk Prediction
                            </span>
                            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>{ap.area} · {ap.crimeType}</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '1.3rem', fontWeight: 800, color: rc }}>{r.risk_percentage}%</span>
                            <span style={{ padding: '3px 10px', borderRadius: 14, background: rc + '20', color: rc, fontSize: '0.76rem', fontWeight: 700, border: `1px solid ${rc}40` }}>
                              <i className={`fas ${riskIcon(level)}`} style={{ marginRight: 5 }}></i>{actionLabel(level)}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Confidence: {Math.round((r.confidence || 0) * 100)}%</span>
                            {r.area_trend && <span style={{ fontSize: '0.75rem', color: r.area_trend.direction === 'decreasing' ? '#22c55e' : '#f97316' }}>
                              {r.area_trend.direction === 'decreasing' ? '↓' : '↑'} 6-month trend {r.area_trend.change_pct > 0 ? '+' : ''}{r.area_trend.change_pct}%
                            </span>}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Admin empty state when no requests */}
      {!isSuperAdmin && myRequests.length === 0 && !loading && !showSubmitForm && (
        <div className={styles.emptyState}>
          <i className="fas fa-inbox"></i>
          <h4>No Requests Yet</h4>
          <p>Submit a new approval request using the <strong>+</strong> button above, or sensitive actions will automatically create requests.</p>
          <button className={styles.submitFormBtn} style={{ marginTop: '12px', fontSize: '0.82rem', padding: '8px 20px' }}
            onClick={() => setShowSubmitForm(true)}>
            <i className="fas fa-plus"></i> Submit New Request
          </button>
        </div>
      )}
    </div>

      {/* Lightbox */}
      {lightboxImage && (
        <div
          className={styles.lightboxOverlay}
          onClick={() => setLightboxImage(null)}
        >
          <div
            className={styles.lightboxContent}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className={styles.lightboxClose}
              onClick={() => setLightboxImage(null)}
            >
              <i className="fas fa-times"></i>
            </button>
            <img src={lightboxImage} alt="FIR Document Full View" />
          </div>
        </div>
      )}
    </>
  );
};

export default PendingApprovalsPanel;
