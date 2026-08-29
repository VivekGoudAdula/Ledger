import React from 'react';
import { useDashboardSocket } from './hooks/useDashboardSocket';
import { Header } from './components/Header';
import { PipelineFlow } from './components/PipelineFlow';
import { MetricCards } from './components/MetricCards';
import { EventStreamTable } from './components/EventStreamTable';
import { WorkerPoolGrid } from './components/WorkerPoolGrid';
import { RecoveryPanel } from './components/RecoveryPanel';
import { IdempotencyPanel } from './components/IdempotencyPanel';
import { SourceHealthPanel } from './components/SourceHealthPanel';
import { BenchmarkCard } from './components/BenchmarkCard';

export default function App() {
  const { data, connectionStatus } = useDashboardSocket();

  return (
    <div className="dashboard-container">
      <Header
        systemStatus={data?.system_status}
        connectionStatus={connectionStatus}
      />

      <PipelineFlow />

      <MetricCards data={data} />

      <div className="content-grid">
        <div className="col-left">
          <EventStreamTable events={data?.recent_events} />
          <WorkerPoolGrid workers={data?.workers} />
        </div>

        <div className="col-right">
          <RecoveryPanel recovery={data?.recovery} />
          <IdempotencyPanel idempotency={data?.idempotency} />
          <SourceHealthPanel sources={data?.sources} />
        </div>
      </div>

      <BenchmarkCard />
    </div>
  );
}
