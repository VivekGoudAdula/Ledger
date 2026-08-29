import React, { useState, useEffect } from 'react';
import { Radio, PauseCircle, PlayCircle } from 'lucide-react';

export function TopHeader({ systemStatus, connectionStatus }) {
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
        <h1 style={{ fontFamily: 'Times New Roman, serif', fontSize: '28px', fontWeight: 300, color: '#0c0a09', letterSpacing: '-0.02em' }}>
          Ledger Control Plane
        </h1>
        <p style={{ fontSize: '14px', color: '#4e4e4e' }}>
          Value-aware admission control for AI agent systems
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <button
          onClick={toggleIngestion}
          disabled={loading}
          className="button-outline"
          style={{ fontSize: '13px', padding: '6px 16px' }}
        >
          {isPaused ? <PlayCircle size={14} color="#16a34a" /> : <PauseCircle size={14} color="#b45309" />}
          {isPaused ? 'Resume Ingestion' : 'Pause Ingestion'}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 500, color: '#292524' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: isPaused ? '#b45309' : '#16a34a' }} />
          <span>{isPaused ? 'INGESTION PAUSED' : systemStatus || 'SYSTEM HEALTHY'}</span>
        </div>

        <span className={`pill-badge ${connectionStatus === 'LIVE STREAM' || connectionStatus === 'CONNECTED' ? 'green' : 'amber'}`}>
          <Radio size={13} style={{ marginRight: 4, verticalAlign: 'middle' }} />
          {connectionStatus === 'LIVE STREAM' ? 'CONNECTED' : connectionStatus}
        </span>
      </div>
    </header>
  );
}
