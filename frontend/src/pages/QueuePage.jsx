import React from 'react';
import { useQueueState } from '../hooks/useQueueState';
import { RefreshCw, Clock, Zap, TrendingUp, CheckCircle2, XCircle, Pause } from 'lucide-react';

/** Format ISO timestamp to short HH:MM:SS display */
function fmtTime(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleTimeString();
  } catch {
    return isoStr;
  }
}

/** Format waiting seconds as human-readable */
function fmtWait(secs) {
  if (!secs && secs !== 0) return '—';
  if (secs < 60) return `${Math.round(secs)}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

/** Format deadline ISO string to relative time */
function fmtDeadline(isoStr) {
  if (!isoStr) return '—';
  try {
    const diff = (new Date(isoStr) - Date.now()) / 1000;
    if (diff < 0) return 'EXPIRED';
    return fmtWait(diff);
  } catch {
    return '—';
  }
}

/** Status pill with appropriate color */
function StatusPill({ status }) {
  const cls = {
    QUEUED: 'green',
    PROCESSING: 'amber',
    DEFERRED: 'amber',
    COMPLETED: 'green',
    FAILED: 'red',
    SHED: 'red',
  }[status] || '';
  return <span className={`pill-badge ${cls}`}>● {status}</span>;
}

/** Section header row */
function SectionHeader({ icon: Icon, title, count, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
      <Icon size={18} color={color || '#0c0a09'} />
      <span style={{ fontFamily: 'Times New Roman, serif', fontSize: '20px', fontWeight: 300, color: '#0c0a09', letterSpacing: '-0.02em' }}>
        {title}
      </span>
      {count !== undefined && (
        <span className="pill-badge" style={{ fontSize: '11px', marginLeft: '4px' }}>{count}</span>
      )}
    </div>
  );
}

/** Empty row for tables */
function EmptyRow({ colSpan, message }) {
  return (
    <tr>
      <td colSpan={colSpan} style={{ textAlign: 'center', color: '#78716c', padding: '28px', fontStyle: 'italic', fontSize: '13px' }}>
        {message}
      </td>
    </tr>
  );
}

export function QueuePage({ onSelectEvent }) {
  const { queueState, loading, error, refresh } = useQueueState();

  if (loading && !queueState) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <QueuePageHeader loading refresh={refresh} />
        <div className="panel" style={{ padding: '40px', textAlign: 'center', color: '#78716c' }}>
          <RefreshCw size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: '12px' }} />
          <div>Loading queue state from backend...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <QueuePageHeader refresh={refresh} />
        <div className="panel" style={{ padding: '32px', background: '#fef2f2', borderColor: '#fecaca' }}>
          <div style={{ color: '#dc2626', fontWeight: 600, marginBottom: '8px' }}>Backend queue state unavailable</div>
          <div style={{ color: '#4e4e4e', fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}>{error}</div>
        </div>
      </div>
    );
  }

  const ready = queueState?.ready_queue || [];
  const processing = queueState?.processing_now || [];
  const deferred = queueState?.deferred_queue || [];
  const completed = queueState?.completed_recent || [];
  const failed = queueState?.failed_recent || [];
  const shed = queueState?.shed_recent || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <QueuePageHeader queueState={queueState} refresh={refresh} />

      {/* ── READY QUEUE ─────────────────────────────────────────────────── */}
      <div className="panel" id="section-queue">
        <SectionHeader icon={Zap} title="Ready Queue" count={ready.length} color="#16a34a" />
        <p style={{ fontSize: '13px', color: '#57534e', marginBottom: '16px' }}>
          Admitted events ordered by backend effective_priority = (base_value + aging_bonus) / compute_cost.
          Backend is authoritative — no re-sorting in React.
        </p>
        <table className="event-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Event ID</th>
              <th>Source / Type</th>
              <th>Base Value</th>
              <th>Compute</th>
              <th>Aging +</th>
              <th>Eff. Priority</th>
              <th>Deadline</th>
              <th>Wait</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {ready.length === 0 ? (
              <EmptyRow colSpan={10} message="No events in READY queue — workers have consumed all admitted work" />
            ) : (
              ready.map((item) => (
                <tr
                  key={item.event_id}
                  onClick={() => onSelectEvent && onSelectEvent({ event_id: item.event_id, ...item })}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: '#0c0a09' }}>{item.position}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#57534e' }}>
                    {item.event_id?.slice(0, 14)}…
                  </td>
                  <td>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#0c0a09' }}>{item.source}</div>
                    <div style={{ fontSize: '11px', color: '#78716c' }}>{item.event_type}</div>
                  </td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{item.base_value?.toFixed(3)}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{item.compute_cost?.toFixed(3)}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#16a34a' }}>
                    +{item.aging_contribution?.toFixed(4)}
                  </td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', fontWeight: 700, color: '#0c0a09' }}>
                    {item.effective_priority?.toFixed(4)}
                  </td>
                  <td style={{ fontSize: '12px', color: item.deadline_at && new Date(item.deadline_at) < new Date() ? '#dc2626' : '#57534e' }}>
                    {fmtDeadline(item.deadline_at)}
                  </td>
                  <td style={{ fontSize: '12px', color: '#57534e' }}>{fmtWait(item.waiting_seconds)}</td>
                  <td><StatusPill status={item.status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── PROCESSING NOW ──────────────────────────────────────────────── */}
      <div className="panel">
        <SectionHeader icon={TrendingUp} title="Processing Now" count={processing.length} color="#b45309" />
        <table className="event-table">
          <thead>
            <tr>
              <th>Worker</th>
              <th>Event ID</th>
              <th>Source / Type</th>
              <th>Value</th>
              <th>Eff. Priority</th>
              <th>Started</th>
              <th>Elapsed</th>
              <th>Attempt</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {processing.length === 0 ? (
              <EmptyRow colSpan={9} message="No events currently being processed — workers idle or all work completed" />
            ) : (
              processing.map((item) => {
                const elapsedSecs = item.started_at
                  ? Math.max(0, (Date.now() - new Date(item.started_at).getTime()) / 1000)
                  : null;
                return (
                  <tr
                    key={item.event_id}
                    onClick={() => onSelectEvent && onSelectEvent({ event_id: item.event_id, ...item })}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', fontWeight: 600, color: '#b45309' }}>
                      {item.worker_id || '—'}
                    </td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#57534e' }}>
                      {item.event_id?.slice(0, 14)}…
                    </td>
                    <td>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: '#0c0a09' }}>{item.source}</div>
                      <div style={{ fontSize: '11px', color: '#78716c' }}>{item.event_type}</div>
                    </td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{item.base_value?.toFixed(3)}</td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', fontWeight: 700 }}>
                      {item.effective_priority?.toFixed(4)}
                    </td>
                    <td style={{ fontSize: '12px' }}>{fmtTime(item.started_at)}</td>
                    <td style={{ fontSize: '12px', color: '#b45309', fontFamily: 'JetBrains Mono, monospace' }}>
                      {elapsedSecs !== null ? fmtWait(elapsedSecs) : '—'}
                    </td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>{item.attempt}</td>
                    <td><StatusPill status="PROCESSING" /></td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── DEFERRED WORK ───────────────────────────────────────────────── */}
      <div className="panel">
        <SectionHeader icon={Pause} title="Deferred Work" count={deferred.length} color="#b45309" />
        <p style={{ fontSize: '13px', color: '#57534e', marginBottom: '16px' }}>
          DEFERRED is not SHED. Deferred work remains recoverable and will be re-evaluated by admission control when capacity becomes available.
        </p>
        <table className="event-table">
          <thead>
            <tr>
              <th>Event ID</th>
              <th>Source / Type</th>
              <th>Value</th>
              <th>Eff. Priority</th>
              <th>Wait</th>
              <th>Deadline</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {deferred.length === 0 ? (
              <EmptyRow colSpan={7} message="No deferred work — capacity is sufficient for all admitted signals" />
            ) : (
              deferred.map((item) => (
                <tr
                  key={item.event_id}
                  onClick={() => onSelectEvent && onSelectEvent({ event_id: item.event_id, ...item })}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#57534e' }}>
                    {item.event_id?.slice(0, 14)}…
                  </td>
                  <td>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#0c0a09' }}>{item.source}</div>
                    <div style={{ fontSize: '11px', color: '#78716c' }}>{item.event_type}</div>
                  </td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{item.base_value?.toFixed(3)}</td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>{item.effective_priority?.toFixed(4)}</td>
                  <td style={{ fontSize: '12px', color: '#57534e' }}>{fmtWait(item.waiting_seconds)}</td>
                  <td style={{ fontSize: '12px', color: item.deadline_at && new Date(item.deadline_at) < new Date() ? '#dc2626' : '#57534e' }}>
                    {fmtDeadline(item.deadline_at)}
                  </td>
                  <td style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color: '#b45309' }}>
                    {item.reason}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── RECENT OUTCOMES ─────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* COMPLETED */}
        <div className="panel">
          <SectionHeader icon={CheckCircle2} title="Completed" count={completed.length} color="#16a34a" />
          <table className="event-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Source / Type</th>
                <th>Worker</th>
                <th>Duration</th>
                <th>Completed At</th>
              </tr>
            </thead>
            <tbody>
              {completed.length === 0 ? (
                <EmptyRow colSpan={5} message="No completed work yet" />
              ) : (
                completed.slice(0, 10).map((item) => (
                  <tr
                    key={item.event_id}
                    onClick={() => onSelectEvent && onSelectEvent({ event_id: item.event_id, ...item })}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#57534e' }}>
                      {item.event_id?.slice(0, 12)}…
                    </td>
                    <td>
                      <div style={{ fontSize: '11px', fontWeight: 600 }}>{item.source}</div>
                      <div style={{ fontSize: '10px', color: '#78716c' }}>{item.event_type}</div>
                    </td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{item.worker_id || '—'}</td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#16a34a' }}>
                      {item.duration_seconds !== null && item.duration_seconds !== undefined ? `${item.duration_seconds}s` : '—'}
                    </td>
                    <td style={{ fontSize: '11px', color: '#57534e' }}>{fmtTime(item.completed_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* FAILED + SHED */}
        <div className="panel">
          <SectionHeader icon={XCircle} title="Failed / Shed" count={failed.length + shed.length} color="#dc2626" />
          <table className="event-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Source / Type</th>
                <th>Status</th>
                <th>Error</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {failed.length === 0 && shed.length === 0 ? (
                <EmptyRow colSpan={5} message="No failures or shed events" />
              ) : (
                [...failed, ...shed].slice(0, 10).map((item) => (
                  <tr
                    key={item.event_id}
                    onClick={() => onSelectEvent && onSelectEvent({ event_id: item.event_id, ...item })}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#57534e' }}>
                      {item.event_id?.slice(0, 12)}…
                    </td>
                    <td>
                      <div style={{ fontSize: '11px', fontWeight: 600 }}>{item.source}</div>
                      <div style={{ fontSize: '10px', color: '#78716c' }}>{item.event_type}</div>
                    </td>
                    <td><StatusPill status={item.status} /></td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#dc2626' }}>
                      {item.error || '—'}
                    </td>
                    <td style={{ fontSize: '11px', color: '#57534e' }}>{fmtTime(item.completed_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/** Page header with live stats and refresh button */
function QueuePageHeader({ queueState, loading, refresh }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Execution Queue</h2>
          <p className="page-description">
            Live scheduling state — all ordering, priority, and aging computed by backend. Polling every 2s.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {queueState && (
            <span style={{ fontSize: '11px', color: '#78716c', fontFamily: 'JetBrains Mono, monospace' }}>
              {queueState.snapshot_at ? `Snapshot: ${new Date(queueState.snapshot_at).toLocaleTimeString()}` : ''}
            </span>
          )}
          <button
            onClick={refresh}
            className="button-outline"
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <RefreshCw size={13} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
        </div>
      </div>

      {queueState && (
        <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="metric-card">
            <div className="card-label">READY</div>
            <div className="card-value" style={{ fontSize: '28px', color: '#16a34a' }}>{queueState.total_ready}</div>
            <div className="card-sub">Awaiting worker</div>
          </div>
          <div className="metric-card">
            <div className="card-label">PROCESSING</div>
            <div className="card-value" style={{ fontSize: '28px', color: '#b45309' }}>{queueState.total_processing}</div>
            <div className="card-sub">Currently executing</div>
          </div>
          <div className="metric-card">
            <div className="card-label">DEFERRED</div>
            <div className="card-value" style={{ fontSize: '28px', color: '#b45309' }}>{queueState.total_deferred}</div>
            <div className="card-sub">Recoverable — awaiting capacity</div>
          </div>
        </div>
      )}
    </div>
  );
}
