import React from 'react';

export function MetricCards({ data }) {
  const ingressRate = data?.ingress_rate_sec ?? 0.0;
  const capacity = data?.processing_capacity_sec ?? 100.0;
  const breakdown = data?.admission_breakdown ?? {};

  return (
    <section className="metrics-grid">
      <div className="metric-card">
        <span className="card-label">INGRESS RATE</span>
        <div className="card-value">
          {ingressRate > 0 ? `${ingressRate.toFixed(1)} /s` : '0 /s'}
        </div>
        <span className="card-sub">Signals entering Ledger</span>
      </div>

      <div className="metric-card">
        <span className="card-label">PROCESSING CAPACITY</span>
        <div className="card-value">{capacity.toFixed(1)} /s</div>
        <span className="card-sub">Current processing capacity</span>
      </div>

      <div className="metric-card">
        <span className="card-label">ADMITTED</span>
        <div className="card-value text-green">{breakdown.admitted_count ?? 0}</div>
        <span className="card-sub">High-value work admitted</span>
      </div>

      <div className="metric-card">
        <span className="card-label">DEFERRED</span>
        <div className="card-value text-amber">{breakdown.deferred_count ?? 0}</div>
        <span className="card-sub">Work waiting for capacity</span>
      </div>

      <div className="metric-card">
        <span className="card-label">SHED</span>
        <div className="card-value text-red">{breakdown.shed_count ?? 0}</div>
        <span className="card-sub">Work rejected under pressure</span>
      </div>
    </section>
  );
}
