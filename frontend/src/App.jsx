import React, { useState } from 'react';
import { useDashboardSocket } from './hooks/useDashboardSocket';
import { Sidebar } from './components/layout/Sidebar';
import { TopHeader } from './components/layout/TopHeader';
import { GlobalEventInspector } from './components/common/GlobalEventInspector';

import { OverviewPage } from './pages/OverviewPage';
import { SignalsPage } from './pages/SignalsPage';
import { CoalescingPage } from './pages/CoalescingPage';
import { ValuationPage } from './pages/ValuationPage';
import { AdmissionPage } from './pages/AdmissionPage';
import { QueuePage } from './pages/QueuePage';
import { WorkersPage } from './pages/WorkersPage';
import { IdempotencyPage } from './pages/IdempotencyPage';
import { RecoveryPage } from './pages/RecoveryPage';
import { OutcomesPage } from './pages/OutcomesPage';
import { BenchmarkPage } from './pages/BenchmarkPage';

export default function App() {
  const { data, connectionStatus } = useDashboardSocket();
  const [activeTab, setActiveTab] = useState('overview');
  const [inspectedEvent, setInspectedEvent] = useState(null);

  function renderActivePage() {
    switch (activeTab) {
      case 'overview':
        return <OverviewPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'signals':
        return <SignalsPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'coalescing':
        return <CoalescingPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'valuation':
        return <ValuationPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'admission':
        return <AdmissionPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'queue':
        return <QueuePage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'workers':
        return <WorkersPage data={data} />;
      case 'idempotency':
        return <IdempotencyPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'recovery':
        return <RecoveryPage data={data} />;
      case 'outcomes':
        return <OutcomesPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
      case 'benchmark':
        return <BenchmarkPage />;
      default:
        return <OverviewPage data={data} onSelectEvent={(e) => setInspectedEvent(e)} />;
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => setActiveTab(tab)}
        systemStatus={data?.system_status}
      />

      <main className="main-content">
        <TopHeader
          systemStatus={data?.system_status}
          connectionStatus={connectionStatus}
          totalIngress={data?.total_ingress_count}
          ingressRate={data?.ingress_rate_sec}
        />

        {renderActivePage()}
      </main>

      {inspectedEvent && (
        <GlobalEventInspector
          event={inspectedEvent}
          onClose={() => setInspectedEvent(null)}
        />
      )}
    </div>
  );
}
