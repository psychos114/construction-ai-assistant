import { useState, useEffect } from "react";
import ChatWindow from "./components/ChatWindow";
import FilePanel from "./components/FilePanel";
import { healthCheck } from "./api/chat";

function App() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    healthCheck()
      .then((data) => setStatus(data))
      .catch(() => setStatus({ error: true }));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 20h20" /><path d="M5 20V8l7-5 7 5v12" /><path d="M9 20v-6h6v6" />
          </svg>
          土木工程智能助手
        </h1>
        <div className="header-status">
          {status ? (
            status.error ? (
              <>
                <span className="status-dot offline" />
                服务未连接
              </>
            ) : (
              <>
                <span className="status-dot" />
                {status.index_ready ? "知识库就绪" : "知识库加载中"}
              </>
            )
          ) : (
            "连接中..."
          )}
        </div>
      </header>
      <div className="app-body">
        <FilePanel />
        <main className="app-main">
          <ChatWindow />
        </main>
      </div>
    </div>
  );
}

export default App;
