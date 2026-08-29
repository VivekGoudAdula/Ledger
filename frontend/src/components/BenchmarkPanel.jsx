import React, { useState, useEffect } from 'react';
import { Play, RefreshCw, Sliders } from 'lucide-react';

export function BenchmarkPanel() {
  const [loading, setLoading] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [error, setError] = useState(null);

  const [scenario, setScenario] = useState('sustained_overload');
  const [size, setSize] = useState(3000);
  const [capacity, setCapacity] = useState(10.0);
  const [seed, setSeed] = useState(42);

  async function handleRunBenchmark(overrideSize = size, overrideScenario = scenario) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/benchmark/run?scenario=${overrideScenario}&size=${overrideSize}&seed=${seed}&capacity=${capacity}`, {
        method: 'POST',
      });
      if (res.ok) {
        const json = await res.json();
        setBenchmarkResult(json);
      } else {
        setError('Failed to execute benchmark.');
      }
    } catch (err) {
      console.error('Benchmark execution error:', err);
      setError('Network error contacting benchmark engine.');
    } finally {
      setLoading(false);
    }
  }

  // Auto-run default benchmark on mount
  useEffect(() => {
    handleRunBenchmark(3000, 'sustained_overload');
  }, []);

  return (
    <div className="panel" id="section-benchmark">
      <div className="panel-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h2>FIFO VS LEDGER BENCHMARK</h2>
          <span className="pill-badge green">Virtual Engine</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => handleRunBenchmark()}
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
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                Running Overload Benchmark...
              </>
            ) : (
              <>
                <Play size={13} />
                {benchmarkResult ? 'Re-run Benchmark' : 'Run Benchmark'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Interactive Simulation Parameters Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', background: '#f8fafc', padding: '12px 16px', borderRadius: '6px', marginBottom: '16px', border: '1px solid #e2e8f0', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase' }}>
          <Sliders size={13} /> Parameters:
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#334155' }}>
          <span>Scenario:</span>
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12px', background: '#fff' }}
          >
            <option value="sustained_overload">sustained_overload (300% Overload)</option>
            <option value="burst">burst (Spike Load)</option>
            <option value="mixed_compute">mixed_compute</option>
            <option value="deadline_pressure">deadline_pressure</option>
            <option value="multi_tenant">multi_tenant</option>
            <option value="failure_recovery">failure_recovery</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#334155' }}>
          <span>Workload Size:</span>
          <select
            value={size}
            onChange={(e) => setSize(Number(e.target.value))}
            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12px', background: '#fff' }}
          >
            <option value={100}>100 items</option>
            <option value={500}>500 items</option>
            <option value={1000}>1000 items</option>
            <option value={3000}>3000 items</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#334155' }}>
          <span>Capacity:</span>
          <select
            value={capacity}
            onChange={(e) => setCapacity(Number(e.target.value))}
            style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '12px', background: '#fff' }}
          >
            <option value={10.0}>10 / sec</option>
            <option value={25.0}>25 / sec</option>
            <option value={50.0}>50 / sec</option>
            <option value={100.0}>100 / sec</option>
          </select>
        </div>
      </div>

      {error && (
        <div style={{ color: '#dc2626', fontSize: '12px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '4px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {benchmarkResult && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', fontSize: '11px', color: '#64748b', background: '#f1f5f9', padding: '8px 12px', borderRadius: '4px' }}>
            <span>Scenario: <strong>{benchmarkResult.scenario}</strong> (Size: <strong>{benchmarkResult.workload_size}</strong> items)</span>
            <span>Capacity Constraint: <strong>{benchmarkResult.capacity_per_sec}/s</strong></span>
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
                <td style={{ fontWeight: 600 }}>Critical Signal Survival Rate</td>
                <td style={{ color: '#dc2626', fontWeight: 600 }}>{benchmarkResult.fifo.critical_survival_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.ledger.critical_survival_rate}%</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>+{benchmarkResult.comparison.critical_survival_delta_pct}%</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>Value Preserved Rate</td>
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
                <td>Low-Value Noise Shed (Preserves Critical Capacity)</td>
                <td style={{ color: '#64748b' }}>0.00 (Deferred: {benchmarkResult.fifo.deferred})</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>{benchmarkResult.ledger.dropped_value} ({benchmarkResult.ledger.shed} items)</td>
                <td style={{ color: '#16a34a', fontWeight: 700 }}>Intentionally Shed Noise</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
