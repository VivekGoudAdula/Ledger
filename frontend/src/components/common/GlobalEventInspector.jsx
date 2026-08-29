import React, { useEffect, useState } from 'react';
import { X, CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';

/**
 * GlobalEventInspector — fetches real per-event lifecycle from
 * GET /api/v1/queue/event/{event_id}/lifecycle and renders it.
 *
 * Zero fake steps. Every step comes from DB records:
 * EventORM, ValuationORM, ExecutionCheckpointORM, ExecutionResultORM, IdempotencyRecordORM.
 */
export function GlobalEventInspector({ event, onClose }) {
  const [lifecycle, setLifecycle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Fetch real lifecycle from backend when event_id is available
  useEffect(() => {
    if (!event?.event_id) return;
    setLoading(true);
    setFetchError(null);
    fetch(`/api/v1/queue/event/${event.event_id}/lifecycle`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setLifecycle(data);
        setLoading(false);
      })
      .catch((err) => {
        setFetchError(err.message);
        setLoading(false);
      });
  }, [event?.event_id]);

  if (!event) return null;

  /** Decide icon/color for a lifecycle step */
  function stepColor(step) {
    if (step.status === 'DONE') return '#16a34a';
    if (step.status === 'PENDING') return '#b45309';
    return '#a8a29e';
  }

  function StepIcon({ status }) {
    if (status === 'DONE') return <CheckCircle2 size={14} color="#16a34a" />;
    if (status === 'PENDING') return <Clock size={14} color="#b45309" />;
    return <AlertCircle size={14} color="#a8a29e" />;
  }

  const displayTitle = lifecycle
    ? `${lifecycle.event_type} — ${lifecycle.source}`
    : event.event_type || 'Event';
  const displayId = lifecycle?.event_id || event.event_id || 'No ID';
  const displayStatus = lifecycle?.current_status || event.status || '—';

  const statusColors = {
    QUEUED: '#16a34a', PROCESSING: '#b45309', COMPLETED: '#16a34a',
    DEFERRED: '#b45309', FAILED: '#dc2626', SHED: '#dc2626',
  };

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(12, 10, 9, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e7e5e4',
          boxShadow: '0 24px 48px rgba(0, 0, 0, 0.12)',
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid #e7e5e4' }}>
          <div>
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#78716c', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
              EVENT LIFECYCLE INSPECTOR
            </div>
            <h2 style={{ fontFamily: 'Times New Roman, serif', fontSize: '22px', fontWeight: 300, color: '#0c0a09', letterSpacing: '-0.02em', margin: 0 }}>
              {displayTitle}
            </h2>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#57534e', marginTop: '4px' }}>
              {displayId}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: statusColors[displayStatus] || '#57534e' }}>
              ● {displayStatus}
            </span>
            <button
              onClick={onClose}
              style={{ border: 'none', background: '#f0efed', borderRadius: '50%', width: '32px', height: '32px', cursor: 'pointer', color: '#57534e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Valuation / Admission Summary Strip */}
        {lifecycle && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
            {[
              { label: 'Base Value', val: lifecycle.base_value?.toFixed(3) ?? '—' },
              { label: 'Compute', val: lifecycle.compute_cost?.toFixed(3) ?? '—' },
              { label: 'V/Compute', val: lifecycle.value_per_compute?.toFixed(3) ?? '—' },
              { label: 'Decision', val: lifecycle.admission_decision || '—' },
            ].map(({ label, val }) => (
              <div key={label} style={{ background: '#f5f5f4', borderRadius: '8px', padding: '10px 12px', border: '1px solid #e7e5e4' }}>
                <div style={{ fontSize: '10px', fontWeight: 600, color: '#78716c', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '14px', fontWeight: 700, color: '#0c0a09', marginTop: '2px' }}>{val}</div>
              </div>
            ))}
          </div>
        )}

        {/* Loading / Error */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '32px', color: '#78716c' }}>
            <Loader2 size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: '8px' }} />
            <div style={{ fontSize: '13px' }}>Loading lifecycle from backend...</div>
          </div>
        )}

        {fetchError && (
          <div style={{ background: '#fef2f2', borderRadius: '8px', padding: '12px 16px', color: '#dc2626', fontSize: '12px', marginBottom: '16px', fontFamily: 'JetBrains Mono, monospace' }}>
            Could not load lifecycle: {fetchError}
          </div>
        )}

        {/* Lifecycle Steps — real DB data */}
        {lifecycle?.lifecycle_steps && lifecycle.lifecycle_steps.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {lifecycle.lifecycle_steps.map((step, idx) => (
              <div
                key={idx}
                style={{
                  background: step.status === 'DONE' ? '#f0fdf4' : step.status === 'PENDING' ? '#fffbeb' : '#fafafa',
                  border: `1px solid ${step.status === 'DONE' ? '#bbf7d0' : step.status === 'PENDING' ? '#fde68a' : '#e7e5e4'}`,
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '12px',
                }}
              >
                <div style={{ fontWeight: 700, color: stepColor(step), display: 'flex', alignItems: 'center', gap: '6px', marginBottom: step.detail ? '4px' : 0 }}>
                  <StepIcon status={step.status} />
                  <span style={{ color: '#0c0a09' }}>{step.step}</span>
                  {step.timestamp && (
                    <span style={{ marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#78716c', fontWeight: 400 }}>
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
                {step.detail && (
                  <div style={{ color: '#4e4e4e', paddingLeft: '20px', lineHeight: '1.5', fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}>
                    {step.detail}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Fallback for events without event_id — show basic data from event prop */}
        {!lifecycle && !loading && !fetchError && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { step: 'SIGNAL_RECEIVED', detail: `Source: ${event.source || '—'} | Type: ${event.event_type || '—'}` },
              { step: 'VALUE_ESTIMATED', detail: `EV: ${event.expected_value ?? '—'} | Cost: ${event.compute_cost ?? '—'} | Urgency: ${event.urgency ?? '—'}` },
              { step: 'ADMISSION_DECIDED', detail: `Decision: ${event.decision || '—'} | Reason: ${event.admission_reason || '—'}` },
              { step: 'STATUS', detail: `Current: ${event.status || '—'} | Worker: ${event.worker_id || '—'}` },
            ].map((s, idx) => (
              <div key={idx} style={{ background: '#f5f5f4', borderRadius: '8px', padding: '10px 14px', border: '1px solid #e7e5e4', fontSize: '12px' }}>
                <div style={{ fontWeight: 700, color: '#0c0a09', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <CheckCircle2 size={13} color="#16a34a" /> {s.step}
                </div>
                <div style={{ color: '#4e4e4e', paddingLeft: '20px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>
                  {s.detail}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Coalescing / Worker / Idempotency details footer */}
        {lifecycle && (
          <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid #e7e5e4', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {lifecycle.coalesced_into_id && (
              <div style={{ fontSize: '11px', color: '#57534e', fontFamily: 'JetBrains Mono, monospace' }}>
                <span style={{ fontWeight: 600, color: '#0c0a09' }}>Incident: </span>{lifecycle.coalesced_into_id.slice(0, 20)}…
              </div>
            )}
            {lifecycle.worker_id && (
              <div style={{ fontSize: '11px', color: '#57534e', fontFamily: 'JetBrains Mono, monospace' }}>
                <span style={{ fontWeight: 600, color: '#0c0a09' }}>Worker: </span>{lifecycle.worker_id}
              </div>
            )}
            {lifecycle.duration_seconds !== null && lifecycle.duration_seconds !== undefined && (
              <div style={{ fontSize: '11px', color: '#57534e', fontFamily: 'JetBrains Mono, monospace' }}>
                <span style={{ fontWeight: 600, color: '#0c0a09' }}>Duration: </span>{lifecycle.duration_seconds}s
              </div>
            )}
            {lifecycle.idempotency_hit && (
              <div style={{ fontSize: '11px', color: '#b45309', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                ⚠ IDEMPOTENCY HIT — duplicate prevented
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
