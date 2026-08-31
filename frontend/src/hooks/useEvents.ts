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
  evaluation_data: {
    results: {
      urgency: { score: number; summary: string };
      conflict: { score: number; summary: string };
      surprise: { score: number; summary: string };
    };
    combined_summary: string;
    pipeline_version: string;
    evaluated_at: string;
  } | null;
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
  fetchEvent: (id: string) => Promise<Event | null>;
  deleteAllEvents: () => Promise<number>;
  runEmbedding: () => Promise<{
    processed: number;
    duplicates_found: number;
    errors: number;
    batch_id: string;
  }>;
  runEvaluation: () => Promise<{
    processed: number;
    errors: number;
    batch_id: string;
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

  const fetchEvent = useCallback(async (id: string): Promise<Event | null> => {
    try {
      const response = await fetch(`${API_URL}/api/events/${id}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch event: ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return null;
    }
  }, []);

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

  const runEmbedding = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/pipeline/run_embedding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `Failed to run embedding: ${response.status}`,
        );
      }

      const data = await response.json();
      await fetchEvents({ limit: 100 });
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return { processed: 0, duplicates_found: 0, errors: 0, batch_id: "" };
    } finally {
      setLoading(false);
    }
  }, [fetchEvents]);

  const runEvaluation = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/pipeline/run_evaluation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `Failed to run evaluation: ${response.status}`,
        );
      }

      const data = await response.json();
      await fetchEvents({ limit: 100 });
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return { processed: 0, errors: 0, batch_id: "" };
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

  useEffect(() => {
    const loadInitial = async () => {
      await fetchEvents({ limit: 100 });
    };
    loadInitial();
  }, [fetchEvents]);

  return {
    events,
    total,
    loading,
    error,
    fetchEvents,
    fetchEvent,
    deleteAllEvents,
    runEmbedding,
    runEvaluation,
    getPipelineStatus,
  };
}
