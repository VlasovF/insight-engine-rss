import React, { ReactNode } from "react";
import styles from "./Layout.module.css";

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <h1 className={styles.title}>Insight Engine</h1>
        <p className={styles.subtitle}>
          News analytics pipeline with dialectical insights
        </p>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
};

export default Layout;
