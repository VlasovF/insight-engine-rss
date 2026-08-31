import React from "react";
import PipelineControl from "../../components/PipelineControl/PipelineControl";
import { useEvents } from "../../hooks/useEvents";
import styles from "./Pipeline.module.css";

const Pipeline: React.FC = () => {
  const {
    loading,
    fetchEvents,
    deleteAllEvents,
    runEmbedding,
    runEvaluation,
    getPipelineStatus,
  } = useEvents();

  const handleFetchFeed = async (urls: string[]) => {
    const response = await fetch("http://localhost:8000/api/feeds/fetch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ feed_urls: urls }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to fetch feeds");
    }

    await fetchEvents({ limit: 100 });
  };

  const handleClearEvents = async (): Promise<number> => {
    const deleted = await deleteAllEvents();
    return deleted;
  };

  return (
    <div className={styles.pipeline}>
      <h2 className={styles.title}>⚙️ Pipeline Control</h2>
      <p className={styles.description}>
        Load RSS feeds, run embedding, evaluate events, and manage data in the
        pipeline
      </p>
      <PipelineControl
        onFetchFeed={handleFetchFeed}
        onClearEvents={handleClearEvents}
        onRunEmbedding={runEmbedding}
        onRunEvaluation={runEvaluation}
        onGetStatus={getPipelineStatus}
        isLoading={loading}
      />
    </div>
  );
};

export default Pipeline;
