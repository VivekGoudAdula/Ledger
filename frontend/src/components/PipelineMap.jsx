import React, { useState } from 'react';
import { Zap } from 'lucide-react';

export function PipelineMap() {
  const [activeStage, setActiveStage] = useState('Admission');

  const stages = [
    { name: 'Sources', sectionId: 'section-sources', tech: 'GitHub, Statuspage, Telemetry', status: 'ACTIVE' },
    { name: 'Ingestion', sectionId: 'section-ingestion', tech: 'EventNormalizer & Hash Deduplication', status: 'ACTIVE' },
    { name: 'Coalescing', sectionId: 'section-coalescing', tech: '5-Min Window Incident Grouping', status: 'ACTIVE' },
    { name: 'Valuation', sectionId: 'section-valuation', tech: 'Rule-Based / LLM Consequence Scoring', status: 'ACTIVE' },
    { name: 'Admission', sectionId: 'section-admission', tech: 'Value-per-Compute Deterministic Guard', status: 'ACTIVE' },
    { name: 'Queue', sectionId: 'section-queue', tech: 'Redis Streams / Memory Broker', status: 'ACTIVE' },
    { name: 'Workers', sectionId: 'section-workers', tech: 'Multi-Worker Supervisor Pool', status: 'RUNNING' },
    { name: 'Idempotency', sectionId: 'section-idempotency', tech: 'Composite Unique Key SQLite WAL Guard', status: 'GUARDED' },
    { name: 'Recovery', sectionId: 'section-recovery', tech: 'Stale Claim Reclaim Engine', status: 'ACTIVE' },
    { name: 'Outcomes', sectionId: 'section-outcomes', tech: 'Outcome Feedback & Telemetry Recorder', status: 'ACTIVE' },
  ];

  function handleStageClick(stage) {
    setActiveStage(stage.name);
    const el = document.getElementById(stage.sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  const currentInfo = stages.find((s) => s.name === activeStage) || stages[4];

  return (
    <section className="pipeline-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          End-to-End Control Pipeline (Click any stage to jump to subsystem panel)
        </span>
      </div>

      <div className="pipeline-flow" style={{ flexWrap: 'wrap', gap: '4px' }}>
        {stages.map((st, idx) => {
          const isSelected = activeStage === st.name;
          return (
            <React.Fragment key={st.name}>
              <div
                className={`pipeline-stage ${isSelected ? 'active' : ''}`}
                onClick={() => handleStageClick(st)}
                style={{ cursor: 'pointer', userSelect: 'none', fontSize: '11px', padding: '5px 10px' }}
                title={`Jump to ${st.name} subsystem`}
              >
                {st.name}
              </div>
              {idx < stages.length - 1 && <span className="arrow" style={{ fontSize: '10px' }}>→</span>}
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ marginTop: '8px', padding: '8px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '11px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#0f172a', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Zap size={13} color="#2563eb" /> Active Subsystem Inspector: <strong>{currentInfo.name}</strong> ({currentInfo.tech})
        </span>
        <span style={{ fontSize: '10px', background: '#dbeafe', color: '#1e40af', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
          {currentInfo.status}
        </span>
      </div>
    </section>
  );
}
