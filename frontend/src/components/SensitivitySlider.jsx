import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * SensitivitySlider — dual-slider panel for live threshold reclassification.
 *
 * Adjusts covered_threshold and drifted_threshold, calls the reclassify API,
 * and reports changed entries back to the parent via onReclassify.
 */
export default function SensitivitySlider({
  coveredDefault = 0.75,
  driftedDefault = 0.4,
  onReclassify,
  loading = false,
}) {
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
    const val = parseFloat(e.target.value);
    if (val <= drifted + 0.01) return;
    setCovered(val);
    triggerReclassify(val, drifted);
  };

  const handleDriftedChange = (e) => {
    const val = parseFloat(e.target.value);
    if (val >= covered - 0.01) return;
    setDrifted(val);
    triggerReclassify(covered, val);
  };

  const handleReset = () => {
    setCovered(coveredDefault);
    setDrifted(driftedDefault);
    setChangedCount(null);
    onReclassify(coveredDefault, driftedDefault);
  };

  // Cleanup debounce on unmount
  useEffect(() => () => clearTimeout(debounceRef.current), []);

  return (
    <div className="glass-card sensitivity-panel" id="sensitivity-panel">
      <div className="sensitivity-header">
        <div className="sensitivity-title">
          <span className="sensitivity-title__icon">⚙️</span>
          Sensitivity Thresholds
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          {changedCount != null && changedCount > 0 && (
            <div className="sensitivity-change-count" id="reclassify-change-count">
              <span>✦</span>
              {changedCount} {changedCount === 1 ? 'entry' : 'entries'} would change
            </div>
          )}
          {!isDefault && (
            <button
              className="sensitivity-reset-btn"
              onClick={handleReset}
              id="sensitivity-reset-btn"
            >
              Reset to defaults
            </button>
          )}
        </div>
      </div>

      <div className="sensitivity-sliders">
        {/* Covered threshold */}
        <div className="sensitivity-slider-group">
          <div className="sensitivity-slider-label">
            <span>
              Covered threshold{' '}
              <span style={{ color: 'var(--status-covered)', fontSize: 'var(--text-xs)' }}>
                (risk &gt; this → Covered)
              </span>
            </span>
            <span className="sensitivity-slider-value" style={{ color: 'var(--status-covered)' }}>
              {(covered * 100).toFixed(0)}%
            </span>
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
            disabled={loading}
          />
        </div>

        {/* Drifted threshold */}
        <div className="sensitivity-slider-group">
          <div className="sensitivity-slider-label">
            <span>
              Drifted threshold{' '}
              <span style={{ color: 'var(--status-drifted)', fontSize: 'var(--text-xs)' }}>
                (risk &lt; this → Drifted)
              </span>
            </span>
            <span className="sensitivity-slider-value" style={{ color: 'var(--status-drifted)' }}>
              {(drifted * 100).toFixed(0)}%
            </span>
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
            disabled={loading}
          />
        </div>

        {/* Threshold visualization bar */}
        <div style={{ flex: '0 0 auto', minWidth: 140, paddingTop: 8 }}>
          <div className="sensitivity-slider-label">
            <span>Preview</span>
          </div>
          <div
            style={{
              height: 28,
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              display: 'flex',
              border: '1px solid var(--border-subtle)',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
            }}
          >
            <div
              style={{
                width: `${drifted * 100}%`,
                background: 'var(--status-drifted-bg)',
                color: 'var(--status-drifted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRight: '2px solid var(--status-drifted)',
                transition: 'width var(--transition-base)',
              }}
            >
              D
            </div>
            <div
              style={{
                flex: 1,
                background: 'var(--status-partial-bg)',
                color: 'var(--status-partial)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'width var(--transition-base)',
              }}
            >
              P
            </div>
            <div
              style={{
                width: `${(1 - covered) * 100}%`,
                background: 'var(--status-covered-bg)',
                color: 'var(--status-covered)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderLeft: '2px solid var(--status-covered)',
                transition: 'width var(--transition-base)',
              }}
            >
              C
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
