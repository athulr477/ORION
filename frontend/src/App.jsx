import { useState, useEffect, useCallback } from 'react';
import StatsBar from './components/StatsBar';
import MatrixTable from './components/MatrixTable';
import SensitivitySlider from './components/SensitivitySlider';
import HeatmapModal from './components/HeatmapModal';
import SimulateModal from './components/SimulateModal';
import LoginModal from './components/LoginModal';
import UserNav from './components/UserNav';
import { fetchMatrix, fetchStats, reclassifyMatrix } from './api/client';

/**
 * Sidebar — navigation panel with logo, active RTM Dashboard view, and system telemetry.
 */
function Sidebar() {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-logo" id="sidebar-logo">
        <div className="sidebar-logo-icon">O</div>
        <div>
          <div className="sidebar-logo-text">Orion</div>
          <div className="sidebar-logo-version">v0.1.0 • Enterprise</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Traceability View</div>
        <div className="sidebar-nav-item active" id="nav-dashboard">
          <span className="sidebar-nav-icon">📊</span>
          RTM Dashboard
        </div>

        {/* System Architecture Specifications Card */}
        <div
          style={{
            marginTop: 'auto',
            padding: '12px 14px',
            backgroundColor: 'var(--bg-tertiary, #161b22)',
            borderRadius: 'var(--radius-md, 10px)',
            border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.6))',
            fontSize: '11px',
            color: 'var(--text-secondary, #8b949e)',
          }}
        >
          <div
            style={{
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 700,
              fontSize: '10px',
              color: 'var(--text-tertiary, #6e7681)',
              marginBottom: '8px',
            }}
          >
            Engine Architecture
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Weights</span>
              <span style={{ color: 'var(--accent-blue, #58a6ff)', fontFamily: 'var(--font-mono)' }}>
                0.6S + 0.4A
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Extractor</span>
              <span style={{ color: 'var(--text-primary, #e6edf3)' }}>Python AST</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Embedding</span>
              <span style={{ color: 'var(--accent-violet, #bc8cff)' }}>BGE-Small ONNX</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Enterprise System Status Indicator */}
      <div className="sidebar-footer" id="sidebar-system-status" style={{ padding: '16px' }}>
        <div
          style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--text-tertiary, #6e7681)',
            marginBottom: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>System Status</span>
          <span
            style={{
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(63, 185, 80, 0.15)',
              color: 'var(--status-covered, #3fb950)',
              fontSize: '10px',
              fontWeight: 700,
            }}
          >
            HEALTHY
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-covered, #3fb950)',
                boxShadow: '0 0 6px rgba(63, 185, 80, 0.6)',
                flexShrink: 0,
              }}
            />
            <span style={{ color: 'var(--text-primary, #e6edf3)', fontWeight: 500 }}>Engine:</span>
            <span style={{ color: 'var(--status-covered, #3fb950)' }}>Online</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-covered, #3fb950)',
                boxShadow: '0 0 6px rgba(63, 185, 80, 0.6)',
                flexShrink: 0,
              }}
            />
            <span style={{ color: 'var(--text-primary, #e6edf3)', fontWeight: 500 }}>pgvector:</span>
            <span style={{ color: 'var(--status-covered, #3fb950)' }}>Active</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-covered, #3fb950)',
                boxShadow: '0 0 6px rgba(63, 185, 80, 0.6)',
                flexShrink: 0,
              }}
            />
            <span style={{ color: 'var(--text-primary, #e6edf3)', fontWeight: 500 }}>AST Parser:</span>
            <span style={{ color: 'var(--status-covered, #3fb950)' }}>Ready</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

/**
 * App — main dashboard layout wiring all Phase 8 components together.
 */
export default function App() {
  // --- RBAC Authentication State ---
  const [currentUser, setCurrentUser] = useState(null);
  const [overrideMap, setOverrideMap] = useState({});

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

  const handleOverrideRisk = useCallback((id, newScore) => {
    setOverrideMap((prev) => ({ ...prev, [id]: newScore }));
  }, []);

  // RBAC Session Gate: Require login before accessing enterprise dashboard
  if (!currentUser) {
    return <LoginModal onLogin={setCurrentUser} />;
  }

  return (
    <div className="app-layout">
      <Sidebar />

      <main className="app-main">
        {/* Page header */}
        <div className="page-header" id="page-header">
          <h1>Traceability Matrix</h1>
          <div className="page-header__actions">
            {/* User Session Nav / RBAC Role Badge with Logout */}
            <UserNav
              currentUser={currentUser}
              onLogout={() => setCurrentUser(null)}
            />
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
          currentUser={currentUser}
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
          overrideMap={overrideMap}
          currentUser={currentUser}
          onOverrideRisk={handleOverrideRisk}
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
