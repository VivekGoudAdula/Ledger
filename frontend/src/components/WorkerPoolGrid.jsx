import React from 'react';

export function WorkerPoolGrid({ workers }) {
  const list = workers || [];

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Active Worker Execution Pool</h2>
        <span className="pill-badge">Supervisor</span>
      </div>

      <div className="worker-grid">
        {list.length === 0 ? (
          <div className="worker-card">No active workers</div>
        ) : (
          list.map((w) => (
            <div className="worker-card" key={w.worker_id}>
              <span className="worker-name">{w.worker_id}</span>
              <span className={`pill-badge ${w.state === 'RUNNING' ? 'green' : 'amber'}`}>
                {w.state}
              </span>
              <span className="worker-jobs">{w.tasks_completed ?? 0} jobs done</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
