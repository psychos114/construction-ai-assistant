import { useState, useEffect, useCallback } from "react";
import { listFiles, deleteFile } from "../api/files";
import FileUploadZone from "./FileUploadZone";

function formatSize(bytes) {
  if (!bytes || bytes < 1024) return `${bytes || 0} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay} 天前`;
  return d.toLocaleDateString("zh-CN");
}

const FILE_ICONS = {
  ".pdf": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  ".docx": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  ".pptx": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
      <polyline points="8 10 12 6 16 10" /><line x1="12" y1="6" x2="12" y2="14" />
    </svg>
  ),
  ".xlsx": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" /><line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  ),
  ".txt": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 7 4 4 20 4 20 7" /><line x1="9" y1="20" x2="15" y2="20" /><line x1="12" y1="4" x2="12" y2="20" />
    </svg>
  ),
  ".md": (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  ),
};

const DEFAULT_ICON = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
    <polyline points="13 2 13 9 20 9" />
  </svg>
);

function FilePanel() {
  const [collapsed, setCollapsed] = useState(false);
  const [files, setFiles] = useState([]);
  const [filesState, setFilesState] = useState("loading"); // loading | empty | error | populated
  const [deleting, setDeleting] = useState(null);

  const fetchFiles = useCallback(async () => {
    setFilesState("loading");
    try {
      const data = await listFiles();
      setFiles(data.files || []);
      setFilesState((data.files || []).length > 0 ? "populated" : "empty");
    } catch {
      setFilesState("error");
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleDelete = async (fileId, filename) => {
    if (!window.confirm(`确认删除「${filename}」？此操作不可撤销。`)) return;
    setDeleting(fileId);
    try {
      await deleteFile(fileId);
      setFiles((prev) => prev.filter((f) => f.file_id !== fileId));
    } catch (err) {
      alert(`删除失败: ${err.message}`);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <aside className={`file-panel${collapsed ? " collapsed" : ""}`}>
      <div className="file-panel-header">
        <button
          className="file-panel-toggle"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "展开文件面板" : "折叠文件面板"}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          {!collapsed && (
            <>
              <span className="file-panel-title">我的文件</span>
              {files.length > 0 && (
                <span className="file-panel-count">{files.length}</span>
              )}
            </>
          )}
        </button>
      </div>

      {!collapsed && (
        <>
          <FileUploadZone onUpload={fetchFiles} />

          <div className="file-list">
            {filesState === "loading" && (
              <div className="file-list-empty">加载中…</div>
            )}
            {filesState === "error" && (
              <div className="file-list-empty file-list-error">
                加载失败
                <button onClick={fetchFiles}>重试</button>
              </div>
            )}
            {filesState === "empty" && (
              <div className="file-list-empty">
                暂无文件<br />
                <span className="file-list-hint">
                  上传 PDF、Word、PPT、Excel、TXT 或 Markdown 文件，问答时将优先检索您的文件。
                </span>
              </div>
            )}
            {filesState === "populated" &&
              files.map((f) => (
                <div key={f.file_id} className="file-list-item">
                  <div className="file-list-item-icon">
                    {FILE_ICONS[f.file_type] || DEFAULT_ICON}
                  </div>
                  <div className="file-list-item-info">
                    <div className="file-list-item-name" title={f.filename}>
                      {f.filename}
                    </div>
                    <div className="file-list-item-meta">
                      {formatSize(f.file_size)} · {f.chunk_count} 段 · {formatTime(f.upload_time)}
                    </div>
                  </div>
                  <button
                    className="file-list-item-delete"
                    onClick={() => handleDelete(f.file_id, f.filename)}
                    disabled={deleting === f.file_id}
                    aria-label={`删除 ${f.filename}`}
                    title="删除"
                  >
                    {deleting === f.file_id ? (
                      <div className="delete-spinner" />
                    ) : (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-2 14H7L5 6" />
                        <path d="M10 11v6" /><path d="M14 11v6" />
                        <path d="M9 6V4h6v2" />
                      </svg>
                    )}
                  </button>
                </div>
              ))}
          </div>
        </>
      )}
    </aside>
  );
}

export default FilePanel;
