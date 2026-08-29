import React, { useState } from 'react';
import { EventLifecycleDrawer } from './EventLifecycleDrawer';

export function EventTrace({ events, onSelectEventForValuation }) {
  const [selectedLifecycleEvent, setSelectedLifecycleEvent] = useState(null);
  const list = events || [];

  function handleRowClick(e) {
    setSelectedLifecycleEvent(e);
    if (onSelectEventForValuation) {
      onSelectEventForValuation(e);
    }
  }

  return (
    <div className="panel" id="section-trace">
      <div className="panel-header">
        <h2>Live Signal Trace Stream</h2>
        <span className="pill-badge green">Real-Time Trace (Click row for 10-step lifecycle)</span>
      </div>

      <table className="event-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Source</th>
            <th>Event Type</th>
            <th>Event ID</th>
            <th>Value</th>
            <th>Cost</th>
            <th>Decision</th>
            <th>Worker</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {list.length === 0 ? (
            <tr>
              <td colSpan="9" style={{ textAlign: 'center', color: '#64748b', padding: '24px' }}>
                <strong style={{ color: '#0f172a', display: 'block', marginBottom: '4px' }}>NO LIVE SIGNALS</strong>
                Ledger is connected and waiting for incoming signals.
              </td>
            </tr>
          ) : (
            list.map((e, idx) => (
              <tr
                key={idx}
                onClick={() => handleRowClick(e)}
                style={{ cursor: 'pointer', transition: 'background-color 0.15s ease' }}
                title="Click to inspect end-to-end lifecycle trace"
              >
                <td>{e.time_str || 'N/A'}</td>
                <td style={{ textTransform: 'capitalize' }}>{e.source}</td>
                <td style={{ fontWeight: 600 }}>{e.event_type}</td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#64748b' }}>{e.event_id || `evt_0${idx+1}`}</td>
                <td>{e.expected_value != null ? e.expected_value.toFixed(2) : '-'}</td>
                <td>{e.compute_cost != null ? `${e.compute_cost.toFixed(2)}s` : '-'}</td>
                <td>
                  <span className={`pill-badge ${e.decision === 'ADMIT' ? 'green' : e.decision === 'DEFER' ? 'amber' : 'red'}`}>
                    {e.decision}
                  </span>
                </td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{e.worker_id || 'worker-1'}</td>
                <td>{e.status || 'QUEUED'}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {selectedLifecycleEvent && (
        <EventLifecycleDrawer
          event={selectedLifecycleEvent}
          onClose={() => setSelectedLifecycleEvent(null)}
        />
      )}
    </div>
  );
}
