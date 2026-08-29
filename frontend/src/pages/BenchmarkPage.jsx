import React from 'react';
import { BenchmarkPanel } from '../components/BenchmarkPanel';

export function BenchmarkPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">FIFO VS LEDGER BENCHMARK</h2>
          <p className="page-description">Virtual clock engine benchmark comparing standard FIFO queues vs Ledger under 300% overload</p>
        </div>
        <span className="pill-badge green">Virtual Engine</span>
      </div>

      <BenchmarkPanel />
    </div>
  );
}
