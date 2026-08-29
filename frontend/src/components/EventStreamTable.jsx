import React, { useState } from 'react';
import { SignalDetailPanel } from './SignalDetailPanel';

export function EventStreamTable({ events }) {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const recentEvents = events || [];

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Live Signal Trace Stream</h2>
        <span className="pill-badge green">Real-time</span>
      </div>

      <table className="event-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Source</th>
            <th>Event Type</th>
            <th>Value</th>
            <th>Cost</th>
            <th>Decision</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {recentEvents.length === 0 ? (
            <tr>
              <td colSpan="7" style={{ textAlign: 'center', color: '#64748b', padding: '24px' }}>
                <strong style={{ color: '#0f172a', display: 'block', marginBottom: '4px' }}>NO LIVE SIGNALS</strong>
                Ledger is connected and waiting for incoming signals.
              </td>
            </tr>
          ) : (
            recentEvents.map((e, idx) => (
              <tr
                key={idx}
                onClick={() => setSelectedEvent(e)}
                style={{ cursor: 'pointer', transition: 'background-color 0.15s ease' }}
                className="event-row"
                title="Click row to view full admission valuation details"
              >
                <td>{e.time_str || 'N/A'}</td>
                <td style={{ textTransform: 'capitalize' }}>{e.source || 'generic'}</td>
                <td style={{ fontWeight: 600 }}>{e.event_type || 'event'}</td>
                <td>{e.expected_value != null ? e.expected_value.toFixed(2) : '-'}</td>
                <td>{e.compute_cost != null ? `${e.compute_cost.toFixed(2)}s` : '-'}</td>
                <td>
                  <span
                    className={`pill-badge ${
                      e.decision === 'ADMIT'
                        ? 'green'
                        : e.decision === 'DEFER'
                        ? 'amber'
                        : 'red'
                    }`}
                  >
                    {e.decision}
                  </span>
                </td>
                <td>{e.status || 'QUEUED'}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {selectedEvent && (
        <SignalDetailPanel
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}
