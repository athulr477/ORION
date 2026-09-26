import { useState, useRef, useEffect } from 'react';
import { Zap, Check, CheckCircle, AlertTriangle, Play, X, Loader2 } from 'lucide-react';
import { simulateWebhook, fetchTask } from '../api/client';

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
  const [steps, setSteps]     = useState([]);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);
  const pollTimerRef          = useRef(null);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, []);

  const handleChange = (field) => (e) => {
    setPayload((p) => ({ ...p, [field]: e.target.value }));
  };

  const handleSubmit = async () => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    setLoading(true);
    setSteps(['Enqueuing task in background queue…']);
    setError(null);
    setResult(null);

    try {
      const res = await simulateWebhook(payload);

      if (res.task_id) {
        setSteps(['Task enqueued in background. Waiting for worker…']);
        const pollInterval = 1000;
        const maxAttempts = 45;
        let attempts = 0;

        const poll = async () => {
          attempts++;
          try {
            const task = await fetchTask(res.task_id);
            if (task.current_step) {
              setSteps((prev) => {
                if (!prev.includes(task.current_step)) {
                  return [...prev, task.current_step];
                }
                return prev;
              });
            }

            if (task.status === 'SUCCESS') {
              setLoading(false);
              const resultData = task.result || {};
              if (resultData.pipeline_steps && resultData.pipeline_steps.length > 0) {
                setSteps(resultData.pipeline_steps);
              }
              setResult(resultData);
              if (onComplete && resultData) {
                onComplete(resultData);
              }
            } else if (task.status === 'FAILURE') {
              setLoading(false);
              setError(task.error_message || 'Background task failed');
            } else if (attempts < maxAttempts) {
              pollTimerRef.current = setTimeout(poll, pollInterval);
            } else {
              setLoading(false);
              setError('Simulation timed out waiting for background worker.');
            }
          } catch (pollErr) {
            if (attempts < maxAttempts) {
              pollTimerRef.current = setTimeout(poll, pollInterval);
            } else {
              setLoading(false);
              setError(pollErr.message || 'Error tracking background task');
            }
          }
        };

        pollTimerRef.current = setTimeout(poll, pollInterval);
      } else {
        setSteps(res.pipeline_steps || []);
        setResult(res);
        setLoading(false);
        if (onComplete) onComplete(res);
      }
    } catch (e) {
      setError(e.message || 'Simulation failed');
      setLoading(false);
    }
  };

  const handleDone = () => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    if (result) onComplete?.(result);
    setSteps([]);
    setResult(null);
    setError(null);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={handleDone} id="simulate-modal-overlay">
      <div
        className="modal-box"
        style={{ maxWidth: 700 }}
        onClick={(e) => e.stopPropagation()}
        id="simulate-modal"
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="modal-title">
              <Zap size={16} color="var(--brand)" />
              Simulate Webhook
            </div>
            <div className="modal-subtitle">Run the full Phases 2–7 pipeline on synthetic data</div>
          </div>
          <button className="modal-close" onClick={handleDone} id="simulate-close-btn" aria-label="Close">
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Form Fields */}
          <div className="form-field">
            <label className="form-label" htmlFor="sim-req-id">Requirement External ID</label>
            <input
              id="sim-req-id"
              className="form-input"
              value={payload.requirement_external_id}
              onChange={handleChange('requirement_external_id')}
              disabled={loading}
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="sim-req-title">Requirement Title</label>
            <input
              id="sim-req-title"
              className="form-input"
              value={payload.requirement_title}
              onChange={handleChange('requirement_title')}
              disabled={loading}
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="sim-req-desc">Requirement Description</label>
            <textarea
              id="sim-req-desc"
              className="form-textarea"
              value={payload.requirement_description}
              onChange={handleChange('requirement_description')}
              disabled={loading}
              rows={3}
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="sim-test-fn">Test Function Name</label>
            <input
              id="sim-test-fn"
              className="form-input"
              value={payload.test_function_name}
              onChange={handleChange('test_function_name')}
              disabled={loading}
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="sim-test-code">Test Source Code</label>
            <textarea
              id="sim-test-code"
              className="form-textarea"
              value={payload.test_source_code}
              onChange={handleChange('test_source_code')}
              disabled={loading}
              rows={6}
            />
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="sim-test-path">Test File Path</label>
            <input
              id="sim-test-path"
              className="form-input"
              value={payload.test_file_path}
              onChange={handleChange('test_file_path')}
              disabled={loading}
            />
          </div>

          {/* Pipeline steps output */}
          {steps.length > 0 && (
            <div className="simulate-steps" id="simulate-steps">
              <div className="simulate-steps__title">Pipeline Steps</div>
              {steps.map((step, i) => {
                const isLast = i === steps.length - 1 && loading;
                return (
                  <div className="simulate-step" key={i}>
                    <span className="simulate-step__icon">
                      {isLast ? (
                        <Loader2 size={13} style={{ animation: 'spin 1s linear infinite', color: 'var(--brand)' }} />
                      ) : (
                        <Check size={13} />
                      )}
                    </span>
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Result */}
          {result?.matrix_entry && (
            <div className="simulate-result" id="simulate-result">
              <CheckCircle size={15} />
              Entry created — Status: <strong>{result.matrix_entry.status}</strong> · Risk:{' '}
              <strong>{((result.matrix_entry.risk_score || 0) * 100).toFixed(1)}%</strong>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="simulate-error">
              <AlertTriangle size={15} />
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="modal-actions">
            <button className="btn-cancel" onClick={handleDone} id="simulate-cancel-btn">
              {result ? 'Close' : 'Cancel'}
            </button>
            {!result && (
              <button
                className="btn-primary"
                onClick={handleSubmit}
                disabled={loading}
                id="simulate-run-btn"
              >
                {loading ? (
                  <><span className="spinner" style={{ width: 13, height: 13, display: 'inline-block', verticalAlign: 'middle', marginRight: 6 }} />Running…</>
                ) : (
                  <><Play size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />Run Simulation</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
