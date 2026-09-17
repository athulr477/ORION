import { useState, useEffect, useCallback } from 'react';
import { LayoutDashboard, Zap, Activity, CheckCircle, XCircle, Plug } from 'lucide-react';
import StatsBar from './components/StatsBar';
import MatrixTable from './components/MatrixTable';
import SensitivitySlider from './components/SensitivitySlider';
import HeatmapModal from './components/HeatmapModal';
import SimulateModal from './components/SimulateModal';
import IntegrationsModal from './components/IntegrationsModal';
import LoginModal from './components/LoginModal';
import UserNav from './components/UserNav';
import TaskQueueDrawer from './components/TaskQueueDrawer';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import { fetchMatrix, fetchStats, reclassifyMatrix, setAuthToken, overrideRiskScore } from './api/client';

/* ── Toast system ─────────────────────────────────────────────── */
let _addToast = null;

export function toast(message, type = 'info') {
  _addToast?.(message, type);
}

function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    _addToast = (message, type) => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
    };
    return () => { _addToast = null; };
  }, []);

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.type}`}>
          {t.type === 'success' && <CheckCircle size={15} color="var(--covered)" />}
          {t.type === 'error'   && <XCircle    size={15} color="var(--drifted)" />}
          {t.type === 'info'    && <Activity   size={15} color="var(--brand)" />}
          {t.message}
        </div>
      ))}
    </div>
  );
}

/* ── Sidebar ──────────────────────────────────────────────────── */
function Sidebar({ onOpenSimulate, onOpenIntegrations }) {
  return (
    <aside className="sidebar" id="sidebar">
      {/* Logo */}
      <div className="sidebar-logo" id="sidebar-logo">
        <div className="sidebar-logo-mark">O</div>
        <div>
          <div className="sidebar-logo-text">Orion</div>
          <div className="sidebar-logo-sub">v0.1 · Enterprise</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Traceability</div>
        <div className="sidebar-nav-item active" id="nav-dashboard">
          <LayoutDashboard size={16} />
          RTM Dashboard
        </div>
        <div 
          className="sidebar-nav-item" 
          onClick={onOpenIntegrations} 
          id="nav-integrations"
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
        >
          <Plug size={16} />
          Integrations
          <span 
            style={{ 
              marginLeft: 'auto', 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              background: 'var(--covered)',
              boxShadow: '0 0 8px var(--covered)',
              display: 'inline-block'
            }} 
            title="Integrations Active (Jira & GitHub)" 
          />
        </div>
      </nav>

      {/* Footer — Simulate */}
      <div className="sidebar-footer">
        <button
          className="sidebar-simulate-btn"
          onClick={onOpenSimulate}
          id="sidebar-simulate-btn"
        >
          <Zap size={14} />
          Simulate Webhook
        </button>
      </div>
    </aside>
  );
}

/* ── App ──────────────────────────────────────────────────────── */
export default function App() {
  const [currentUser, setCurrentUser]   = useState(null);
  const [overrideMap, setOverrideMap]   = useState({});
  const [isQueueOpen, setIsQueueOpen]   = useState(false);
  const [simulateOpen, setSimulateOpen] = useState(false);
  const [integrationsOpen, setIntegrationsOpen] = useState(false);

  const [stats, setStats]               = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [rows, setRows]                 = useState([]);
  const [total, setTotal]               = useState(0);
  const [page, setPage]                 = useState(1);
  const [pageSize]                      = useState(50);
  const [sort, setSort]                 = useState('risk_score');
  const [order, setOrder]               = useState('desc');
  const [statusFilter, setStatusFilter] = useState(null);
  const [search, setSearch]             = useState('');
  const [matrixLoading, setMatrixLoading] = useState(true);
  const [reclassifiedMap, setReclassifiedMap] = useState({});
  const [heatmapEntryId, setHeatmapEntryId]   = useState(null);

  /* Data fetching */
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
      const data = await fetchMatrix({ page, pageSize, status: statusFilter, sort, order, search: search || undefined });
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

  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { loadMatrix(); }, [loadMatrix]);

  useEffect(() => {
    const handleWS = () => { setPage(1); loadStats(); loadMatrix(); };
    window.addEventListener('workspaceChange', handleWS);
    return () => window.removeEventListener('workspaceChange', handleWS);
  }, [loadStats, loadMatrix]);

  /* Handlers */
  const handleSort = useCallback((col) => {
    if (sort === col) setOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    else { setSort(col); setOrder('desc'); }
    setPage(1);
  }, [sort]);

  const handleFilter = useCallback((status) => {
    setStatusFilter(status);
    setPage(1);
  }, []);

  const handleSearch = useCallback((term) => {
    setSearch(term);
    setPage(1);
  }, []);

  const handleReclassify = useCallback(async (coveredThreshold, driftedThreshold) => {
    try {
      const result = await reclassifyMatrix(coveredThreshold, driftedThreshold);
      const map = {};
      for (const row of result.rows) {
        if (row.changed) map[row.id] = row.new_status;
      }
      setReclassifiedMap(map);
      return result;
    } catch (err) {
      console.error('Reclassify failed:', err);
      return null;
    }
  }, []);

  const handleSimulateComplete = useCallback(() => {
    loadStats();
    loadMatrix();
    setIsQueueOpen(true);
    toast('Simulation complete — table refreshed', 'success');
  }, [loadStats, loadMatrix]);

  const handleOverrideRisk = useCallback(async (id, newStatus, rationale) => {
    try {
      await overrideRiskScore(id, newStatus, rationale);
      setOverrideMap((prev) => ({ ...prev, [id]: true }));
      loadMatrix();
      toast(`Override saved — status set to ${newStatus}`, 'success');
    } catch (err) {
      console.error('Failed to override score:', err);
      toast(`Override failed: ${err.message}`, 'error');
    }
  }, [loadMatrix]);

  /* Session gate */
  if (!currentUser) {
    return (
      <LoginModal
        onLogin={(user) => {
          setAuthToken(user.token);
          setCurrentUser(user);
        }}
      />
    );
  }

  return (
    <WorkspaceProvider currentUser={currentUser}>
      <div className="app-layout">
        <Sidebar 
          onOpenSimulate={() => setSimulateOpen(true)} 
          onOpenIntegrations={() => setIntegrationsOpen(true)} 
        />

        <main className="app-main">
          {/* Header */}
          <div className="page-header" id="page-header">
            <h1>Traceability Matrix</h1>
            <div className="page-header-actions">
              <button
                className="tasks-btn"
                onClick={() => setIsQueueOpen(true)}
                id="tasks-btn"
              >
                <Activity size={14} />
                Tasks
              </button>
              <UserNav currentUser={currentUser} onLogout={() => setCurrentUser(null)} />
            </div>
          </div>

          {/* Stats */}
          <StatsBar
            stats={stats}
            loading={statsLoading}
            statusFilter={statusFilter}
            onFilter={handleFilter}
          />

          {/* Sensitivity */}
          <SensitivitySlider
            coveredDefault={0.25}
            driftedDefault={0.6}
            onReclassify={handleReclassify}
            loading={matrixLoading}
            currentUser={currentUser}
          />

          {/* Table */}
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
            onPageChange={setPage}
            onRowClick={(row) => setHeatmapEntryId(row.id)}
          />
        </main>

        {/* Modals & Drawers */}
        <HeatmapModal entryId={heatmapEntryId} onClose={() => setHeatmapEntryId(null)} />
        <SimulateModal open={simulateOpen} onClose={() => setSimulateOpen(false)} onComplete={handleSimulateComplete} />
        <IntegrationsModal 
          isOpen={integrationsOpen} 
          onClose={() => setIntegrationsOpen(false)} 
          onSyncComplete={() => { loadStats(); loadMatrix(); }}
          onToast={(msg, type) => toast(msg, type)}
        />
        <TaskQueueDrawer isOpen={isQueueOpen} onClose={() => setIsQueueOpen(false)} />
        <ToastContainer />
      </div>
    </WorkspaceProvider>
  );
}
