import { useState, useRef, useEffect, useCallback } from "react";
import { sendCombinedStream } from "../api/chat";
import MessageBubble from "./MessageBubble";

const SUGGESTED = [
  "地下室外墙防水规范要求？",
  "梁钢筋搭接长度是多少？",
  "施工现场临时用电规定？",
  "深基坑施工安全注意事项？",
];

function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const abortRef = useRef(null);

  // 组件卸载时取消进行中的 SSE 请求
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 页面加载时从 localStorage 恢复历史消息
  useEffect(() => {
    try {
      const saved = localStorage.getItem("chat-history");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch {
      // JSON 解析失败则忽略
    }
  }, []);

  // 消息变化时自动保存到 localStorage
  useEffect(() => {
    if (messages.length === 0) return;
    // 保存前清洗：未完成的流式消息标记为已结束
    const toSave = messages.map((msg) =>
      msg.streaming
        ? { ...msg, streaming: false, content: msg.content || "[回答中断—刷新页面时流未完成]" }
        : msg
    );
    try {
      localStorage.setItem("chat-history", JSON.stringify(toSave));
    } catch {
      // localStorage 满了则静默失败
    }
  }, [messages]);

  const handleSend = useCallback(async (text) => {
    const question = (text || input).trim();
    if (!question || loading) return;

    setInput("");
    const userMsg = { role: "user", content: question };
    const aiMsg = { role: "assistant", content: "", reasoning: "", analysis: null, sources: [], streaming: true };
    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setLoading(true);

    try {
      // 创建 AbortController 以支持取消请求
      const controller = new AbortController();
      abortRef.current = controller;
      const stream = sendCombinedStream(question, { signal: controller.signal });
      for await (const event of stream) {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || last.role !== "assistant") return prev;

          // 不可变更新：创建新对象，不修改 prev state（React 严格模式安全）
          let updates = {};

          if (event.type === "reasoning") {
            updates = { reasoning: last.reasoning + event.content };
          } else if (event.type === "analysis") {
            updates = { analysis: event.data };
          } else if (event.type === "token") {
            updates = { content: last.content + event.content };
          } else if (event.type === "source") {
            updates = { sources: [...last.sources, event.data] };
          } else if (event.type === "done") {
            updates = { streaming: false };
          } else if (event.type === "error") {
            updates = { content: `抱歉，查询出错：${event.message}`, streaming: false };
          } else if (event.type === "tool_call") {
            // Agent 调用了工具 — 在 sources 中展示工具使用记录
            updates = { sources: [...last.sources, { source_type: "tool", tool_name: event.tool, content: event.content }] };
          } else {
            return prev;
          }

          const updated = [...prev];
          updated[updated.length - 1] = { ...last, ...updates };
          return updated;
        });
      }
    } catch (err) {
      // AbortError 是正常取消，不需显示错误
      if (err.name === "AbortError") return;

      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== "assistant") return prev;
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...last,
          content: `网络错误：${err.message}`,
          streaming: false,
        };
        return updated;
      });
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  }, [input, loading]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-hero">
            <div className="chat-hero-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
              </svg>
            </div>
            <h2>您好，我是您的土木工程智能助手</h2>
            <p>基于中国国家标准(GB)、行业标准(JGJ/JTG/SL)和法律法规，为建筑工程从业人员提供专业规范查询与解答。</p>
            <div className="suggested-questions">
              {SUGGESTED.map((q, i) => (
                <button key={i} onClick={() => { setInput(q); textareaRef.current?.focus(); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))
        )}

        {loading && messages[messages.length - 1]?.streaming === false && (
          <div className="message assistant">
            <div className="message-label">思考中</div>
            <div className="message-body">
              <div className="typing-indicator"><span /><span /><span /></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入规范相关问题，如：梁钢筋搭接长度是多少？"
            rows={1}
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            aria-label="发送"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
        <div className="chat-input-footer">
          {messages.length > 0 && (
            <button
              className="clear-history-btn"
              onClick={() => {
                localStorage.removeItem("chat-history");
                setMessages([]);
              }}
              disabled={loading}
            >
              清空对话
            </button>
          )}
          <p className="chat-disclaimer">答案仅供参考，实际工程请以官方发布的最新标准规范为准</p>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
