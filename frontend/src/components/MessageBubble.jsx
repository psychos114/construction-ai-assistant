import { useState, useEffect, useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import SourceCard from "./SourceCard";

// 配置 marked 安全选项
marked.setOptions({
  breaks: true,
  gfm: true,
});

/** 安全解析 Markdown → 消毒后的 HTML */
function renderMarkdown(text) {
  if (!text) return null;
  const rawHtml = marked.parse(text);
  return DOMPurify.sanitize(rawHtml);
}

/** 分析摘要字段的中文标签 */
const ANALYSIS_LABELS = {
  question: "问题概括",
  retrieval: "规范检索",
  reasoning: "分析推理",
  conclusion: "分析结论",
};

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const isStreaming = message.streaming === true;
  const hasSources = !isUser && message.sources && message.sources.length > 0;
  const hasAnalysis = !isUser && message.analysis;
  const hasReasoning = !isUser && message.reasoning;

  const [analysisExpanded, setAnalysisExpanded] = useState(false);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);

  // 分析摘要到达时自动展开；流式完成后自动折叠
  useEffect(() => {
    if (hasAnalysis && isStreaming) {
      setAnalysisExpanded(true);
    } else if (hasAnalysis && !isStreaming) {
      setAnalysisExpanded(false);
    }
  }, [hasAnalysis, isStreaming]);

  // 思考过程：流式时展开，完成后折叠
  useEffect(() => {
    if (hasReasoning && isStreaming) {
      setReasoningExpanded(true);
    } else if (hasReasoning && !isStreaming) {
      setReasoningExpanded(false);
    }
  }, [hasReasoning, isStreaming]);

  // 缓存 Markdown 解析：仅在回答内容变化时重新解析（经过 DOMPurify 消毒）
  const contentHtml = useMemo(() => {
    return renderMarkdown(message.content);
  }, [message.content]);

  return (
    <div className={`message ${message.role}`}>
      <div className="message-label">
        {isUser ? "您" : isStreaming ? "回答中..." : "助手"}
      </div>
      <div className="message-body">
        {/* ===== 思考过程（流式推理链）===== */}
        {hasReasoning && (
          <div className={`thinking-section${isStreaming ? " thinking-active" : ""}`}>
            <button
              className="thinking-header"
              onClick={() => setReasoningExpanded(!reasoningExpanded)}
              aria-expanded={reasoningExpanded}
            >
              <span className="thinking-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/>
                  <path d="M12 6v4l2.5 2.5"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <circle cx="15.5" cy="8.5" r="1.5"/>
                </svg>
              </span>
              <span className="thinking-label">
                {isStreaming ? "思考中…" : "思考过程"}
              </span>
              <span className={`thinking-toggle${reasoningExpanded ? " expanded" : ""}`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </span>
            </button>
            {reasoningExpanded && (
              <div className="thinking-content reasoning-content">
                <p className="analysis-field-text">{message.reasoning}</p>
              </div>
            )}
          </div>
        )}

        {/* ===== 分析摘要区域（纯文本，不走 Markdown 解析）===== */}
        {hasAnalysis && (
          <div className={`thinking-section${isStreaming ? " thinking-active" : ""}`}>
            <button
              className="thinking-header"
              onClick={() => setAnalysisExpanded(!analysisExpanded)}
              aria-expanded={analysisExpanded}
            >
              <span className="thinking-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/>
                  <path d="M12 6v4l2.5 2.5"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <circle cx="15.5" cy="8.5" r="1.5"/>
                </svg>
              </span>
              <span className="thinking-label">
                {isStreaming ? "分析中..." : "分析摘要"}
              </span>
              <span className={`thinking-toggle${analysisExpanded ? " expanded" : ""}`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </span>
            </button>
            {analysisExpanded && (
              <div className="thinking-content">
                {/* 纯文本渲染，不经过 marked.parse() */}
                {Object.entries(ANALYSIS_LABELS).map(([key, label]) => {
                  const text = message.analysis[key];
                  if (!text) return null;
                  return (
                    <div key={key} className="analysis-field">
                      <span className="analysis-field-label">{label}</span>
                      <p className="analysis-field-text">{text}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ===== 回答区域（Markdown 解析）===== */}
        {contentHtml && (
          <div className="markdown-body" dangerouslySetInnerHTML={{ __html: contentHtml }} />
        )}
        {isStreaming && <span className="streaming-cursor" />}

        {/* ===== 引用来源 ===== */}
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

export default MessageBubble;
