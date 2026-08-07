"""
查询引擎模块 — 检索 + 重排序 + 生成（非流式 + 流式 + 结构化 JSON）
"""
import asyncio
import json
from typing import AsyncGenerator, Tuple, Any

import httpx
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import QueryBundle

from src.config import (
    TOP_K_RETRIEVE, TOP_K_RERANK,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
)
from src.rag.llm import get_llm
from src.rag.reranker import ModelScopeReranker
from src.rag.prompts import (
    CONSTRUCTION_QA_PROMPT, CONSTRUCTION_SYSTEM_PROMPT,
    CONSTRUCTION_JSON_SYSTEM_PROMPT, CONSTRUCTION_JSON_QA_TMPL,
)


def get_query_engine(index: VectorStoreIndex):
    """创建标准查询引擎（非流式）"""
    llm = get_llm()
    reranker = ModelScopeReranker(top_n=TOP_K_RERANK)

    return index.as_query_engine(
        llm=llm,
        similarity_top_k=TOP_K_RETRIEVE,
        node_postprocessors=[reranker],
        response_mode="compact",
        text_qa_template=CONSTRUCTION_QA_PROMPT,
        system_prompt=CONSTRUCTION_SYSTEM_PROMPT,
        verbose=False,
    )


def get_streaming_query_engine(index: VectorStoreIndex):
    """创建流式查询引擎（逐字输出）"""
    llm = get_llm()
    llm.temperature = 0.1
    reranker = ModelScopeReranker(top_n=TOP_K_RERANK)

    return index.as_query_engine(
        llm=llm,
        similarity_top_k=TOP_K_RETRIEVE,
        node_postprocessors=[reranker],
        response_mode="compact",
        text_qa_template=CONSTRUCTION_QA_PROMPT,
        system_prompt=CONSTRUCTION_SYSTEM_PROMPT,
        streaming=True,
        verbose=False,
    )


def query_with_sources(index: VectorStoreIndex, question: str) -> dict:
    """非流式查询"""
    query_engine = get_query_engine(index)
    response = query_engine.query(question)

    sources = []
    for node in response.source_nodes:
        metadata = node.metadata or {}
        sources.append({
            "standard_id": metadata.get("standard_id", ""),
            "standard_name": metadata.get("standard_name", ""),
            "chapter": metadata.get("chapter", ""),
            "clause": metadata.get("clause", ""),
            "content": node.get_content()[:500],
            "score": round(node.score or 0.0, 4),
        })

    return {"answer": str(response), "sources": sources}


async def astream_query_structured(
    index: VectorStoreIndex, question: str, user_index=None,
) -> AsyncGenerator[Tuple[str, Any], None]:
    """结构化 RAG 查询 — LLM 返回 JSON，分离分析摘要与回答

    流程：
    1. 检索标准知识库 + 用户文件（如已上传）
    2. 重排序标准库结果
    3. 合并上下文：用户文件内容在前
    4. 使用 JSON Prompt 请求 DeepSeek Chat（非流式，保证 JSON 完整）
    5. 解析 JSON 响应，提取 analysis_summary 和 answer
    6. 发送 analysis 事件（结构化摘要）→ token 伪流式 → source → done

    Args:
        index: 标准规范知识库的 LlamaIndex 索引
        question: 用户问题
        user_index: UserFAISSIndex | None — 用户文件 FAISS 索引

    Yields:
        ("analysis", dict)  — 结构化分析摘要 {question, retrieval, reasoning, conclusion}
        ("token", str)      — 回答文本增量（伪流式，2-3 字符）
        ("source", dict)    — 规范/用户文件来源引用
        ("done", None)      — 流结束
        ("error", str)      — 出错
    """
    from src.config import USER_TOP_K

    reranker = ModelScopeReranker(top_n=TOP_K_RERANK)

    # ── Step 1: 标准知识库检索 ──
    retriever = index.as_retriever(similarity_top_k=TOP_K_RETRIEVE)
    nodes = await retriever.aretrieve(question)

    # ── Step 2: 用户文件检索（优先级更高，放在 context 前面）──
    user_results = []
    if user_index is not None and user_index.has_files():
        user_results = await user_index.asearch(question, top_k=USER_TOP_K)

    # ── Step 3: 如果标准和用户库都没结果 ──
    if not nodes and not user_results:
        yield ("error", "未检索到相关规范条文或用户文件内容，请尝试更换问法。")
        return

    # ── Step 4: 标准库结果重排序 ──
    if nodes:
        query_bundle = QueryBundle(question)
        nodes = reranker._postprocess_nodes(nodes, query_bundle)

    # ── Step 5: 组装 Prompt（用户文件在前）──
    context_parts = []

    if user_results:
        user_context = "\n\n".join(
            f"【用户上传文件: {r['filename']}】\n{r['content']}"
            for r in user_results
        )
        context_parts.append(user_context)

    if nodes:
        standard_context = "\n\n".join(
            f"[{n.metadata.get('standard_id', '')} "
            f"{n.metadata.get('chapter', '')} §{n.metadata.get('clause', '')}]\n"
            f"{n.get_content()}"
            for n in nodes
        )
        context_parts.append(standard_context)

    context_str = "\n\n---\n\n".join(context_parts)

    prompt_text = CONSTRUCTION_JSON_QA_TMPL.format(
        context_str=context_str, query_str=question
    )

    # Step 4: 非流式请求 DeepSeek Chat（保证返回完整 JSON）
    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": CONSTRUCTION_JSON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                yield ("error", f"DeepSeek API 返回 {resp.status_code}: {resp.text[:200]}")
                return

            body = resp.json()
            choices = body.get("choices", [])
            if not choices:
                yield ("error", "DeepSeek API 返回空响应")
                return

            raw_content = choices[0].get("message", {}).get("content", "")

    except httpx.TimeoutException:
        yield ("error", "请求 DeepSeek API 超时，请稍后重试。")
        return
    except Exception as e:
        yield ("error", str(e))
        return

    # Step 5: 解析 JSON 响应
    analysis_summary = None
    answer_text = ""

    parsed = _extract_json(raw_content)
    if parsed and isinstance(parsed, dict):
        analysis_summary = parsed.get("analysis_summary", None)
        answer_text = parsed.get("answer", "")
    else:
        # JSON 解析失败：整个响应作为纯文本回答，无分析摘要
        answer_text = raw_content

    # Step 6: 发送分析摘要
    if analysis_summary and isinstance(analysis_summary, dict):
        yield ("analysis", {
            "question": str(analysis_summary.get("question", "")),
            "retrieval": str(analysis_summary.get("retrieval", "")),
            "reasoning": str(analysis_summary.get("reasoning", "")),
            "conclusion": str(analysis_summary.get("conclusion", "")),
        })

    # Step 7: 伪流式输出回答文本
    if answer_text:
        buffer = ""
        for char in answer_text:
            buffer += char
            if len(buffer) >= 3 or char in "\n,，。；;":
                yield ("token", buffer)
                buffer = ""
                await asyncio.sleep(0.01)
        if buffer:
            yield ("token", buffer)

    # Step 8: 发送引用来源 ── 用户文件优先 ──
    # 用户文件来源
    for r in user_results:
        yield ("source", {
            "standard_id": r.get("filename", ""),
            "standard_name": "",
            "chapter": "",
            "clause": "",
            "content": r.get("content", "")[:500],
            "score": r.get("score", 0.0),
            "source_type": "user",
            "file_id": r.get("file_id", ""),
            "filename": r.get("filename", ""),
        })
        await asyncio.sleep(0.01)

    # 标准库来源
    for node in nodes:
        metadata = node.metadata or {}
        source_data = {
            "standard_id": metadata.get("standard_id", ""),
            "standard_name": metadata.get("standard_name", ""),
            "chapter": metadata.get("chapter", ""),
            "clause": metadata.get("clause", ""),
            "content": node.get_content()[:500],
            "score": round(node.score or 0.0, 4),
            "source_type": "standard",
            "file_id": "",
            "filename": "",
        }
        yield ("source", source_data)
        await asyncio.sleep(0.01)

    yield ("done", None)


def _extract_json(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON 对象

    尝试策略（按顺序）：
    1. 整个文本直接解析
    2. 提取 ```json ... ``` 代码块
    3. 正则匹配最外层 { ... }
    """
    import re

    if not text or not text.strip():
        return None

    text = text.strip()

    # 策略 1: 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 ```json ... ``` 或 ``` ... ``` 代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 策略 3: 正则匹配最外层 JSON 对象
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None
