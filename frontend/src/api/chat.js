/**
 * API 封装 — 支持普通 + 流式两种模式
 */

const API_BASE = "/api";

/** 普通请求 */
export async function sendMessage(question) {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 流式请求 — 返回 ReadableStream
 *
 * 使用方式:
 *   const stream = sendMessageStream("问题", { signal: abortController.signal });
 *   for await (const event of stream) {
 *     if (event.type === "token")  追加文本
 *     if (event.type === "source") 添加引用
 *     if (event.type === "done")   流结束
 *   }
 */
export async function* sendMessageStream(question, options = {}) {
  const resp = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal: options.signal,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // 保留不完整的行

    for (const line of lines) {
      if (!line.trim() || !line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        yield data;
        if (data.type === "done" || data.type === "error") return;
      } catch {
        // 跳过解析失败的行
      }
    }
  }
}

/** 健康检查 */
export async function healthCheck() {
  const resp = await fetch(`${API_BASE}/health`);
  return resp.json();
}
