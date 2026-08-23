import React from "react";
import styles from "./Insights.module.css";

const Insights: React.FC = () => {
  return (
    <div className={styles.insights}>
      <div className={styles.placeholder}>
        <p>💡 Insights coming soon...</p>
        <p className={styles.hint}>Dialectical synthesis will appear here</p>
      </div>
    </div>
  );
};

export default Insights;
