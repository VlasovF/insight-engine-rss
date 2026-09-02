import React, { useEffect } from "react";
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
  } = useSSE();

  const isGenerating =
    Object.values(stages).some((content) => content.length > 0) &&
    !isComplete &&
    !isError;

  // Reset state when component unmounts
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
      />
    </div>
  );
};

export default Insights;
