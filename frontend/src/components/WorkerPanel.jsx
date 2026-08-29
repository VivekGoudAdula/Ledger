import React from 'react';
import { Cpu, Server } from 'lucide-react';

export function WorkerPanel({ workers }) {
  const list = workers || [
    { worker_id: 'worker-1', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-2', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-3', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
  ];

  return (
    <div className="panel" id="section-workers">
      <div className="panel-header">
        <h2>Worker Execution Pool</h2>
        <span className="pill-badge green">Supervisor Active</span>
      </div>

      <div className="worker-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
        {list.map((w) => {
          const isRunning = w.state === 'RUNNING' || w.state === 'ONLINE';
          const isFailed = w.state === 'FAILED';
          const badgeClass = isRunning ? 'green' : isFailed ? 'red' : 'amber';

          return (
            <div
              className="worker-card"
              key={w.worker_id}
              style={{
                border: isFailed ? '1px solid #fecaca' : '1px solid #e2e8f0',
                background: isFailed ? '#fef2f2' : '#f8fafc',
                padding: '10px',
                borderRadius: '6px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="worker-name" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{w.worker_id}</span>
                <span className={`pill-badge ${badgeClass}`}>● {w.state}</span>
              </div>

              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                Jobs completed: <strong style={{ color: '#0f172a' }}>{w.tasks_completed ?? 0}</strong>
              </div>
              {w.tasks_failed > 0 && (
                <div style={{ fontSize: '11px', color: '#dc2626' }}>
                  Jobs failed: <strong>{w.tasks_failed}</strong>
                </div>
              )}
              <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                Task: {w.current_task || 'Idle awaiting messages'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
