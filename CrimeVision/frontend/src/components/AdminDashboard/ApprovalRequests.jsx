import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';
import apiService from '../../services/apiService_updated';
import styles from './ApprovalRequests.module.css';

const actionLabels = {
  delete_user: 'Delete User',
  bulk_delete: 'Bulk Delete Users',
  bulk_suspend: 'Bulk Suspend Users',
  change_role_to_admin: 'Promote to Admin',
  change_role_to_superadmin: 'Promote to Super Admin',
  fir_ocr_submission: 'FIR OCR Submission',
};

const statusConfig = {
  pending: { icon: 'fas fa-clock', color: '#f9a826', label: 'Pending' },
  approved: { icon: 'fas fa-check-circle', color: '#1dd1a1', label: 'Approved' },
  rejected: { icon: 'fas fa-times-circle', color: '#ff6b6b', label: 'Rejected' },
};

const ApprovalRequests = () => {
  const { token } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  const fetchRequests = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getMyApprovalRequests(token);
      setRequests(data.requests || []);
    } catch (err) {
      console.error('Failed to fetch approval requests:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const filteredRequests = filter === 'all'
    ? requests
    : requests.filter((r) => r.status === filter);

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <div className={styles.approvalPanel}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}>
            <i className="fas fa-clipboard-check"></i>
          </div>
          <div>
            <h3>My Approval Requests</h3>
            <p className={styles.headerSub}>
              Track status of your submitted requests for sensitive actions
            </p>
          </div>
        </div>
        <button className={styles.refreshBtn} onClick={fetchRequests} disabled={loading}>
          <i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className={styles.filterTabs}>
        {['all', 'pending', 'approved', 'rejected'].map((f) => {
          const count = f === 'all' ? requests.length : requests.filter((r) => r.status === f).length;
          return (
            <button
              key={f}
              className={`${styles.filterTab} ${filter === f ? styles.filterActive : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : statusConfig[f]?.label || f}
              <span className={styles.filterCount}>{count}</span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className={styles.requestsList}>
        {loading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner}></div>
            <p>Loading requests...</p>
          </div>
        ) : error ? (
          <div className={styles.errorState}>
            <i className="fas fa-exclamation-triangle"></i>
            <p>{error}</p>
            <button onClick={fetchRequests}>Retry</button>
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className={styles.emptyState}>
            <i className="fas fa-inbox"></i>
            <h4>No Requests Found</h4>
            <p>{filter === 'all' ? 'You haven\'t submitted any approval requests yet.' : `No ${filter} requests.`}</p>
          </div>
        ) : (
          filteredRequests.map((req) => {
            const status = statusConfig[req.status] || statusConfig.pending;
            return (
              <div key={req.id} className={`${styles.requestCard} ${styles[`status_${req.status}`]}`}>
                <div className={styles.requestTop}>
                  <div className={styles.actionBadge}>
                    <i className="fas fa-gavel"></i>
                    {actionLabels[req.action_type] || req.action_type}
                  </div>
                  <div className={styles.statusBadge} style={{ color: status.color, borderColor: status.color }}>
                    <i className={status.icon}></i> {status.label}
                  </div>
                </div>
                <div className={styles.requestBody}>
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}><i className="fas fa-crosshairs"></i> Target</span>
                    <span>{req.target_type} {req.target_id ? `#${req.target_id}` : ''}</span>
                  </div>
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}><i className="far fa-calendar-alt"></i> Submitted</span>
                    <span>{formatDate(req.requested_at || req.created_at)}</span>
                  </div>
                  {req.reviewed_by && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}><i className="fas fa-user-shield"></i> Reviewed By</span>
                      <span>{req.reviewed_by}</span>
                    </div>
                  )}
                  {req.reviewed_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}><i className="fas fa-calendar-check"></i> Reviewed At</span>
                      <span>{formatDate(req.reviewed_at)}</span>
                    </div>
                  )}
                  {req.review_notes && (
                    <div className={styles.reviewNotes}>
                      <i className="fas fa-comment-alt"></i>
                      <span>{req.review_notes}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default ApprovalRequests;

