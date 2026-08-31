import React, { useEffect, useState } from "react";
import styles from "./EventModal.module.css";

interface EvaluationScores {
  urgency: { score: number; summary: string };
  conflict: { score: number; summary: string };
  surprise: { score: number; summary: string };
}

interface EventData {
  id: string;
  title: string;
  content: string;
  source_url: string | null;
  status: string;
  is_duplicate: boolean;
  published_at: string | null;
  evaluation_data: {
    results: EvaluationScores;
    combined_summary: string;
    pipeline_version: string;
    evaluated_at: string;
  } | null;
}

interface EventModalProps {
  eventId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onFetchEvent: (id: string) => Promise<EventData | null>;
}

const scoreColor = (score: number): string => {
  if (score >= 0.7) return styles.scoreHigh;
  if (score >= 0.4) return styles.scoreMedium;
  return styles.scoreLow;
};

const scoreLabel = (score: number): string => {
  if (score >= 0.7) return "High";
  if (score >= 0.4) return "Medium";
  return "Low";
};

const EventModal: React.FC<EventModalProps> = ({
  eventId,
  isOpen,
  onClose,
  onFetchEvent,
}) => {
  const [event, setEvent] = useState<EventData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && eventId) {
      const loadEvent = async () => {
        setLoading(true);
        setError(null);
        try {
          const data = await onFetchEvent(eventId);
          setEvent(data);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to load event");
        } finally {
          setLoading(false);
        }
      };
      loadEvent();
    }
  }, [isOpen, eventId, onFetchEvent]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const renderEvaluation = () => {
    if (!event?.evaluation_data) {
      return (
        <div className={styles.noData}>
          <p>No evaluation data available</p>
          <p className={styles.hint}>Run the evaluation pipeline first</p>
        </div>
      );
    }

    const { results, combined_summary, evaluated_at } = event.evaluation_data;
    const scores: {
      key: keyof EvaluationScores;
      label: string;
      emoji: string;
    }[] = [
      { key: "urgency", label: "Urgency", emoji: "🔴" },
      { key: "conflict", label: "Conflict", emoji: "🟡" },
      { key: "surprise", label: "Surprise", emoji: "🔵" },
    ];

    return (
      <div className={styles.evaluation}>
        <div className={styles.scores}>
          {scores.map(({ key, label, emoji }) => {
            const data = results[key];
            return (
              <div key={key} className={styles.scoreCard}>
                <div className={styles.scoreHeader}>
                  <span className={styles.scoreEmoji}>{emoji}</span>
                  <span className={styles.scoreLabel}>{label}</span>
                </div>
                <div
                  className={`${styles.scoreValue} ${scoreColor(data.score)}`}
                >
                  {(data.score * 100).toFixed(0)}%
                </div>
                <div
                  className={`${styles.scoreBadge} ${scoreColor(data.score)}`}
                >
                  {scoreLabel(data.score)}
                </div>
                <p className={styles.scoreSummary}>{data.summary}</p>
              </div>
            );
          })}
        </div>

        <div className={styles.combinedSummary}>
          <h4>📝 Combined Summary</h4>
          <p>{combined_summary}</p>
        </div>

        <div className={styles.metadata}>
          <span>Pipeline: {event.evaluation_data.pipeline_version}</span>
          <span>Evaluated: {new Date(evaluated_at).toLocaleString()}</span>
        </div>
      </div>
    );
  };

  return (
    <div className={styles.overlay} onClick={handleBackdropClick}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2 className={styles.title}>{event?.title || "Loading..."}</h2>
          <button className={styles.closeButton} onClick={onClose}>
            ✕
          </button>
        </div>

        <div className={styles.body}>
          {loading && (
            <div className={styles.loading}>
              <div className={styles.spinner}></div>
              <p>Loading event details...</p>
            </div>
          )}

          {error && <div className={styles.error}>❌ {error}</div>}

          {event && !loading && (
            <>
              <div className={styles.meta}>
                <span
                  className={`${styles.statusBadge} ${styles[event.status]}`}
                >
                  Status: {event.status}
                </span>
                {event.is_duplicate && (
                  <span className={styles.duplicateBadge}>🔄 Duplicate</span>
                )}
                {event.source_url && (
                  <a
                    href={event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.sourceLink}
                  >
                    🔗 Source
                  </a>
                )}
                {event.published_at && (
                  <span className={styles.date}>
                    Published: {new Date(event.published_at).toLocaleString()}
                  </span>
                )}
              </div>

              <div className={styles.content}>
                <h4>📄 Content</h4>
                <p>{event.content}</p>
              </div>

              <div className={styles.evaluationSection}>
                <h4>📊 Evaluation</h4>
                {renderEvaluation()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EventModal;
