import { useState, useEffect, useCallback } from 'react';
import { Play, CheckCircle, XCircle, Clock, Loader2, List, X, RefreshCw } from 'lucide-react';
import { fetchTasks as apiFetchTasks } from '../api/client';

/**
 * TaskQueueDrawer — slide-in panel showing background task status.
 * Polls every 3 s while open. Has a manual refresh button.
 */
export default function TaskQueueDrawer({ isOpen, onClose }) {
  const [tasks, setTasks]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadTasks = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await apiFetchTasks(15);
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) loadTasks();
    const interval = setInterval(() => { if (isOpen) loadTasks(true); }, 3000);
    return () => clearInterval(interval);
  }, [isOpen, loadTasks]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'PENDING': return <Clock    size={16} color="var(--partial)"  />;
      case 'RUNNING': return <Loader2  size={16} color="var(--brand)"    style={{ animation: 'spin 0.8s linear infinite' }} />;
      case 'SUCCESS': return <CheckCircle size={16} color="var(--covered)" />;
      case 'FAILURE': return <XCircle  size={16} color="var(--drifted)"  />;
      default:        return <Play     size={16} color="var(--text-tertiary)" />;
    }
  };

  return (
    <>
      <div className={`drawer-overlay ${isOpen ? 'is-open' : ''}`} onClick={onClose} />
      <div className={`drawer ${isOpen ? 'is-open' : ''}`} id="task-queue-drawer">
        {/* Header */}
        <div className="drawer__header">
          <div className="drawer__title">
            <List size={17} />
            Background Tasks
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              className="drawer__refresh"
              onClick={() => loadTasks(true)}
              disabled={refreshing}
              id="drawer-refresh-btn"
              title="Refresh tasks"
            >
              <RefreshCw size={12} style={refreshing ? { animation: 'spin 0.7s linear infinite' } : {}} />
              Refresh
            </button>
            <button className="drawer__close" onClick={onClose} id="drawer-close-btn" aria-label="Close tasks panel">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="drawer__content">
          {loading && tasks.length === 0 ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '48px 0' }}>
              <div className="spinner" />
            </div>
          ) : tasks.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '48px 0', fontSize: '13px' }}>
              <Play size={28} color="var(--text-tertiary)" style={{ marginBottom: '12px', opacity: 0.4 }} />
              <div>No background tasks yet.</div>
              <div style={{ marginTop: '6px', fontSize: '12px' }}>
                Run a simulation to see pipeline tasks here.
              </div>
            </div>
          ) : (
            tasks.map((task) => (
              <div key={task.id} className="task-card" id={`task-${task.id}`}>
                {/* Task header */}
                <div className="task-card__header">
                  <div className="task-card__left">
                    {getStatusIcon(task.status)}
                    <span className="task-card__name">
                      {task.task_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="task-card__time">
                    {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {/* Running progress */}
                {task.status === 'RUNNING' && (
                  <div style={{ marginTop: '8px' }}>
                    <div className="task-card__progress-info">
                      <span>{task.current_step || 'Processing…'}</span>
                      <span>{Math.round((task.progress || 0) * 100)}%</span>
                    </div>
                    <div className="task-progress-bar">
                      <div
                        className="task-progress-fill"
                        style={{ width: `${Math.max(5, (task.progress || 0) * 100)}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Failure */}
                {task.status === 'FAILURE' && (
                  <div className="task-error">{task.error_message || 'Unknown error occurred'}</div>
                )}

                {/* Success */}
                {task.status === 'SUCCESS' && (
                  <div className="task-success">Completed successfully.</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
