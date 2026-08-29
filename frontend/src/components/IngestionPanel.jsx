import React from 'react';
import { ShieldCheck, FileCode } from 'lucide-react';

export function IngestionPanel({ ingressRate, totalIngress, recentEvents }) {
  const latestEvent = recentEvents && recentEvents.length > 0 ? recentEvents[0] : null;

  return (
    <div className="panel" id="section-ingestion">
      <div className="panel-header">
        <h2>Ingestion Subsystem</h2>
        <span className="pill-badge green">SHA-256 Fingerprinted</span>
      </div>

      <div className="metric-list" style={{ marginBottom: '12px' }}>
        <div className="metric-row">
          <span>Ingress Rate</span>
          <strong>{ingressRate > 0 ? `${ingressRate.toFixed(1)}/s` : '0/s'}</strong>
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

      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px 12px', borderRadius: '6px', fontSize: '11px' }}>
        <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <FileCode size={13} color="#2563eb" /> Latest Canonical Event Preview
        </div>
        {latestEvent ? (
          <div style={{ fontFamily: 'JetBrains Mono, monospace', color: '#0f172a', lineHeight: '1.4' }}>
            <div><strong>ID:</strong> {latestEvent.event_id || 'evt_canonical_01'}</div>
            <div><strong>Type:</strong> {latestEvent.event_type} ({latestEvent.source})</div>
            <div><strong>Tenant:</strong> {latestEvent.tenant_id}</div>
          </div>
        ) : (
          <div style={{ color: '#64748b' }}>Waiting for canonical signal payloads...</div>
        )}
      </div>
    </div>
  );
}
