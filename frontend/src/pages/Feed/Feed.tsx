import React, { useState } from "react";
import EventTable from "../../components/EventTable/EventTable";
import { useEvents } from "../../hooks/useEvents";
import styles from "./Feed.module.css";

const Feed: React.FC = () => {
  const { events, total, loading, fetchEvents } = useEvents();
  const [statusFilter, setStatusFilter] = useState<string>("");

  const handleFilterChange = (status: string) => {
    setStatusFilter(status);
    fetchEvents({
      status: status || undefined,
      limit: 100,
    });
  };

  const handleRefresh = () => {
    fetchEvents({
      status: statusFilter || undefined,
      limit: 100,
    });
  };

  return (
    <div className={styles.feed}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>📰 News Feed</h2>
          <p className={styles.subtitle}>
            {total} event{total !== 1 ? "s" : ""} found
          </p>
        </div>
        <div className={styles.controls}>
          <select
            className={styles.filter}
            value={statusFilter}
            onChange={(e) => handleFilterChange(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="embedded">Embedded</option>
            <option value="evaluated">Evaluated</option>
          </select>
          <button
            className={styles.refreshButton}
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? "⏳" : "🔄"}
          </button>
        </div>
      </div>
      <EventTable events={events} loading={loading} />
    </div>
  );
};

export default Feed;
