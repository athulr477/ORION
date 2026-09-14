import { useEffect, useState } from 'react';

/**
 * AnimatedCounter — counts up from 0 to `value` on mount/change.
 */
function AnimatedCounter({ value, duration = 600 }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value == null) return;
    const startTime = performance.now();
    const step = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setDisplay(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [value, duration]);

  return <span className="animate-in">{display}</span>;
}

/**
 * StatsBar — four summary stat cards at the top of the dashboard.
 */
export default function StatsBar({ stats, loading }) {
  if (loading) {
    return (
      <div className="stats-bar" id="stats-bar">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="glass-card stat-card">
            <div className="skeleton" style={{ width: 80, height: 12, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: 60, height: 32 }} />
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: 'Total Entries',
      value: stats?.total_entries ?? 0,
      detail: `${stats?.total_requirements ?? 0} reqs · ${stats?.total_test_cases ?? 0} tests`,
      variant: 'total',
    },
    {
      label: 'Covered',
      value: stats?.covered_count ?? 0,
      detail: stats?.avg_risk_score != null ? `avg risk ${(stats.avg_risk_score * 100).toFixed(1)}%` : '—',
      variant: 'covered',
    },
    {
      label: 'Partial',
      value: stats?.partial_count ?? 0,
      detail: stats?.avg_semantic_score != null ? `avg semantic ${(stats.avg_semantic_score * 100).toFixed(1)}%` : '—',
      variant: 'partial',
    },
    {
      label: 'Drifted',
      value: stats?.drifted_count ?? 0,
      detail: stats?.avg_structural_score != null ? `avg structural ${(stats.avg_structural_score * 100).toFixed(1)}%` : '—',
      variant: 'drifted',
    },
  ];

  return (
    <div className="stats-bar" id="stats-bar">
      {cards.map((c) => (
        <div key={c.variant} className={`glass-card stat-card stat-card--${c.variant}`} id={`stat-${c.variant}`}>
          <div className="stat-card__label">{c.label}</div>
          <div className="stat-card__value">
            <AnimatedCounter value={c.value} />
          </div>
          <div className="stat-card__detail">{c.detail}</div>
        </div>
      ))}
    </div>
  );
}
