import React, { useEffect, useRef, useCallback } from "react";
import styles from "./InsightPanel.module.css";

interface SavedInsight {
  id: string;
  content: string;
  event_count: number;
  created_at: string;
  stages?: {
    analyst: string;
    skeptic: string;
    synthesis: string;
  } | null;
}

interface InsightPanelProps {
  stages: Record<string, string>;
  activeStage: string | null;
  isComplete: boolean;
  isError: boolean;
  error: string | null;
  insightId: string | null;
  onGenerate: () => void;
  isGenerating: boolean;
  savedInsights: SavedInsight[];
  isLoadingHistory: boolean;
  onLoadInsight: (id: string) => Promise<void>;
  onDeleteInsight?: (id: string) => Promise<void>;
}

const stageLabels: Record<string, string> = {
  analyst: "📊 Analyst",
  skeptic: "🤔 Skeptic",
  synthesis: "✨ Synthesis",
};

const stageIcons: Record<string, string> = {
  analyst: "🔍",
  skeptic: "🧐",
  synthesis: "💡",
};

const stageColors: Record<string, string> = {
  analyst: styles.stageAnalyst,
  skeptic: styles.stageSkeptic,
  synthesis: styles.stageSynthesis,
};

const InsightPanel: React.FC<InsightPanelProps> = ({
  stages,
  activeStage,
  isComplete,
  isError,
  error,
  insightId,
  onGenerate,
  isGenerating,
  savedInsights,
  isLoadingHistory,
  onLoadInsight,
  onDeleteInsight,
}) => {
  const contentRefs = useRef<Record<string, HTMLDivElement | null>>({
    analyst: null,
    skeptic: null,
    synthesis: null,
  });

  // Create refs using useCallback
  const setContentRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      contentRefs.current[key] = el;
    },
    [],
  );

  // Scroll to bottom when content updates
  useEffect(() => {
    const stageKeys = ["analyst", "skeptic", "synthesis"] as const;
    stageKeys.forEach((key) => {
      const ref = contentRefs.current[key];
      if (ref) {
        ref.scrollTop = ref.scrollHeight;
      }
    });
  }, [stages]);

  const handleLoadInsight = async (id: string) => {
    await onLoadInsight(id);
  };

  const handleDeleteInsight = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("Delete this insight?")) {
      await onDeleteInsight?.(id);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const hasContent = Object.values(stages).some(
    (content) => content.length > 0,
  );

  // Get current insight stages or use empty
  const displayStages = hasContent
    ? stages
    : { analyst: "", skeptic: "", synthesis: "" };

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3 className={styles.title}>💡 Dialectical Insight</h3>
        <button
          className={styles.generateButton}
          onClick={onGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? "⏳ Generating..." : "🚀 Generate Insight"}
        </button>
      </div>

      {/* History sidebar */}
      <div className={styles.historySection}>
        <div className={styles.historyHeader}>
          <span className={styles.historyTitle}>📚 History</span>
          <span className={styles.historyCount}>
            {savedInsights.length}{" "}
            {savedInsights.length === 1 ? "insight" : "insights"}
          </span>
          {isLoadingHistory && <span className={styles.loadingBadge}>⏳</span>}
        </div>
        <div className={styles.historyList}>
          {savedInsights.length === 0 && !isLoadingHistory && (
            <p className={styles.historyEmpty}>No insights generated yet</p>
          )}
          {savedInsights.map((insight) => (
            <div
              key={insight.id}
              className={`${styles.historyItem} ${insight.id === insightId ? styles.activeHistory : ""}`}
              onClick={() => handleLoadInsight(insight.id)}
            >
              <div className={styles.historyItemHeader}>
                <span className={styles.historyDate}>
                  {formatDate(insight.created_at)}
                </span>
                <span className={styles.historyBadge}>
                  {insight.event_count} events
                </span>
                {onDeleteInsight && (
                  <button
                    className={styles.deleteButton}
                    onClick={(e) => handleDeleteInsight(insight.id, e)}
                    title="Delete insight"
                  >
                    ✕
                  </button>
                )}
              </div>
              <div className={styles.historyPreview}>
                {insight.content.slice(0, 120)}...
              </div>
            </div>
          ))}
        </div>
      </div>

      {isError && (
        <div className={styles.error}>
          ❌ {error || "An error occurred during generation"}
        </div>
      )}

      {isComplete && insightId && (
        <div className={styles.success}>
          ✅ Insight generated successfully!
          <span className={styles.insightId}>ID: {insightId.slice(0, 8)}</span>
        </div>
      )}

      {!hasContent && !isGenerating && !isError && !isComplete && (
        <div className={styles.placeholder}>
          <p>Click "Generate Insight" to create a dialectical synthesis</p>
          <p className={styles.hint}>Requires at least 2 evaluated events</p>
        </div>
      )}

      <div className={styles.stagesGrid}>
        {["analyst", "skeptic", "synthesis"].map((key) => {
          const content = displayStages[key] || "";
          const isActive = activeStage === key && isGenerating;
          const isDone = isComplete || (content.length > 0 && !isActive);

          return (
            <div
              key={key}
              className={`${styles.stageCard} ${stageColors[key]} ${
                isActive ? styles.active : ""
              } ${isDone && !isActive ? styles.done : ""}`}
            >
              <div className={styles.stageHeader}>
                <span className={styles.stageIcon}>{stageIcons[key]}</span>
                <span className={styles.stageLabel}>{stageLabels[key]}</span>
                {isActive && (
                  <span className={styles.statusBadge}>⏳ Generating...</span>
                )}
                {isDone && !isActive && content.length > 0 && (
                  <span className={styles.statusBadge}>✅ Complete</span>
                )}
              </div>
              <div className={styles.stageContent} ref={setContentRef(key)}>
                {content || (
                  <span className={styles.placeholderText}>
                    {isActive ? "Generating..." : "Waiting..."}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {isComplete && (
        <div className={styles.actions}>
          <button
            className={styles.downloadButton}
            onClick={onGenerate}
            disabled={isGenerating}
          >
            🔄 Regenerate
          </button>
        </div>
      )}
    </div>
  );
};

export default InsightPanel;
