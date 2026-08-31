import React, { useState, useEffect, useCallback } from "react";
import styles from "./PipelineControl.module.css";

interface PipelineStatus {
  pending: number;
  embedded: number;
  evaluated: number;
}

interface PipelineControlProps {
  onFetchFeed: (urls: string[]) => Promise<void>;
  onClearEvents: () => Promise<number>;
  onRunEmbedding: () => Promise<{
    processed: number;
    duplicates_found: number;
    errors: number;
    batch_id: string;
  }>;
  onRunEvaluation: () => Promise<{
    processed: number;
    errors: number;
    batch_id: string;
  }>;
  onGetStatus: () => Promise<Record<string, number>>;
  isLoading?: boolean;
}

const PipelineControl: React.FC<PipelineControlProps> = ({
  onFetchFeed,
  onClearEvents,
  onRunEmbedding,
  onRunEvaluation,
  onGetStatus,
  isLoading = false,
}) => {
  const [feedUrls, setFeedUrls] = useState<string>("");
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [isEmbedding, setIsEmbedding] = useState<boolean>(false);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [status, setStatus] = useState<PipelineStatus>({
    pending: 0,
    embedded: 0,
    evaluated: 0,
  });
  const [embeddingResult, setEmbeddingResult] = useState<{
    processed: number;
    duplicates: number;
    errors: number;
  } | null>(null);
  const [evaluationResult, setEvaluationResult] = useState<{
    processed: number;
    errors: number;
  } | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const data = await onGetStatus();
      setStatus({
        pending: data.pending || 0,
        embedded: data.embedded || 0,
        evaluated: data.evaluated || 0,
      });
    } catch {
      // Silently fail
    }
  }, [onGetStatus]);

  useEffect(() => {
    const loadInitial = async () => {
      await loadStatus();
    };
    loadInitial();

    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  const handleFetchFeed = async () => {
    if (!feedUrls.trim()) {
      setError("Please enter at least one RSS feed URL");
      return;
    }

    const urls = feedUrls
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url.length > 0);

    if (urls.length === 0) {
      setError("Please enter at least one valid URL");
      return;
    }

    setIsFetching(true);
    setError(null);
    setSuccess(null);

    try {
      await onFetchFeed(urls);
      setSuccess(`Successfully fetched ${urls.length} feed(s)`);
      setFeedUrls("");
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch feeds");
    } finally {
      setIsFetching(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Delete all events? This action cannot be undone.")) {
      return;
    }

    setIsClearing(true);
    setError(null);
    setSuccess(null);

    try {
      const count = await onClearEvents();
      setSuccess(`Deleted ${count} event(s)`);
      setEmbeddingResult(null);
      setEvaluationResult(null);
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear events");
    } finally {
      setIsClearing(false);
    }
  };

  const handleRunEmbedding = async () => {
    setIsEmbedding(true);
    setError(null);
    setSuccess(null);
    setEmbeddingResult(null);

    try {
      const result = await onRunEmbedding();
      setEmbeddingResult({
        processed: result.processed,
        duplicates: result.duplicates_found,
        errors: result.errors,
      });
      setSuccess(
        `Embedding completed: ${result.processed} events processed (batch: ${result.batch_id.slice(0, 8)})`,
      );
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run embedding");
    } finally {
      setIsEmbedding(false);
    }
  };

  const handleRunEvaluation = async () => {
    setIsEvaluating(true);
    setError(null);
    setSuccess(null);
    setEvaluationResult(null);

    try {
      const result = await onRunEvaluation();
      setEvaluationResult({
        processed: result.processed,
        errors: result.errors,
      });
      setSuccess(
        `Evaluation completed: ${result.processed} events evaluated (batch: ${result.batch_id.slice(0, 8)})`,
      );
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run evaluation");
    } finally {
      setIsEvaluating(false);
    }
  };

  const isBusy =
    isLoading || isFetching || isClearing || isEmbedding || isEvaluating;

  return (
    <div className={styles.control}>
      {/* Pipeline Status */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>📊 Pipeline Status</h3>
        <div className={styles.statusGrid}>
          <div className={`${styles.statusItem} ${styles.statusPending}`}>
            <span className={styles.statusLabel}>Pending</span>
            <span className={styles.statusValue}>{status.pending}</span>
          </div>
          <div className={`${styles.statusItem} ${styles.statusEmbedded}`}>
            <span className={styles.statusLabel}>Embedded</span>
            <span className={styles.statusValue}>{status.embedded}</span>
          </div>
          <div className={`${styles.statusItem} ${styles.statusEvaluated}`}>
            <span className={styles.statusLabel}>Evaluated</span>
            <span className={styles.statusValue}>{status.evaluated}</span>
          </div>
        </div>
        <button
          className={styles.refreshButton}
          onClick={loadStatus}
          disabled={isBusy}
        >
          🔄 Refresh Status
        </button>
      </div>

      <div className={styles.divider} />

      {/* Embedding */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>🧠 Run Embedding</h3>
        <button
          className={`${styles.button} ${styles.embedButton}`}
          onClick={handleRunEmbedding}
          disabled={isBusy || status.pending === 0}
        >
          {isEmbedding ? "⏳ Embedding..." : "🧠 Run Embedding"}
        </button>
        {status.pending === 0 && !isEmbedding && (
          <p className={styles.hint}>No pending events to embed</p>
        )}
        {embeddingResult && (
          <div className={styles.result}>
            <span>✅ Processed: {embeddingResult.processed}</span>
            <span>🔄 Duplicates: {embeddingResult.duplicates}</span>
            <span>❌ Errors: {embeddingResult.errors}</span>
          </div>
        )}
      </div>

      {/* Evaluation */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>📊 Run Evaluation</h3>
        <button
          className={`${styles.button} ${styles.evaluateButton}`}
          onClick={handleRunEvaluation}
          disabled={isBusy || status.embedded === 0}
        >
          {isEvaluating ? "⏳ Evaluating..." : "📊 Run Evaluation"}
        </button>
        {status.embedded === 0 && !isEvaluating && (
          <p className={styles.hint}>No embedded events to evaluate</p>
        )}
        {evaluationResult && (
          <div className={styles.result}>
            <span>✅ Processed: {evaluationResult.processed}</span>
            <span>❌ Errors: {evaluationResult.errors}</span>
          </div>
        )}
      </div>

      <div className={styles.divider} />

      {/* RSS Feed Loading */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>📡 Load RSS Feeds</h3>
        <div className={styles.inputGroup}>
          <textarea
            className={styles.textarea}
            value={feedUrls}
            onChange={(e) => setFeedUrls(e.target.value)}
            placeholder="Enter RSS feed URLs (one per line)&#10;e.g. https://news.ycombinator.com/rss"
            rows={3}
            disabled={isBusy}
          />
          <button
            className={styles.button}
            onClick={handleFetchFeed}
            disabled={isBusy || !feedUrls.trim()}
          >
            {isFetching ? "Loading..." : "📥 Fetch Feeds"}
          </button>
        </div>
      </div>

      <div className={styles.divider} />

      {/* Data Management */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>🗑️ Data Management</h3>
        <button
          className={`${styles.button} ${styles.dangerButton}`}
          onClick={handleClear}
          disabled={isBusy}
        >
          {isClearing ? "Deleting..." : "🗑️ Clear All Events"}
        </button>
        <p className={styles.hint}>
          This will delete all events from the database
        </p>
      </div>

      {error && <div className={styles.error}>❌ {error}</div>}

      {success && <div className={styles.success}>✅ {success}</div>}
    </div>
  );
};

export default PipelineControl;
