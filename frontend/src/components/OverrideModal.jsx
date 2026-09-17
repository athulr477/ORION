import React, { useState, useEffect } from 'react';
import { X, ShieldAlert } from 'lucide-react';

export default function OverrideModal({ open, onClose, onSave, row }) {
  const [status, setStatus]     = useState('');
  const [rationale, setRationale] = useState('');

  useEffect(() => {
    if (open && row) {
      setStatus(row.status || 'Covered');
      setRationale('');
    }
  }, [open, row]);

  if (!open || !row) return null;

  const handleSave = (e) => {
    e.preventDefault();
    if (!status || !rationale.trim()) return;
    onSave(row.id, status, rationale);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose} id="override-modal-overlay">
      <div
        className="modal-box"
        style={{ maxWidth: 480 }}
        onClick={(e) => e.stopPropagation()}
        id="override-modal"
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="modal-title" style={{ color: 'var(--drifted)' }}>
              <ShieldAlert size={16} />
              Override Risk Score
            </div>
            <div className="modal-subtitle">
              Requirement: <strong style={{ color: 'var(--text-primary)' }}>{row.requirement_external_id}</strong>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} id="override-close-btn" aria-label="Close">
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSave} className="modal-body">
          <div
            style={{
              padding: 'var(--sp-3) var(--sp-4)',
              background: 'var(--drifted-bg)',
              border: '1px solid var(--drifted-border)',
              borderRadius: 'var(--r-md)',
              fontSize: 12.5,
              color: 'var(--drifted)',
              marginBottom: 'var(--sp-5)',
              lineHeight: 1.5,
            }}
          >
            ⚠ Manual overrides are audit-logged and cannot be undone automatically.
            Provide a clear rationale below.
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="override-status">New Status</label>
            <select
              id="override-status"
              className="form-select"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="Covered">Covered</option>
              <option value="Partial">Partial</option>
              <option value="Drifted">Drifted</option>
            </select>
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="override-rationale">
              Audit Rationale <span style={{ color: 'var(--drifted)' }}>*</span>
            </label>
            <textarea
              id="override-rationale"
              className="form-textarea"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="Provide a clear reason for this manual override…"
              required
              rows={4}
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn-danger"
              disabled={!rationale.trim()}
              id="override-save-btn"
            >
              Save Override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
