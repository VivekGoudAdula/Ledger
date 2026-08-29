import React from 'react';
import { QueuePanel } from '../components/QueuePanel';

export function QueuePage({ data, onSelectEvent }) {
  const pendingCount = data?.queue_pending_count || 0;
  const events = data?.recent_events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Redis Stream Queue Broker</h2>
          <p className="page-description">Redis Streams message queue telemetry, consumer group state, and message stream buffer</p>
        </div>
        <span className="pill-badge green">Stream Broker Active</span>
      </div>

      <QueuePanel pendingCount={pendingCount} />

      <div className="panel">
        <div className="panel-header">
          <h2>Stream Message Stream Inspection</h2>
          <span className="pill-badge green">ledger:work_stream</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Message ID</th>
              <th>Event ID</th>
              <th>Consumer Group</th>
              <th>Claim Worker</th>
              <th>State</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No messages buffered in Stream Broker...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => (
                <tr key={idx} onClick={() => onSelectEvent(e)} style={{ cursor: 'pointer' }}>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>171923485-{idx+101}-0</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{e.event_id || `evt_0${idx+1}`}</td>
                  <td style={{ fontSize: '12px' }}>ledger_workers</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.worker_id || 'worker-1'}</td>
                  <td>
                    <span className="pill-badge green">{e.status || 'QUEUED'}</span>
                  </td>
                  <td>{e.time_str}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
