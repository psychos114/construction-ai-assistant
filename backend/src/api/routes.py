"""
API 路由 — 对话接口（含流式）、健康检查
"""
import json
import asyncio
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from llama_index.core import VectorStoreIndex

from src.api.schemas import ChatRequest, ChatResponse, SourceDoc, HealthResponse
from src.config import (
    INDEX_STORAGE_DIR, DEEPSEEK_MODEL, EMBEDDING_MODEL, RERANK_MODEL,
    USE_REASONING,
)
from src.rag.index_singleton import get_index
from src.rag.query import query_with_sources, get_streaming_query_engine, astream_query_structured, astream_query_reasoning
from src.api.files import get_user_index

router = APIRouter()


def _get_index_or_raise() -> VectorStoreIndex:
    """获取索引，若未就绪则抛出 HTTP 503"""
    try:
        return get_index()
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=f"知识库索引未就绪: {e}。请先将规范文档放入 documents/ 目录。"
        )


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查+当前配置信息"""
    index_ready = INDEX_STORAGE_DIR.exists() and any(INDEX_STORAGE_DIR.iterdir())
    user_files_count = 0
    try:
        ui = get_user_index()
        user_files_count = ui.get_file_count()
    except Exception:
        pass
    return HealthResponse(
        llm_model=DEEPSEEK_MODEL,
        embedding_model=EMBEDDING_MODEL,
        rerank_model=RERANK_MODEL,
        index_ready=index_ready,
        user_files_count=user_files_count,
    )


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """RAG 对话接口 — 检索增强生成（非流式）"""
    try:
        index = _get_index_or_raise()
    except HTTPException:
        raise

    result = query_with_sources(index, request.question)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceDoc(**s) for s in result["sources"]],
        question=request.question,
    )


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """RAG 流式对话接口 — SSE (Server-Sent Events)

    事件格式:
      data: {"type":"analysis","data":{...}}               # 结构化分析摘要
      data: {"type":"token","content":"..."}                 # 回答文本（伪流式）
      data: {"type":"source","data":{...}}                   # 引用来源
      data: {"type":"done"}                                  # 结束
      data: {"type":"error","message":"..."}                 # 出错
    """
    try:
        index = _get_index_or_raise()
    except HTTPException:
        raise

    async def event_generator():
        try:
            if USE_REASONING:
                # ===== 推理模式：DeepSeek Reasoner 真流式 + 原生思维链 =====
                async for event_type, data in astream_query_reasoning(
                    index, request.question, user_index=get_user_index()
                ):
                    if event_type == "reasoning":
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': data}, ensure_ascii=False)}\n\n"
                    elif event_type == "token":
                        yield f"data: {json.dumps({'type': 'token', 'content': data}, ensure_ascii=False)}\n\n"
                    elif event_type == "source":
                        yield f"data: {json.dumps({'type': 'source', 'data': data}, ensure_ascii=False)}\n\n"
                    elif event_type == "done":
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    elif event_type == "error":
                        yield f"data: {json.dumps({'type': 'error', 'message': data}, ensure_ascii=False)}\n\n"
                        return
            else:
                # ===== 标准模式：真实流式输出 =====
                query_engine = get_streaming_query_engine(index)

                response = await query_engine.aquery(request.question)

                # 尝试使用 LlamaIndex 的真实流式生成器
                if hasattr(response, 'async_response_gen'):
                    async for token in response.async_response_gen():
                        yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.01)
                else:
                    # 降级：伪流式（逐字输出）
                    answer_text = str(response)
                    buffer = ""
                    for char in answer_text:
                        buffer += char
                        if len(buffer) >= 3 or char in "\n,，。；;":
                            yield f"data: {json.dumps({'type': 'token', 'content': buffer}, ensure_ascii=False)}\n\n"
                            buffer = ""
                            await asyncio.sleep(0.01)
                    if buffer:
                        yield f"data: {json.dumps({'type': 'token', 'content': buffer}, ensure_ascii=False)}\n\n"

                # 发送引用来源
                for node in response.source_nodes:
                    metadata = node.metadata or {}
                    source_data = {
                        "standard_id": metadata.get("standard_id", ""),
                        "standard_name": metadata.get("standard_name", ""),
                        "chapter": metadata.get("chapter", ""),
                        "clause": metadata.get("clause", ""),
                        "content": node.get_content()[:500],
                        "score": round(node.score or 0.0, 4),
                    }
                    yield f"data: {json.dumps({'type': 'source', 'data': source_data}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
