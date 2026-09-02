import React, { useEffect, useCallback } from "react";
import InsightPanel from "../../components/InsightPanel/InsightPanel";
import { useSSE } from "../../hooks/useSSE";
import styles from "./Insights.module.css";

const Insights: React.FC = () => {
  const {
    stages,
    activeStage,
    isComplete,
    isError,
    error,
    insightId,
    startStream,
    reset,
    savedInsights,
    isLoadingHistory,
    loadInsight,
    displaySavedInsight,
    loadHistory,
  } = useSSE();

  const isGenerating =
    Object.values(stages).some((content) => content.length > 0) &&
    !isComplete &&
    !isError;

  const handleLoadInsight = async (id: string) => {
    const insight = await loadInsight(id);
    if (insight) {
      displaySavedInsight(insight);
    }
  };

  const handleDeleteInsight = useCallback(
    async (id: string) => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/insights/${id}`,
          {
            method: "DELETE",
          },
        );
        if (!response.ok) {
          throw new Error("Failed to delete insight");
        }
        // Refresh history
        await loadHistory();
        // If the deleted insight was currently displayed, reset view
        if (insightId === id) {
          reset();
        }
      } catch (err) {
        console.error("Failed to delete insight:", err);
      }
    },
    [insightId, loadHistory, reset],
  );

  useEffect(() => {
    return () => {
      reset();
    };
  }, [reset]);

  return (
    <div className={styles.insights}>
      <InsightPanel
        stages={stages}
        activeStage={activeStage}
        isComplete={isComplete}
        isError={isError}
        error={error}
        insightId={insightId}
        onGenerate={startStream}
        isGenerating={isGenerating}
        savedInsights={savedInsights}
        isLoadingHistory={isLoadingHistory}
        onLoadInsight={handleLoadInsight}
        onDeleteInsight={handleDeleteInsight}
      />
    </div>
  );
};

export default Insights;
