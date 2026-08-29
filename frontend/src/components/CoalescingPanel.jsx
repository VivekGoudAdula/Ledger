import React from 'react';
import { Layers, GitMerge } from 'lucide-react';

export function CoalescingPanel({ totalIngress }) {
  const total = totalIngress || 15;
  const logicalWorkItems = Math.max(1, Math.ceil(total * 0.4));
  const coalescedCount = total - logicalWorkItems;
  const reductionPct = total > 0 ? ((coalescedCount / total) * 100).toFixed(1) : '0.0';

  return (
    <div className="panel" id="section-coalescing">
      <div className="panel-header">
        <h2>Event Coalescing</h2>
        <span className="pill-badge green">5-Min Sliding Window</span>
      </div>

      <div className="metric-list" style={{ marginBottom: '12px' }}>
        <div className="metric-row">
          <span>Signals Received</span>
          <strong>{total}</strong>
        </div>
        <div className="metric-row">
          <span>Logical Work Items</span>
          <strong style={{ color: '#2563eb' }}>{logicalWorkItems}</strong>
        </div>
        <div className="metric-row">
          <span>Coalesced Signals</span>
          <strong className="text-green">{coalescedCount}</strong>
        </div>
        <div className="metric-row">
          <span>Noise Reduction</span>
          <strong className="text-green">{reductionPct}%</strong>
        </div>
      </div>

      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px 12px', borderRadius: '6px', fontSize: '11px' }}>
        <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <GitMerge size={13} color="#2563eb" /> Active Coalesced Incident Group
        </div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', color: '#0f172a', lineHeight: '1.4' }}>
          <div style={{ color: '#2563eb', fontWeight: 600 }}>incident_database_outage</div>
          <div style={{ color: '#64748b', paddingLeft: '8px' }}>├── evt_github_db_fail_01</div>
          <div style={{ color: '#64748b', paddingLeft: '8px' }}>├── evt_status_db_degraded_02</div>
          <div style={{ color: '#64748b', paddingLeft: '8px' }}>└── evt_infra_cpu_spike_03</div>
        </div>
      </div>
    </div>
  );
}
