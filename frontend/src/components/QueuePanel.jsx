import React from 'react';
import { Database, Server } from 'lucide-react';

export function QueuePanel({ pendingCount }) {
  const pending = pendingCount || 0;

  return (
    <div className="panel" id="section-queue">
      <div className="panel-header">
        <h2>Redis Stream Broker</h2>
        <span className="pill-badge green">Multi-Consumer Stream</span>
      </div>

      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '6px', fontSize: '11px', marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Database size={13} color="#2563eb" /> Stream Key: <code>ledger:work_stream</code>
          </span>
          <span style={{ fontSize: '10px', background: '#dbeafe', color: '#1e40af', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
            Consumer Group: ledger_workers
          </span>
        </div>
      </div>

      <div className="metric-list">
        <div className="metric-row">
          <span>Stream Queue Depth</span>
          <strong>{pending} pending</strong>
        </div>
        <div className="metric-row">
          <span>Active Consumers</span>
          <strong style={{ color: '#16a34a' }}>3 Workers (W1, W2, W3)</strong>
        </div>
        <div className="metric-row">
          <span>Max Buffer Capacity</span>
          <strong>1,000 Messages</strong>
        </div>
        <div className="metric-row">
          <span>Message Schema Version</span>
          <strong style={{ fontFamily: 'JetBrains Mono, monospace' }}>v1.0 Validated</strong>
        </div>
      </div>
    </div>
  );
}
