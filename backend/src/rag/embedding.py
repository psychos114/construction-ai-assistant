"""
Embedding 模块 — 魔搭社区 Embedding 模型适配器
封装 ModelScope API 为 LlamaIndex BaseEmbedding 子类
"""
from typing import Any, List
import httpx
from llama_index.core.embeddings import BaseEmbedding
from src.config import (
    MODELSCOPE_API_KEY,
    MODELSCOPE_BASE_URL,
    EMBEDDING_MODEL,
)


class ModelScopeEmbedding(BaseEmbedding):
    """魔搭社区 Embedding 模型适配器

    调用 ModelScope 文本向量化 API，
    模型: Qwen/Qwen3-Embedding-8B
    """

    _api_key: str
    _base_url: str
    _model: str
    _timeout: float

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._api_key = api_key or MODELSCOPE_API_KEY
        self._base_url = base_url or MODELSCOPE_BASE_URL
        self._model = model or EMBEDDING_MODEL
        self._timeout = timeout

    @classmethod
    def class_name(cls) -> str:
        return "ModelScopeEmbedding"

    def _call_embed_api(self, texts: List[str]) -> List[List[float]]:
        """调用 ModelScope Embedding API（批量）"""
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/models/{self._model}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def _acall_embed_api(self, texts: List[str]) -> List[List[float]]:
        """异步调用 ModelScope Embedding API（批量）"""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/models/{self._model}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    # ===== 同步方法 =====

    def _get_text_embedding(self, text: str) -> List[float]:
        """获取单条文本向量（Abstract — 必须实现）"""
        return self._call_embed_api([text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量（Override 基类默认循环，一次 API 调用完成）"""
        return self._call_embed_api(texts)

    def _get_query_embedding(self, query: str) -> List[float]:
        """获取查询向量（Abstract — 必须实现）"""
        return self._call_embed_api([query])[0]

    # ===== 异步方法 =====

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """异步获取单条文本向量"""
        result = await self._acall_embed_api([text])
        return result[0]

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """异步批量获取文本向量"""
        return await self._acall_embed_api(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """异步获取查询向量"""
        result = await self._acall_embed_api([query])
        return result[0]
