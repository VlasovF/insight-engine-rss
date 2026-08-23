import React from "react";
import styles from "./Pipeline.module.css";

const Pipeline: React.FC = () => {
  return (
    <div className={styles.pipeline}>
      <div className={styles.placeholder}>
        <p>⚙️ Pipeline Control coming soon...</p>
        <p className={styles.hint}>RSS fetch, embedding, evaluation controls</p>
      </div>
    </div>
  );
};

export default Pipeline;
