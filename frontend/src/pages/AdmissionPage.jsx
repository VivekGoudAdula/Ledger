import React from 'react';
import { AdmissionPanel } from '../components/AdmissionPanel';

export function AdmissionPage({ data, onSelectEvent }) {
  const events = data?.recent_events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Admission Control Subsystem</h2>
          <p className="page-description">Deterministic Value-per-Compute (VpC) scheduling, tenant quotas, and backpressure shedding</p>
        </div>
        <span className="pill-badge green">Core Admission Engine</span>
      </div>

      <AdmissionPanel data={data} />

      <div className="panel">
        <div className="panel-header">
          <h2>Live Decision Stream with Rationale</h2>
          <span className="pill-badge green">Click row for decision inspection</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event Type</th>
              <th>Source</th>
              <th>EV Score</th>
              <th>Compute Cost</th>
              <th>Decision</th>
              <th>Decision Rationale</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No active admission decisions recorded...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => (
                <tr
                  key={idx}
                  onClick={() => onSelectEvent(e)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>{e.time_str}</td>
                  <td style={{ fontWeight: 600 }}>{e.event_type}</td>
                  <td style={{ textTransform: 'capitalize' }}>{e.source}</td>
                  <td>{e.expected_value != null ? e.expected_value.toFixed(2) : '0.85'}</td>
                  <td>{e.compute_cost != null ? `${e.compute_cost.toFixed(2)}s` : '0.25s'}</td>
                  <td>
                    <span className={`pill-badge ${e.decision === 'ADMIT' ? 'green' : e.decision === 'DEFER' ? 'amber' : 'red'}`}>
                      {e.decision}
                    </span>
                  </td>
                  <td style={{ color: '#475569' }}>
                    {e.admission_reason || (e.decision === 'ADMIT' ? 'High consequence work admitted' : 'Low value dropped under overload')}
                  </td>
                  <td>
                    <button style={{ border: 'none', background: '#f0efed', padding: '2px 8px', borderRadius: '9999px', fontSize: '11px', cursor: 'pointer' }}>
                      Inspect Why
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
