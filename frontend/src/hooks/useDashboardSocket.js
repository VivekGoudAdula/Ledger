import { useState, useEffect, useRef } from 'react';

export function useDashboardSocket() {
  const [data, setData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('CONNECTING');
  const wsRef = useRef(null);
  const reconnectDelayRef = useRef(1000);

  useEffect(() => {
    let isMounted = true;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host;
      const wsUrl = `${protocol}//${host}/ws/dashboard`;

      setConnectionStatus('CONNECTING');
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setConnectionStatus('LIVE STREAM');
        reconnectDelayRef.current = 1000;
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch (err) {
          console.error('Error parsing dashboard WebSocket data:', err);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setConnectionStatus('RECONNECTING');
        scheduleReconnect();
      };

      ws.onerror = () => {
        if (!isMounted) return;
        ws.close();
      };
    }

    function scheduleReconnect() {
      setTimeout(() => {
        if (isMounted) {
          reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 10000);
          connect();
        }
      }, reconnectDelayRef.current);
    }

    connect();

    async function fetchFallback() {
      try {
        // Use relative path to leverage Vite proxy (/api -> http://localhost:8000)
        const res = await fetch('/api/v1/dashboard/summary');
        if (res.ok && isMounted) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.warn('Fallback REST fetch error:', err);
      }
    }
    fetchFallback();

    return () => {
      isMounted = false;
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return { data, connectionStatus };
}
