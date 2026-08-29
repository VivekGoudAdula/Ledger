import React from 'react';
import { MetricCards } from '../components/MetricCards';
import { PipelineMap } from '../components/PipelineMap';
import { SourcePanel } from '../components/SourcePanel';
import { SystemHealthPanel } from '../components/SystemHealthPanel';
import { WorkerPanel } from '../components/WorkerPanel';
import { RecoveryPanel } from '../components/RecoveryPanel';
import { EventTrace } from '../components/EventTrace';

export function OverviewPage({ data, onSelectEvent }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Executive System Overview</h2>
          <p className="page-description">Real-time health, capacity, admission pipeline, and execution status</p>
        </div>
        <span className="pill-badge green">● Operational</span>
      </div>

      <MetricCards data={data} />

      <PipelineMap />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <SourcePanel sources={data?.sources} />
        <SystemHealthPanel systemStatus={data?.system_status} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <WorkerPanel workers={data?.workers} />
        <RecoveryPanel recovery={data?.recovery} />
      </div>

      <EventTrace
        events={data?.recent_events}
        onSelectEventForValuation={onSelectEvent}
      />
    </div>
  );
}
