import { useState, useCallback } from 'react';
import StatusBadge from './StatusBadge';

/**
 * ScoreCell — renders a score value with a mini progress bar.
 */
function ScoreCell({ value }) {
  if (value == null) return <span className="cell-score" style={{ color: 'var(--text-tertiary)' }}>—</span>;

  const pct = Math.round(value * 100);
  const fillClass = pct >= 75 ? 'high' : pct >= 40 ? 'mid' : 'low';

  return (
    <span className="cell-score">
      <span className="score-bar">
        <span className="score-bar__track">
          <span
            className={`score-bar__fill score-bar__fill--${fillClass}`}
            style={{ width: `${pct}%` }}
          />
        </span>
        {(value * 100).toFixed(1)}%
      </span>
    </span>
  );
}

const COLUMNS = [
  { key: 'requirement_external_id', label: 'Req ID', sortable: false },
  { key: 'requirement_title', label: 'Requirement', sortable: false },
  { key: 'test_function_name', label: 'Test Function', sortable: false },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'risk_score', label: 'Risk', sortable: true },
  { key: 'semantic_score', label: 'Semantic', sortable: true },
  { key: 'structural_score', label: 'Structural', sortable: true },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'actions', label: 'RBAC ACTION', sortable: false },
];

/**
 * MatrixTable — sortable, filterable RTM table with pagination.
 */
export default function MatrixTable({
  rows,
  total,
  page,
  pageSize,
  sort,
  order,
  statusFilter,
  search,
  reclassifiedMap,
  overrideMap = {},
  currentUser,
  onOverrideRisk,
  loading,
  onSort,
  onFilter,
  onSearch,
  onPageChange,
  onRowClick,
}) {
  const [searchInput, setSearchInput] = useState(search || '');

  const handleOverrideClick = (row) => {
    const currentVal = overrideMap?.[row.id] ?? row.risk_score ?? 0.5;
    const input = window.prompt(
      `[RBAC Security Check: QA Lead Authorized]\n\nEnter overridden risk score (0.0 to 1.0) for ${row.requirement_external_id}:`,
      String(currentVal)
    );
    if (input !== null) {
      const parsed = parseFloat(input);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
        onOverrideRisk?.(row.id, parsed);
      } else {
        alert('Invalid score. Please enter a numerical value between 0.0 and 1.0.');
      }
    }
  };

  const handleSearchKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter') onSearch(searchInput);
    },
    [searchInput, onSearch]
  );

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getNewStatus = (id) => reclassifiedMap?.[id];

  return (
    <div className="glass-card" id="matrix-table-container">
      {/* Controls */}
      <div className="matrix-controls" style={{ padding: 'var(--space-md) var(--space-md) 0' }}>
        <div className="matrix-search">
          <span className="matrix-search__icon">🔍</span>
          <input
            id="matrix-search-input"
            className="matrix-search__input"
            type="text"
            placeholder="Search requirements..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            onBlur={() => onSearch(searchInput)}
          />
        </div>

        <div className="matrix-filter-group" id="status-filter-group">
          {['All', 'Covered', 'Partial', 'Drifted'].map((f) => (
            <button
              key={f}
              className={`matrix-filter-btn${(f === 'All' && !statusFilter) || statusFilter === f ? ' active' : ''}`}
              onClick={() => onFilter(f === 'All' ? null : f)}
              id={`filter-btn-${f.toLowerCase()}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="matrix-table-wrapper">
        <table className="matrix-table" id="matrix-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={col.sortable ? () => onSort(col.key) : undefined}
                  style={!col.sortable ? { cursor: 'default' } : undefined}
                >
                  {col.label}
                  {col.sortable && (
                    <span className={`th-sort-indicator${sort === col.key ? ' active' : ''}`}>
                      {sort === col.key ? (order === 'asc' ? '▲' : '▼') : '↕'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={`skel-${i}`}>
                  {COLUMNS.map((col) => (
                    <td key={col.key}>
                      <div className="skeleton" style={{ width: '70%', height: 14 }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length}>
                  <div className="matrix-empty">
                    <div className="matrix-empty__icon">📋</div>
                    <div>No traceability entries found</div>
                    <div style={{ fontSize: 'var(--text-xs)', marginTop: 8 }}>
                      Use the Simulate button to create demo data
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const newStatus = getNewStatus(row.id);
                const displayStatus = newStatus || row.status;
                const changed = newStatus && newStatus !== row.status;
                const effectiveRiskScore =
                  overrideMap?.[row.id] != null ? overrideMap[row.id] : row.risk_score;
                const isOverridden = overrideMap?.[row.id] != null;
                const isQALead =
                  currentUser?.role?.includes('QA Lead') ||
                  currentUser?.role?.includes('Administrator');

                return (
                  <tr key={row.id} onClick={() => onRowClick(row)} id={`row-${row.id}`}>
                    <td className="cell-id">{row.requirement_external_id}</td>
                    <td className="cell-title" title={row.requirement_title}>
                      {row.requirement_title}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                      {row.test_function_name}
                    </td>
                    <td>
                      <StatusBadge status={displayStatus} changed={changed} />
                    </td>
                    <td>
                      <ScoreCell value={effectiveRiskScore} />
                      {isOverridden && (
                        <span
                          style={{
                            display: 'block',
                            fontSize: '10px',
                            color: 'var(--accent-blue, #58a6ff)',
                            marginTop: '2px',
                          }}
                        >
                          Manual Override
                        </span>
                      )}
                    </td>
                    <td><ScoreCell value={row.semantic_score} /></td>
                    <td><ScoreCell value={row.structural_score} /></td>
                    <td><ScoreCell value={row.confidence} /></td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {/* RBAC Rule 2: Override button disabled for developers */}
                      <button
                        disabled={!isQALead}
                        title={!isQALead ? 'Requires QA Lead permissions to override' : 'Override risk score'}
                        className="pagination-btn"
                        style={!isQALead ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
                        onClick={isQALead ? () => handleOverrideClick(row) : undefined}
                      >
                        {isQALead ? 'Override' : 'Locked'}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="matrix-pagination" id="matrix-pagination">
          <span>
            Showing {Math.min((page - 1) * pageSize + 1, total)}–{Math.min(page * pageSize, total)} of {total}
          </span>
          <div className="matrix-pagination__buttons">
            <button
              className="pagination-btn"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              id="pagination-prev"
            >
              ← Prev
            </button>
            <button
              className="pagination-btn"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              id="pagination-next"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
