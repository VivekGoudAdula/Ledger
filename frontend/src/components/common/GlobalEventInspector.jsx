import React, { useEffect } from 'react';
import { X, CheckCircle2 } from 'lucide-react';

export function GlobalEventInspector({ event, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!event) return null;

  const steps = [
    { title: '1. Source Arrival', desc: `Signal received from ${event.source || 'github'} adapter` },
    { title: '2. Ingestion & Fingerprint', desc: `Validated canonical SignalEvent (2MB payload limit, SHA-256 hash fingerprint)` },
    { title: '3. Incident Coalescing', desc: `Evaluated against 5-min sliding window for candidate linking` },
    { title: '4. Value Estimation', desc: `Calculated Urgency (${event.urgency ?? 0.80}) × Consequence (${event.consequence_of_drop ?? 0.85}) / Compute Cost (${event.compute_cost ?? 0.25}s)` },
    { title: '5. Admission Decision', desc: `Decision: ${event.decision || 'ADMIT'} (${event.admission_reason || 'VpC evaluation'})` },
    { title: '6. Stream Queue Enqueue', desc: `Serialized into ledger:work_stream (Redis Streams Broker)` },
    { title: '7. Worker Pool Claim', desc: `Claimed by ${event.worker_id || 'worker-1'} in WorkerPool supervisor` },
    { title: '8. Idempotency Guard Check', desc: `Atomic claim check on key: ${event.tenant_id || 'tenant_default'}:${event.event_id || 'evt_01'}:EXECUTE` },
    { title: '9. Task Execution', desc: `Worker processed payload & committed SQLite WAL execution checkpoint` },
    { title: '10. Outcome Feedback', desc: `Status: ${event.status || 'COMPLETED'} broadcast over WebSocket stream` },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(12, 10, 9, 0.4)',
        backdropFilter: 'blur(3px)',
        zIndex: 9999,
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
          borderRadius: '12px',
          border: '1px solid #e7e5e4',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
          width: '100%',
          maxWidth: '640px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '24px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e7e5e4', paddingBottom: '14px', marginBottom: '16px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#777169', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              GLOBAL EVENT LIFECYCLE INSPECTOR
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#0c0a09', marginTop: '2px', fontFamily: 'JetBrains Mono, monospace' }}>
              {event.event_type} ({event.event_id || 'evt_canonical_01'})
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ border: 'none', background: '#f0efed', borderRadius: '50%', width: '32px', height: '32px', cursor: 'pointer', color: '#777169', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {steps.map((st, idx) => (
            <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e7e5e4', borderRadius: '8px', padding: '10px 14px', fontSize: '12px' }}>
              <div style={{ fontWeight: 700, color: '#0c0a09', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                <CheckCircle2 size={14} color="#16a34a" /> {st.title}
              </div>
              <div style={{ color: '#475569', paddingLeft: '20px', lineHeight: '1.4' }}>
                {st.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
