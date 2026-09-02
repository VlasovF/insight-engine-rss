import { useState, useEffect, useCallback, useRef } from "react";

export interface SSEStage {
  stage: "analyst" | "skeptic" | "synthesis" | "done" | "error";
  content: string;
  status: "start" | "complete" | "error";
  error?: string;
  insight_id?: string;
}

export interface SavedInsight {
  id: string;
  content: string;
  event_ids: string[] | null;
  event_count: number;
  stages: {
    analyst: string;
    skeptic: string;
    synthesis: string;
  } | null;
  created_at: string;
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
  savedInsights: SavedInsight[];
  isLoadingHistory: boolean;
  loadHistory: () => Promise<void>;
  loadInsight: (id: string) => Promise<SavedInsight | null>;
  displaySavedInsight: (insight: SavedInsight) => void;
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
  const [savedInsights, setSavedInsights] = useState<SavedInsight[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const isMountedRef = useRef<boolean>(true);

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

  const loadHistory = useCallback(async () => {
    if (!isMountedRef.current) return;
    setIsLoadingHistory(true);
    try {
      const response = await fetch(`${API_URL}/api/insights/?limit=20`);
      if (!response.ok) {
        throw new Error(`Failed to load insights: ${response.status}`);
      }
      const data = await response.json();
      if (isMountedRef.current) {
        setSavedInsights(data.items || []);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(
          err instanceof Error ? err.message : "Failed to load insight history",
        );
        setIsError(true);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoadingHistory(false);
      }
    }
  }, []);

  const loadInsight = useCallback(
    async (id: string): Promise<SavedInsight | null> => {
      try {
        const response = await fetch(`${API_URL}/api/insights/${id}`);
        if (!response.ok) {
          throw new Error(`Failed to load insight: ${response.status}`);
        }
        return await response.json();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load insight");
        setIsError(true);
        return null;
      }
    },
    [],
  );

  const displaySavedInsight = useCallback(
    (insight: SavedInsight) => {
      reset();
      if (insight.stages) {
        setStages({
          analyst: insight.stages.analyst || "",
          skeptic: insight.stages.skeptic || "",
          synthesis: insight.stages.synthesis || "",
        });
      } else {
        setStages({
          analyst: "",
          skeptic: "",
          synthesis: insight.content || "",
        });
      }
      setIsComplete(true);
      setInsightId(insight.id);
    },
    [reset],
  );

  const startStream = useCallback(() => {
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
              // Refresh history after new insight
              loadHistory();
            }
            eventSource.close();
            return;
          }

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
  }, [reset, loadHistory]);

  // Load history on mount - using a separate effect with no setState in body
  useEffect(() => {
    const loadHistoryOnMount = async () => {
      await loadHistory();
    };
    loadHistoryOnMount();
  }, [loadHistory]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
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
    savedInsights,
    isLoadingHistory,
    loadHistory,
    loadInsight,
    displaySavedInsight,
  };
}
