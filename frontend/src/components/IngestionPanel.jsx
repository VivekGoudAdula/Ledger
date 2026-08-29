import React from 'react';
import { FileCode } from 'lucide-react';

export function IngestionPanel({ ingressRate, totalIngress, recentEvents }) {
  const latestEvent = recentEvents && recentEvents.length > 0 ? recentEvents[0] : null;

  return (
    <div className="panel" id="section-ingestion">
      <div className="panel-header">
        <h2>Ingestion Subsystem</h2>
        <span className="pill-badge green">SHA-256 Fingerprinted</span>
      </div>

      <div className="metric-list" style={{ marginBottom: '14px' }}>
        <div className="metric-row">
          <span>Ingress Rate</span>
          <strong>{ingressRate > 0 ? `${ingressRate.toFixed(1)} /s` : '0 /s'}</strong>
        </div>
        <div className="metric-row">
          <span>Total Received</span>
          <strong>{totalIngress ?? 0}</strong>
        </div>
        <div className="metric-row">
          <span>Payload Limit</span>
          <strong style={{ color: '#2563eb' }}>2.0 MB Max</strong>
        </div>
        <div className="metric-row">
          <span>Normalization</span>
          <strong className="text-green">Validated</strong>
        </div>
      </div>

      <div style={{ background: '#f5f5f4', border: '1px solid #e7e5e4', padding: '12px', borderRadius: '8px', fontSize: '12px' }}>
        <div style={{ fontWeight: 700, color: '#0c0a09', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FileCode size={14} color="#2563eb" /> Latest Canonical Event Preview
        </div>
        {latestEvent ? (
          <div style={{ fontFamily: 'JetBrains Mono, monospace', color: '#0c0a09', lineHeight: '1.5' }}>
            <div><strong>ID:</strong> {latestEvent.event_id || 'evt_canonical_01'}</div>
            <div><strong>Type:</strong> {latestEvent.event_type} ({latestEvent.source})</div>
            <div><strong>Tenant:</strong> {latestEvent.tenant_id}</div>
          </div>
        ) : (
          <div style={{ color: '#57534e' }}>Waiting for canonical signal payloads...</div>
        )}
      </div>
    </div>
  );
}
