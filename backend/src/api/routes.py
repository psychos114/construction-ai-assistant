"""
API 路由 — 对话接口、健康检查
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from llama_index.core import VectorStoreIndex

from src.api.schemas import ChatRequest, ChatResponse, SourceDoc, HealthResponse
from src.config import INDEX_STORAGE_DIR, DEEPSEEK_MODEL, EMBEDDING_MODEL, RERANK_MODEL
from src.rag.indexing import build_index
from src.rag.query import query_with_sources

router = APIRouter()

# 全局索引实例（懒加载）
_index: VectorStoreIndex | None = None


def get_index() -> VectorStoreIndex:
    """获取或初始化向量索引（懒加载）"""
    global _index
    if _index is None:
        try:
            _index = build_index()
        except ValueError as e:
            raise HTTPException(
                status_code=503,
                detail=f"知识库索引未就绪: {e}。请先将规范文档放入 documents/ 目录。"
            )
    return _index


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查+当前配置信息"""
    index_ready = INDEX_STORAGE_DIR.exists() and any(INDEX_STORAGE_DIR.iterdir())
    return HealthResponse(
        llm_model=DEEPSEEK_MODEL,
        embedding_model=EMBEDDING_MODEL,
        rerank_model=RERANK_MODEL,
        index_ready=index_ready,
    )


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """RAG 对话接口 — 检索增强生成"""
    try:
        index = get_index()
    except HTTPException:
        raise

    # 执行 RAG 查询
    result = query_with_sources(index, request.question)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceDoc(**s) for s in result["sources"]],
        question=request.question,
    )
