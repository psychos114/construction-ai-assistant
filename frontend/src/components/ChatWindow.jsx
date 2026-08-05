import { useState, useRef, useEffect } from "react";
import { sendMessage } from "../api/chat";
import MessageBubble from "./MessageBubble";

const EXAMPLE_QUESTIONS = [
  "地下室外墙防水有哪些规范要求？",
  "梁钢筋搭接长度是多少？",
  "施工现场临时用电有哪些规定？",
  "深基坑施工需要注意哪些安全问题？",
];

function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
    ]);
    setLoading(true);

    try {
      const result = await sendMessage(question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          sources: result.sources || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ 抱歉，查询出错了：${err.message}`,
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <h2>👷 我是您的土木工程智能助手</h2>
            <p style={{ marginBottom: 12 }}>
              基于中国国家标准(GB)、行业标准(JGJ/JTG/SL) 和法律法规，
              <br />
              为您提供专业的土木工程知识问答。
            </p>
            <p style={{ marginBottom: 8, fontWeight: 600 }}>试试这些问题：</p>
            <ul>
              {EXAMPLE_QUESTIONS.map((q, i) => (
                <li
                  key={i}
                  style={{ cursor: "pointer", color: "var(--color-primary-light)" }}
                  onClick={() => setInput(q)}
                >
                  {q}
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-role">助手</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题，如：梁钢筋搭接长度是多少？"
            rows={1}
            disabled={loading}
          />
          <button onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? "思考中" : "发送"}
          </button>
        </div>
        <p className="chat-disclaimer">
          ⚠️ 答案仅供参考，实际工程请以官方发布的最新标准规范为准
        </p>
      </div>
    </div>
  );
}

export default ChatWindow;
