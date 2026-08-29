import React from 'react';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export function RecoveryPanel({ recovery }) {
  const rec = recovery || {};
  const hasReclaimed = (rec.reclaimed_count || 0) > 0 || (rec.stale_count || 0) > 0;

  return (
    <div className="panel" id="section-recovery">
      <div className="panel-header">
        <h2>Failure Recovery & Reclaim</h2>
        <span className="pill-badge green">Stale Claim Manager</span>
      </div>

      {hasReclaimed && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '6px 10px', borderRadius: '4px', fontSize: '11px', color: '#b45309', fontWeight: 600, marginBottom: '10px' }}>
          WORKER CRASH DETECTED → WORK RECLAIMED → TASK RECOVERED
        </div>
      )}

      <div className="metric-list">
        <div className="metric-row">
          <span>Pending Messages</span>
          <strong>{rec.pending_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Stale Candidates (&gt;10s Idle)</span>
          <strong>{rec.stale_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Reclaimed Count</span>
          <strong className={rec.reclaimed_count > 0 ? 'text-amber' : ''}>{rec.reclaimed_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Recovery Failures</span>
          <strong className={rec.failures_count > 0 ? 'text-red' : ''}>{rec.failures_count ?? 0}</strong>
        </div>
      </div>
    </div>
  );
}
