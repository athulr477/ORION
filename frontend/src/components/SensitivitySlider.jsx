import { useState, useCallback, useRef, useEffect } from 'react';
import { SlidersHorizontal, Sparkles, Lock, ChevronDown } from 'lucide-react';

/**
 * SensitivitySlider — collapsible dual-slider panel for live threshold reclassification.
 * Collapsed by default for Developers, expanded by default for QA Leads.
 *
 * Polarity (risk_score = 1 - alignment):
 *   risk < coveredDefault  → Covered  (low risk)
 *   risk > driftedDefault  → Drifted  (high risk)
 */
export default function SensitivitySlider({
  coveredDefault = 0.25,
  driftedDefault = 0.6,
  onReclassify,
  loading = false,
  currentUser,
}) {
  const isQALead =
    currentUser?.role?.includes('QA Lead') ||
    currentUser?.role?.includes('Administrator');

  const [open, setOpen] = useState(false);
  const [covered, setCovered] = useState(coveredDefault);
  const [drifted, setDrifted] = useState(driftedDefault);
  const [changedCount, setChangedCount] = useState(null);
  const debounceRef = useRef(null);

  const isDefault =
    Math.abs(covered - coveredDefault) < 0.001 &&
    Math.abs(drifted - driftedDefault) < 0.001;

  const triggerReclassify = useCallback(
    (c, d) => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onReclassify(c, d).then((result) => {
          setChangedCount(result?.changed_count ?? null);
        });
      }, 300);
    },
    [onReclassify]
  );

  const handleCoveredChange = (e) => {
    if (!isQALead) return;
    const val = parseFloat(e.target.value);
    // covered must stay below drifted
    if (val >= drifted - 0.01) return;
    setCovered(val);
    triggerReclassify(val, drifted);
  };

  const handleDriftedChange = (e) => {
    if (!isQALead) return;
    const val = parseFloat(e.target.value);
    // drifted must stay above covered
    if (val <= covered + 0.01) return;
    setDrifted(val);
    triggerReclassify(covered, val);
  };

  const handleReset = () => {
    if (!isQALead) return;
    setCovered(coveredDefault);
    setDrifted(driftedDefault);
    setChangedCount(null);
    onReclassify(coveredDefault, driftedDefault);
  };

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  return (
    <div className="sensitivity-panel" id="sensitivity-panel">
      {/* Collapsible Header */}
      <div
        className="sensitivity-panel-header"
        onClick={() => setOpen((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setOpen((v) => !v)}
        id="sensitivity-panel-toggle"
      >
        <div className="sensitivity-panel-header-left">
          <SlidersHorizontal size={15} color="var(--brand)" />
          <span className="sensitivity-panel-title">Sensitivity Thresholds</span>
          {!isQALead && (
            <span className="sensitivity-lock-badge">
              <Lock size={10} /> Locked
            </span>
          )}
          {changedCount != null && changedCount > 0 && (
            <span className="sensitivity-change-badge" id="reclassify-change-count">
              <Sparkles size={12} />
              {changedCount} {changedCount === 1 ? 'entry' : 'entries'} would change
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
          {!isDefault && isQALead && (
            <button
              className="btn-ghost-sm"
              onClick={(e) => { e.stopPropagation(); handleReset(); }}
              id="sensitivity-reset-btn"
            >
              Reset
            </button>
          )}
          <span className={`sensitivity-panel-chevron${open ? ' open' : ''}`}>
            <ChevronDown size={15} />
          </span>
        </div>
      </div>

      {/* Collapsible Body */}
      {open && (
        <div className="sensitivity-panel-body">
          <div className="sensitivity-sliders">
            {/* Covered threshold */}
            <div className="sensitivity-slider-group">
              <div className="sensitivity-slider-label">
                <span>Covered threshold <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>(risk &lt; this → Covered)</span></span>
                <strong style={{ color: 'var(--covered)' }}>{(covered * 100).toFixed(0)}%</strong>
              </div>
              <input
                type="range"
                className="sensitivity-slider sensitivity-slider--covered"
                id="sensitivity-slider-covered"
                min="0"
                max="1"
                step="0.01"
                value={covered}
                onChange={handleCoveredChange}
                disabled={loading || !isQALead}
                title={!isQALead ? 'Requires QA Lead permissions' : 'Adjust covered threshold'}
              />
            </div>

            {/* Drifted threshold */}
            <div className="sensitivity-slider-group">
              <div className="sensitivity-slider-label">
                <span>Drifted threshold <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>(risk &gt; this → Drifted)</span></span>
                <strong style={{ color: 'var(--drifted)' }}>{(drifted * 100).toFixed(0)}%</strong>
              </div>
              <input
                type="range"
                className="sensitivity-slider sensitivity-slider--drifted"
                id="sensitivity-slider-drifted"
                min="0"
                max="1"
                step="0.01"
                value={drifted}
                onChange={handleDriftedChange}
                disabled={loading || !isQALead}
                title={!isQALead ? 'Requires QA Lead permissions' : 'Adjust drifted threshold'}
              />
            </div>

            {/* Threshold preview bar — left-to-right: Covered → Partial → Drifted */}
            <div>
              <div className="sensitivity-slider-label">
                <span>Zone preview</span>
              </div>
              <div className="sensitivity-preview-bar">
                <div
                  style={{
                    width: `${covered * 100}%`,
                    background: 'var(--covered-bg)',
                    color: 'var(--covered)',
                    borderRight: '2px solid var(--covered)',
                  }}
                >
                  C
                </div>
                <div
                  style={{
                    flex: 1,
                    background: 'var(--partial-bg)',
                    color: 'var(--partial)',
                  }}
                >
                  P
                </div>
                <div
                  style={{
                    width: `${(1 - drifted) * 100}%`,
                    background: 'var(--drifted-bg)',
                    color: 'var(--drifted)',
                    borderLeft: '2px solid var(--drifted)',
                  }}
                >
                  D
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
