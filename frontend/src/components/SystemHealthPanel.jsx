import React from 'react';

export function SystemHealthPanel({ systemStatus }) {
  const isHealthy = systemStatus !== 'OVERLOADED' && systemStatus !== 'DOWN';

  const subsystems = [
    { name: 'Ingestion Layer', status: 'HEALTHY' },
    { name: 'Event Coalescing', status: 'HEALTHY' },
    { name: 'Value Estimator', status: 'HEALTHY' },
    { name: 'Admission Control', status: isHealthy ? 'HEALTHY' : 'DEGRADED' },
    { name: 'Stream Queue Broker', status: 'HEALTHY' },
    { name: 'Worker Supervisor', status: 'HEALTHY' },
    { name: 'Database SQLite WAL', status: 'HEALTHY' },
    { name: 'Stale Claim Recovery', status: 'HEALTHY' },
  ];

  return (
    <div className="panel" id="section-health">
      <div className="panel-header">
        <h2>System Subsystem Health</h2>
        <span className={`pill-badge ${isHealthy ? 'green' : 'amber'}`}>
          ● {systemStatus || 'HEALTHY'}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
        {subsystems.map((sub, idx) => (
          <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '4px', fontSize: '11px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: '#334155' }}>{sub.name}</span>
            <span className={`pill-badge ${sub.status === 'HEALTHY' ? 'green' : 'amber'}`} style={{ fontSize: '10px' }}>
              ● {sub.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
