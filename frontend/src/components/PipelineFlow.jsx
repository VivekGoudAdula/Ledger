import React, { useState } from 'react';
import { Zap } from 'lucide-react';

export function PipelineFlow() {
  const [selectedStage, setSelectedStage] = useState('Admission');

  const stages = [
    { 
      name: 'Sources', 
      desc: 'Raw webhook & API signal ingestion from GitHub, Status feeds, and Infrastructure Telemetry.',
      tech: 'GitHub REST, Statuspage JSON, Telemetry Adapters',
      status: 'UP'
    },
    { 
      name: 'Ingestion', 
      desc: 'Payload validation, size limits (2MB), SHA-256 fingerprint hashing, and canonical SignalEvent normalization.',
      tech: 'EventNormalizer, Payload Hash Deduplication',
      status: 'ACTIVE'
    },
    { 
      name: 'Coalescing', 
      desc: '5-minute sliding window grouping of related signals into single actionable Incidents.',
      tech: 'CoalescingService, IncidentORM Linking',
      status: 'ACTIVE'
    },
    { 
      name: 'Valuation', 
      desc: 'AI & Rule-based value estimation computing Urgency × Consequence / Compute Cost (Value-per-Compute ratio).',
      tech: 'RuleBasedValueEstimator, LLM Estimator',
      status: 'ACTIVE'
    },
    { 
      name: 'Admission', 
      desc: 'Deterministic value-aware admission control evaluating VpC against capacity & tenant quotas with aging starvation guard.',
      tech: 'AdmissionController (ADMIT / DEFER / SHED)',
      status: 'ACTIVE'
    },
    { 
      name: 'Queue Stream', 
      desc: 'Durable multi-consumer stream queue supporting Redis Streams & In-Memory Stream Broker.',
      tech: 'Redis Streams / MemoryStreamBroker',
      status: 'ACTIVE'
    },
    { 
      name: 'Workers', 
      desc: 'Concurrent worker execution pool processing admitted queue messages with execution checkpointing.',
      tech: 'LedgerWorker Pool (worker-1, worker-2, worker-3)',
      status: 'RUNNING'
    },
    { 
      name: 'Idempotency', 
      desc: 'Database-backed composite unique key guard preventing duplicate side-effects across worker crashes.',
      tech: 'IdempotencyRepository (SQLite WAL)',
      status: 'GUARDED'
    },
  ];

  const currentInfo = stages.find((s) => s.name === selectedStage) || stages[4];

  return (
    <section className="pipeline-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          End-to-End Operational Pipeline (Click any stage to view architecture details)
        </span>
      </div>

      <div className="pipeline-flow">
        {stages.map((st, idx) => {
          const isSelected = selectedStage === st.name;
          return (
            <React.Fragment key={st.name}>
              <div
                className={`pipeline-stage ${isSelected ? 'active' : ''}`}
                onClick={() => setSelectedStage(st.name)}
                style={{ cursor: 'pointer', userSelect: 'none' }}
                title={`Click to inspect ${st.name} stage`}
              >
                {st.name}
              </div>
              {idx < stages.length - 1 && <span className="arrow">→</span>}
            </React.Fragment>
          );
        })}
      </div>

      {currentInfo && (
        <div style={{ marginTop: '10px', padding: '12px 16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={14} color="#2563eb" /> {currentInfo.name} Phase Architecture
            </span>
            <span style={{ fontSize: '10px', background: '#dbeafe', color: '#1e40af', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
              {currentInfo.status}
            </span>
          </div>
          <p style={{ margin: '4px 0', color: '#334155', lineHeight: '1.4' }}>
            {currentInfo.desc}
          </p>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
            <strong>Sub-Engine:</strong> {currentInfo.tech}
          </div>
        </div>
      )}
    </section>
  );
}
