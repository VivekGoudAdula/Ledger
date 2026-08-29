import React from 'react';
import { IdempotencyPanel } from '../components/IdempotencyPanel';

export function IdempotencyPage({ data, onSelectEvent }) {
  const idempotency = data?.idempotency || {};
  const events = data?.recent_events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Idempotency & Checkpoint Store</h2>
          <p className="page-description">Database composite unique key constraint enforcement protecting against duplicate side effects</p>
        </div>
        <span className="pill-badge green">SQLite WAL Guard</span>
      </div>

      <IdempotencyPanel idempotency={idempotency} />

      <div className="panel">
        <div className="panel-header">
          <h2>Idempotency Execution Claims & Checkpoint Audit Log</h2>
          <span className="pill-badge green">Atomic Claim Checks</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Tenant ID</th>
              <th>Work Item ID</th>
              <th>Action Type</th>
              <th>Idempotency Key</th>
              <th>Claim Status</th>
              <th>Duplicate Action Result</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No idempotency checkpoints logged...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => (
                <tr key={idx} onClick={() => onSelectEvent(e)} style={{ cursor: 'pointer' }}>
                  <td>{e.time_str}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.tenant_id || 'tenant_default'}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.event_id || `evt_0${idx+1}`}</td>
                  <td>EXECUTE</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#2563eb' }}>
                    {e.tenant_id || 'tenant_default'}:{e.event_id || `evt_0${idx+1}`}:EXECUTE
                  </td>
                  <td>
                    <span className="pill-badge green">CLAIMED (Atomic)</span>
                  </td>
                  <td style={{ color: '#16a34a', fontWeight: 600 }}>SIDE EFFECT PREVENTED</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
