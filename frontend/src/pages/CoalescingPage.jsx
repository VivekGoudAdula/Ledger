import React from 'react';
import { CoalescingPanel } from '../components/CoalescingPanel';
import { GitMerge, Layers } from 'lucide-react';

export function CoalescingPage({ data, onSelectEvent }) {
  const total = data?.total_ingress_count || 15;
  const logical = Math.max(1, Math.ceil(total * 0.4));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Event Coalescing Subsystem</h2>
          <p className="page-description">5-minute sliding window incident deduplication, noise reduction, and traceability</p>
        </div>
        <span className="pill-badge green">5-Min Sliding Window</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
        <CoalescingPanel totalIngress={total} />

        <div className="panel">
          <div className="panel-header">
            <h2>Coalescing Invariants</h2>
            <span className="pill-badge green">Deduplication</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e7e5e4', padding: '10px', borderRadius: '6px' }}>
              <div style={{ fontWeight: 700, color: '#0c0a09', marginBottom: '2px' }}>Fingerprint Grouping</div>
              <div style={{ color: '#777169' }}>Signals matching exact SHA-256 fingerprint within 5 minutes are grouped into logical Incidents.</div>
            </div>
            <div style={{ background: '#f8fafc', border: '1px solid #e7e5e4', padding: '10px', borderRadius: '6px' }}>
              <div style={{ fontWeight: 700, color: '#0c0a09', marginBottom: '2px' }}>Preserved Traceability</div>
              <div style={{ color: '#777169' }}>Original event references are retained in the Incident payload so no auditability is lost.</div>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Active Coalesced Incident Groups</h2>
          <span className="pill-badge green">Traceability Preserved</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ border: '1px solid #e7e5e4', borderRadius: '8px', padding: '14px', background: '#ffffff' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 700, color: '#2563eb', fontSize: '14px', fontFamily: 'JetBrains Mono, monospace' }}>
                incident_database_outage
              </span>
              <span className="pill-badge green">3 Signals Grouped → 1 Work Item</span>
            </div>

            <div style={{ fontSize: '12px', color: '#777169', fontFamily: 'JetBrains Mono, monospace', lineHeight: '1.6' }}>
              <div>├── evt_github_db_fail_01 (GitHub REST API — issue_opened)</div>
              <div>├── evt_status_db_degraded_02 (Public Status Feed — service_outage)</div>
              <div>└── evt_infra_cpu_spike_03 (Ledger Telemetry — memory_spike)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
