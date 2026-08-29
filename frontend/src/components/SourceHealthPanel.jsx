import React from 'react';

export function SourceHealthPanel({ sources }) {
  const list = sources || [
    { name: 'GitHub REST API', status: 'UP' },
    { name: 'Public Status Feed', status: 'UP' },
    { name: 'Ledger Telemetry', status: 'UP' },
  ];

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Signal Source Health</h2>
      </div>

      <div className="metric-list">
        {list.map((s, idx) => (
          <div className="metric-row" key={idx}>
            <span>{s.name}</span>
            <span className={`pill-badge ${s.status === 'UP' ? 'green' : 'red'}`}>
              {s.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
