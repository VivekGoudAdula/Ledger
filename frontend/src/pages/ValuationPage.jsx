import React from 'react';
import { ValueEstimatorPanel } from '../components/ValueEstimatorPanel';

export function ValuationPage({ data, onSelectEvent }) {
  const events = data?.recent_events || [];
  const activeEvent = events.length > 0 ? events[0] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Value Estimation Subsystem</h2>
          <p className="page-description">AI LLM Consequence Estimator + Rule-Based Fallback Engine scoring Value per Compute (VpC)</p>
        </div>
        <span className="pill-badge green">VpC Evaluator</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
        <ValueEstimatorPanel selectedEvent={activeEvent} />

        <div className="panel">
          <div className="panel-header">
            <h2>Scoring Pipeline Invariant</h2>
            <span className="pill-badge green">Deterministic Guard</span>
          </div>

          <div style={{ padding: '12px', background: '#f8fafc', border: '1px solid #e7e5e4', borderRadius: '6px', fontSize: '12px', lineHeight: '1.6' }}>
            <div style={{ fontWeight: 700, color: '#0c0a09', marginBottom: '4px' }}>AI Estimation Role</div>
            <p style={{ color: '#777169' }}>
              The AI LLM estimator provides structured numerical scores (Urgency, Confidence, Consequence). It does <strong>NOT</strong> directly make admission decisions.
            </p>
            <div style={{ margin: '12px 0 6px', fontWeight: 700, color: '#2563eb' }}>
              SEMANTIC ESTIMATION → STRUCTURED VALUES → DETERMINISTIC ADMISSION
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Live Signal Valuation Stream</h2>
          <span className="pill-badge green">Click row to view scoring breakdown</span>
        </div>

        <table className="event-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event Type</th>
              <th>Urgency</th>
              <th>Confidence</th>
              <th>Consequence</th>
              <th>Compute Cost</th>
              <th>Expected Value (EV)</th>
              <th>Value / Compute (VpC)</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', color: '#777169', padding: '24px' }}>
                  No active valuation signals evaluating...
                </td>
              </tr>
            ) : (
              events.map((e, idx) => {
                const ev = e.expected_value ?? 0.85;
                const cost = e.compute_cost ?? 0.25;
                const vpc = cost > 0 ? (ev / cost).toFixed(2) : '3.40';

                return (
                  <tr
                    key={idx}
                    onClick={() => onSelectEvent(e)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{e.time_str}</td>
                    <td style={{ fontWeight: 600 }}>{e.event_type}</td>
                    <td>{e.urgency != null ? e.urgency.toFixed(2) : '0.80'}</td>
                    <td>{e.confidence != null ? e.confidence.toFixed(2) : '0.90'}</td>
                    <td style={{ color: '#16a34a', fontWeight: 700 }}>{e.consequence_of_drop != null ? e.consequence_of_drop.toFixed(2) : '0.85'}</td>
                    <td>{cost.toFixed(2)}s</td>
                    <td style={{ fontWeight: 700 }}>{ev.toFixed(2)}</td>
                    <td style={{ color: '#2563eb', fontWeight: 800, fontFamily: 'JetBrains Mono, monospace' }}>{vpc}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
