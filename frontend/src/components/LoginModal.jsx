import { useState } from 'react';

/**
 * LoginModal — Role-Based Access Control (RBAC) session gate for Orion.
 *
 * Full-screen overlay allowing examiners/users to switch between
 * "QA Lead / System Administrator" and "Software Developer" roles.
 *
 * @param {Object} props
 * @param {Function} props.onLogin - Callback invoked with { username: string, role: string }
 */
export default function LoginModal({ onLogin }) {
  const [username, setUsername] = useState('lead_auditor');
  const [role, setRole] = useState('QA Lead / System Administrator');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) {
      setError('Please provide a username to proceed.');
      return;
    }
    setError('');
    onLogin({ username: trimmed, role });
  };

  const setPreset = (presetUser, presetRole) => {
    setUsername(presetUser);
    setRole(presetRole);
    setError('');
  };

  const isQALead = role === 'QA Lead / System Administrator';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(7, 9, 15, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        padding: '24px',
        fontFamily: "var(--font-sans, 'Inter', -apple-system, sans-serif)",
      }}
    >
      {/* Background ambient decorative glow */}
      <div
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(88, 166, 255, 0.12) 0%, rgba(188, 140, 255, 0.05) 50%, transparent 70%)',
          pointerEvents: 'none',
          filter: 'blur(40px)',
        }}
      />

      {/* Modal Container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '460px',
          backgroundColor: 'var(--bg-secondary, #0d1117)',
          border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.8))',
          borderRadius: '16px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(88, 166, 255, 0.15)',
          padding: '32px',
          color: 'var(--text-primary, #e6edf3)',
          zIndex: 1,
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              margin: '0 auto 14px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '22px',
              fontWeight: '800',
              color: '#07090f',
              boxShadow: '0 0 16px rgba(88, 166, 255, 0.4)',
            }}
          >
            O
          </div>
          <h2
            style={{
              margin: 0,
              fontSize: '22px',
              fontWeight: 700,
              letterSpacing: '-0.02em',
              background: 'linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Orion Enterprise Console
          </h2>
          <p
            style={{
              margin: '6px 0 0',
              fontSize: '13px',
              color: 'var(--text-secondary, #8b949e)',
            }}
          >
            Role-Based Access Control (RBAC) Verification Session
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {/* Username Field */}
          <div style={{ marginBottom: '20px' }}>
            <label
              htmlFor="rbac-username"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-secondary, #8b949e)',
                marginBottom: '8px',
              }}
            >
              Username
            </label>
            <input
              id="rbac-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username (e.g., alex.dev, qa.lead)"
              style={{
                width: '100%',
                padding: '10px 14px',
                backgroundColor: 'var(--bg-tertiary, #161b22)',
                border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.8))',
                borderRadius: '8px',
                color: 'var(--text-primary, #e6edf3)',
                fontSize: '14px',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.2s, box-shadow 0.2s',
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#58a6ff';
                e.target.style.boxShadow = '0 0 0 3px rgba(88, 166, 255, 0.15)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'rgba(48, 54, 61, 0.8)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Role Dropdown */}
          <div style={{ marginBottom: '20px' }}>
            <label
              htmlFor="rbac-role"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-secondary, #8b949e)',
                marginBottom: '8px',
              }}
            >
              Select Role
            </label>
            <select
              id="rbac-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                backgroundColor: 'var(--bg-tertiary, #161b22)',
                border: '1px solid var(--border-subtle, rgba(48, 54, 61, 0.8))',
                borderRadius: '8px',
                color: 'var(--text-primary, #e6edf3)',
                fontSize: '14px',
                outline: 'none',
                boxSizing: 'border-box',
                cursor: 'pointer',
              }}
            >
              <option value="QA Lead / System Administrator">
                QA Lead / System Administrator
              </option>
              <option value="Software Developer">
                Software Developer
              </option>
            </select>

            {/* Role Privilege Badge */}
            <div
              style={{
                marginTop: '10px',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: isQALead
                  ? 'rgba(63, 185, 80, 0.12)'
                  : 'rgba(88, 166, 255, 0.12)',
                border: `1px solid ${
                  isQALead
                    ? 'rgba(63, 185, 80, 0.3)'
                    : 'rgba(88, 166, 255, 0.3)'
                }`,
                color: isQALead ? '#3fb950' : '#58a6ff',
              }}
            >
              <span>{isQALead ? '🛡️' : '💻'}</span>
              <span>
                {isQALead
                  ? 'Full Privileges: Override Risk Scores, Reclassify Matrix, Run Simulations'
                  : 'Developer Privileges: Inspect Traceability, View AST Evidence (Score overrides locked)'}
              </span>
            </div>
          </div>

          {/* Quick Preset Selector for Live Demo Presentation */}
          <div style={{ marginBottom: '22px' }}>
            <div
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--text-tertiary, #6e7681)',
                marginBottom: '6px',
              }}
            >
              Quick Examiner Demo Presets
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setPreset('lead_auditor', 'QA Lead / System Administrator')}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  backgroundColor: 'rgba(22, 27, 34, 0.7)',
                  border: '1px solid rgba(48, 54, 61, 0.6)',
                  borderRadius: '6px',
                  color: 'var(--text-secondary, #8b949e)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = '#e6edf3';
                  e.target.style.borderColor = '#58a6ff';
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = '#8b949e';
                  e.target.style.borderColor = 'rgba(48, 54, 61, 0.6)';
                }}
              >
                QA Lead
              </button>
              <button
                type="button"
                onClick={() => setPreset('chen_dev', 'Software Developer')}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  backgroundColor: 'rgba(22, 27, 34, 0.7)',
                  border: '1px solid rgba(48, 54, 61, 0.6)',
                  borderRadius: '6px',
                  color: 'var(--text-secondary, #8b949e)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = '#e6edf3';
                  e.target.style.borderColor = '#bc8cff';
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = '#8b949e';
                  e.target.style.borderColor = 'rgba(48, 54, 61, 0.6)';
                }}
              >
                Developer
              </button>
            </div>
          </div>

          {/* Validation Error Message */}
          {error && (
            <div
              style={{
                marginBottom: '16px',
                padding: '8px 12px',
                borderRadius: '6px',
                backgroundColor: 'rgba(248, 81, 73, 0.15)',
                border: '1px solid rgba(248, 81, 73, 0.4)',
                color: '#f85149',
                fontSize: '13px',
              }}
            >
              ⚠️ {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            id="rbac-login-btn"
            style={{
              width: '100%',
              padding: '12px 16px',
              background: 'linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%)',
              border: 'none',
              borderRadius: '8px',
              color: '#07090f',
              fontSize: '14px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(88, 166, 255, 0.25)',
              transition: 'transform 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'translateY(-1px)';
              e.target.style.boxShadow = '0 6px 18px rgba(88, 166, 255, 0.35)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 4px 14px rgba(88, 166, 255, 0.25)';
            }}
          >
            Login / Enter Dashboard →
          </button>
        </form>
      </div>
    </div>
  );
}
