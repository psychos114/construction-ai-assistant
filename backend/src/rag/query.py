"""
查询引擎模块 — 检索 + 重排序 + 生成
"""
from llama_index.core import VectorStoreIndex

from src.config import TOP_K_RETRIEVE, TOP_K_RERANK
from src.rag.llm import get_llm
from src.rag.reranker import ModelScopeReranker
from src.rag.prompts import CONSTRUCTION_QA_PROMPT, CONSTRUCTION_SYSTEM_PROMPT


def get_query_engine(index: VectorStoreIndex):
    """创建查询引擎

    流程: 用户问题 → 向量检索(top_k=10) → Rerank(top=5) → LLM生成 → 结构化答案
    """
    llm = get_llm()
    reranker = ModelScopeReranker(top_n=TOP_K_RERANK)

    query_engine = index.as_query_engine(
        llm=llm,
        similarity_top_k=TOP_K_RETRIEVE,
        node_postprocessors=[reranker],
        response_mode="compact",
        text_qa_template=CONSTRUCTION_QA_PROMPT,
        system_prompt=CONSTRUCTION_SYSTEM_PROMPT,
        verbose=False,
    )

    return query_engine


def query_with_sources(index: VectorStoreIndex, question: str) -> dict:
    """查询并返回带来源的答案

    Args:
        index: 向量索引
        question: 用户问题

    Returns:
        {
            "answer": "回答文本",
            "sources": [
                {
                    "standard_id": "GB 50010-2010",
                    "standard_name": "混凝土结构设计规范",
                    "chapter": "4 材料",
                    "clause": "4.1.2",
                    "content": "原文片段...",
                    "score": 0.92
                },
                ...
            ]
        }
    """
    query_engine = get_query_engine(index)
    response = query_engine.query(question)

    # 提取来源节点
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

    return {
        "answer": str(response),
        "sources": sources,
    }
