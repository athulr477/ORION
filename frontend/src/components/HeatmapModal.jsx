import { useEffect, useState } from 'react';
import { ClipboardList, Link as LinkIcon, Tags, MessageSquare, FileText, X } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { fetchHeatmap } from '../api/client';

/**
 * HeatmapModal — XAI keyword-overlap evidence modal.
 * Shows requirement constraints matched against test assertions with
 * colour-coded scores and a keyword overlap cloud.
 */
export default function HeatmapModal({ entryId, onClose }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!entryId) return;
    setLoading(true);
    setError(null);
    fetchHeatmap(entryId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entryId]);

  // Escape to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!entryId) return null;

  const scoreColor = (v) => {
    if (v == null) return 'var(--text-tertiary)';
    if (v >= 0.75) return 'var(--covered)';
    if (v >= 0.4)  return 'var(--partial)';
    return 'var(--drifted)';
  };

  return (
    <div className="modal-overlay" onClick={onClose} id="heatmap-modal-overlay">
      <div
        className="modal-box"
        style={{ maxWidth: 760 }}
        onClick={(e) => e.stopPropagation()}
        id="heatmap-modal"
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="modal-title">
              <ClipboardList size={16} />
              {loading ? 'Loading…' : data ? `${data.requirement_external_id} — XAI Evidence` : 'Error'}
            </div>
            {data && (
              <div className="modal-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginTop: 6 }}>
                <StatusBadge status={data.status} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{data.test_function_name}</span>
              </div>
            )}
          </div>
          <button className="modal-close" onClick={onClose} id="heatmap-close-btn" aria-label="Close">
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {loading && (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto' }} />
            </div>
          )}

          {error && (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--drifted)' }}>
              Error: {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Score cards */}
              <div className="heatmap-scores" id="heatmap-scores">
                {[
                  { label: 'Semantic Score',    value: data.semantic_score },
                  { label: 'Structural Score',  value: data.structural_score },
                  { label: 'Risk Score',        value: data.risk_score },
                ].map((s) => (
                  <div className="heatmap-score-card" key={s.label}>
                    <div className="heatmap-score-card__label">{s.label}</div>
                    <div className="heatmap-score-card__value" style={{ color: scoreColor(s.value) }}>
                      {s.value != null ? `${(s.value * 100).toFixed(1)}%` : '—'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Requirement */}
              <div className="heatmap-section">
                <div className="heatmap-section__title"><ClipboardList size={13} /> Requirement</div>
                <div className="req-block">
                  <strong style={{ color: 'var(--text-primary)' }}>{data.requirement_title}</strong>
                  {data.requirement_description && (
                    <div style={{ marginTop: 8 }}>{data.requirement_description}</div>
                  )}
                </div>
              </div>

              {/* Constraint → Assertion matches */}
              <div className="heatmap-section" id="heatmap-matches">
                <div className="heatmap-section__title"><LinkIcon size={13} /> Constraint → Assertion Matches</div>
                {data.matches.length === 0 ? (
                  <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
                    No structural matches found.
                  </div>
                ) : (
                  <div className="match-grid">
                    {data.matches.map((m, i) => (
                      <div className="match-row" key={i}>
                        <div className="match-row__constraint">
                          <div className="match-row__meta">Constraint #{m.constraint_index + 1}</div>
                          {m.constraint_text || `${m.constraint_operator || ''} ${m.constraint_value || ''}`.trim() || '—'}
                        </div>
                        <div className="match-row__score">
                          <span className="match-row__score-val" style={{ color: scoreColor(m.combined_score) }}>
                            {(m.combined_score * 100).toFixed(0)}%
                          </span>
                          <span className="match-row__score-lbl">match</span>
                          <span className="match-row__arrow">⟷</span>
                        </div>
                        <div className="match-row__assertion">
                          <div className="match-row__meta">Assertion #{m.assertion_index + 1}</div>
                          {m.assertion_text || '—'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Keyword Overlap */}
              {data.keywords.length > 0 && (
                <div className="heatmap-section" id="heatmap-keywords">
                  <div className="heatmap-section__title"><Tags size={13} /> Keyword Overlap</div>
                  <div className="keyword-cloud">
                    {data.keywords.map((kw, i) => {
                      const cls = kw.matched
                        ? 'keyword-pill--matched'
                        : kw.source === 'requirement'
                        ? 'keyword-pill--req'
                        : 'keyword-pill--test';
                      return (
                        <span key={`${kw.word}-${i}`} className={`keyword-pill ${cls}`}>{kw.word}</span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Audit Summary */}
              {data.audit_summary && (
                <div className="heatmap-section" id="heatmap-audit">
                  <div className="heatmap-section__title"><MessageSquare size={13} /> Audit Summary</div>
                  <div className="audit-summary">{data.audit_summary}</div>
                </div>
              )}

              {/* Requirement Delta */}
              {data.requirement_delta && Object.keys(data.requirement_delta).length > 0 && (
                <div className="heatmap-section" id="heatmap-delta">
                  <div className="heatmap-section__title"><FileText size={13} /> Requirement Delta</div>
                  <pre style={{
                    padding: 'var(--sp-4)',
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--r-md)',
                    border: '1px solid var(--border-default)',
                    fontSize: 11,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    overflow: 'auto',
                    maxHeight: 200,
                  }}>
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
