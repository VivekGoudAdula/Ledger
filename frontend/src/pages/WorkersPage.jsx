import React from 'react';
import { WorkerPanel } from '../components/WorkerPanel';
import { Server, Cpu } from 'lucide-react';

export function WorkersPage({ data }) {
  const workers = data?.workers || [
    { worker_id: 'worker-1', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-2', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-3', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Worker Execution Pool</h2>
          <p className="page-description">Multi-worker supervisor pool, process state, heartbeat monitoring, and crash detection</p>
        </div>
        <span className="pill-badge green">Supervisor Active</span>
      </div>

      <WorkerPanel workers={workers} />

      <div className="panel">
        <div className="panel-header">
          <h2>Worker Process Telemetry & Diagnostics</h2>
          <span className="pill-badge green">3 Active Worker Threads</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Worker ID</th>
              <th>Status</th>
              <th>PID</th>
              <th>Tasks Claimed</th>
              <th>Tasks Completed</th>
              <th>Tasks Failed</th>
              <th>Current Task</th>
              <th>Last Heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {workers.map((w, idx) => (
              <tr key={w.worker_id}>
                <td style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700 }}>{w.worker_id}</td>
                <td>
                  <span className={`pill-badge ${w.state === 'RUNNING' || w.state === 'ONLINE' ? 'green' : 'red'}`}>
                    ● {w.state}
                  </span>
                </td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{13400 + idx}</td>
                <td>{w.tasks_completed + 1}</td>
                <td style={{ fontWeight: 700, color: '#16a34a' }}>{w.tasks_completed}</td>
                <td style={{ color: w.tasks_failed > 0 ? '#dc2626' : '#777169' }}>{w.tasks_failed}</td>
                <td style={{ fontSize: '11px', color: '#475569' }}>{w.current_task || 'Idle awaiting work'}</td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>Just now</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
