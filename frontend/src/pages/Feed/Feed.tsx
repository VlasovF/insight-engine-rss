import React, { useState } from "react";
import EventTable from "../../components/EventTable/EventTable";
import EventModal from "../../components/EventModal/EventModal";
import { useEvents } from "../../hooks/useEvents";
import styles from "./Feed.module.css";

const Feed: React.FC = () => {
  const { events, total, loading, fetchEvents, fetchEvent } = useEvents();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

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

  const handleRowClick = (event: { id: string }) => {
    setSelectedEventId(event.id);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEventId(null);
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

      <EventTable
        events={events}
        loading={loading}
        onRowClick={handleRowClick}
      />

      <EventModal
        eventId={selectedEventId}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onFetchEvent={fetchEvent}
      />
    </div>
  );
};

export default Feed;
