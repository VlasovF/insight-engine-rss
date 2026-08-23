import React, { useState } from "react";
import Layout from "./components/Layout/Layout";
import Tabs, { type Tab } from "./components/Tabs/Tabs";
import Feed from "./pages/Feed/Feed";
import Pipeline from "./pages/Pipeline/Pipeline";
import Insights from "./pages/Insights/Insights";
import styles from "./App.module.css";

const tabs: Tab[] = [
  { id: "feed", label: "📰 Feed" },
  { id: "pipeline", label: "⚙️ Pipeline" },
  { id: "insights", label: "💡 Insights" },
];

function App() {
  const [activeTab, setActiveTab] = useState<string>("feed");

  const renderContent = () => {
    switch (activeTab) {
      case "feed":
        return <Feed />;
      case "pipeline":
        return <Pipeline />;
      case "insights":
        return <Insights />;
      default:
        return <Feed />;
    }
  };

  return (
    <Layout>
      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
      <div className={styles.content}>{renderContent()}</div>
    </Layout>
  );
}

export default App;
