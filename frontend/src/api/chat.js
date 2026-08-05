/**
 * API 调用封装 — 与后端 /api/chat 通信
 */

const API_BASE = "/api";

/**
 * 发送聊天请求
 * @param {string} question - 用户问题
 * @returns {Promise<{answer: string, sources: Array}>}
 */
export async function sendMessage(question) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `请求失败 (${response.status})`);
  }

  return response.json();
}

/**
 * 健康检查
 * @returns {Promise<{status: string, llm_model: string, index_ready: boolean}>}
 */
export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
