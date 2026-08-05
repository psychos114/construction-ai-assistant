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
        <span className="source-id">{standard_id || "标准引用"}</span>
        {chapter && <span className="source-chapter">{chapter}</span>}
        {clause && <span className="source-chapter">§{clause}</span>}
      </div>
      {standard_name && (
        <div className="source-name">{standard_name}</div>
      )}
      {content && (
        <div className="source-excerpt">{content}</div>
      )}
    </div>
  );
}

export default SourceCard;
