import { useState, useRef, useCallback } from "react";
import { uploadFile } from "../api/files";

const ALLOWED_EXTS = [".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md"];
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileUploadZone({ onUpload }) {
  const [state, setState] = useState("default"); // default | dragging | uploading | success | error
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef(null);

  const validateFile = useCallback((file) => {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      return `不支持的文件类型: ${ext}。支持: ${ALLOWED_EXTS.join(", ")}`;
    }
    if (file.size > MAX_SIZE) {
      return `文件过大 (${formatSize(file.size)}，上限 50MB)`;
    }
    if (file.size === 0) {
      return "文件为空";
    }
    return null;
  }, []);

  const processFile = useCallback(async (file) => {
    const error = validateFile(file);
    if (error) {
      setState("error");
      setErrorMsg(error);
      return;
    }

    setState("uploading");
    setErrorMsg("");

    try {
      await uploadFile(file);
      setState("success");
      setTimeout(() => setState("default"), 1500);
      if (onUpload) onUpload();
    } catch (err) {
      setState("error");
      setErrorMsg(err.message || "上传失败");
    }
  }, [validateFile, onUpload]);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setState("dragging");
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setState((s) => (s === "dragging" ? "default" : s));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer?.files;
    if (files?.length) processFile(files[0]);
  };

  const handleClick = () => inputRef.current?.click();

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = "";
  };

  const isBusy = state === "uploading";

  const messages = {
    default: "上传文档 — 拖拽到此处或点击选择",
    dragging: "释放以上传文件",
    uploading: "解析中…",
    success: "上传成功 ✓",
    error: errorMsg || "上传失败",
  };

  return (
    <div
      className={`file-upload-zone ${state}`}
      onClick={isBusy ? undefined : handleClick}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      aria-label="上传文档"
    >
      <svg className="upload-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
      <span className="upload-text">{messages[state]}</span>
      {isBusy && <div className="upload-spinner" />}
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_EXTS.join(",")}
        onChange={handleFileInput}
        style={{ display: "none" }}
      />
    </div>
  );
}

export default FileUploadZone;
