import React from "react";
import styles from "./EventTable.module.css";

export interface Event {
  id: string;
  title: string;
  status: "pending" | "embedded" | "evaluated";
  is_duplicate: boolean;
  published_at: string | null;
  created_at: string;
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
            <th>Duplicate</th>
            <th>Published</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
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
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default EventTable;
