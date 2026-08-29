import React from 'react';

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

      <div className="worker-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {list.map((w) => {
          const isRunning = w.state === 'RUNNING' || w.state === 'ONLINE';
          const isFailed = w.state === 'FAILED';
          const badgeClass = isRunning ? 'green' : isFailed ? 'red' : 'amber';

          return (
            <div
              className="worker-card"
              key={w.worker_id}
              style={{
                border: isFailed ? '1px solid #fecaca' : '1px solid #e7e5e4',
                background: isFailed ? '#fef2f2' : '#f5f5f4',
                padding: '12px',
                borderRadius: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span className="worker-name" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', fontWeight: 700, color: '#0c0a09' }}>
                  {w.worker_id}
                </span>
                <span className={`pill-badge ${badgeClass}`}>● {w.state}</span>
              </div>

              <div style={{ fontSize: '12px', color: '#57534e', marginTop: '4px' }}>
                Jobs completed: <strong style={{ color: '#0c0a09', fontFamily: 'JetBrains Mono, monospace', marginLeft: '4px' }}>{w.tasks_completed ?? 0}</strong>
              </div>
              {w.tasks_failed > 0 && (
                <div style={{ fontSize: '12px', color: '#dc2626', marginTop: '2px' }}>
                  Jobs failed: <strong>{w.tasks_failed}</strong>
                </div>
              )}
              <div style={{ fontSize: '11px', color: '#78716c', marginTop: '6px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                Task: {w.current_task || 'Processing admitted signals'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
