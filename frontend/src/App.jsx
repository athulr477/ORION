import { useState, useEffect, useCallback } from 'react';
import StatsBar from './components/StatsBar';
import MatrixTable from './components/MatrixTable';
import SensitivitySlider from './components/SensitivitySlider';
import HeatmapModal from './components/HeatmapModal';
import SimulateModal from './components/SimulateModal';
import { fetchMatrix, fetchStats, reclassifyMatrix } from './api/client';

/**
 * Sidebar — navigation panel with logo and nav items.
 */
function Sidebar() {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-logo" id="sidebar-logo">
        <div className="sidebar-logo-icon">O</div>
        <div>
          <div className="sidebar-logo-text">Orion</div>
          <div className="sidebar-logo-version">v0.1.0</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Analytics</div>
        <div className="sidebar-nav-item active" id="nav-dashboard">
          <span className="sidebar-nav-icon">📊</span>
          RTM Dashboard
        </div>
        <div className="sidebar-nav-item" id="nav-requirements">
          <span className="sidebar-nav-icon">📋</span>
          Requirements
        </div>
        <div className="sidebar-nav-item" id="nav-tests">
          <span className="sidebar-nav-icon">🧪</span>
          Test Cases
        </div>
        <div className="sidebar-section-label">Tools</div>
        <div className="sidebar-nav-item" id="nav-webhooks">
          <span className="sidebar-nav-icon">🔗</span>
          Webhooks
        </div>
        <div className="sidebar-nav-item" id="nav-settings">
          <span className="sidebar-nav-icon">⚙️</span>
          Settings
        </div>
      </nav>
      <div className="sidebar-footer">
        AI-powered Requirements Traceability
      </div>
    </aside>
  );
}

/**
 * App — main dashboard layout wiring all Phase 8 components together.
 */
export default function App() {
  // --- State ---
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [sort, setSort] = useState('risk_score');
  const [order, setOrder] = useState('desc');
  const [statusFilter, setStatusFilter] = useState(null);
  const [search, setSearch] = useState('');
  const [matrixLoading, setMatrixLoading] = useState(true);

  const [reclassifiedMap, setReclassifiedMap] = useState({});

  const [heatmapEntryId, setHeatmapEntryId] = useState(null);
  const [simulateOpen, setSimulateOpen] = useState(false);

  // --- Data fetching ---
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadMatrix = useCallback(async () => {
    setMatrixLoading(true);
    try {
      const data = await fetchMatrix({
        page,
        pageSize,
        status: statusFilter,
        sort,
        order,
        search: search || undefined,
      });
      setRows(data.rows);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load matrix:', err);
      setRows([]);
      setTotal(0);
    } finally {
      setMatrixLoading(false);
    }
  }, [page, pageSize, statusFilter, sort, order, search]);

  // Initial load
  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadMatrix();
  }, [loadMatrix]);

  // --- Event handlers ---
  const handleSort = useCallback(
    (col) => {
      if (sort === col) {
        setOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
      } else {
        setSort(col);
        setOrder('desc');
      }
      setPage(1);
    },
    [sort]
  );

  const handleFilter = useCallback((status) => {
    setStatusFilter(status);
    setPage(1);
  }, []);

  const handleSearch = useCallback((term) => {
    setSearch(term);
    setPage(1);
  }, []);

  const handlePageChange = useCallback((newPage) => {
    setPage(newPage);
  }, []);

  const handleRowClick = useCallback((row) => {
    setHeatmapEntryId(row.id);
  }, []);

  const handleReclassify = useCallback(async (coveredThreshold, driftedThreshold) => {
    try {
      const result = await reclassifyMatrix(coveredThreshold, driftedThreshold);
      const map = {};
      for (const row of result.rows) {
        if (row.changed) {
          map[row.id] = row.new_status;
        }
      }
      setReclassifiedMap(map);
      return result;
    } catch (err) {
      console.error('Reclassify failed:', err);
      setReclassifiedMap({});
      return null;
    }
  }, []);

  const handleSimulateComplete = useCallback(() => {
    // Refresh data after simulation
    loadStats();
    loadMatrix();
  }, [loadStats, loadMatrix]);

  return (
    <div className="app-layout">
      <Sidebar />

      <main className="app-main">
        {/* Page header */}
        <div className="page-header" id="page-header">
          <h1>Traceability Matrix</h1>
          <div className="page-header__actions">
            <button
              className="simulate-trigger"
              onClick={() => setSimulateOpen(true)}
              id="simulate-trigger-btn"
            >
              ⚡ Simulate Webhook
            </button>
          </div>
        </div>

        {/* Stats cards */}
        <StatsBar stats={stats} loading={statsLoading} />

        {/* Sensitivity slider */}
        <SensitivitySlider
          coveredDefault={0.75}
          driftedDefault={0.4}
          onReclassify={handleReclassify}
          loading={matrixLoading}
        />

        {/* RTM table */}
        <MatrixTable
          rows={rows}
          total={total}
          page={page}
          pageSize={pageSize}
          sort={sort}
          order={order}
          statusFilter={statusFilter}
          search={search}
          reclassifiedMap={reclassifiedMap}
          loading={matrixLoading}
          onSort={handleSort}
          onFilter={handleFilter}
          onSearch={handleSearch}
          onPageChange={handlePageChange}
          onRowClick={handleRowClick}
        />

        {/* Heatmap modal */}
        <HeatmapModal
          entryId={heatmapEntryId}
          onClose={() => setHeatmapEntryId(null)}
        />

        {/* Simulate modal */}
        <SimulateModal
          open={simulateOpen}
          onClose={() => setSimulateOpen(false)}
          onComplete={handleSimulateComplete}
        />
      </main>
    </div>
  );
}
