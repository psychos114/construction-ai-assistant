import SourceCard from "./SourceCard";

/**
 * 单条消息气泡
 * @param {{ message: { role: string, content: string, sources?: Array } }} props
 */
function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message ${message.role}`}>
      <div className="message-role">{isUser ? "您" : "助手"}</div>
      <div className="message-content">
        {renderContent(message.content)}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="sources-section">
            <div className="sources-title">
              📚 参考来源（{message.sources.length} 条）
            </div>
            {message.sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** 简单 Markdown 渲染（支持加粗和换行） */
function renderContent(text) {
  if (!text) return null;

  // 分割段落
  const paragraphs = text.split("\n");
  return paragraphs.map((line, i) => {
    // 加粗
    const withBold = line.replace(
      /\*\*(.+?)\*\*/g,
      "<strong>$1</strong>"
    );
    return (
      <p key={i} dangerouslySetInnerHTML={{ __html: withBold || "&nbsp;" }} />
    );
  });
}

export default MessageBubble;
