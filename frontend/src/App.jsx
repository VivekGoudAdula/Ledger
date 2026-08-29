import React, { useState } from 'react';
import { useDashboardSocket } from './hooks/useDashboardSocket';
import { SystemHeader } from './components/SystemHeader';
import { PipelineMap } from './components/PipelineMap';
import { MetricCards } from './components/MetricCards';
import { SourcePanel } from './components/SourcePanel';
import { IngestionPanel } from './components/IngestionPanel';
import { CoalescingPanel } from './components/CoalescingPanel';
import { ValueEstimatorPanel } from './components/ValueEstimatorPanel';
import { AdmissionPanel } from './components/AdmissionPanel';
import { QueuePanel } from './components/QueuePanel';
import { WorkerPanel } from './components/WorkerPanel';
import { IdempotencyPanel } from './components/IdempotencyPanel';
import { RecoveryPanel } from './components/RecoveryPanel';
import { OutcomePanel } from './components/OutcomePanel';
import { EventTrace } from './components/EventTrace';
import { BenchmarkPanel } from './components/BenchmarkPanel';
import { SystemHealthPanel } from './components/SystemHealthPanel';

export default function App() {
  const { data, connectionStatus } = useDashboardSocket();
  const [selectedValuationEvent, setSelectedValuationEvent] = useState(null);

  return (
    <div className="dashboard-container">
      <SystemHeader
        systemStatus={data?.system_status}
        connectionStatus={connectionStatus}
        totalIngress={data?.total_ingress_count}
        ingressRate={data?.ingress_rate_sec}
      />

      <PipelineMap />

      <MetricCards data={data} />

      {/* Row 1: Ingestion & Signal Intake Subsystems */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        <SourcePanel sources={data?.sources} />
        <IngestionPanel
          ingressRate={data?.ingress_rate_sec}
          totalIngress={data?.total_ingress_count}
          recentEvents={data?.recent_events}
        />
        <CoalescingPanel totalIngress={data?.total_ingress_count} />
      </div>

      {/* Row 2: Value Estimation & Admission Control */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <ValueEstimatorPanel selectedEvent={selectedValuationEvent || (data?.recent_events && data.recent_events[0])} />
        <AdmissionPanel data={data} />
      </div>

      {/* Row 3: Queue Broker & Worker Pool */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <QueuePanel pendingCount={data?.queue_pending_count} />
        <WorkerPanel workers={data?.workers} />
      </div>

      {/* Row 4: Idempotency & Failure Recovery */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <IdempotencyPanel idempotency={data?.idempotency} />
        <RecoveryPanel recovery={data?.recovery} />
      </div>

      {/* Row 5: Outcomes & System Health */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <OutcomePanel data={data} />
        <SystemHealthPanel systemStatus={data?.system_status} />
      </div>

      {/* Full Width: Live Trace Table with End-to-End Lifecycle Drawer */}
      <EventTrace
        events={data?.recent_events}
        onSelectEventForValuation={(evt) => setSelectedValuationEvent(evt)}
      />

      {/* Full Width: FIFO vs LEDGER Benchmark */}
      <BenchmarkPanel />
    </div>
  );
}
