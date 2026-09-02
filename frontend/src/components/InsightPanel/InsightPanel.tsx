import React, { useState, useEffect, useRef, useCallback } from "react";
import styles from "./InsightPanel.module.css";

interface InsightPanelProps {
  stages: Record<string, string>;
  activeStage: string | null;
  isComplete: boolean;
  isError: boolean;
  error: string | null;
  insightId: string | null;
  onGenerate: () => void;
  isGenerating: boolean;
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
}) => {
  const contentRefs = useRef<Record<string, HTMLDivElement | null>>({
    analyst: null,
    skeptic: null,
    synthesis: null,
  });
  const [displayedStages, setDisplayedStages] = useState<
    Record<string, string>
  >({
    analyst: "",
    skeptic: "",
    synthesis: "",
  });
  const typewriterTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Create refs using useCallback
  const setContentRef = useCallback(
    (key: string) => (el: HTMLDivElement | null) => {
      contentRefs.current[key] = el;
    },
    [],
  );

  // Typewriter effect - only runs when stages content changes
  useEffect(() => {
    const stageKeys = ["analyst", "skeptic", "synthesis"] as const;

    // Clear existing timer
    if (typewriterTimerRef.current) {
      clearTimeout(typewriterTimerRef.current);
      typewriterTimerRef.current = null;
    }

    let updatedKey: string | null = null;
    let newChar: string | null = null;

    for (const key of stageKeys) {
      const targetText = stages[key] || "";
      const currentDisplay = displayedStages[key] || "";

      // If target is shorter than current (reset case), update immediately via setTimeout
      if (targetText.length < currentDisplay.length) {
        setTimeout(() => {
          setDisplayedStages((prev) => ({
            ...prev,
            [key]: targetText,
          }));
        }, 0);
      } else if (targetText.length > currentDisplay.length) {
        // Type out one character at a time with delay
        updatedKey = key;
        newChar = targetText[currentDisplay.length];
        break; // Only type one character at a time
      }
    }

    // If we have a character to type, schedule it
    if (updatedKey && newChar !== null) {
      typewriterTimerRef.current = setTimeout(() => {
        setDisplayedStages((prev) => ({
          ...prev,
          [updatedKey]: prev[updatedKey] + newChar,
        }));
      }, 10); // 10ms per character for fast typing
    }

    // Cleanup timer on unmount or when effect re-runs
    return () => {
      if (typewriterTimerRef.current) {
        clearTimeout(typewriterTimerRef.current);
        typewriterTimerRef.current = null;
      }
    };
  }, [stages, displayedStages]);

  // Auto-scroll to bottom when content updates
  useEffect(() => {
    const stageKeys = ["analyst", "skeptic", "synthesis"] as const;
    stageKeys.forEach((key) => {
      const ref = contentRefs.current[key];
      if (ref) {
        ref.scrollTop = ref.scrollHeight;
      }
    });
  }, [displayedStages]);

  const handleGenerate = () => {
    setDisplayedStages({ analyst: "", skeptic: "", synthesis: "" });
    onGenerate();
  };

  const isAnyStageActive = Object.values(stages).some(
    (content) => content.length > 0,
  );

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3 className={styles.title}>💡 Dialectical Insight</h3>
        <button
          className={styles.generateButton}
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? "⏳ Generating..." : "🚀 Generate Insight"}
        </button>
      </div>

      {isError && (
        <div className={styles.error}>
          ❌ {error || "An error occurred during generation"}
        </div>
      )}

      {isComplete && (
        <div className={styles.success}>
          ✅ Insight generated successfully!
          {insightId && (
            <span className={styles.insightId}>
              ID: {insightId.slice(0, 8)}
            </span>
          )}
        </div>
      )}

      {!isAnyStageActive && !isGenerating && !isError && !isComplete && (
        <div className={styles.placeholder}>
          <p>Click "Generate Insight" to create a dialectical synthesis</p>
          <p className={styles.hint}>Requires at least 2 evaluated events</p>
        </div>
      )}

      <div className={styles.stagesGrid}>
        {["analyst", "skeptic", "synthesis"].map((key) => {
          const content = displayedStages[key] || "";
          const isActive = activeStage === key;
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
          <button className={styles.downloadButton} onClick={handleGenerate}>
            🔄 Regenerate
          </button>
        </div>
      )}
    </div>
  );
};

export default InsightPanel;
