"""
RAG 知识库 CrewAI 工具 — 将 LlamaIndex 检索封装为 Agent 可调用的 Tool
"""
import sys
from pathlib import Path

# 确保 backend/ 和 backend/src/ 都在 sys.path 中（兼容两种运行方式）
_SRC_DIR = Path(__file__).resolve().parent.parent       # backend/src/
_BACKEND_DIR = _SRC_DIR.parent                           # backend/
for _d in (_BACKEND_DIR, _SRC_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

from crewai.tools import BaseTool

from src.rag.index_singleton import get_index
from src.rag.query import query_with_sources


class RAGKnowledgeBaseTool(BaseTool):
    name: str = "knowledge_base_search"
    description: str = (
        "搜索土木工程规范知识库，查询国家标准(GB)、行业标准(JGJ/JTG/SL)中的"
        "技术条文和规范要求。输入一个自然语言问题，返回相关规范条文和解答。"
        "适用于：查询具体规范参数、施工要求、材料标准、验收准则等。"
        "示例问题：混凝土裂缝宽度限值、钢筋搭接长度要求、抗震设防标准。"
    )

    def _run(self, question: str) -> str:
        """同步执行知识库检索（CrewAI 要求 _run 为同步方法）

        Args:
            question: 要查询的工程问题

        Returns:
            格式化的检索结果文本（含来源引用）
        """
        try:
            index = get_index()
        except Exception as e:
            return f"[知识库暂时不可用: {e}]"

        result = query_with_sources(index, question)
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        parts = [answer]
        if sources:
            parts.append("\n---\n**参考规范条文:**")
            for i, src in enumerate(sources[:5], 1):
                sid = src.get("standard_id", "") or src.get("standard_name", "")
                chapter = f"第{src['chapter']}章" if src.get("chapter") else ""
                clause = f"第{src['clause']}条" if src.get("clause") else ""
                location = f"{sid} {chapter} {clause}".strip()
                content = (src.get("content", "") or "")[:300]
                parts.append(f"{i}. [{location}] {content}")

        return "\n".join(parts)
