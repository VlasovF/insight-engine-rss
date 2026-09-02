import { useState, useEffect, useCallback, useRef } from "react";

export interface SSEStage {
  stage: "analyst" | "skeptic" | "synthesis" | "done" | "error";
  content: string;
  status: "start" | "complete" | "error";
  error?: string;
  insight_id?: string;
}

interface UseSSEResult {
  stages: Record<string, string>;
  isComplete: boolean;
  isError: boolean;
  error: string | null;
  insightId: string | null;
  startStream: () => void;
  reset: () => void;
  activeStage: string | null;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useSSE(): UseSSEResult {
  const [stages, setStages] = useState<Record<string, string>>({
    analyst: "",
    skeptic: "",
    synthesis: "",
  });
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [insightId, setInsightId] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStages({ analyst: "", skeptic: "", synthesis: "" });
    setIsComplete(false);
    setIsError(false);
    setError(null);
    setInsightId(null);
    setActiveStage(null);
  }, []);

  const startStream = useCallback(() => {
    // Reset state before starting
    reset();

    try {
      const url = `${API_URL}/api/insights/stream`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data: SSEStage = JSON.parse(event.data);

          if (data.stage === "error") {
            setIsError(true);
            setError(data.error || "Unknown error occurred");
            eventSource.close();
            return;
          }

          if (data.stage === "done") {
            setIsComplete(true);
            if (data.insight_id) {
              setInsightId(data.insight_id);
            }
            eventSource.close();
            return;
          }

          // Update stage content
          setActiveStage(data.stage);
          setStages((prev) => ({
            ...prev,
            [data.stage]: prev[data.stage] + data.content,
          }));
        } catch {
          setError("Failed to parse SSE data");
          setIsError(true);
          eventSource.close();
        }
      };

      eventSource.onerror = () => {
        setError("Connection lost to server");
        setIsError(true);
        eventSource.close();
      };
    } catch {
      setError("Failed to connect to SSE stream");
      setIsError(true);
    }
  }, [reset]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    stages,
    isComplete,
    isError,
    error,
    insightId,
    startStream,
    reset,
    activeStage,
  };
}
