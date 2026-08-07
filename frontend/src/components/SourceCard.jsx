import { marked } from "marked";

/**
 * 将 Markdown 文本转为纯文本
 * 先通过 marked 解析，再去除 HTML 标签，保留段落结构
 * 处理规范文档中常见的 *** / ** / - 等分隔符和格式化符号
 */
function markdownToPlainText(md) {
  if (!md) return "";
  const html = marked.parse(md);
  return html
    // 块级元素结束标签 → 换行
    .replace(/<\/(p|h[1-6]|li|div|tr|ul|ol|blockquote|pre)>/g, "\n")
    // <br> → 换行
    .replace(/<br\s*\/?>/g, "\n")
    // 去除所有剩余 HTML 标签
    .replace(/<[^>]*>/g, "")
    // 合并多余空行
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function SourceCard({ source }) {
  const {
    standard_id = "",
    standard_name = "",
    chapter = "",
    clause = "",
    content = "",
    score = 0,
    source_type = "standard",
    file_id = "",
    filename = "",
  } = source;

  const cleanContent = markdownToPlainText(content);
  const isUser = source_type === "user";

  return (
    <div className={`source-card${isUser ? " source-card-user" : ""}`}>
      <div className="source-card-header">
        {isUser ? (
          <>
            <span className="source-id source-id-user">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                <polyline points="13 2 13 9 20 9" />
              </svg>
              {filename || "用户文件"}
            </span>
            <span className="source-badge-user">用户上传</span>
          </>
        ) : (
          <>
            <span className="source-id">{standard_id || "标准引用"}</span>
            {chapter && <span className="source-chapter">{chapter}</span>}
            {clause && <span className="source-chapter">§{clause}</span>}
          </>
        )}
      </div>
      {isUser && standard_id && (
        <div className="source-name">{standard_id}</div>
      )}
      {!isUser && standard_name && (
        <div className="source-name">{standard_name}</div>
      )}
      {cleanContent && (
        <div className="source-excerpt">{cleanContent}</div>
      )}
    </div>
  );
}

export default SourceCard;
