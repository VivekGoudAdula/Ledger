import React from 'react';
import { RecoveryPanel } from '../components/RecoveryPanel';
import { RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';

export function RecoveryPage({ data }) {
  const recovery = data?.recovery || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Failure Recovery & Reclaim Engine</h2>
          <p className="page-description">Automatic detection of crashed workers (over 10s idle threshold), message reclaim, and backoff retry</p>
        </div>
        <span className="pill-badge green">Stale Claim Manager</span>
      </div>

      <RecoveryPanel recovery={recovery} />

      <div className="panel">
        <div className="panel-header">
          <h2>Stale Task Recovery Timeline & Lifecycle</h2>
          <span className="pill-badge green">Live Recovery Stream</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ background: '#f8fafc', border: '1px solid #e7e5e4', borderRadius: '8px', padding: '14px' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#777169', textTransform: 'uppercase', marginBottom: '8px' }}>
              Fault-Tolerance Invariant Lifecycle
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '12px', fontWeight: 700 }}>
              <span className="pill-badge red">WORKER FAILED</span>
              <span>→</span>
              <span className="pill-badge amber">UNACKNOWLEDGED PENDING</span>
              <span>→</span>
              <span className="pill-badge amber">STALE (OVER 10s IDLE)</span>
              <span>→</span>
              <span className="pill-badge green">RECLAIMED & REASSIGNED</span>
              <span>→</span>
              <span className="pill-badge green">TASK RECOVERED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
