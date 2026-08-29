import React, { useState } from 'react';

export function WorkerPanel({ workers }) {
  const [selectedModes, setSelectedModes] = useState({});
  const [actionMessage, setActionMessage] = useState(null);
  const [loadingWorker, setLoadingWorker] = useState(null);

  const list = workers || [
    { worker_id: 'worker-1', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-2', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
    { worker_id: 'worker-3', state: 'RUNNING', tasks_completed: 0, tasks_failed: 0, current_task: 'Processing admitted signals' },
  ];

  const handlePause = async (workerId) => {
    setLoadingWorker(workerId);
    try {
      const res = await fetch(`/api/v1/admin/workers/${workerId}/pause`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Pause failed');
      }
      setActionMessage(`Worker ${workerId} paused successfully.`);
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setLoadingWorker(null);
    }
  };

  const handleResume = async (workerId) => {
    setLoadingWorker(workerId);
    try {
      const res = await fetch(`/api/v1/admin/workers/${workerId}/resume`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Resume failed');
      }
      setActionMessage(`Worker ${workerId} resumed successfully.`);
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setLoadingWorker(null);
    }
  };

  const handleInjectFailure = async (workerId) => {
    const mode = selectedModes[workerId] || 'after_execution_before_ack';
    setLoadingWorker(workerId);
    try {
      const res = await fetch(`/api/v1/admin/workers/${workerId}/inject-failure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ failure_mode: mode, one_shot: true }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failure injection failed');
      }
      setActionMessage(`Injected failure '${mode}' into ${workerId}`);
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setLoadingWorker(null);
    }
  };

  const handleClearFailure = async (workerId) => {
    setLoadingWorker(workerId);
    try {
      const res = await fetch(`/api/v1/admin/workers/${workerId}/clear-failure`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Clear failed');
      }
      setActionMessage(`Cleared failure state for ${workerId}`);
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setLoadingWorker(null);
    }
  };

  return (
    <div className="panel" id="section-workers">
      <div className="panel-header">
        <div>
          <h2>Worker Execution Pool & Real Fault Injection</h2>
          <div style={{ fontSize: '11px', color: '#78716c', marginTop: '2px' }}>
            Real backend control plane operating over active asyncio workers & Redis PEL recovery
          </div>
        </div>
        <span className="pill-badge green">Supervisor Active</span>
      </div>

      {actionMessage && (
        <div style={{ padding: '8px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', fontSize: '12px', color: '#166534', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#166534', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      <div className="worker-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {list.map((w) => {
          const isRunning = w.state === 'RUNNING' || w.state === 'ONLINE';
          const isFailed = w.state === 'FAILED';
          const isPaused = w.state === 'PAUSED';
          const isRecovering = w.state === 'RECOVERING';
          const badgeClass = isRunning ? 'green' : isFailed ? 'red' : isPaused ? 'amber' : isRecovering ? 'amber' : 'gray';
          const currentMode = selectedModes[w.worker_id] || 'after_execution_before_ack';

          return (
            <div
              className="worker-card"
              key={w.worker_id}
              style={{
                border: isFailed ? '1px solid #fecaca' : isPaused ? '1px solid #fde68a' : '1px solid #e7e5e4',
                background: isFailed ? '#fef2f2' : isPaused ? '#fffbeb' : '#f5f5f4',
                padding: '12px',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                justify: 'space-between',
              }}
            >
              <div>
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

              {/* Real Fault Injection Control Unit */}
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #e7e5e4' }}>
                <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: '#78716c', marginBottom: '6px', letterSpacing: '0.5px' }}>
                  Fault Injection Controls
                </div>

                <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                  {isPaused ? (
                    <button
                      onClick={() => handleResume(w.worker_id)}
                      disabled={loadingWorker === w.worker_id}
                      style={{ flex: 1, padding: '4px 8px', fontSize: '11px', fontWeight: 600, background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      ▶ Resume
                    </button>
                  ) : (
                    <button
                      onClick={() => handlePause(w.worker_id)}
                      disabled={loadingWorker === w.worker_id}
                      style={{ flex: 1, padding: '4px 8px', fontSize: '11px', fontWeight: 600, background: '#d97706', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      ⏸ Pause
                    </button>
                  )}
                  <button
                    onClick={() => handleClearFailure(w.worker_id)}
                    disabled={loadingWorker === w.worker_id}
                    style={{ padding: '4px 8px', fontSize: '11px', background: '#e7e5e4', color: '#44403c', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Clear
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <select
                    value={currentMode}
                    onChange={(e) => setSelectedModes({ ...selectedModes, [w.worker_id]: e.target.value })}
                    style={{ fontSize: '11px', padding: '4px 6px', borderRadius: '4px', border: '1px solid #d6d3d1', background: '#fff', color: '#1c1917' }}
                  >
                    <option value="after_execution_before_ack">After Exec / Before ACK</option>
                    <option value="during_execution">During Execution</option>
                    <option value="before_execution">Before Execution</option>
                  </select>

                  <button
                    onClick={() => handleInjectFailure(w.worker_id)}
                    disabled={loadingWorker === w.worker_id}
                    style={{ padding: '5px 8px', fontSize: '11px', fontWeight: 600, background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    ⚡ Inject Failure Mode
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
