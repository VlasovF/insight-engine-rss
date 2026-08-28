import { useState, useCallback, useEffect } from "react";

export interface Event {
  id: string;
  title: string;
  content: string;
  source_url: string | null;
  published_at: string | null;
  status: "pending" | "embedded" | "evaluated";
  is_duplicate: boolean;
  content_hash: string;
  evaluation_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface UseEventsResult {
  events: Event[];
  total: number;
  loading: boolean;
  error: string | null;
  fetchEvents: (params?: {
    status?: string;
    isDuplicate?: boolean;
    limit?: number;
    offset?: number;
  }) => Promise<void>;
  deleteAllEvents: () => Promise<number>;
  runEmbedding: () => Promise<{
    processed: number;
    duplicates_found: number;
    errors: number;
  }>;
  getPipelineStatus: () => Promise<Record<string, number>>;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useEvents(): UseEventsResult {
  const [events, setEvents] = useState<Event[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(
    async (params?: {
      status?: string;
      isDuplicate?: boolean;
      limit?: number;
      offset?: number;
    }) => {
      setLoading(true);
      setError(null);

      try {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append("status", params.status);
        if (params?.isDuplicate !== undefined)
          queryParams.append("is_duplicate", String(params.isDuplicate));
        if (params?.limit) queryParams.append("limit", String(params.limit));
        if (params?.offset) queryParams.append("offset", String(params.offset));

        const url = `${API_URL}/api/events/?${queryParams.toString()}`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Failed to fetch events: ${response.status}`);
        }

        const data = await response.json();
        setEvents(data.items || []);
        setTotal(data.total || 0);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const deleteAllEvents = useCallback(async (): Promise<number> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/events/`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Failed to delete events: ${response.status}`);
      }

      const data = await response.json();
      setEvents([]);
      setTotal(0);
      return data.deleted_count || 0;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return 0;
    } finally {
      setLoading(false);
    }
  }, []);

  const runEmbedding = useCallback(async (): Promise<{
    processed: number;
    duplicates_found: number;
    errors: number;
  }> => {
    setLoading(true);
    setError(null);

    try {
      console.log("🚀 Running embedding pipeline...");
      const response = await fetch(`${API_URL}/api/pipeline/run_embedding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("❌ Embedding failed:", errorData);
        throw new Error(
          errorData.detail || `Failed to run embedding: ${response.status}`,
        );
      }

      const data = await response.json();
      console.log("✅ Embedding completed:", data);

      // Refresh events after embedding
      await fetchEvents({ limit: 100 });

      return data;
    } catch (err) {
      console.error("❌ Embedding error:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return { processed: 0, duplicates_found: 0, errors: 0 };
    } finally {
      setLoading(false);
    }
  }, [fetchEvents]);

  const getPipelineStatus = useCallback(async (): Promise<
    Record<string, number>
  > => {
    try {
      const response = await fetch(`${API_URL}/api/pipeline/status`);
      if (!response.ok) {
        throw new Error(`Failed to get pipeline status: ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return {};
    }
  }, []);

  // Initial load on mount
  useEffect(() => {
    const loadInitial = async () => {
      await fetchEvents({ limit: 100 });
    };
    loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    events,
    total,
    loading,
    error,
    fetchEvents,
    deleteAllEvents,
    runEmbedding,
    getPipelineStatus,
  };
}
