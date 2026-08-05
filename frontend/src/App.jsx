import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import { healthCheck } from "./api/chat";

function App() {
  const [status, setStatus] = useState(null);

  useState(() => {
    healthCheck()
      .then((data) => setStatus(data))
      .catch(() => setStatus({ error: true }));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏗️ 土木工程智能助手</h1>
        <div className="header-status">
          {status ? (
            status.error ? (
              <span className="status-offline">⚠️ 后端未连接</span>
            ) : (
              <span className="status-online">
                ✅ {status.llm_model}
                {status.index_ready ? " · 知识库就绪" : " · 知识库未加载"}
              </span>
            )
          ) : (
            <span className="status-loading">🔄 连接中...</span>
          )}
        </div>
      </header>
      <main className="app-main">
        <ChatWindow />
      </main>
    </div>
  );
}

export default App;
