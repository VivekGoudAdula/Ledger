import React, { useEffect } from 'react';
import { X, CheckCircle2, AlertTriangle, XCircle, ShieldAlert, Cpu, Clock, DollarSign } from 'lucide-react';

export function SignalDetailPanel({ event, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!event) return null;

  const decision = event.decision || 'ADMIT';
  const isAdmit = decision === 'ADMIT';
  const isDefer = decision === 'DEFER';

  const badgeClass = isAdmit ? 'green' : isDefer ? 'amber' : 'red';
  const BadgeIcon = isAdmit ? CheckCircle2 : isDefer ? AlertTriangle : XCircle;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(15, 23, 42, 0.4)',
        backdropFilter: 'blur(2px)',
        zIndex: 999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
          width: '100%',
          maxWidth: '540px',
          padding: '24px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', pb: '16px', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Signal Valuation & Admission Inspection
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', marginTop: '2px', fontFamily: 'JetBrains Mono, monospace' }}>
              {event.event_type}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              border: 'none',
              background: '#f1f5f9',
              borderRadius: '4px',
              padding: '6px',
              cursor: 'pointer',
              color: '#64748b',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Decision Badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#f8fafc', padding: '12px 16px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #e2e8f0' }}>
          <div>
            <span style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '2px' }}>ADMISSION DECISION</span>
            <span className={`pill-badge ${badgeClass}`} style={{ fontSize: '13px', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px' }}>
              <BadgeIcon size={14} /> {decision}
            </span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '11px', color: '#64748b', display: 'block', marginBottom: '2px' }}>STATUS</span>
            <span style={{ fontSize: '12px', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#0f172a' }}>
              {event.status || 'COMPLETED'}
            </span>
          </div>
        </div>

        {/* Valuation Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <DollarSign size={13} color="#2563eb" /> Expected Value (EV)
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginTop: '4px', color: '#0f172a' }}>
              {event.expected_value != null ? event.expected_value.toFixed(2) : '0.85'}
            </div>
          </div>

          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Cpu size={13} color="#2563eb" /> Estimated Compute Cost
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginTop: '4px', color: '#0f172a' }}>
              {event.compute_cost != null ? `${event.compute_cost.toFixed(2)}s` : '0.25s'}
            </div>
          </div>

          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={13} color="#64748b" /> Event Arrival Time
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', marginTop: '4px', color: '#0f172a' }}>
              {event.time_str}
            </div>
          </div>

          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
            <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={13} color="#64748b" /> Signal Source
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', marginTop: '4px', color: '#0f172a', textTransform: 'capitalize' }}>
              {event.source}
            </div>
          </div>
        </div>

        {/* Rationale / Explanation */}
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px 16px', fontSize: '12px' }}>
          <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px' }}>Admission Rationale</div>
          <div style={{ color: '#64748b', lineHeight: '1.4' }}>
            {isAdmit
              ? 'High value-per-compute ratio evaluated above admission threshold under current capacity.'
              : isDefer
              ? 'Work item deferred to backpressure queue due to temporary capacity constraints.'
              : 'Low consequence score relative to compute cost intentionally shed under overload.'}
          </div>
        </div>
      </div>
    </div>
  );
}
