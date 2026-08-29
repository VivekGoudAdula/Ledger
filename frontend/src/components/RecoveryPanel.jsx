import React from 'react';

export function RecoveryPanel({ recovery }) {
  const rec = recovery || {};

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Failure Recovery & Reclaim</h2>
      </div>

      {(rec.reclaimed_count > 0 || rec.stale_count > 0) && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '6px 10px', borderRadius: '4px', fontSize: '11px', color: '#b45309', fontWeight: 600, marginBottom: '12px' }}>
          WORKER CRASH DETECTED → WORK RECLAIMED → TASK RECOVERED
        </div>
      )}

      <div className="metric-list">
        <div className="metric-row">
          <span>Pending Messages</span>
          <strong>{rec.pending_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Stale Candidates</span>
          <strong>{rec.stale_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Reclaimed Count</span>
          <strong className={rec.reclaimed_count > 0 ? 'text-amber' : ''}>{rec.reclaimed_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Idempotency Hits</span>
          <strong>{rec.already_completed_hits ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Recovery Failures</span>
          <strong className={rec.failures_count > 0 ? 'text-red' : ''}>{rec.failures_count ?? 0}</strong>
        </div>
      </div>
    </div>
  );
}
