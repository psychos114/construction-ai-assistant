"""
Reranker 模块 — 魔搭社区 Rerank 模型后处理器
封装 ModelScope Rerank API 为 LlamaIndex NodePostprocessor
"""
from typing import Any, List, Optional
import httpx
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from src.config import (
    MODELSCOPE_API_KEY,
    MODELSCOPE_BASE_URL,
    RERANK_MODEL,
    TOP_K_RERANK,
)


class ModelScopeReranker(BaseNodePostprocessor):
    """魔搭社区 Rerank 模型后处理器

    对检索结果进行重排序，提升答案相关性。
    模型: Qwen/Qwen3-Reranker-8B
    """

    _api_key: str
    _base_url: str
    _model: str
    _top_n: int
    _timeout: float

    def __init__(
        self,
        top_n: int = TOP_K_RERANK,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._api_key = api_key or MODELSCOPE_API_KEY
        self._base_url = base_url or MODELSCOPE_BASE_URL
        self._model = model or RERANK_MODEL
        self._top_n = top_n
        self._timeout = timeout

    @classmethod
    def class_name(cls) -> str:
        return "ModelScopeReranker"

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """对检索节点进行重排序"""
        if not nodes or query_bundle is None:
            return nodes[: self._top_n]

        query = query_bundle.query_str
        documents = [node.get_content() for node in nodes]

        try:
            scores = self._call_rerank_api(query, documents)

            # 将分数赋给节点
            for node, score in zip(nodes, scores):
                node.score = score

            # 按分数降序排列，取 top_n
            nodes = sorted(nodes, key=lambda n: n.score or 0.0, reverse=True)
            return nodes[: self._top_n]

        except Exception as e:
            # Rerank 失败时降级：返回原始排序的前 top_n
            print(f"[WARN] Rerank API 调用失败 ({e})，降级为原始排序。"
                  f"请检查 MODELSCOPE_API_KEY 和网络连接。")
            return nodes[: self._top_n]

    def _call_rerank_api(self, query: str, documents: List[str]) -> List[float]:
        """调用 ModelScope Rerank API"""
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/models/{self._model}/rerank",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "documents": documents,
                    "top_n": self._top_n,
                },
            )
            response.raise_for_status()
            data = response.json()

            # 重建完整分数列表（API 可能只返回 top_n）
            results = {r["index"]: r["relevance_score"] for r in data.get("results", [])}
            return [results.get(i, 0.0) for i in range(len(documents))]
