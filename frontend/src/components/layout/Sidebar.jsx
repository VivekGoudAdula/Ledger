import React from 'react';
import {
  LayoutDashboard,
  Radio,
  GitMerge,
  Cpu,
  ShieldCheck,
  Database,
  Server,
  Lock,
  RefreshCw,
  CheckCircle2,
  BarChart3,
} from 'lucide-react';

export function Sidebar({ activeTab, onSelectTab, systemStatus }) {
  const isHealthy = systemStatus !== 'OVERLOADED' && systemStatus !== 'DOWN';

  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, status: 'green' },
    { id: 'signals', label: 'Signals & Ingestion', icon: Radio, status: 'green' },
    { id: 'coalescing', label: 'Coalescing', icon: GitMerge, status: 'green' },
    { id: 'valuation', label: 'Value Estimation', icon: Cpu, status: 'green' },
    { id: 'admission', label: 'Admission Control', icon: ShieldCheck, status: isHealthy ? 'green' : 'amber' },
    { id: 'queue', label: 'Queue Broker', icon: Database, status: 'green' },
    { id: 'workers', label: 'Worker Execution', icon: Server, status: 'green' },
    { id: 'idempotency', label: 'Idempotency Store', icon: Lock, status: 'green' },
    { id: 'recovery', label: 'Failure Recovery', icon: RefreshCw, status: 'green' },
    { id: 'outcomes', label: 'Outcomes & Feedback', icon: CheckCircle2, status: 'green' },
    { id: 'benchmark', label: 'FIFO vs Ledger', icon: BarChart3, status: 'green' },
  ];

  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-brand">
          <img src="/logo.png" alt="Ledger Logo" className="sidebar-logo" />
          <div>
            <div className="sidebar-title">LEDGER</div>
            <div className="sidebar-subtitle">Control Plane</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-group-label">Operational Subsystems</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <div
                key={item.id}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(item.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Icon size={16} />
                  <span>{item.label}</span>
                </div>
                <span className={`nav-item-status ${item.status}`} />
              </div>
            );
          })}
        </nav>
      </div>

      <div style={{ padding: '12px 10px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e7e5e4', fontSize: '11px' }}>
        <div style={{ color: '#777169', fontWeight: 600 }}>System Telemetry</div>
        <div style={{ color: '#0c0a09', fontWeight: 700, marginTop: '2px' }}>
          ● {systemStatus || 'HEALTHY'}
        </div>
      </div>
    </aside>
  );
}
