/**
 * 用户文件管理 API — 上传、列表、删除
 */

const API_BASE = "/api/files";

/** 上传文件（FormData） */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const resp = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `上传失败 (${resp.status})`);
  }
  return resp.json();
}

/** 获取已上传文件列表 */
export async function listFiles() {
  const resp = await fetch(API_BASE);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `获取列表失败 (${resp.status})`);
  }
  return resp.json();
}

/** 删除文件 */
export async function deleteFile(fileId) {
  const resp = await fetch(`${API_BASE}/${fileId}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `删除失败 (${resp.status})`);
  }
  return resp.json();
}

