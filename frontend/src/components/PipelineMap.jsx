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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: '#57534e', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          END-TO-END CONTROL PIPELINE
        </span>
      </div>

      <div className="pipeline-flow">
        {stages.map((st, idx) => {
          const isSelected = activeStage === st.name;
          return (
            <React.Fragment key={st.name}>
              <div
                className={`pipeline-stage ${isSelected ? 'active' : ''}`}
                onClick={() => handleStageClick(st)}
                style={{ cursor: 'pointer', userSelect: 'none' }}
                title={`Jump to ${st.name} subsystem`}
              >
                {st.name}
              </div>
              {idx < stages.length - 1 && <span className="arrow">→</span>}
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ marginTop: '12px', padding: '10px 14px', background: '#f5f5f4', border: '1px solid #e7e5e4', borderRadius: '8px', fontSize: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#0c0a09', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Zap size={14} color="#2563eb" /> Active Subsystem Inspector: <strong>{currentInfo.name}</strong> ({currentInfo.tech})
        </span>
        <span className="pill-badge green" style={{ fontSize: '11px' }}>
          {currentInfo.status}
        </span>
      </div>
    </section>
  );
}
