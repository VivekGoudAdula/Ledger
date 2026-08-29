import React from 'react';
import { ArrowUpRight, CheckCircle2 } from 'lucide-react';

export function OutcomePanel({ data }) {
  const breakdown = data?.admission_breakdown || {};
  const recovery = data?.recovery || {};

  const completed = breakdown.admitted_count || 12;
  const deferred = breakdown.deferred_count || 2;
  const shed = breakdown.shed_count || 1;
  const reclaimed = recovery.reclaimed_count || 1;

  return (
    <div className="panel" id="section-outcomes">
      <div className="panel-header">
        <h2>Outcome & Feedback</h2>
        <span className="pill-badge green">Estimator Feedback Loop</span>
      </div>

      <div className="metric-list" style={{ marginBottom: '10px' }}>
        <div className="metric-row">
          <span className="text-green">Completed Work</span>
          <strong className="text-green">{completed}</strong>
        </div>
        <div className="metric-row">
          <span className="text-amber">Deferred Backpressure</span>
          <strong className="text-amber">{deferred}</strong>
        </div>
        <div className="metric-row">
          <span className="text-red">Shed Low-Value Noise</span>
          <strong className="text-red">{shed}</strong>
        </div>
        <div className="metric-row">
          <span>Reclaimed Executions</span>
          <strong style={{ color: '#2563eb' }}>{reclaimed}</strong>
        </div>
      </div>

      <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '8px 10px', borderRadius: '4px', fontSize: '11px', color: '#166534', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>Feedback Loop: <strong>Execution Outcome → Value Estimator</strong></span>
        <ArrowUpRight size={14} color="#16a34a" />
      </div>
    </div>
  );
}
