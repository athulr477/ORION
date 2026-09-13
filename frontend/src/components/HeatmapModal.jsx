import { useEffect, useState } from 'react';
import StatusBadge from './StatusBadge';
import { fetchHeatmap } from '../api/client';

/**
 * HeatmapModal — XAI keyword-overlap evidence modal.
 *
 * Shows requirement constraints matched against test assertions with
 * color-coded scores and keyword overlap cloud.
 */
export default function HeatmapModal({ entryId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!entryId) return;
    setLoading(true);
    setError(null);
    fetchHeatmap(entryId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entryId]);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!entryId) return null;

  const scoreColor = (v) => {
    if (v == null) return 'var(--text-tertiary)';
    if (v >= 0.75) return 'var(--status-covered)';
    if (v >= 0.4) return 'var(--status-partial)';
    return 'var(--status-drifted)';
  };

  return (
    <div className="modal-overlay" onClick={onClose} id="heatmap-modal-overlay">
      <div className="modal-content" onClick={(e) => e.stopPropagation()} id="heatmap-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header__info">
            <h2>
              {loading ? 'Loading...' : data ? `${data.requirement_external_id} — XAI Evidence` : 'Error'}
            </h2>
            {data && (
              <div className="modal-header__meta">
                <StatusBadge status={data.status} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                  {data.test_function_name}
                </span>
              </div>
            )}
          </div>
          <button className="modal-close-btn" onClick={onClose} id="heatmap-close-btn">✕</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {loading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <span className="loading-spinner" />
            </div>
          )}

          {error && (
            <div style={{ textAlign: 'center', padding: 48, color: 'var(--status-drifted)' }}>
              Error: {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Score cards */}
              <div className="heatmap-scores" id="heatmap-scores">
                {[
                  { label: 'Semantic Score', value: data.semantic_score },
                  { label: 'Structural Score', value: data.structural_score },
                  { label: 'Risk Score', value: data.risk_score },
                ].map((s) => (
                  <div className="heatmap-score-card" key={s.label}>
                    <div className="heatmap-score-card__label">{s.label}</div>
                    <div
                      className="heatmap-score-card__value"
                      style={{ color: scoreColor(s.value) }}
                    >
                      {s.value != null ? `${(s.value * 100).toFixed(1)}%` : '—'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Requirement title */}
              <div className="heatmap-section">
                <div className="heatmap-section__title">📋 Requirement</div>
                <div
                  style={{
                    padding: 'var(--space-md)',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--text-sm)',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.7,
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <strong style={{ color: 'var(--text-primary)' }}>{data.requirement_title}</strong>
                  {data.requirement_description && (
                    <div style={{ marginTop: 8 }}>{data.requirement_description}</div>
                  )}
                </div>
              </div>

              {/* Constraint → Assertion matches */}
              {data.matches.length > 0 && (
                <div className="heatmap-section" id="heatmap-matches">
                  <div className="heatmap-section__title">🔗 Constraint → Assertion Matches</div>
                  <div className="match-grid">
                    {data.matches.map((m, i) => (
                      <div className="match-row" key={i}>
                        <div className="match-row__constraint">
                          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
                            Constraint #{m.constraint_index + 1}
                          </div>
                          {m.constraint_text || `${m.constraint_operator || ''} ${m.constraint_value || ''}`.trim() || '—'}
                        </div>
                        <div className="match-row__score">
                          <div
                            className="match-row__score-value"
                            style={{ color: scoreColor(m.combined_score) }}
                          >
                            {(m.combined_score * 100).toFixed(0)}%
                          </div>
                          <div className="match-row__score-label">match</div>
                          <div className="match-row__arrow">⟷</div>
                        </div>
                        <div className="match-row__assertion">
                          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginBottom: 4 }}>
                            Assertion #{m.assertion_index + 1}
                          </div>
                          {m.assertion_text || '—'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {data.matches.length === 0 && (
                <div className="heatmap-section">
                  <div className="heatmap-section__title">🔗 Constraint → Assertion Matches</div>
                  <div
                    style={{
                      padding: 'var(--space-lg)',
                      textAlign: 'center',
                      color: 'var(--text-tertiary)',
                      fontSize: 'var(--text-sm)',
                    }}
                  >
                    No structural matches found between constraints and assertions
                  </div>
                </div>
              )}

              {/* Keyword Overlap */}
              {data.keywords.length > 0 && (
                <div className="heatmap-section" id="heatmap-keywords">
                  <div className="heatmap-section__title">🏷️ Keyword Overlap</div>
                  <div className="keyword-cloud">
                    {data.keywords.map((kw, i) => {
                      const cls = kw.matched
                        ? 'keyword-pill--matched'
                        : kw.source === 'requirement'
                        ? 'keyword-pill--req'
                        : 'keyword-pill--test';
                      return (
                        <span key={`${kw.word}-${i}`} className={`keyword-pill ${cls}`}>
                          {kw.word}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Audit Summary */}
              {data.audit_summary && (
                <div className="heatmap-section" id="heatmap-audit">
                  <div className="heatmap-section__title">💬 Audit Summary</div>
                  <div className="audit-summary">{data.audit_summary}</div>
                </div>
              )}

              {/* Requirement Delta */}
              {data.requirement_delta && Object.keys(data.requirement_delta).length > 0 && (
                <div className="heatmap-section" id="heatmap-delta">
                  <div className="heatmap-section__title">📝 Requirement Delta</div>
                  <pre
                    style={{
                      padding: 'var(--space-md)',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: 'var(--text-xs)',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-secondary)',
                      overflow: 'auto',
                      maxHeight: 200,
                    }}
                  >
                    {JSON.stringify(data.requirement_delta, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
