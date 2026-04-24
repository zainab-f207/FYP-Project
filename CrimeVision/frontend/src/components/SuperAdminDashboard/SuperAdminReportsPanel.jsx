import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import apiService from '../../services/apiService_updated';
import styles from './SuperAdminReportsPanel.module.css';

const PAGE_SIZE = 50;
const RISK_COLORS = { High: '#dc2626', Medium: '#f9a826', Low: '#1dd1a1' };
const STATUS_CFG  = {
  verified: { color: '#1dd1a1', icon: 'fa-circle-check' },
  pending:  { color: '#f9a826', icon: 'fa-clock' },
  rejected: { color: '#dc2626', icon: 'fa-circle-xmark' },
};

const SuperAdminReportsPanel = ({ token }) => {
  const [crimes,        setCrimes]        = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [dateRange,     setDateRange]     = useState({ start: '', end: '' });
  const [areaFilter,    setAreaFilter]    = useState('all');
  const [typeFilter,    setTypeFilter]    = useState('all');
  const [riskFilter,    setRiskFilter]    = useState('all');
  const [statusFilter,  setStatusFilter]  = useState('all');
  const [currentPage,   setCurrentPage]   = useState(1);
  const [masterAreas,   setMasterAreas]   = useState([]);
  const [masterTypes,   setMasterTypes]   = useState([]);
  const [exporting,     setExporting]     = useState(null);
  const [approvalStats, setApprovalStats] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [sortCol,       setSortCol]       = useState('date');
  const [sortAsc,       setSortAsc]       = useState(false);
  const [search,        setSearch]        = useState('');
  const initialLoadDone = useRef(false);

  useEffect(() => {
    if (!token || initialLoadDone.current) return;
    const fetchMasterLists = async () => {
      try {
        const data = await apiService.getCrimes({ limit: 5000 });
        const allCrimes = Array.isArray(data) ? data : (data?.crimes || []);
        setMasterAreas([...new Set(allCrimes.map(c => c.area).filter(Boolean))].sort());
        setMasterTypes([...new Set(allCrimes.map(c => c.type || c.crime_type).filter(Boolean))].sort());
        initialLoadDone.current = true;
      } catch (err) { console.error('Failed to fetch master lists:', err); }
    };
    fetchMasterLists();
  }, [token]);

  useEffect(() => {
    if (!token) return;
    const fetchApprovalStats = async () => {
      try {
        const pending = await apiService.getPendingApprovals(token, 100);
        const pArr = Array.isArray(pending) ? pending : (pending?.requests || []);
        setApprovalStats({
          pending: pArr.filter(r => r.status === 'pending').length,
          approved: pArr.filter(r => r.status === 'approved').length,
          rejected: pArr.filter(r => r.status === 'rejected').length,
        });
      } catch (err) { console.error('Failed to fetch approval stats:', err); }
    };
    fetchApprovalStats();
  }, [token]);

  const fetchCrimes = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = { limit: 1000 };
      if (dateRange.start) params.start_date = dateRange.start;
      if (dateRange.end) params.end_date = dateRange.end;
      if (areaFilter !== 'all') params.area = areaFilter;
      if (typeFilter !== 'all') params.crime_type = typeFilter;
      const data = await apiService.getCrimes(params);
      setCrimes(Array.isArray(data) ? data : (data?.crimes || []));
      setCurrentPage(1);
    } catch (err) { console.error('Failed to fetch crimes:', err); }
    finally { setLoading(false); }
  }, [token, dateRange, areaFilter, typeFilter]);

  useEffect(() => { fetchCrimes(); }, [fetchCrimes]);

  // ── Analytics ──────────────────────────────────────────────────────────────
  const byArea   = useMemo(() => { const m = {}; crimes.forEach(c => { const a = c.area || 'Unknown'; m[a] = (m[a] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1]); }, [crimes]);
  const byType   = useMemo(() => { const m = {}; crimes.forEach(c => { const t = c.type || c.crime_type || 'Unknown'; m[t] = (m[t] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1]); }, [crimes]);
  const byRisk   = useMemo(() => { const m = { High: 0, Medium: 0, Low: 0 }; crimes.forEach(c => { const r = c.risk_level || 'Low'; m[r] = (m[r] || 0) + 1; }); return m; }, [crimes]);
  const byStatus = useMemo(() => { const m = { verified: 0, pending: 0, rejected: 0 }; crimes.forEach(c => { const s = c.status || 'pending'; if (m[s] !== undefined) m[s]++; }); return m; }, [crimes]);
  const byMonth  = useMemo(() => { const m = {}; crimes.forEach(c => { const d = c.date || c.crime_date; if (!d) return; const mo = d.substring(0, 7); m[mo] = (m[mo] || 0) + 1; }); return Object.entries(m).sort((a, b) => a[0].localeCompare(b[0])).slice(-12); }, [crimes]);
  const byHour   = useMemo(() => { const h = Array(24).fill(0); crimes.forEach(c => { const dt = (c.date || c.crime_date || ''); const t = dt.split(' ')[1] || dt.split('T')[1] || ''; const hr = parseInt((t.split(':')[0] || '-1'), 10); if (hr >= 0 && hr < 24) h[hr]++; }); return h; }, [crimes]);
  const verificationRate = crimes.length > 0 ? Math.round((byStatus.verified / crimes.length) * 100) : 0;

  // ── Client-side filter + sort + search ─────────────────────────────────────
  const filteredCrimes = useMemo(() => {
    let res = crimes;
    if (riskFilter !== 'all')   res = res.filter(c => c.risk_level === riskFilter);
    if (statusFilter !== 'all') res = res.filter(c => (c.status || 'pending') === statusFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      res = res.filter(c =>
        (c.area || '').toLowerCase().includes(q) ||
        (c.area_translit || '').toLowerCase().includes(q) ||
        (c.type || c.crime_type || '').toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q) ||
        (c.verified_by || '').toLowerCase().includes(q) ||
        String(c.id ?? '').includes(q)
      );
    }
    const dir = sortAsc ? 1 : -1;
    return [...res].sort((a, b) => {
      if (sortCol === 'date') return dir * ((a.date || a.crime_date || '') < (b.date || b.crime_date || '') ? -1 : 1);
      if (sortCol === 'risk') { const ord = { High: 3, Medium: 2, Low: 1 }; return dir * ((ord[a.risk_level] || 0) - (ord[b.risk_level] || 0)); }
      if (sortCol === 'area') return dir * (a.area || '').localeCompare(b.area || '');
      if (sortCol === 'type') return dir * ((a.type || a.crime_type || '') < (b.type || b.crime_type || '') ? -1 : 1);
      return 0;
    });
  }, [crimes, riskFilter, statusFilter, search, sortCol, sortAsc]);

  const totalPages      = Math.ceil(filteredCrimes.length / PAGE_SIZE);
  const paginatedCrimes = useMemo(() => { const s = (currentPage - 1) * PAGE_SIZE; return filteredCrimes.slice(s, s + PAGE_SIZE); }, [filteredCrimes, currentPage]);
  const handleSort      = col => { if (sortCol === col) setSortAsc(a => !a); else { setSortCol(col); setSortAsc(true); } setCurrentPage(1); };
  const sortIcon        = col => sortCol === col ? (sortAsc ? ' ↑' : ' ↓') : '';

  // ── Chart data ──────────────────────────────────────────────────────────────
  const colors       = ['#1a3a5f','#2d7fb8','#00a6a6','#f9a826','#1dd1a1','#0b7285','#f97316','#dc2626','#64748b','#94a3b8'];
  const chartOpts    = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
  const areaChartData  = { labels: byArea.slice(0, 10).map(([a]) => a), datasets: [{ label: 'Crimes', data: byArea.slice(0, 10).map(([, c]) => c), backgroundColor: colors, borderRadius: 6 }] };
  const typeChartData  = { labels: byType.slice(0, 8).map(([t]) => t),  datasets: [{ data: byType.slice(0, 8).map(([, c]) => c),  backgroundColor: colors, borderWidth: 0 }] };
  const riskChartData  = { labels: ['High','Medium','Low'], datasets: [{ data: [byRisk.High, byRisk.Medium, byRisk.Low], backgroundColor: ['#dc2626','#f9a826','#1dd1a1'], borderWidth: 0 }] };
  const trendChartData = { labels: byMonth.map(([m]) => m), datasets: [{ label: 'Crimes', data: byMonth.map(([, c]) => c), borderColor: '#2d7fb8', backgroundColor: 'rgba(45,127,184,0.10)', fill: true, tension: 0.4, pointRadius: 3 }] };
  const hourLabels     = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
  const hourChartData  = { labels: hourLabels, datasets: [{ label: 'Incidents', data: byHour, backgroundColor: 'rgba(45,127,184,0.65)', borderRadius: 4 }] };

  // ── Enriched CSV export ─────────────────────────────────────────────────────
  const exportCSV = () => {
    const meta = [
      '# SafeVision — SuperAdmin Enriched Crime Report',
      `# Generated: ${new Date().toLocaleString()}`,
      `# Filters: Area=${areaFilter} | Type=${typeFilter} | Risk=${riskFilter} | Status=${statusFilter} | From=${dateRange.start || 'all'} | To=${dateRange.end || 'all'}`,
      `# Total: ${crimes.length} | Verified: ${byStatus.verified} | Pending: ${byStatus.pending} | Verification Rate: ${verificationRate}%`,
      '',
    ];
    const headers = ['FIR ID','Area (English)','Area (Urdu)','Crime Type','Date','Time','Risk Level','Status','Verified By','Latitude','Longitude','Description'];
    const rows = crimes.map(c => {
      const dt   = c.date || c.crime_date || '';
      const date = dt.substring(0, 10);
      const time = dt.length > 10 ? dt.substring(11, 19) : '';
      const desc = (c.description || '').replace(/"/g, '""');
      return [c.id ?? '', `"${c.area ?? ''}"`, `"${c.area_translit ?? ''}"`, `"${c.type || c.crime_type || ''}"`, date, time, c.risk_level ?? '', c.status ?? 'pending', `"${c.verified_by ?? ''}"`, c.coordinates?.[0] ?? c.latitude ?? '', c.coordinates?.[1] ?? c.longitude ?? '', `"${desc}"`].join(',');
    });
    const blob = new Blob(['\uFEFF' + [...meta, headers.join(','), ...rows].join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a'); a.href = url; a.download = `SafeVision_superadmin_${new Date().toISOString().split('T')[0]}.csv`; a.click(); URL.revokeObjectURL(url);
  };

  const exportReport = async (format) => {
    setExporting(format);
    try { await apiService.exportFilteredReport(token, { format, start_date: dateRange.start || undefined, end_date: dateRange.end || undefined, area: areaFilter, crime_type: typeFilter }); }
    catch (err) { console.error(`Failed to export ${format}:`, err); }
    finally { setExporting(null); }
  };

  const SUMMARY_CARDS = [
    { icon: 'fa-database',            color: '#1a3a5f', val: crimes.length.toLocaleString(),        label: 'Total Crimes',       accent: true },
    { icon: 'fa-triangle-exclamation',color: '#dc2626', val: byRisk.High.toLocaleString(),           label: 'High Risk' },
    { icon: 'fa-circle-exclamation',  color: '#f9a826', val: byRisk.Medium.toLocaleString(),         label: 'Medium Risk' },
    { icon: 'fa-circle-check',        color: '#1dd1a1', val: byRisk.Low.toLocaleString(),            label: 'Low Risk' },
    { icon: 'fa-map-location-dot',    color: '#2d7fb8', val: masterAreas.length,                     label: 'Areas Covered' },
    { icon: 'fa-tags',                color: '#00a6a6', val: masterTypes.length,                     label: 'Crime Types' },
    { icon: 'fa-circle-check',        color: '#1dd1a1', val: byStatus.verified.toLocaleString(),     label: 'Verified FIRs' },
    { icon: 'fa-clock',               color: '#f9a826', val: byStatus.pending.toLocaleString(),      label: 'Pending Review',     pending: true },
    { icon: 'fa-circle-xmark',        color: '#dc2626', val: byStatus.rejected.toLocaleString(),     label: 'Rejected FIRs' },
    { icon: 'fa-percent',             color: '#2d7fb8', val: `${verificationRate}%`,                 label: 'Verification Rate' },
    { icon: 'fa-hourglass-half',      color: '#f9a826', val: approvalStats.pending,                  label: 'Pending Approvals',  pending: true },
    { icon: 'fa-user-check',          color: '#1dd1a1', val: approvalStats.approved,                 label: 'Approved Requests' },
  ];

  return (
    <div className={styles.reportsPanel}>
      {/* ── Header ── */}
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><i className="fas fa-chart-pie"></i></div>
          <div><h3>System Reports & Intelligence</h3><p className={styles.headerSub}>{crimes.length.toLocaleString()} records · {filteredCrimes.length.toLocaleString()} matching · SuperAdmin View</p></div>
        </div>
        <div className={styles.headerActions}>
          <button className={`${styles.exportBtn} ${styles.exportPdf}`} onClick={() => exportReport('pdf')} disabled={!!exporting}>{exporting === 'pdf' ? <i className={`fas fa-spinner ${styles.spin}`}></i> : <i className="fas fa-file-pdf"></i>} PDF</button>
          <button className={`${styles.exportBtn} ${styles.exportExcel}`} onClick={() => exportReport('excel')} disabled={!!exporting}>{exporting === 'excel' ? <i className={`fas fa-spinner ${styles.spin}`}></i> : <i className="fas fa-file-excel"></i>} Excel</button>
          <button className={styles.exportBtn} onClick={exportCSV}><i className="fas fa-download"></i> CSV (Enriched)</button>
          <button className={styles.refreshBtn} onClick={fetchCrimes} disabled={loading}><i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i></button>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className={styles.filtersRow}>
        <div className={styles.filterGroup}><label>From</label><input type="date" value={dateRange.start} onChange={e => setDateRange(p => ({ ...p, start: e.target.value }))} className={styles.dateInput} /></div>
        <div className={styles.filterGroup}><label>To</label><input type="date" value={dateRange.end} onChange={e => setDateRange(p => ({ ...p, end: e.target.value }))} className={styles.dateInput} /></div>
        <div className={styles.filterGroup}><label>Area</label><select value={areaFilter} onChange={e => { setAreaFilter(e.target.value); setCurrentPage(1); }} className={styles.filterSelect}><option value="all">All Areas</option>{masterAreas.map(a => <option key={a} value={a}>{a}</option>)}</select></div>
        <div className={styles.filterGroup}><label>Type</label><select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setCurrentPage(1); }} className={styles.filterSelect}><option value="all">All Types</option>{masterTypes.map(t => <option key={t} value={t}>{t}</option>)}</select></div>
        <div className={styles.filterGroup}><label>Risk</label><select value={riskFilter} onChange={e => { setRiskFilter(e.target.value); setCurrentPage(1); }} className={styles.filterSelect}><option value="all">All Risks</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select></div>
        <div className={styles.filterGroup}><label>Status</label><select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }} className={styles.filterSelect}><option value="all">All Statuses</option><option value="verified">Verified</option><option value="pending">Pending</option><option value="rejected">Rejected</option></select></div>
      </div>

      {loading ? (
        <div className={styles.loadingState}><div className={styles.spinner}></div><p>Loading system reports…</p></div>
      ) : (<>
        {/* ── Summary Cards (12) ── */}
        <div className={styles.summaryCards}>
          {SUMMARY_CARDS.map((card, i) => (
            <div key={i} className={`${styles.summaryCard} ${card.accent ? styles.cardAccent : ''} ${card.pending ? styles.cardPending : ''}`}>
              <div className={styles.summaryIcon}><i className={`fas ${card.icon}`} style={{ color: card.color }}></i></div>
              <div className={styles.summaryValue} style={{ color: card.accent ? undefined : card.color }}>{card.val}</div>
              <div className={styles.summaryLabel}>{card.label}</div>
            </div>
          ))}
        </div>

        {/* ── Charts (2×2 + 1 full-width hourly) ── */}
        <div className={styles.chartsGrid}>
          <div className={styles.chartCard}><h4><i className="fas fa-chart-line"></i> Monthly Crime Trend</h4><div className={styles.chartBody}><Line data={trendChartData} options={chartOpts} /></div></div>
          <div className={styles.chartCard}><h4><i className="fas fa-chart-bar"></i> By Area (Top 10)</h4><div className={styles.chartBody}><Bar data={areaChartData} options={chartOpts} /></div></div>
          <div className={styles.chartCard}><h4><i className="fas fa-chart-pie"></i> Crime Type Distribution</h4><div className={styles.chartBody}><Doughnut data={typeChartData} options={{ ...chartOpts, plugins: { legend: { display: true, position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } } }} /></div></div>
          <div className={styles.chartCard}><h4><i className="fas fa-shield-alt"></i> Risk Level Distribution</h4><div className={styles.chartBody}><Doughnut data={riskChartData} options={{ ...chartOpts, plugins: { legend: { display: true, position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } } }} /></div></div>
          <div className={styles.chartCard} style={{ gridColumn: 'span 2' }}><h4><i className="fas fa-clock"></i> Hourly Crime Pattern (24h)</h4><div className={styles.chartBody}><Bar data={hourChartData} options={{ ...chartOpts, scales: { x: { ticks: { font: { size: 10 } } } } }} /></div></div>
        </div>

        {/* ── Advanced Data Table ── */}
        <div className={styles.tableSection}>
          <div className={styles.tableSectionHeader}>
            <h4><i className="fas fa-table"></i> Crime Records ({filteredCrimes.length.toLocaleString()} / {crimes.length.toLocaleString()})</h4>
            <div className={styles.tableSearch}>
              <i className="fas fa-search" style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}></i>
              <input className={styles.searchInput} type="text" placeholder="Search area, type, description, FIR ID…" value={search} onChange={e => { setSearch(e.target.value); setCurrentPage(1); }} />
              {search && <button className={styles.clearSearch} onClick={() => { setSearch(''); setCurrentPage(1); }}><i className="fas fa-xmark" style={{ fontSize: '0.8rem' }}></i></button>}
            </div>
          </div>
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable}>
              <thead><tr>
                <th>#</th>
                <th className={styles.thSort} onClick={() => handleSort('id')}>FIR ID{sortIcon('id')}</th>
                <th className={styles.thSort} onClick={() => handleSort('area')}>Area (EN){sortIcon('area')}</th>
                <th>Area (UR)</th>
                <th className={styles.thSort} onClick={() => handleSort('type')}>Crime Type{sortIcon('type')}</th>
                <th className={styles.thSort} onClick={() => handleSort('date')}>Date{sortIcon('date')}</th>
                <th>Time</th>
                <th className={styles.thSort} onClick={() => handleSort('risk')}>Risk{sortIcon('risk')}</th>
                <th>Status</th>
                <th>Verified By</th>
                <th>Description</th>
              </tr></thead>
              <tbody>
                {paginatedCrimes.length === 0 ? (
                  <tr><td colSpan={11} className={styles.emptyRow}><i className="fas fa-inbox"></i> No records match the current filters.</td></tr>
                ) : paginatedCrimes.map((c, i) => {
                  const dt = c.date || c.crime_date || '';
                  const date = dt.substring(0, 10);
                  const time = dt.length > 10 ? dt.substring(11, 16) : '—';
                  const status = c.status || 'pending';
                  const sCfg = STATUS_CFG[status] || STATUS_CFG.pending;
                  return (
                    <tr key={c.id || i}>
                      <td className={styles.rankCell}>{(currentPage - 1) * PAGE_SIZE + i + 1}</td>
                      <td className={styles.idCell}>{c.id ?? '—'}</td>
                      <td>{c.area || '—'}</td>
                      <td style={{ fontFamily: 'serif', direction: 'rtl', fontSize: '0.82rem' }}>{c.area_translit || '—'}</td>
                      <td>{c.type || c.crime_type || '—'}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>{date || '—'}</td>
                      <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.8rem' }}>{time}</td>
                      <td><span className={styles.riskBadge} style={{ background: (RISK_COLORS[c.risk_level] || '#6b7280') + '20', color: RISK_COLORS[c.risk_level] || '#6b7280', border: `1px solid ${(RISK_COLORS[c.risk_level] || '#6b7280')}40` }}>{c.risk_level || '—'}</span></td>
                      <td><span className={styles.statusBadge} style={{ background: sCfg.color + '20', color: sCfg.color, border: `1px solid ${sCfg.color}40` }}><i className={`fas ${sCfg.icon}`}></i> {status}</span></td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{c.verified_by || '—'}</td>
                      <td className={styles.descCell} title={c.description || ''}>{c.description || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button className={styles.pageBtn} disabled={currentPage === 1} onClick={() => setCurrentPage(1)}><i className="fas fa-angle-double-left"></i></button>
              <button className={styles.pageBtn} disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}><i className="fas fa-angle-left"></i></button>
              <span className={styles.pageInfo}>Page {currentPage} of {totalPages} · {filteredCrimes.length.toLocaleString()} records</span>
              <button className={styles.pageBtn} disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}><i className="fas fa-angle-right"></i></button>
              <button className={styles.pageBtn} disabled={currentPage === totalPages} onClick={() => setCurrentPage(totalPages)}><i className="fas fa-angle-double-right"></i></button>
            </div>
          )}
        </div>
      </>)}
    </div>
  );
};

export default SuperAdminReportsPanel;

