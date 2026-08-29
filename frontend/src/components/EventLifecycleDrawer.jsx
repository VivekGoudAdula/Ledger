import React, { useEffect } from 'react';
import { X, CheckCircle2, ArrowRight, ShieldCheck, Cpu, Clock } from 'lucide-react';

export function EventLifecycleDrawer({ event, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!event) return null;

  const steps = [
    { title: '1. Source Arrival', desc: `Signal received from ${event.source} adapter` },
    { title: '2. Ingestion & Fingerprint', desc: `Validated canonical SignalEvent (2MB limit, SHA-256 hash)` },
    { title: '3. Incident Coalescing', desc: `Evaluated against 5-min sliding window for candidate linking` },
    { title: '4. Value Estimation', desc: `Calculated Urgency (${event.urgency ?? 0.80}) × Consequence (${event.consequence_of_drop ?? 0.85}) / Compute Cost (${event.compute_cost ?? 0.25}s)` },
    { title: '5. Admission Decision', desc: `Decision: ${event.decision} (${event.admission_reason || 'VpC evaluation'})` },
    { title: '6. Stream Enqueue', desc: `Serialized into ledger:work_stream (Redis Streams)` },
    { title: '7. Worker Claim', desc: `Claimed by ${event.worker_id || 'worker-1'} in WorkerPool supervisor` },
    { title: '8. Idempotency Check', desc: `Atomic claim check on ${event.tenant_id || 'tenant_default'}:${event.event_id || 'evt_01'}:EXECUTE` },
    { title: '9. Task Execution', desc: `Worker processed payload & committed execution checkpoint` },
    { title: '10. Outcome Feedback', desc: `Status: ${event.status || 'COMPLETED'} broadcast over WebSocket` },
  ];

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
          maxWidth: '600px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '24px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              End-to-End Signal Lifecycle Trace
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', marginTop: '2px', fontFamily: 'JetBrains Mono, monospace' }}>
              {event.event_type} ({event.event_id || 'evt_canonical_01'})
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ border: 'none', background: '#f1f5f9', borderRadius: '4px', padding: '6px', cursor: 'pointer', color: '#64748b' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {steps.map((st, idx) => (
            <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '10px 14px', fontSize: '12px' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                <CheckCircle2 size={13} color="#16a34a" /> {st.title}
              </div>
              <div style={{ color: '#475569', paddingLeft: '19px', lineHeight: '1.4' }}>
                {st.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
