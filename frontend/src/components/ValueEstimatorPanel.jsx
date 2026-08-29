import React from 'react';
import { Cpu, ShieldCheck, Zap } from 'lucide-react';

export function ValueEstimatorPanel({ selectedEvent }) {
  const event = selectedEvent || {
    event_type: 'workflow_failure',
    source: 'github',
    expected_value: 0.85,
    compute_cost: 0.25,
    urgency: 0.80,
    confidence: 0.90,
    consequence_of_drop: 0.85,
  };

  const ev = event.expected_value != null ? event.expected_value : 0.85;
  const cost = event.compute_cost != null ? event.compute_cost : 0.25;
  const vpc = cost > 0 ? (ev / cost).toFixed(2) : '3.40';

  return (
    <div className="panel" id="section-valuation">
      <div className="panel-header">
        <h2>Value Estimator Subsystem</h2>
        <span className="pill-badge green">VpC Evaluator</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '4px', fontSize: '11px' }}>
          <span style={{ color: '#64748b', display: 'block' }}>AI Estimator</span>
          <span style={{ fontWeight: 700, color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px' }}>
            ● HEALTHY (300ms)
          </span>
        </div>
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '8px 10px', borderRadius: '4px', fontSize: '11px' }}>
          <span style={{ color: '#64748b', display: 'block' }}>Rule Engine Fallback</span>
          <span style={{ fontWeight: 700, color: '#2563eb', display: 'flex', alignItems: 'center', gap: '4px' }}>
            ● ACTIVE READY
          </span>
        </div>
      </div>

      <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px', fontWeight: 600 }}>
        Active Signal Valuation Scorecard ({event.event_type}):
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginBottom: '10px' }}>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '6px 8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b' }}>Urgency</div>
          <div style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#0f172a' }}>
            {event.urgency != null ? event.urgency.toFixed(2) : '0.80'}
          </div>
        </div>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '6px 8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b' }}>Confidence</div>
          <div style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#0f172a' }}>
            {event.confidence != null ? event.confidence.toFixed(2) : '0.90'}
          </div>
        </div>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '6px 8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#64748b' }}>Consequence</div>
          <div style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#16a34a' }}>
            {event.consequence_of_drop != null ? event.consequence_of_drop.toFixed(2) : '0.85'}
          </div>
        </div>
      </div>

      <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: '8px 12px', borderRadius: '4px', fontSize: '11px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Formula: <strong>VpC = EV ÷ Compute Cost</strong></span>
        <span style={{ fontSize: '14px', fontWeight: 800, color: '#1e40af', fontFamily: 'JetBrains Mono, monospace' }}>
          VpC = {vpc}
        </span>
      </div>
    </div>
  );
}
