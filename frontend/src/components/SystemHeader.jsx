import React, { useState, useEffect } from 'react';
import { Radio, PauseCircle, PlayCircle, Activity } from 'lucide-react';

export function SystemHeader({ systemStatus, connectionStatus, totalIngress, ingressRate }) {
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(false);
  const isOverloaded = systemStatus === 'OVERLOADED';

  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await fetch('/api/v1/ingestion/status');
        if (res.ok) {
          const json = await res.json();
          setIsPaused(json.ingestion_paused);
        }
      } catch (err) {
        console.warn('Error checking ingestion status:', err);
      }
    }
    checkStatus();
  }, []);

  async function toggleIngestion() {
    setLoading(true);
    const endpoint = isPaused ? '/api/v1/ingestion/resume' : '/api/v1/ingestion/pause';
    try {
      const res = await fetch(endpoint, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setIsPaused(json.ingestion_paused);
      }
    } catch (err) {
      console.error('Error toggling ingestion:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <header className="header">
      <div className="brand" style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/logo.png" alt="Ledger Logo" className="brand-logo" style={{ height: '38px', marginRight: '14px', borderRadius: '4px' }} />
        <div>
          <h1 className="brand-title" style={{ fontSize: '22px', fontWeight: 800 }}>LEDGER CONTROL UNIT</h1>
          <p className="brand-subtitle">Value-aware admission control for AI agent systems</p>
        </div>
      </div>

      <div className="status-badge-container" style={{ gap: '12px' }}>
        <button
          onClick={toggleIngestion}
          disabled={loading}
          title={isPaused ? "Resume background signal ingestion" : "Pause background signal ingestion to save API calls"}
          style={{
            background: isPaused ? '#f0fdf4' : '#fffbeb',
            color: isPaused ? '#166534' : '#b45309',
            border: `1px solid ${isPaused ? '#bbf7d0' : '#fde68a'}`,
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: loading ? 'wait' : 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          {isPaused ? <PlayCircle size={14} color="#16a34a" /> : <PauseCircle size={14} color="#d97706" />}
          {isPaused ? 'Resume Ingestion' : 'Pause Ingestion'}
        </button>

        <span className={`pulse-dot ${isPaused ? 'amber' : isOverloaded ? 'red' : 'green'}`} />
        <span style={{ fontWeight: 600, fontSize: '12px', letterSpacing: '0.02em' }}>
          SYSTEM {isPaused ? 'PAUSED ⏸️' : systemStatus || 'HEALTHY'}
        </span>
        <span className={`ws-badge ${connectionStatus === 'LIVE STREAM' || connectionStatus === 'CONNECTED' ? 'live' : 'connecting'}`}>
          <Radio size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
          {connectionStatus === 'LIVE STREAM' ? 'CONNECTED' : connectionStatus}
        </span>
      </div>
    </header>
  );
}
