import React from 'react';
import { OutcomePanel } from '../components/OutcomePanel';

export function OutcomesPage({ data, onSelectEvent }) {
  const events = data?.recent_events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Outcome & Feedback Recorder</h2>
          <p className="page-description">Execution outcome logging, telemetry metrics, and outcome feedback to Value Estimator</p>
        </div>
        <span className="pill-badge green">Outcome Feedback Active</span>
      </div>

      <OutcomePanel data={data} />

      <div className="panel">
        <div className="panel-header">
          <h2>Completed Action Execution Audit Trail</h2>
          <span className="pill-badge green">Feedback Stream</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event ID</th>
              <th>Source</th>
              <th>Worker ID</th>
              <th>Action Result</th>
              <th>Execution Time</th>
              <th>Feedback Event</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No completed execution outcomes recorded...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => (
                <tr key={idx} onClick={() => onSelectEvent(e)} style={{ cursor: 'pointer' }}>
                  <td>{e.time_str}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{e.event_id || `evt_0${idx+1}`}</td>
                  <td style={{ textTransform: 'capitalize' }}>{e.source}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.worker_id || 'worker-1'}</td>
                  <td>
                    <span className={`pill-badge ${e.status === 'COMPLETED' ? 'green' : 'amber'}`}>
                      {e.status || 'COMPLETED'}
                    </span>
                  </td>
                  <td>{e.compute_cost != null ? `${e.compute_cost.toFixed(2)}s` : '0.25s'}</td>
                  <td style={{ color: '#16a34a', fontWeight: 600 }}>Feedback Broadcast Sent</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
