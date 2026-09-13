/**
 * StatusBadge — Covered / Partial / Drifted pill badge with animated dot.
 */
export default function StatusBadge({ status, changed = false }) {
  const normalized = (status || '').toLowerCase();
  const variant = ['covered', 'partial', 'drifted'].includes(normalized)
    ? normalized
    : 'unknown';
  const label = status || '—';

  return (
    <span
      className={`status-badge status-badge--${variant}${changed ? ' status-badge--changed' : ''}`}
      id={`status-badge-${variant}`}
    >
      <span className="status-badge__dot" />
      {label}
    </span>
  );
}
