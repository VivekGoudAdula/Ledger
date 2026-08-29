import React from 'react';
import { ShieldCheck, Lock } from 'lucide-react';

export function IdempotencyPanel({ idempotency }) {
  const idem = idempotency || {};
  const hasHits = (idem.hits_count || 0) > 0;

  return (
    <div className="panel" id="section-idempotency">
      <div className="panel-header">
        <h2>Idempotency & Checkpoint Store</h2>
        <span className="pill-badge green">SQLite WAL Guard</span>
      </div>

      {hasHits && (
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '6px 10px', borderRadius: '4px', fontSize: '11px', color: '#166534', fontWeight: 600, marginBottom: '10px' }}>
          DUPLICATE DETECTED → IDEMPOTENCY HIT → SIDE EFFECT PREVENTED
        </div>
      )}

      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '6px', fontSize: '11px', marginBottom: '10px' }}>
        <span style={{ color: '#64748b', display: 'block', marginBottom: '2px' }}>Logical Key Constraint:</span>
        <code style={{ fontSize: '11px', color: '#2563eb', fontWeight: 700 }}>tenant_id : work_item_id : action_type</code>
      </div>

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
          <strong className={hasHits ? 'text-green' : ''}>{idem.hits_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Duplicates Prevented</span>
          <strong>{idem.duplicates_prevented_count ?? 0}</strong>
        </div>
      </div>
    </div>
  );
}
