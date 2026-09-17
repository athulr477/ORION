import { useWorkspace } from '../contexts/WorkspaceContext';
import { LogOut, Shield, Code2 } from 'lucide-react';

/**
 * UserNav — compact header bar showing user identity, role badge,
 * workspace switcher, and logout.
 */
export default function UserNav({ currentUser, onLogout }) {
  const { workspaces, currentWorkspace, switchWorkspace, loading } = useWorkspace() || {};

  if (!currentUser) return null;

  const isQALead = currentUser.role === 'QA Lead / System Administrator';
  const initials = currentUser.username?.slice(0, 2).toUpperCase() || 'U';

  return (
    <div className="user-nav" id="user-nav-container">
      {/* Avatar */}
      <div className="user-avatar" title={currentUser.username}>{initials}</div>

      {/* Info */}
      <div className="user-info">
        <div className="user-name">{currentUser.username}</div>
        <div className="user-role">
          <span className={`role-badge ${isQALead ? 'role-badge--qa' : 'role-badge--dev'}`}>
            {isQALead ? <Shield size={9} /> : <Code2 size={9} />}
            {isQALead ? 'QA Lead' : 'Developer'}
          </span>
        </div>
      </div>

      <div className="user-divider" />

      {/* Workspace switcher */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Workspace
        </span>
        <select
          className="workspace-select"
          value={currentWorkspace?.id || ''}
          onChange={(e) => switchWorkspace(e.target.value)}
          disabled={loading || !workspaces?.length}
          id="workspace-select"
          aria-label="Switch workspace"
        >
          {loading ? (
            <option>Loading…</option>
          ) : (
            workspaces?.map((ws) => (
              <option key={ws.id} value={ws.id}>{ws.name}</option>
            ))
          )}
        </select>
      </div>

      <div className="user-divider" />

      {/* Logout */}
      <button
        className="btn-logout"
        onClick={onLogout}
        id="user-logout-btn"
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut size={13} />
        Logout
      </button>
    </div>
  );
}
