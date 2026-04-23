/** React hook for consuming the SSE stream for a job. */

import { useCallback, useEffect, useRef, useState } from "react";
import { SSEEvent } from "./types";
import { sseUrl } from "./api";

interface SSEStreamState {
  events: SSEEvent[];
  isConnected: boolean;
  error: string | null;
}

/**
 * Opens an EventSource to the SSE endpoint for the given job.
 * Returns the accumulated events, connection status, and any error.
 */
export function useSSEStream(
  jobId: string | null,
  onEvent?: (event: SSEEvent) => void,
): SSEStreamState {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const appendEvent = useCallback((evt: SSEEvent) => {
    setEvents((prev) => [...prev, evt]);
    onEventRef.current?.(evt);
  }, []);

  useEffect(() => {
    if (!jobId) return;

    setEvents([]);
    setError(null);

    const url = sseUrl(jobId);
    const es = new EventSource(url);

    es.onopen = () => setIsConnected(true);
    es.onerror = () => {
      setIsConnected(false);
      if (es.readyState === EventSource.CLOSED) {
        setError("SSE connection closed.");
      }
    };

    const handler = (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data) as SSEEvent;
        appendEvent(parsed);

        if (parsed.event_type === "complete" || parsed.event_type === "error") {
          es.close();
          setIsConnected(false);
        }
      } catch {
        // Ignore malformed events.
      }
    };

    es.addEventListener("message", handler);

    return () => {
      es.removeEventListener("message", handler);
      es.close();
      setIsConnected(false);
    };
  }, [jobId, appendEvent]);

  return { events, isConnected, error };
}
