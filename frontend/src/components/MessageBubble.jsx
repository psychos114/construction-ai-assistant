import SourceCard from "./SourceCard";

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const hasSources = !isUser && message.sources && message.sources.length > 0;

  return (
    <div className={`message ${message.role}`}>
      <div className="message-label">
        {isUser ? "您" : "助手"}
      </div>
      <div className="message-body">
        {renderContent(message.content)}
        {hasSources && (
          <div className="sources-container">
            <div className="sources-title">参考来源 · {message.sources.length} 条</div>
            {message.sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function renderContent(text) {
  if (!text) return null;
  const paragraphs = text.split("\n");
  return paragraphs.map((line, i) => {
    const html = line
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>");
    return (
      <p key={i} dangerouslySetInnerHTML={{ __html: html || "&nbsp;" }} />
    );
  });
}

export default MessageBubble;
