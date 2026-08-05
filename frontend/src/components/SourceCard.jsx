/**
 * 规范来源引用卡片
 * @param {{ source: { standard_id: string, standard_name: string, chapter: string, clause: string, content: string, score: number } }} props
 */
function SourceCard({ source }) {
  const {
    standard_id = "",
    standard_name = "",
    chapter = "",
    clause = "",
    content = "",
    score = 0,
  } = source;

  return (
    <div className="source-card">
      <div className="source-card-header">
        <span className="source-card-id">
          {standard_id}
          {clause ? ` · 第${clause}条` : ""}
        </span>
        {chapter && <span className="source-card-chapter">{chapter}</span>}
      </div>
      {standard_name && (
        <div style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", marginBottom: 4 }}>
          {standard_name}
        </div>
      )}
      {content && <div className="source-card-content">{content}</div>}
    </div>
  );
}

export default SourceCard;
