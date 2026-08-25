import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import apiService from '../../services/apiService';
import styles from './ReportsPanel.module.css';

const PAGE_SIZE = 50;

const normalizeRiskLevel = (value) => {
  const v = String(value || '').toLowerCase();
  if (v.includes('critical') || v.includes('avoid')) return 'Critical';
  if (v.includes('high') || v.includes('warning')) return 'High';
  if (v.includes('moderate') || v.includes('medium') || v.includes('caution')) return 'Moderate';
  return 'Low';
};

const actionLabel = (level) => {
  if (level === 'Critical') return 'Avoid';
  if (level === 'High') return 'Warning';
  if (level === 'Moderate') return 'Caution';
  return 'Safe';
};

const riskColor = (level) => ({ Critical: '#7c3aed', High: '#ff6b6b', Moderate: '#f9a826', Low: '#1dd1a1' }[level] || '#1dd1a1');

const ReportsPanel = ({ token }) => {
  const [crimes, setCrimes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [areaFilter, setAreaFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [masterAreas, setMasterAreas] = useState([]);
  const [masterTypes, setMasterTypes] = useState([]);
  const [exporting, setExporting] = useState(null); // 'pdf' | 'excel' | null
  const initialLoadDone = useRef(false);

  // Fetch master dropdown lists once on mount (unfiltered)
  useEffect(() => {
    if (!token || initialLoadDone.current) return;
    const fetchMasterLists = async () => {
      try {
        const data = await apiService.getCrimes({ limit: 5000 });
        const allCrimes = Array.isArray(data) ? data : (data?.crimes || []);
        setMasterAreas([...new Set(allCrimes.map(c => c.area).filter(Boolean))].sort());
        setMasterTypes([...new Set(allCrimes.map(c => c.type || c.crime_type).filter(Boolean))].sort());
        initialLoadDone.current = true;
      } catch (err) {
        console.error('Failed to fetch master lists:', err);
      }
    };
    fetchMasterLists();
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
    } catch (err) {
      console.error('Failed to fetch crimes:', err);
    } finally {
      setLoading(false);
    }
  }, [token, dateRange, areaFilter, typeFilter]);

  useEffect(() => { fetchCrimes(); }, [fetchCrimes]);

  // Use master lists for dropdown options (never shrink when filters applied)
  const areas = masterAreas;
  const types = masterTypes;

  const byArea = useMemo(() => {
    const map = {};
    crimes.forEach(c => { const a = c.area || 'Unknown'; map[a] = (map[a] || 0) + 1; });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [crimes]);

  const byType = useMemo(() => {
    const map = {};
    crimes.forEach(c => { const t = c.type || c.crime_type || 'Unknown'; map[t] = (map[t] || 0) + 1; });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [crimes]);

  const byRisk = useMemo(() => {
    const map = { Critical: 0, High: 0, Moderate: 0, Low: 0 };
    crimes.forEach(c => {
      const r = normalizeRiskLevel(c.risk_level);
      map[r] = (map[r] || 0) + 1;
    });
    return map;
  }, [crimes]);

  const byMonth = useMemo(() => {
    const map = {};
    crimes.forEach(c => {
      const d = c.date || c.crime_date;
      if (!d) return;
      const month = d.substring(0, 7);
      map[month] = (map[month] || 0) + 1;
    });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0])).slice(-12);
  }, [crimes]);

  // Pagination
  const totalPages = Math.ceil(crimes.length / PAGE_SIZE);
  const paginatedCrimes = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return crimes.slice(start, start + PAGE_SIZE);
  }, [crimes, currentPage]);

  const chartColors = ['#2d7fb8', '#1dd1a1', '#f9a826', '#ff6b6b', '#a29bfe', '#fd79a8', '#00cec9', '#6c5ce7', '#e17055', '#00b894'];

  const areaChartData = {
    labels: byArea.slice(0, 10).map(([a]) => a),
    datasets: [{ label: 'Crimes', data: byArea.slice(0, 10).map(([, c]) => c), backgroundColor: chartColors, borderRadius: 6 }]
  };

  const typeChartData = {
    labels: byType.slice(0, 8).map(([t]) => t),
    datasets: [{ data: byType.slice(0, 8).map(([, c]) => c), backgroundColor: chartColors, borderWidth: 0 }]
  };

  const riskChartData = {
    labels: ['Avoid', 'Warning', 'Caution', 'Safe'],
    datasets: [{ data: [byRisk.Critical, byRisk.High, byRisk.Moderate, byRisk.Low], backgroundColor: ['#7c3aed', '#ff6b6b', '#f9a826', '#1dd1a1'], borderWidth: 0 }]
  };

  const trendChartData = {
    labels: byMonth.map(([m]) => m),
    datasets: [{ label: 'Crimes', data: byMonth.map(([, c]) => c), borderColor: '#2d7fb8', backgroundColor: 'rgba(45,127,184,0.1)', fill: true, tension: 0.4, pointRadius: 3 }]
  };

  const chartOpts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };

  const exportCSV = () => {
    const headers = ['ID', 'Area', 'Type', 'Date', 'Risk Level', 'Latitude', 'Longitude'];
    const rows = crimes.map(c => [c.id, c.area, c.type || c.crime_type, c.date || c.crime_date, actionLabel(normalizeRiskLevel(c.risk_level)), c.coordinates?.[0], c.coordinates?.[1]]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `crime_report_${new Date().toISOString().split('T')[0]}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportReport = async (format) => {
    setExporting(format);
    try {
      await apiService.exportFilteredReport(token, {
        format,
        start_date: dateRange.start || undefined,
        end_date: dateRange.end || undefined,
        area: areaFilter,
        crime_type: typeFilter,
      });
    } catch (err) {
      console.error(`Failed to export ${format}:`, err);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className={styles.reportsPanel}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><i className="fas fa-file-alt"></i></div>
          <div>
            <h3>Crime Reports & Analytics</h3>
            <p className={styles.headerSub}>{crimes.length} total records</p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button className={`${styles.exportBtn} ${styles.exportPdf}`} onClick={() => exportReport('pdf')} disabled={!!exporting}>
            {exporting === 'pdf' ? <i className={`fas fa-spinner ${styles.spin}`}></i> : <i className="fas fa-file-pdf"></i>} PDF
          </button>
          <button className={`${styles.exportBtn} ${styles.exportExcel}`} onClick={() => exportReport('excel')} disabled={!!exporting}>
            {exporting === 'excel' ? <i className={`fas fa-spinner ${styles.spin}`}></i> : <i className="fas fa-file-excel"></i>} Excel
          </button>
          <button className={styles.exportBtn} onClick={exportCSV}><i className="fas fa-download"></i> CSV</button>
          <button className={styles.refreshBtn} onClick={fetchCrimes} disabled={loading}>
            <i className={`fas fa-sync-alt ${loading ? styles.spin : ''}`}></i>
          </button>
        </div>
      </div>

      <div className={styles.filtersRow}>
        <div className={styles.filterGroup}>
          <label>From</label>
          <input type="date" value={dateRange.start} onChange={e => setDateRange(p => ({ ...p, start: e.target.value }))} className={styles.dateInput} />
        </div>
        <div className={styles.filterGroup}>
          <label>To</label>
          <input type="date" value={dateRange.end} onChange={e => setDateRange(p => ({ ...p, end: e.target.value }))} className={styles.dateInput} />
        </div>
        <div className={styles.filterGroup}>
          <label>Area</label>
          <select value={areaFilter} onChange={e => setAreaFilter(e.target.value)} className={styles.filterSelect}>
            <option value="all">All Areas</option>
            {areas.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div className={styles.filterGroup}>
          <label>Type</label>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className={styles.filterSelect}>
            <option value="all">All Types</option>
            {types.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className={styles.loadingState}><div className={styles.spinner}></div><p>Loading reports...</p></div>
      ) : (
        <>
          <div className={styles.summaryCards}>
            <div className={styles.summaryCard}><div className={styles.summaryValue}>{crimes.length}</div><div className={styles.summaryLabel}>Total Crimes</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue} style={{color:'#7c3aed'}}>{byRisk.Critical}</div><div className={styles.summaryLabel}>Avoid</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue} style={{color:'#ff6b6b'}}>{byRisk.High}</div><div className={styles.summaryLabel}>Warning</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue} style={{color:'#f9a826'}}>{byRisk.Moderate}</div><div className={styles.summaryLabel}>Caution</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue} style={{color:'#1dd1a1'}}>{byRisk.Low}</div><div className={styles.summaryLabel}>Safe</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue}>{areas.length}</div><div className={styles.summaryLabel}>Areas</div></div>
            <div className={styles.summaryCard}><div className={styles.summaryValue}>{types.length}</div><div className={styles.summaryLabel}>Crime Types</div></div>
          </div>
          <div className={styles.chartsGrid}>
            <div className={styles.chartCard}><h4><i className="fas fa-chart-line"></i> Monthly Trend</h4><div className={styles.chartBody}><Line data={trendChartData} options={chartOpts}/></div></div>
            <div className={styles.chartCard}><h4><i className="fas fa-chart-bar"></i> By Area (Top 10)</h4><div className={styles.chartBody}><Bar data={areaChartData} options={chartOpts}/></div></div>
            <div className={styles.chartCard}><h4><i className="fas fa-chart-pie"></i> By Type</h4><div className={styles.chartBody}><Doughnut data={typeChartData} options={{...chartOpts, plugins:{legend:{display:true,position:'right',labels:{boxWidth:12,font:{size:11}}}}}}/></div></div>
            <div className={styles.chartCard}><h4><i className="fas fa-shield-alt"></i> Risk Distribution</h4><div className={styles.chartBody}><Doughnut data={riskChartData} options={{...chartOpts, plugins:{legend:{display:true,position:'right',labels:{boxWidth:12,font:{size:11}}}}}}/></div></div>
          </div>
          <div className={styles.tableSection}>
            <h4><i className="fas fa-table"></i> Crime Records ({crimes.length})</h4>
            <div className={styles.tableWrapper}>
              <table className={styles.dataTable}>
                <thead><tr><th>#</th><th>Area</th><th>Type</th><th>Date</th><th>Risk</th></tr></thead>
                <tbody>
                  {paginatedCrimes.map((c, i) => (
                    <tr key={c.id || i}>
                      <td>{(currentPage - 1) * PAGE_SIZE + i + 1}</td><td>{c.area}</td><td>{c.type || c.crime_type}</td><td>{(c.date || c.crime_date || '').substring(0, 10)}</td>
                      <td>
                        {(() => {
                          const level = normalizeRiskLevel(c.risk_level);
                          const color = riskColor(level);
                          return (
                            <span className={styles.riskBadge} style={{ background: `${color}20`, color, border: `1px solid ${color}45` }}>
                              {actionLabel(level)}
                            </span>
                          );
                        })()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className={styles.pagination}>
                <button className={styles.pageBtn} disabled={currentPage === 1} onClick={() => setCurrentPage(1)}>
                  <i className="fas fa-angle-double-left"></i>
                </button>
                <button className={styles.pageBtn} disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}>
                  <i className="fas fa-angle-left"></i>
                </button>
                <span className={styles.pageInfo}>
                  Page {currentPage} of {totalPages} &nbsp;·&nbsp; {crimes.length} records
                </span>
                <button className={styles.pageBtn} disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}>
                  <i className="fas fa-angle-right"></i>
                </button>
                <button className={styles.pageBtn} disabled={currentPage === totalPages} onClick={() => setCurrentPage(totalPages)}>
                  <i className="fas fa-angle-double-right"></i>
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ReportsPanel;

