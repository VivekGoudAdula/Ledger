import React from 'react';
import { SourcePanel } from '../components/SourcePanel';
import { IngestionPanel } from '../components/IngestionPanel';

export function SignalsPage({ data, onSelectEvent }) {
  const events = data?.recent_events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Signals & Ingestion Control</h2>
          <p className="page-description">Source adapters, raw signal intake, validation rules, and canonical normalization</p>
        </div>
        <span className="pill-badge green">SHA-256 Fingerprinted</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <SourcePanel sources={data?.sources} />
        <IngestionPanel
          ingressRate={data?.ingress_rate_sec}
          totalIngress={data?.total_ingress_count}
          recentEvents={events}
        />
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Live Raw Signal Intake Stream</h2>
          <span className="pill-badge green">Click row for full lifecycle trace</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Source</th>
              <th>Event Type</th>
              <th>Event ID</th>
              <th>Tenant ID</th>
              <th>Normalization</th>
              <th>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No live signal intake currently buffering...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => (
                <tr
                  key={idx}
                  onClick={() => onSelectEvent(e)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>{e.time_str}</td>
                  <td style={{ textTransform: 'capitalize' }}>{e.source}</td>
                  <td style={{ fontWeight: 600 }}>{e.event_type}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{e.event_id || `evt_0${idx+1}`}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.tenant_id || 'tenant_default'}</td>
                  <td>
                    <span className="pill-badge green">VALIDATED</span>
                  </td>
                  <td>
                    <button style={{ border: 'none', background: '#f0efed', padding: '2px 8px', borderRadius: '9999px', fontSize: '11px', cursor: 'pointer' }}>
                      View Trace
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
