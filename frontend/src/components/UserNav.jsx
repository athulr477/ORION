/**
 * UserNav — Header/Navbar badge component displaying the authenticated RBAC user.
 *
 * Displays: "Logged in as: [Username] ([Role])" with a styled "Logout" button.
 *
 * @param {Object} props
 * @param {{ username: string, role: string }} props.currentUser - The active session user object
 * @param {Function} props.onLogout - Callback function that resets currentUser to null
 */
export default function UserNav({ currentUser, onLogout }) {
  if (!currentUser) return null;

  const isQALead = currentUser.role === 'QA Lead / System Administrator';

  return (
    <div
      id="user-nav-container"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '12px',
        padding: '6px 14px',
        backgroundColor: 'var(--bg-tertiary, #161b22)',
        border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.6))',
        borderRadius: '8px',
        fontSize: '13px',
        color: 'var(--text-secondary, #8b949e)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isQALead ? '#3fb950' : '#58a6ff',
            boxShadow: `0 0 8px ${isQALead ? '#3fb950' : '#58a6ff'}`,
          }}
        />
        <span>
          Logged in as:{' '}
          <strong style={{ color: 'var(--text-primary, #e6edf3)' }}>
            {currentUser.username}
          </strong>{' '}
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '9999px',
              backgroundColor: isQALead
                ? 'rgba(63, 185, 80, 0.15)'
                : 'rgba(88, 166, 255, 0.15)',
              color: isQALead ? '#3fb950' : '#58a6ff',
              border: `1px solid ${
                isQALead
                  ? 'rgba(63, 185, 80, 0.3)'
                  : 'rgba(88, 166, 255, 0.3)'
              }`,
              fontWeight: 500,
            }}
          >
            {currentUser.role}
          </span>
        </span>
      </div>

      <button
        type="button"
        onClick={onLogout}
        id="user-logout-btn"
        style={{
          marginLeft: '4px',
          padding: '4px 10px',
          backgroundColor: 'transparent',
          border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.6))',
          borderRadius: '6px',
          color: 'var(--text-secondary, #8b949e)',
          fontSize: '12px',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.target.style.color = '#f85149';
          e.target.style.borderColor = 'rgba(248, 81, 73, 0.4)';
          e.target.style.backgroundColor = 'rgba(248, 81, 73, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.target.style.color = 'var(--text-secondary, #8b949e)';
          e.target.style.borderColor = 'var(--border-subtle, rgba(48, 54, 61, 0.6))';
          e.target.style.backgroundColor = 'transparent';
        }}
      >
        Logout ⎋
      </button>
    </div>
  );
}
