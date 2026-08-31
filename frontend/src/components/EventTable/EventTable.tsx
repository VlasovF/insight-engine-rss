import React from "react";
import styles from "./EventTable.module.css";

export interface Event {
  id: string;
  title: string;
  status: "pending" | "embedded" | "evaluated";
  is_duplicate: boolean;
  published_at: string | null;
  created_at: string;
  evaluation_data?: {
    results: {
      urgency: { score: number };
      conflict: { score: number };
      surprise: { score: number };
    };
  } | null;
}

interface EventTableProps {
  events: Event[];
  loading?: boolean;
  onRowClick?: (event: Event) => void;
}

const statusLabels: Record<Event["status"], string> = {
  pending: "⏳ Pending",
  embedded: "📥 Embedded",
  evaluated: "✅ Evaluated",
};

const statusColors: Record<Event["status"], string> = {
  pending: styles.statusPending,
  embedded: styles.statusEmbedded,
  evaluated: styles.statusEvaluated,
};

const getScoreColor = (score: number): string => {
  if (score >= 0.7) return styles.indicatorHigh;
  if (score >= 0.4) return styles.indicatorMedium;
  return styles.indicatorLow;
};

const EventTable: React.FC<EventTableProps> = ({
  events,
  loading = false,
  onRowClick,
}) => {
  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner}></div>
        <p>Loading events...</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No events found</p>
        <p className={styles.hint}>Load RSS feeds to see events here</p>
      </div>
    );
  }

  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Scores</th>
            <th>Duplicate</th>
            <th>Published</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const scores = event.evaluation_data?.results;
            const hasScores = scores && event.status === "evaluated";

            return (
              <tr
                key={event.id}
                className={styles.row}
                onClick={() => onRowClick?.(event)}
              >
                <td className={styles.title}>{event.title}</td>
                <td>
                  <span
                    className={`${styles.statusBadge} ${statusColors[event.status]}`}
                  >
                    {statusLabels[event.status]}
                  </span>
                </td>
                <td>
                  {hasScores ? (
                    <div className={styles.scoreIndicators}>
                      <span
                        className={`${styles.indicator} ${getScoreColor(scores.urgency.score)}`}
                        title={`Urgency: ${(scores.urgency.score * 100).toFixed(0)}%`}
                      >
                        🔴
                      </span>
                      <span
                        className={`${styles.indicator} ${getScoreColor(scores.conflict.score)}`}
                        title={`Conflict: ${(scores.conflict.score * 100).toFixed(0)}%`}
                      >
                        🟡
                      </span>
                      <span
                        className={`${styles.indicator} ${getScoreColor(scores.surprise.score)}`}
                        title={`Surprise: ${(scores.surprise.score * 100).toFixed(0)}%`}
                      >
                        🔵
                      </span>
                    </div>
                  ) : (
                    <span className={styles.noScores}>—</span>
                  )}
                </td>
                <td>
                  {event.is_duplicate ? (
                    <span className={styles.duplicateBadge}>🔄 Duplicate</span>
                  ) : (
                    <span className={styles.uniqueBadge}>✓ Unique</span>
                  )}
                </td>
                <td className={styles.date}>
                  {event.published_at
                    ? new Date(event.published_at).toLocaleDateString()
                    : "N/A"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default EventTable;
