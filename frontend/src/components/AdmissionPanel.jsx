import React from 'react';

export function AdmissionPanel({ data }) {
  const capacity = data?.processing_capacity_sec ?? 100.0;
  const breakdown = data?.admission_breakdown || {};
  const queuePending = data?.queue_pending_count || 0;
  const availableCompute = Math.max(0.0, capacity - (queuePending * 0.25)).toFixed(1);

  return (
    <div className="panel" id="section-admission">
      <div className="panel-header">
        <h2>Admission Control</h2>
        <span className="pill-badge green">Deterministic Scheduler</span>
      </div>

      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>Target Capacity</div>
          <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>{capacity.toFixed(1)}/s</div>
        </div>
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>Available Compute</div>
          <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#16a34a' }}>{availableCompute}/s</div>
        </div>
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>Tenant Quota</div>
          <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#2563eb' }}>50 Units</div>
        </div>
      </div>

      <div className="metric-list">
        <div className="metric-row">
          <span>Admitted (High Value)</span>
          <strong className="text-green">{breakdown.admitted_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Deferred (Backpressure)</span>
          <strong className="text-amber">{breakdown.deferred_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Shed (Low Value Dropped)</span>
          <strong className="text-red">{breakdown.shed_count ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Aging Starvation Guard</span>
          <strong style={{ color: '#2563eb' }}>Active (+0.001/s)</strong>
        </div>
      </div>
    </div>
  );
}
