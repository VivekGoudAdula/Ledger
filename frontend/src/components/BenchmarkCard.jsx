import React, { useState } from 'react';
import { Play, CheckCircle2, TrendingUp, ShieldCheck, Zap, RefreshCw } from 'lucide-react';

export function BenchmarkCard() {
  const [loading, setLoading] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleRunBenchmark() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/benchmark/run?scenario=sustained_overload&size=100&seed=42&capacity=10.0', {
        method: 'POST',
      });
      if (res.ok) {
        const json = await res.json();
        setBenchmarkResult(json);
      } else {
        setError('Failed to execute benchmark simulation.');
      }
    } catch (err) {
      console.error('Benchmark execution error:', err);
      setError('Network error contacting benchmark engine.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h2>FIFO VS LEDGER BENCHMARK</h2>
          <span className="pill-badge green">Virtual Engine</span>
        </div>
        <button
          onClick={handleRunBenchmark}
          disabled={loading}
          style={{
            background: loading ? '#cbd5e1' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'background 0.2s ease',
          }}
        >
          {loading ? (
            <>
              <RefreshCw size={13} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
              Simulating Overload...
            </>
          ) : (
            <>
              <Play size={13} />
              {benchmarkResult ? 'Re-run Benchmark' : 'Run Benchmark'}
            </>
          )}
        </button>
      </div>

      {!benchmarkResult && !loading && (
        <div style={{ padding: '20px', textAlign: 'center', background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '6px' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>BENCHMARK NOT RUN</div>
          <p style={{ fontSize: '12px', color: '#64748b', maxWidth: '500px', margin: '0 auto 12px' }}>
            Run virtual clock simulation to compare traditional FIFO queues against Ledger value-aware admission control under sustained 300% overload.
          </p>
          <button
            onClick={handleRunBenchmark}
            style={{
              background: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '6px 16px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Run Benchmark Simulation
          </button>
        </div>
      )}

      {error && (
        <div style={{ color: '#dc2626', fontSize: '12px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '4px', marginTop: '10px' }}>
          {error}
        </div>
      )}

      {benchmarkResult && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '11px', color: '#64748b' }}>
            <span>Scenario: <strong>{benchmarkResult.scenario}</strong> (Size: {benchmarkResult.workload_size} items)</span>
            <span>Capacity: <strong>{benchmarkResult.capacity_per_sec}/s</strong></span>
          </div>

          <table className="event-table" style={{ fontSize: '12px' }}>
            <thead>
              <tr>
                <th>Operational Metric</th>
                <th>Traditional FIFO Queue</th>
                <th>LEDGER Platform</th>
                <th>Delta Improvement</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Critical Signal Survival Rate</td>
                <td style={{ color: '#dc2626', fontWeight: 600 }}>{benchmarkResult.fifo.critical_survival_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.ledger.critical_survival_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>+{benchmarkResult.comparison.critical_survival_delta_pct}%</td>
              </tr>
              <tr>
                <td>Value Preserved Rate</td>
                <td style={{ color: '#d97706', fontWeight: 600 }}>{benchmarkResult.fifo.value_preserved_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.ledger.value_preserved_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>+{benchmarkResult.comparison.value_preserved_delta_pct}%</td>
              </tr>
              <tr>
                <td>Throughput (Items/sec)</td>
                <td>{benchmarkResult.fifo.throughput}/s</td>
                <td>{benchmarkResult.ledger.throughput}/s</td>
                <td style={{ color: '#64748b' }}>0.0</td>
              </tr>
              <tr>
                <td>Mean Latency</td>
                <td>{benchmarkResult.fifo.mean_latency_sec}s</td>
                <td>{benchmarkResult.ledger.mean_latency_sec}s</td>
                <td style={{ color: '#64748b' }}>0.00s</td>
              </tr>
              <tr>
                <td>Dropped Consequence Value</td>
                <td style={{ color: '#dc2626' }}>{benchmarkResult.fifo.dropped_value}</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.ledger.dropped_value}</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.comparison.dropped_value_delta}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
