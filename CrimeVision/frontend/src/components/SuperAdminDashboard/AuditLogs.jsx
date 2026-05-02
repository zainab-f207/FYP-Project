import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import styles from './AuditLogs.module.css';

const API_BASE_URL =
  window._apiBase ||
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000';

const formatTimestamp = (iso) => {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch {
    return iso;
  }
};

const actionTone = (action) => {
  const a = (action || '').toLowerCase();
  if (a.includes('reject') || a.includes('delete') || a.includes('remove')) return 'danger';
  if (a.includes('approve') || a.includes('login') || a.includes('create')) return 'ok';
  if (a.includes('update') || a.includes('edit') || a.includes('change')) return 'warn';
  return 'neutral';
};

const prettifyAction = (action) =>
  (action || '—').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const AuditLogs = ({ token }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [targetFilter, setTargetFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [limit, setLimit] = useState(100);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.append('action', actionFilter);
      if (targetFilter) params.append('target_type', targetFilter);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      params.append('limit', String(limit));
      const res = await fetch(`${API_BASE_URL}/admin/audit-logs?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(detail || `Failed to load audit logs (${res.status})`);
      }
      const data = await res.json();
      setLogs(Array.isArray(data?.audit_logs) ? data.audit_logs : []);
    } catch (e) {
      setError(e.message || 'Failed to load audit logs');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [token, actionFilter, targetFilter, startDate, endDate, limit]);

  useEffect(() => { load(); }, [load]);

  // Build option lists from current results so filters reflect what's there.
  const actionOptions = useMemo(() => {
    const set = new Set();
    logs.forEach((l) => l.action && set.add(l.action));
    return Array.from(set).sort();
  }, [logs]);
  const targetOptions = useMemo(() => {
    const set = new Set();
    logs.forEach((l) => l.target_type && set.add(l.target_type));
    return Array.from(set).sort();
  }, [logs]);

  // Client-side text search across admin, action, target, IP and details.
  const filteredLogs = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return logs;
    return logs.filter((l) => {
      const blob = [
        l.admin_username, l.action, l.target_type, l.target_id,
        l.ip_address, l.user_agent,
        l.details ? JSON.stringify(l.details) : '',
      ].join(' ').toLowerCase();
      return blob.includes(q);
    });
  }, [logs, search]);

  // Reset to page 1 whenever the active result set changes.
  useEffect(() => { setPage(1); }, [search, actionFilter, targetFilter, startDate, endDate, pageSize, logs.length]);

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageStart = (safePage - 1) * pageSize;
  const pageEnd = pageStart + pageSize;
  const pagedLogs = filteredLogs.slice(pageStart, pageEnd);

  // Build a small numeric pager around the current page (max ~5 buttons).
  const pageNumbers = useMemo(() => {
    const window = 2;
    const start = Math.max(1, safePage - window);
    const end = Math.min(totalPages, safePage + window);
    const arr = [];
    for (let i = start; i <= end; i++) arr.push(i);
    return arr;
  }, [safePage, totalPages]);

  const exportCSV = () => {
    const head = ['Timestamp', 'Admin', 'Action', 'Target Type', 'Target ID', 'IP', 'Details'];
    const rows = filteredLogs.map((l) => [
      l.created_at || '',
      l.admin_username || '',
      l.action || '',
      l.target_type || '',
      l.target_id ?? '',
      l.ip_address || '',
      l.details ? JSON.stringify(l.details).replace(/"/g, '""') : '',
    ]);
    const csv = [head, ...rows]
      .map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  const clearFilters = () => {
    setSearch(''); setActionFilter(''); setTargetFilter('');
    setStartDate(''); setEndDate(''); setLimit(100);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <span className={styles.eyebrow}><i className="fas fa-shield-alt"></i> AUDIT TRAIL</span>
          <h2 className={styles.title}>Admin Activity Logs</h2>
          <p className={styles.subtitle}>
            Every admin action is recorded with username, target, IP and timestamp. Filter, search, and export below.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.refreshBtn} onClick={load} disabled={loading}>
            <i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i> Refresh
          </button>
          <button className={styles.exportBtn} onClick={exportCSV} disabled={!filteredLogs.length}>
            <i className="fas fa-file-csv"></i> Export CSV
          </button>
        </div>
      </div>

      <div className={styles.filterBar}>
        <div className={styles.searchWrap}>
          <i className="fas fa-search"></i>
          <input
            type="text"
            placeholder="Search admin, action, target, IP, details…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className={styles.clearSearch} onClick={() => setSearch('')} title="Clear search">
              <i className="fas fa-times"></i>
            </button>
          )}
        </div>

        <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
          <option value="">All Actions</option>
          {actionOptions.map((a) => (
            <option key={a} value={a}>{prettifyAction(a)}</option>
          ))}
        </select>

        <select value={targetFilter} onChange={(e) => setTargetFilter(e.target.value)}>
          <option value="">All Targets</option>
          {targetOptions.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} title="Start date" />
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} title="End date" />

        <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} title="Max records">
          <option value={50}>50 rows</option>
          <option value={100}>100 rows</option>
          <option value={250}>250 rows</option>
          <option value={500}>500 rows</option>
          <option value={1000}>1000 rows</option>
        </select>

        <button className={styles.clearBtn} onClick={clearFilters} title="Reset all filters">
          <i className="fas fa-times-circle"></i> Clear
        </button>
      </div>

      <div className={styles.summaryRow}>
        <span>
          Showing <strong>{filteredLogs.length === 0 ? 0 : pageStart + 1}-{Math.min(pageEnd, filteredLogs.length)}</strong>
          {' '}of <strong>{filteredLogs.length}</strong>
        </span>
        <span>·</span>
        <span><strong>{logs.length}</strong> loaded</span>
        {error && <span className={styles.errorPill}><i className="fas fa-exclamation-circle"></i> {error}</span>}
      </div>

      <div className={styles.tableWrap}>
        {loading ? (
          <div className={styles.loadingState}>
            <i className={`fas fa-spinner ${styles.spin}`}></i>
            <span>Loading audit logs…</span>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className={styles.emptyState}>
            <i className="fas fa-folder-open"></i>
            <span>No audit log entries match the current filters.</span>
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Admin</th>
                <th>Action</th>
                <th>Target</th>
                <th>IP Address</th>
                <th>User Agent</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pagedLogs.map((l) => (
                <tr key={l.id} className={styles[`row_${actionTone(l.action)}`]}>
                  <td className={styles.tsCell}>{formatTimestamp(l.created_at)}</td>
                  <td>
                    <span className={styles.adminBadge}>
                      <i className="fas fa-user-shield"></i> {l.admin_username || '—'}
                    </span>
                  </td>
                  <td>
                    <span className={`${styles.actionBadge} ${styles[`action_${actionTone(l.action)}`]}`}>
                      {prettifyAction(l.action)}
                    </span>
                  </td>
                  <td>
                    {l.target_type ? (
                      <span className={styles.targetCell}>
                        {l.target_type}
                        {l.target_id != null && <small> #{l.target_id}</small>}
                      </span>
                    ) : '—'}
                  </td>
                  <td className={styles.ipCell}>{l.ip_address || '—'}</td>
                  <td className={styles.uaCell} title={l.user_agent || ''}>
                    {l.user_agent ? l.user_agent.slice(0, 38) + (l.user_agent.length > 38 ? '…' : '') : '—'}
                  </td>
                  <td>
                    <button className={styles.viewBtn} onClick={() => setSelected(l)}>
                      <i className="fas fa-eye"></i>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pager */}
      {filteredLogs.length > 0 && (
        <div className={styles.pager}>
          <div className={styles.pagerLeft}>
            <span>Rows per page:</span>
            <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className={styles.pagerRight}>
            <button
              className={styles.pagerBtn}
              disabled={safePage === 1}
              onClick={() => setPage(1)}
              title="First page"
            ><i className="fas fa-angle-double-left"></i></button>
            <button
              className={styles.pagerBtn}
              disabled={safePage === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              title="Previous"
            ><i className="fas fa-angle-left"></i></button>
            {pageNumbers.map((n) => (
              <button
                key={n}
                className={`${styles.pagerBtn} ${n === safePage ? styles.pagerBtnActive : ''}`}
                onClick={() => setPage(n)}
              >{n}</button>
            ))}
            <button
              className={styles.pagerBtn}
              disabled={safePage === totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              title="Next"
            ><i className="fas fa-angle-right"></i></button>
            <button
              className={styles.pagerBtn}
              disabled={safePage === totalPages}
              onClick={() => setPage(totalPages)}
              title="Last page"
            ><i className="fas fa-angle-double-right"></i></button>
            <span className={styles.pageInfo}>Page {safePage} of {totalPages}</span>
          </div>
        </div>
      )}

      {/* Detail modal — portalled to document.body so a parent transform
          (the dashboard runs a transition with translateY/scale) cannot
          turn this fixed overlay into a containing-block child that drifts
          off-screen. */}
      {selected && createPortal(
        <div className={styles.detailOverlay} onClick={() => setSelected(null)}>
          <div className={styles.detailCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.detailHead}>
              <div className={styles.detailHeadLeft}>
                <span className={`${styles.actionBadge} ${styles[`action_${actionTone(selected.action)}`]}`}>
                  {prettifyAction(selected.action)}
                </span>
                <h3>{selected.admin_username || 'Admin'}</h3>
                <small>{formatTimestamp(selected.created_at)}</small>
              </div>
              <button className={styles.closeBtn} onClick={() => setSelected(null)}>
                <i className="fas fa-times"></i>
              </button>
            </div>

            <div className={styles.detailKvList}>
              <div className={styles.kvRow}>
                <i className={`fas fa-bullseye ${styles.kvIcon}`}></i>
                <div className={styles.kvBody}>
                  <span className={styles.kvLabel}>Target</span>
                  <span className={styles.kvValue}>
                    {selected.target_type || '—'}
                    {selected.target_id != null && <em className={styles.kvSubtle}> #{selected.target_id}</em>}
                  </span>
                </div>
              </div>

              <div className={styles.kvRow}>
                <i className={`fas fa-network-wired ${styles.kvIcon}`}></i>
                <div className={styles.kvBody}>
                  <span className={styles.kvLabel}>IP Address</span>
                  <span className={`${styles.kvValue} ${styles.kvMono}`}>{selected.ip_address || '—'}</span>
                  {selected.ip_address === '127.0.0.1' && (
                    <span className={styles.kvNote}>Loopback — request originated on the same host as the server (local development).</span>
                  )}
                </div>
              </div>

              <div className={styles.kvRow}>
                <i className={`fas fa-laptop ${styles.kvIcon}`}></i>
                <div className={styles.kvBody}>
                  <span className={styles.kvLabel}>Device / Browser</span>
                  <span className={styles.kvValue}>{prettifyUserAgent(selected.user_agent)}</span>
                  {selected.user_agent && (
                    <span className={styles.kvSubtle} title={selected.user_agent}>
                      {selected.user_agent}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className={styles.detailExtra}>
              <div className={styles.detailExtraHead}>
                <i className="fas fa-list-ul"></i>
                <span>Details</span>
              </div>
              {selected.details && typeof selected.details === 'object' && Object.keys(selected.details).length ? (
                <div className={styles.detailKvGrid}>
                  {Object.entries(selected.details).map(([k, v]) => (
                    <div key={k} className={`${styles.detailKvCell} ${Array.isArray(v) ? styles.detailKvCellWide : ''}`}>
                      <span className={styles.detailKvKey}>{prettifyKey(k)}</span>
                      <DetailValue value={v} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.detailEmpty}>— no extra details recorded —</div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

// Pretty-print a User-Agent string into something readable.
function prettifyUserAgent(ua) {
  if (!ua) return '—';
  const s = ua;
  let browser = 'Unknown browser';
  let os = 'Unknown OS';
  if (/Edg\//i.test(s)) browser = 'Microsoft Edge';
  else if (/OPR\//i.test(s) || /Opera/i.test(s)) browser = 'Opera';
  else if (/Chrome\//i.test(s) && !/Edg\//i.test(s)) browser = 'Google Chrome';
  else if (/Firefox\//i.test(s)) browser = 'Firefox';
  else if (/Safari/i.test(s) && !/Chrome/i.test(s)) browser = 'Safari';
  if (/Windows NT 10/i.test(s)) os = 'Windows 10/11';
  else if (/Windows/i.test(s)) os = 'Windows';
  else if (/Mac OS X/i.test(s)) os = 'macOS';
  else if (/Android/i.test(s)) os = 'Android';
  else if (/iPhone|iPad|iOS/i.test(s)) os = 'iOS';
  else if (/Linux/i.test(s)) os = 'Linux';
  return `${browser} on ${os}`;
}

function prettifyKey(k) {
  return String(k)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDetailValue(v) {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

// Renders a single detail value with type-aware formatting.
// Arrays of strings (e.g. "changed_keys") become chip-style tags so they're
// scannable instead of a JSON blob. Nested objects become nested mini-cells.
function DetailValue({ value }) {
  if (value === null || value === undefined || value === '') {
    return <span className={styles.detailKvVal}>—</span>;
  }
  if (typeof value === 'boolean') {
    return (
      <span className={`${styles.detailKvVal} ${value ? styles.valYes : styles.valNo}`}>
        <i className={`fas ${value ? 'fa-check-circle' : 'fa-times-circle'}`}></i> {value ? 'Yes' : 'No'}
      </span>
    );
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className={styles.detailKvVal}>— empty list —</span>;
    }
    const allPrimitive = value.every((x) => x == null || ['string', 'number', 'boolean'].includes(typeof x));
    if (allPrimitive) {
      return (
        <div className={styles.chipRow}>
          {value.map((x, i) => (
            <span key={i} className={styles.chip}>{prettifyKey(x)}</span>
          ))}
        </div>
      );
    }
    // Array of objects — render as numbered nested cells
    return (
      <div className={styles.nestedList}>
        {value.map((item, i) => (
          <div key={i} className={styles.nestedItem}>
            <span className={styles.nestedIdx}>#{i + 1}</span>
            <DetailValue value={item} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === 'object') {
    return (
      <div className={styles.nestedKv}>
        {Object.entries(value).map(([k, v]) => (
          <div key={k} className={styles.nestedKvRow}>
            <span className={styles.nestedKvKey}>{prettifyKey(k)}:</span>
            <span className={styles.nestedKvVal}>{formatDetailValue(v)}</span>
          </div>
        ))}
      </div>
    );
  }
  return <span className={styles.detailKvVal}>{String(value)}</span>;
}

export default AuditLogs;
