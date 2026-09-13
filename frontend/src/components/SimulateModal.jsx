import { useState } from 'react';
import { simulateWebhook } from '../api/client';

const DEFAULT_PAYLOAD = {
  requirement_external_id: 'REQ-DEMO-001',
  requirement_title: 'Response time must be less than 200ms',
  requirement_description:
    'The API response time must be less than 200 milliseconds ' +
    'under normal load conditions. The system must handle at ' +
    'least 100 concurrent requests.',
  test_function_name: 'test_response_time_under_limit',
  test_source_code:
    '@traces("REQ-DEMO-001")\n' +
    'def test_response_time_under_limit():\n' +
    '    """Verify API responds within 200ms."""\n' +
    "    response = client.get('/api/endpoint')\n" +
    '    assert response.elapsed.total_seconds() < 0.2\n' +
    '    assert response.status_code == 200\n',
  test_file_path: 'tests/test_performance.py',
};

/**
 * SimulateModal — dialog for running the simulate-webhook end-to-end demo.
 */
export default function SimulateModal({ open, onClose, onComplete }) {
  const [payload, setPayload] = useState({ ...DEFAULT_PAYLOAD });
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (field) => (e) => {
    setPayload((p) => ({ ...p, [field]: e.target.value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setSteps([]);
    setError(null);
    setResult(null);

    try {
      const res = await simulateWebhook(payload);
      setSteps(res.pipeline_steps || []);
      setResult(res);
    } catch (e) {
      setError(e.message || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDone = () => {
    if (result) {
      onComplete?.(result);
    }
    setSteps([]);
    setResult(null);
    setError(null);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={handleDone} id="simulate-modal-overlay">
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        id="simulate-modal"
        style={{ maxWidth: 720 }}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header__info">
            <h2>🚀 Simulate Webhook</h2>
            <div className="modal-header__meta">
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                Run the full Phases 2–7 pipeline on synthetic data
              </span>
            </div>
          </div>
          <button className="modal-close-btn" onClick={handleDone} id="simulate-close-btn">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="modal-body simulate-dialog">
          {/* Form Fields */}
          <div className="simulate-field">
            <label htmlFor="sim-req-id">Requirement External ID</label>
            <input
              id="sim-req-id"
              value={payload.requirement_external_id}
              onChange={handleChange('requirement_external_id')}
              disabled={loading}
            />
          </div>

          <div className="simulate-field">
            <label htmlFor="sim-req-title">Requirement Title</label>
            <input
              id="sim-req-title"
              value={payload.requirement_title}
              onChange={handleChange('requirement_title')}
              disabled={loading}
            />
          </div>

          <div className="simulate-field">
            <label htmlFor="sim-req-desc">Requirement Description</label>
            <textarea
              id="sim-req-desc"
              value={payload.requirement_description}
              onChange={handleChange('requirement_description')}
              disabled={loading}
              rows={3}
              style={{ minHeight: 80 }}
            />
          </div>

          <div className="simulate-field">
            <label htmlFor="sim-test-fn">Test Function Name</label>
            <input
              id="sim-test-fn"
              value={payload.test_function_name}
              onChange={handleChange('test_function_name')}
              disabled={loading}
            />
          </div>

          <div className="simulate-field">
            <label htmlFor="sim-test-code">Test Source Code</label>
            <textarea
              id="sim-test-code"
              value={payload.test_source_code}
              onChange={handleChange('test_source_code')}
              disabled={loading}
              rows={6}
            />
          </div>

          <div className="simulate-field">
            <label htmlFor="sim-test-path">Test File Path</label>
            <input
              id="sim-test-path"
              value={payload.test_file_path}
              onChange={handleChange('test_file_path')}
              disabled={loading}
            />
          </div>

          {/* Pipeline steps output */}
          {steps.length > 0 && (
            <div className="simulate-steps" id="simulate-steps">
              <div className="simulate-steps__title">Pipeline Steps</div>
              {steps.map((step, i) => (
                <div className="simulate-step" key={i}>
                  <span className="simulate-step__icon">✓</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          )}

          {/* Result summary */}
          {result?.matrix_entry && (
            <div
              style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-md)',
                background: 'var(--status-covered-bg)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--status-covered-border)',
                fontSize: 'var(--text-sm)',
                color: 'var(--status-covered)',
              }}
              id="simulate-result"
            >
              ✅ Entry created — Status:{' '}
              <strong>{result.matrix_entry.status}</strong> · Risk:{' '}
              <strong>{((result.matrix_entry.risk_score || 0) * 100).toFixed(1)}%</strong>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-md)',
                background: 'var(--status-drifted-bg)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--status-drifted-border)',
                fontSize: 'var(--text-sm)',
                color: 'var(--status-drifted)',
              }}
            >
              ❌ {error}
            </div>
          )}

          {/* Actions */}
          <div className="simulate-actions">
            <button
              className="simulate-cancel-btn"
              onClick={handleDone}
              id="simulate-cancel-btn"
            >
              {result ? 'Close' : 'Cancel'}
            </button>
            {!result && (
              <button
                className="simulate-trigger"
                onClick={handleSubmit}
                disabled={loading}
                id="simulate-run-btn"
              >
                {loading && <span className="loading-spinner" />}
                {loading ? 'Running pipeline...' : '⚡ Run Simulation'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
