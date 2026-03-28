/**
 * useJobStream – Custom Hook für Server-Sent Events Job-Status-Updates.
 *
 * Verbindet sich mit GET /api/v1/jobs/{jobId}/stream und liefert Echtzeit-Updates.
 * Fällt automatisch auf Polling zurück wenn SSE nicht verfügbar ist.
 */

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../api/client.js";
import type { GenerationJobStatus } from "../api/generation.js";

export interface JobStreamData {
  job_id: string;
  job_type: string;
  status: GenerationJobStatus;
  result_url: string | null;
  glb_file_path: string | null;
  asset_id: string | null;
  error_type: string | null;
  error_detail: string | null;
  updated_at: string | null;
}

interface UseJobStreamOptions {
  /** Aktiviert den Stream nur wenn true (default: true) */
  enabled?: boolean;
  /** Polling-Intervall als Fallback in ms (default: 3000) */
  pollIntervalMs?: number;
}

interface UseJobStreamResult {
  data: JobStreamData | null;
  isStreaming: boolean;
  error: string | null;
}

export function useJobStream(
  jobId: string | null,
  options: UseJobStreamOptions = {}
): UseJobStreamResult {
  const { enabled = true, pollIntervalMs = 3000 } = options;

  const [data, setData] = useState<JobStreamData | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId || !enabled) {
      return;
    }

    // Prüfen ob wir uns bereits in einem abgeschlossenen Zustand befinden
    if (data && (data.status === "done" || data.status === "failed")) {
      return;
    }

    const apiKey = import.meta.env.VITE_API_KEY as string | undefined;
    const streamUrl = `${API_BASE}/api/v1/jobs/${jobId}/stream`;

    // SSE mit Authorization via URL-Parameter wenn nötig
    // (EventSource unterstützt keine custom Headers im Browser)
    const urlWithAuth = apiKey
      ? `${streamUrl}?api_key=${encodeURIComponent(apiKey)}`
      : streamUrl;

    let es: EventSource | null = null;

    const startPollingFallback = () => {
      // Polling-Fallback wenn SSE nicht verfügbar
      const { apiClient } = require("../api/client.js");
      pollRef.current = setInterval(async () => {
        try {
          const { data: jobData } = await apiClient.get(
            `/jobs?limit=1&job_id_filter=${jobId}`
          );
          if (jobData) {
            setData(jobData);
          }
        } catch {
          // Polling-Fehler ignorieren
        }
      }, pollIntervalMs);
    };

    try {
      es = new EventSource(urlWithAuth);
      esRef.current = es;
      setIsStreaming(true);
      setError(null);

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as JobStreamData;
          setData(parsed);

          if (parsed.status === "done" || parsed.status === "failed") {
            es?.close();
            esRef.current = null;
            setIsStreaming(false);
          }
        } catch {
          // Ungültige JSON-Daten ignorieren
        }
      };

      es.addEventListener("done", () => {
        es?.close();
        esRef.current = null;
        setIsStreaming(false);
      });

      es.addEventListener("error_event", (event) => {
        try {
          const parsed = JSON.parse((event as MessageEvent).data) as { error: string };
          setError(parsed.error);
        } catch {
          setError("SSE Verbindungsfehler");
        }
        es?.close();
        esRef.current = null;
        setIsStreaming(false);
      });

      es.addEventListener("timeout", () => {
        es?.close();
        esRef.current = null;
        setIsStreaming(false);
      });

      es.onerror = () => {
        // EventSource hat keinen guten Error-Recovery-Mechanismus
        // Bei Fehler: SSE schließen und auf Polling-Fallback wechseln
        if (es?.readyState === EventSource.CLOSED) {
          esRef.current = null;
          setIsStreaming(false);
        }
      };
    } catch {
      // SSE nicht verfügbar (z.B. älterer Browser) – Polling-Fallback
      startPollingFallback();
    }

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      setIsStreaming(false);
    };
  }, [jobId, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, isStreaming, error };
}
