"""
Embedding 模块 — 双模式支持
  1. 本地模式 (默认): sentence-transformers + BAAI/bge-small-zh-v1.5
  2. API 模式: ModelScope Qwen3-Embedding-8B
"""
from typing import Any, List
from llama_index.core.embeddings import BaseEmbedding
from src.config import (
    EMBEDDING_MODE,
    MODELSCOPE_API_KEY,
    MODELSCOPE_BASE_URL,
    EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
)


class LocalEmbedding(BaseEmbedding):
    """本地 Embedding — 使用 sentence-transformers 离线运行

    模型: BAAI/bge-small-zh-v1.5 (约 100MB, 中文优化)
    首次运行自动下载，之后完全离线。
    """

    _model_name: str
    _model: Any = None

    def __init__(self, model_name: str | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._model_name = model_name or LOCAL_EMBEDDING_MODEL

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    @classmethod
    def class_name(cls) -> str:
        return "LocalEmbedding"

    def _get_text_embedding(self, text: str) -> List[float]:
        self._load_model()
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._get_text_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._get_text_embeddings(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)


class ModelScopeEmbedding(BaseEmbedding):
    """魔搭社区 API Embedding 适配器（需要网络且 API 可达）

    调用 ModelScope 文本向量化 API,
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
        import httpx
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
        import httpx
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

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._call_embed_api([text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._call_embed_api(texts)

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._call_embed_api([query])[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        result = await self._acall_embed_api([text])
        return result[0]

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return await self._acall_embed_api(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        result = await self._acall_embed_api([query])
        return result[0]


def get_embedding() -> BaseEmbedding:
    """根据配置获取 Embedding 实例"""
    if EMBEDDING_MODE == "api":
        return ModelScopeEmbedding()
    else:
        return LocalEmbedding()
