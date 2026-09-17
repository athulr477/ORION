import { useState, useCallback, useEffect } from 'react';
import { Search, X, Database, Edit2, Lock } from 'lucide-react';
import StatusBadge from './StatusBadge';
import OverrideModal from './OverrideModal';

/**
 * ScoreCell — renders a score value with a mini progress bar.
 */
function ScoreCell({ value }) {
  if (value == null) return <span style={{ color: 'var(--text-tertiary)' }}>—</span>;

  const pct = Math.round(value * 100);
  const fillClass = pct >= 75 ? 'high' : pct >= 40 ? 'mid' : 'low';

  return (
    <span className="score-cell">
      <span className="score-bar">
        <span className={`score-fill score-fill--${fillClass}`} style={{ width: `${pct}%` }} />
      </span>
      {(value * 100).toFixed(1)}%
    </span>
  );
}

const COLUMNS = [
  { key: 'requirement_external_id', label: 'Req ID',       sortable: false },
  { key: 'requirement_title',       label: 'Requirement',  sortable: false },
  { key: 'test_function_name',      label: 'Test Function', sortable: false },
  { key: 'status',                  label: 'Status',        sortable: true  },
  { key: 'risk_score',              label: 'Risk',          sortable: true  },
  { key: 'semantic_score',          label: 'Semantic',      sortable: true  },
  { key: 'structural_score',        label: 'Structural',    sortable: true  },
  { key: 'confidence',              label: 'Confidence',    sortable: true  },
  { key: 'actions',                 label: 'Action',        sortable: false },
];

/**
 * MatrixTable — sortable, filterable, searchable RTM table with pagination.
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
  const [overrideRow, setOverrideRow] = useState(null);

  // Real-time search with 300ms debounce
  useEffect(() => {
    const t = setTimeout(() => onSearch(searchInput), 300);
    return () => clearTimeout(t);
  }, [searchInput, onSearch]);

  const handleOverrideClick = (row) => setOverrideRow(row);
  const handleOverrideSave = (id, newStatus, rationale) => {
    onOverrideRisk?.(id, newStatus, rationale);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;
  const getNewStatus = (id) => reclassifiedMap?.[id];

  return (
    <div className="matrix-card" id="matrix-table-container">
      {/* Toolbar */}
      <div className="matrix-toolbar">
        {/* Search */}
        <div className="matrix-search">
          <span className="matrix-search__icon"><Search size={14} /></span>
          <input
            id="matrix-search-input"
            className="matrix-search__input"
            type="text"
            placeholder="Search requirements or tests…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <button
              className="matrix-search__clear"
              onClick={() => { setSearchInput(''); onSearch(''); }}
              aria-label="Clear search"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Filter pills */}
        <div className="matrix-filters" id="status-filter-group">
          {['All', 'Covered', 'Partial', 'Drifted'].map((f) => (
            <button
              key={f}
              className={`filter-pill${
                (f === 'All' && !statusFilter) || statusFilter === f
                  ? ' active'
                  : ''
              }${f !== 'All' ? ` pill--${f.toLowerCase()}` : ''}`}
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
                  className={col.sortable ? 'sortable' : ''}
                  onClick={col.sortable ? () => onSort(col.key) : undefined}
                >
                  {col.label}
                  {col.sortable && (
                    <span className={`sort-icon${sort === col.key ? ' active' : ''}`}>
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
                      <div className="skeleton" style={{ width: '70%', height: 13 }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length}>
                  <div className="matrix-empty">
                    <div className="matrix-empty__icon"><Database size={22} /></div>
                    <div className="matrix-empty__title">No Traceability Data Yet</div>
                    <div className="matrix-empty__sub">
                      Get started by importing requirements and test results, or connect
                      an external source like Jira or GitHub.
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const newStatus = getNewStatus(row.id);
                const displayStatus = newStatus || row.status;
                const changed = newStatus && newStatus !== row.status;
                const isOverridden = row.is_manually_overridden || overrideMap?.[row.id];
                const isQALead =
                  currentUser?.role?.includes('QA Lead') ||
                  currentUser?.role?.includes('Administrator');

                return (
                  <tr key={row.id} onClick={() => onRowClick(row)} id={`row-${row.id}`}>
                    <td className="cell-id">{row.requirement_external_id}</td>
                    <td className="cell-title" title={row.requirement_title}>
                      {row.requirement_title}
                    </td>
                    <td className="cell-fn">{row.test_function_name}</td>
                    <td><StatusBadge status={displayStatus} changed={changed} /></td>
                    <td>
                      <ScoreCell value={row.risk_score} />
                      {isOverridden && (
                        <span className="override-label">Manual Override</span>
                      )}
                    </td>
                    <td><ScoreCell value={row.semantic_score} /></td>
                    <td><ScoreCell value={row.structural_score} /></td>
                    <td><ScoreCell value={row.confidence} /></td>
                    <td className="action-cell" onClick={(e) => e.stopPropagation()}>
                      <button
                        disabled={!isQALead}
                        title={
                          !isQALead
                            ? 'Requires QA Lead permissions'
                            : 'Override risk classification'
                        }
                        className="btn-override"
                        onClick={isQALead ? () => handleOverrideClick(row) : undefined}
                      >
                        {isQALead ? (
                          <><Edit2 size={11} /> Override</>
                        ) : (
                          <><Lock size={11} /> Locked</>
                        )}
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
        <div className="matrix-footer" id="matrix-pagination">
          <span>
            Showing {Math.min((page - 1) * pageSize + 1, total)}–
            {Math.min(page * pageSize, total)} of {total}
          </span>
          <div className="pagination-btns">
            <button
              className="btn-page"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              id="pagination-prev"
            >
              ← Prev
            </button>
            <button
              className="btn-page"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              id="pagination-next"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Override Modal */}
      <OverrideModal
        open={!!overrideRow}
        onClose={() => setOverrideRow(null)}
        onSave={handleOverrideSave}
        row={overrideRow}
      />
    </div>
  );
}
