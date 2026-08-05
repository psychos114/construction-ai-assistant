import { useState, useRef, useEffect } from "react";
import { sendMessage } from "../api/chat";
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text) => {
    const question = (text || input).trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const result = await sendMessage(question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, sources: result.sources || [] },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `抱歉，查询出错：${err.message}`, sources: [] },
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

        {loading && (
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
        <p className="chat-disclaimer">答案仅供参考，实际工程请以官方发布的最新标准规范为准</p>
      </div>
    </div>
  );
}

export default ChatWindow;
