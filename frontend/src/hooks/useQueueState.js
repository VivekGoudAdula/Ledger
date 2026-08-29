import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook that polls GET /api/v1/queue/state every 2 seconds.
 * Returns real scheduling state from the backend — no sorting or fabrication in React.
 *
 * @returns {{ queueState: object|null, loading: boolean, error: string|null, refresh: function }}
 */
export function useQueueState() {
  const [queueState, setQueueState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  async function fetchQueueState() {
    try {
      const res = await fetch('/api/v1/queue/state');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      setQueueState(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Initial fetch immediately
    fetchQueueState();

    // Poll every 2 seconds — backend is source of truth
    intervalRef.current = setInterval(fetchQueueState, 2000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return { queueState, loading, error, refresh: fetchQueueState };
}
