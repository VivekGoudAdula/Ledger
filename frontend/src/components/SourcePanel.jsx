import React from 'react';

export function SourcePanel({ sources }) {
  const list = sources || [
    { name: 'GitHub REST API', status: 'UP', events_received: 0, last_poll_time: 'Just now' },
    { name: 'Public Status Feed', status: 'UP', events_received: 0, last_poll_time: 'Just now' },
    { name: 'Ledger Telemetry', status: 'UP', events_received: 0, last_poll_time: 'Just now' },
  ];

  return (
    <div className="panel" id="section-sources">
      <div className="panel-header">
        <h2>Signal Sources</h2>
        <span className="pill-badge green">3 Adapters Active</span>
      </div>

      <div className="metric-list">
        {list.map((s, idx) => (
          <div key={idx} style={{ padding: '10px 0', borderBottom: idx < list.length - 1 ? '1px dashed #e7e5e4' : 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#0c0a09' }}>{s.name}</span>
              <span className={`pill-badge ${s.status === 'UP' ? 'green' : 'red'}`}>
                ● {s.status}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#57534e' }}>
              <span>Last poll: {s.last_poll_time || 'Just now'}</span>
              <span>Events: <strong style={{ color: '#0c0a09', fontFamily: 'JetBrains Mono, monospace', marginLeft: '4px' }}>{s.events_received ?? 0}</strong></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
