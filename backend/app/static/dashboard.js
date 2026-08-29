/**
 * LEDGER Live Operational Dashboard JavaScript Client.
 * Handles WebSocket real-time updates, DOM element mutations, and automatic reconnects.
 */

class LedgerDashboard {
  constructor() {
    this.ws = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 10000;
    this.init();
  }

  init() {
    this.connect();
    // Fallback REST fetch if WebSocket fails
    this.fetchRestSummary();
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    this.updateWsStatus('● CONNECTING...', 'amber');
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.updateWsStatus('● LIVE STREAM', 'green');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.renderDashboard(data);
      } catch (err) {
        console.error('Error parsing dashboard WebSocket JSON:', err);
      }
    };

    this.ws.onclose = () => {
      this.updateWsStatus('● RECONNECTING', 'amber');
      this.scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.warn('Dashboard WebSocket connection error:', err);
      this.ws.close();
    };
  }

  scheduleReconnect() {
    setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  async fetchRestSummary() {
    try {
      const res = await fetch('/api/v1/dashboard/summary');
      if (res.ok) {
        const data = await res.json();
        this.renderDashboard(data);
      }
    } catch (err) {
      console.warn('REST fallback fetch error:', err);
    }
  }

  updateWsStatus(text, color) {
    const statusEl = document.getElementById('ws-status');
    if (statusEl) {
      statusEl.textContent = text;
      statusEl.className = `ws-indicator ${color}`;
    }
  }

  renderDashboard(data) {
    if (!data) return;

    // Header & Status
    const statusTextEl = document.getElementById('system-status-text');
    const systemDotEl = document.getElementById('system-dot');
    if (statusTextEl && systemDotEl) {
      statusTextEl.textContent = `SYSTEM ${data.system_status || 'HEALTHY'}`;
      systemDotEl.className = `pulse-dot ${data.system_status === 'OVERLOADED' ? 'red' : 'green'}`;
    }

    // Top Overview Cards
    this.setText('ingress-rate', `${(data.ingress_rate_sec || 0).toFixed(1)} /s`);
    this.setText('total-ingress', data.total_ingress_count || 0);
    this.setText('capacity', `${(data.processing_capacity_sec || 100).toFixed(1)} /s`);

    const breakdown = data.admission_breakdown || {};
    this.setText('admitted-count', breakdown.admitted_count || 0);
    this.setText('deferred-count', breakdown.deferred_count || 0);
    this.setText('shed-count', breakdown.shed_count || 0);

    // Workers Grid
    this.renderWorkers(data.workers || []);

    // Recovery & Idempotency
    const rec = data.recovery || {};
    this.setText('rec-pending', rec.pending_count || 0);
    this.setText('rec-stale', rec.stale_count || 0);
    this.setText('rec-reclaimed', rec.reclaimed_count || 0);
    this.setText('rec-hits', rec.already_completed_hits || 0);
    this.setText('rec-failures', rec.failures_count || 0);

    const idem = data.idempotency || {};
    this.setText('idem-checks', idem.checks_count || 0);
    this.setText('idem-claims', idem.claims_count || 0);
    this.setText('idem-hits', idem.hits_count || 0);
    this.setText('idem-prevented', idem.duplicates_prevented_count || 0);

    // Source Health
    this.renderSourceHealth(data.sources || []);

    // Recent Event Trace Table
    this.renderEventsTable(data.recent_events || []);
  }

  renderWorkers(workers) {
    const grid = document.getElementById('worker-grid');
    if (!grid) return;
    if (!workers.length) {
      grid.innerHTML = '<div class="worker-card">No active workers</div>';
      return;
    }
    grid.innerHTML = workers.map(w => `
      <div class="worker-card">
        <span class="worker-name">${w.worker_id}</span>
        <span class="badge ${w.state === 'RUNNING' ? 'green' : 'amber'}">${w.state}</span>
        <span class="worker-jobs">${w.tasks_completed || 0} jobs done</span>
      </div>
    `).join('');
  }

  renderSourceHealth(sources) {
    const list = document.getElementById('source-health-list');
    if (!list || !sources.length) return;
    list.innerHTML = sources.map(s => `
      <div class="metric-row">
        <span>${s.name}</span>
        <span class="badge ${s.status === 'UP' ? 'green' : 'red'}">${s.status}</span>
      </div>
    `).join('');
  }

  renderEventsTable(events) {
    const tbody = document.getElementById('event-table-body');
    if (!tbody) return;
    if (!events.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="loading">No recent signal events</td></tr>';
      return;
    }
    tbody.innerHTML = events.map(e => `
      <tr>
        <td>${e.time_str || 'N/A'}</td>
        <td>${e.source || 'generic'}</td>
        <td>${e.event_type || 'event'}</td>
        <td>${e.expected_value != null ? e.expected_value.toFixed(2) : '-'}</td>
        <td>${e.compute_cost != null ? e.compute_cost.toFixed(2) : '-'}</td>
        <td><span class="badge ${e.decision === 'ADMIT' ? 'green' : (e.decision === 'DEFER' ? 'amber' : 'red')}">${e.decision}</span></td>
        <td>${e.status || 'QUEUED'}</td>
      </tr>
    `).join('');
  }

  setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }
}

// Instantiate Dashboard Client upon page load
window.addEventListener('DOMContentLoaded', () => {
  window.dashboardClient = new LedgerDashboard();
});
