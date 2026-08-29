import React, { useState, useEffect } from 'react';
import { Radio, PauseCircle, PlayCircle } from 'lucide-react';

export function TopHeader({ systemStatus, connectionStatus, totalIngress, ingressRate }) {
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(false);

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
    <header className="top-header">
      <div>
        <h1 style={{ fontSize: '18px', fontWeight: 800, color: '#0c0a09', letterSpacing: '-0.02em' }}>
          LEDGER CONTROL PLANE
        </h1>
        <p style={{ fontSize: '12px', color: '#777169' }}>
          Value-aware admission control for AI agent systems
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={toggleIngestion}
          disabled={loading}
          style={{
            background: isPaused ? '#f0fdf4' : '#fffbeb',
            color: isPaused ? '#166534' : '#b45309',
            border: `1px solid ${isPaused ? '#bbf7d0' : '#fde68a'}`,
            padding: '6px 14px',
            borderRadius: '9999px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: loading ? 'wait' : 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          {isPaused ? <PlayCircle size={14} color="#16a34a" /> : <PauseCircle size={14} color="#b45309" />}
          {isPaused ? 'Resume Ingestion' : 'Pause Ingestion'}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: isPaused ? '#b45309' : '#16a34a' }} />
          <span>{isPaused ? 'INGESTION PAUSED' : systemStatus || 'SYSTEM HEALTHY'}</span>
        </div>

        <span className={`pill-badge ${connectionStatus === 'LIVE STREAM' || connectionStatus === 'CONNECTED' ? 'green' : 'amber'}`}>
          <Radio size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
          {connectionStatus === 'LIVE STREAM' ? 'CONNECTED' : connectionStatus}
        </span>
      </div>
    </header>
  );
}
