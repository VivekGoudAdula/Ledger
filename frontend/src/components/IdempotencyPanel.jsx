import React from 'react';

export function IdempotencyPanel({ idempotency }) {
  const idem = idempotency || {};

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Database Idempotency Guard</h2>
      </div>

      {idem.hits_count > 0 && (
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '6px 10px', borderRadius: '4px', fontSize: '11px', color: '#166534', fontWeight: 600, marginBottom: '12px' }}>
          DUPLICATE DETECTED → IDEMPOTENCY HIT → SIDE EFFECT PREVENTED
        </div>
      )}

      <div className="metric-list">
        <div className="metric-row">
          <span>Idempotency Checks</span>
          <strong>{idem.checks_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Atomic Claims</span>
          <strong>{idem.claims_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Duplicate Hits</span>
          <strong className={idem.hits_count > 0 ? 'text-green' : ''}>{idem.hits_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Duplicates Prevented</span>
          <strong>{idem.duplicates_prevented_count ?? 0}</strong>
        </div>
      </div>

      <p style={{ marginTop: '12px', fontSize: '11px', color: '#64748b', lineHeight: '1.4', borderTop: '1px solid #e2e8f0', paddingTop: '8px' }}>
        Database-backed uniqueness protects logical side effects during retries and duplicate delivery.
      </p>
    </div>
  );
}
