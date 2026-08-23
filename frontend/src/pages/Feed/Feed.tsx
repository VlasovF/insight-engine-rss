import React from "react";
import styles from "./Feed.module.css";

const Feed: React.FC = () => {
  return (
    <div className={styles.feed}>
      <div className={styles.placeholder}>
        <p>📰 Feed coming soon...</p>
        <p className={styles.hint}>RSS articles will appear here</p>
      </div>
    </div>
  );
};

export default Feed;
