/**
 * API 封装 — 支持普通 + 流式两种模式（RAG / Agent）
 */

const API_BASE = "/api";

/** SSE 流式响应解析器（async generator） */
async function* parseSSEStream(resp) {
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
 * RAG 流式请求 — 知识库检索增强生成
 *
 * 使用方式:
 *   const stream = sendMessageStream("问题", { signal: abortController.signal });
 *   for await (const event of stream) {
 *     event.type: "analysis" | "token" | "source" | "done" | "error"
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

  yield* parseSSEStream(resp);
}

/**
 * Agent 流式请求 — CrewAI Agent + RAG知识库 + MCP搜索
 *
 * 事件类型与 RAG 模式兼容:
 *   "token"      — 回答文本（流式）
 *   "tool_call"  — Agent 调用工具（可展示为工具使用提示）
 *   "done"       — 流结束
 *   "error"      — 出错
 */
export async function* sendAgentMessageStream(question, options = {}) {
  const resp = await fetch(`${API_BASE}/chat/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal: options.signal,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败 (${resp.status})`);
  }

  yield* parseSSEStream(resp);
}

/**
 * 合并流式请求 — 同时调用 RAG + Agent，结果实时合并
 *
 * RAG 提供：reasoning / token / source（知识库引用）
 * Agent 提供：token / tool_call（联网搜索结果）
 * 两条流并行，事件实时合并，全部结束后发 done
 */
export async function* sendCombinedStream(question, options = {}) {
  const queue = [];
  let pending = 2;
  let wakeup = null;

  const feed = (event) => {
    queue.push(event);
    if (wakeup) { wakeup(); wakeup = null; }
  };

  // 并行跑 RAG 流
  (async () => {
    try {
      for await (const e of sendMessageStream(question, options)) {
        if (e.type !== "done") feed(e);
      }
    } catch (err) {
      feed({ type: "error", message: `知识库: ${err.message}` });
    } finally {
      pending--;
    }
  })();

  // 并行跑 Agent 流
  (async () => {
    try {
      for await (const e of sendAgentMessageStream(question, options)) {
        if (e.type !== "done") feed(e);
      }
    } catch (err) {
      feed({ type: "error", message: `联网搜索: ${err.message}` });
    } finally {
      pending--;
    }
  })();

  // 逐个吐出事件，两条流都结束才发 done
  while (pending > 0 || queue.length > 0) {
    if (queue.length === 0) {
      await new Promise((r) => { wakeup = r; });
    }
    while (queue.length > 0) {
      yield queue.shift();
    }
  }
  yield { type: "done" };
}

/** 健康检查 */
export async function healthCheck() {
  const resp = await fetch(`${API_BASE}/health`);
  return resp.json();
}
