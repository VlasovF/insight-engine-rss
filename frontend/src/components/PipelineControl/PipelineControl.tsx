import React, { useState } from "react";
import styles from "./PipelineControl.module.css";

interface PipelineControlProps {
  onFetchFeed: (urls: string[]) => Promise<void>;
  onClearEvents: () => Promise<void>;
  isLoading?: boolean;
}

const PipelineControl: React.FC<PipelineControlProps> = ({
  onFetchFeed,
  onClearEvents,
  isLoading = false,
}) => {
  const [feedUrls, setFeedUrls] = useState<string>("");
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear events");
    } finally {
      setIsClearing(false);
    }
  };

  const isBusy = isLoading || isFetching || isClearing;

  return (
    <div className={styles.control}>
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>📡 Load RSS Feeds</h3>
        <div className={styles.inputGroup}>
          <textarea
            className={styles.textarea}
            value={feedUrls}
            onChange={(e) => setFeedUrls(e.target.value)}
            placeholder="Enter RSS feed URLs (one per line)&#10;e.g. https://example.com/rss"
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
