import { useState } from 'react';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import orionLogo from '../assets/orion.png';

/**
 * LoginModal — enterprise session gate.
 * Authenticates against the real backend /api/v1/auth/token endpoint.
 */
export default function LoginModal({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const performLogin = async (userToAuth, passToAuth) => {
    const trimmed = userToAuth.trim();
    if (!trimmed || !passToAuth) {
      setError('Please provide both username and password.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', trimmed);
      formData.append('password', passToAuth);

      const res = await fetch('http://localhost:8000/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      if (!res.ok) {
        setError('Invalid credentials. Check username and password.');
        setLoading(false);
        return;
      }

      const data = await res.json();
      const backendRole =
        data.role === 'QA_LEAD' ? 'QA Lead / System Administrator' : 'Software Developer';

      onLogin({ username: data.username, role: backendRole, token: data.access_token });
    } catch {
      setError('Could not reach auth server. Is the backend running?');
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    performLogin(username, password);
  };

  const handleQuickLogin = (u, p) => {
    setUsername(u);
    setPassword(p);
    performLogin(u, p);
  };

  return (
    <div className="login-screen" id="login-screen">
      <div className="login-card" id="login-card">
        {/* Logo */}
        <div className="login-logo">
          <img src={orionLogo} alt="Orion" className="login-logo-img" />
          <div>
            <div className="login-title">Sign in to Orion</div>
            <div className="login-subtitle">Enterprise Traceability Platform</div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label className="form-label" htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              className="form-input"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="form-field" style={{ position: 'relative' }}>
            <label className="form-label" htmlFor="login-password">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                id="login-password"
                type={showPass ? 'text' : 'password'}
                className="form-input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                style={{ paddingRight: '38px' }}
              />
              <button
                type="button"
                onClick={() => setShowPass((v) => !v)}
                style={{
                  position: 'absolute',
                  right: 10,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-tertiary)',
                  cursor: 'pointer',
                  display: 'flex',
                  padding: 2,
                }}
                tabIndex={-1}
                aria-label="Toggle password visibility"
              >
                {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error" id="login-error">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          <button
            type="submit"
            id="login-submit-btn"
            className="btn-login"
            disabled={loading}
            style={{ marginTop: '4px' }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {/* 1-Click Quick Demo Sign In */}
        <div className="login-hint" id="login-hint" style={{ marginTop: '16px' }}>
          <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Instant Demo Sign-In
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <button
              type="button"
              id="quick-login-admin"
              onClick={() => handleQuickLogin('admin', 'orion_secret_key')}
              disabled={loading}
              className="btn-page"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '8px 10px',
                textAlign: 'left',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-elevated)',
                cursor: 'pointer',
              }}
            >
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '12px' }}>QA Lead</span>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>admin</span>
            </button>
            <button
              type="button"
              id="quick-login-dev"
              onClick={() => handleQuickLogin('devuser', 'dev_password')}
              disabled={loading}
              className="btn-page"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '8px 10px',
                textAlign: 'left',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-elevated)',
                cursor: 'pointer',
              }}
            >
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '12px' }}>Developer</span>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>devuser</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
