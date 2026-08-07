"""
用户文件 FAISS 向量索引 — 增删查改 + 持久化

使用 faiss.IndexIDMap(IndexFlatIP) 实现：
- IndexFlatIP（内积）: embedding 已 L2 归一化，内积 = 余弦相似度
- IndexIDMap: 支持按 ID 删除向量（remove_ids）
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any

import faiss
from llama_index.core.node_parser import SentenceSplitter

from src.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_DIM


class UserFAISSIndex:
    """管理用户上传文件的 FAISS 向量索引"""

    def __init__(self, persist_dir: Path, embed_model, dim: int = EMBEDDING_DIM):
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._embed_model = embed_model
        self._dim = dim
        self._index: faiss.Index | None = None
        self._metadata: dict = {"files": {}, "next_id": 0, "total_chunks": 0}
        self._chunk_texts: dict[int, str] = {}  # faiss_id → chunk text
        self._load_or_create()

    # ── 路径 ─────────────────────────────────────────

    def _index_path(self) -> Path:
        return self._persist_dir / "faiss.index"

    def _meta_path(self) -> Path:
        return self._persist_dir / "metadata.json"

    # ── 持久化 ──────────────────────────────────────

    def _load_or_create(self):
        """从磁盘加载已有索引和元数据，不存在则创建空索引"""
        idx_path = self._index_path()
        meta_path = self._meta_path()

        if idx_path.exists() and meta_path.exists():
            try:
                self._index = faiss.read_index(str(idx_path))
            except Exception as e:
                print(f"加载 FAISS 索引文件失败 ({e})，将创建新索引。")
                self._create_new_index()
                return

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
                # 重建 chunk_texts 缓存
                self._chunk_texts = self._metadata.get("chunk_texts", {})
                # 兼容旧格式：chunk_texts key 是字符串，转回 int；跳过无效键
                if self._chunk_texts:
                    repaired = {}
                    for k, v in self._chunk_texts.items():
                        try:
                            repaired[int(k)] = v
                        except (ValueError, TypeError):
                            print(f"[WARN] chunk_texts 跳过无效键: {k!r}")
                    self._chunk_texts = repaired
                # 验证元数据完整性：无 files 字段说明数据损坏
                if "files" not in self._metadata or "next_id" not in self._metadata:
                    raise ValueError("元数据缺少必要字段 (files/next_id)")
                print(f"已加载 FAISS 用户索引: {self._metadata.get('total_chunks', 0)} 个向量, "
                      f"{len(self._metadata.get('files', {}))} 个文件")
                return
            except Exception as e:
                print(f"加载 FAISS 元数据失败 ({e})，索引文件完好但元数据损坏。")
                print("  将重建元数据（文件索引将丢失，但 FAISS 向量保留）。")
                # 保留索引文件，但重建空元数据（保守策略：宁可丢失映射也不丢弃向量）
                # 实际上 IndexIDMap 中的向量仍在，但没有 metadata 无法检索
                self._create_new_index()
                return

        # 索引或元数据文件不存在 — 创建新索引
        self._create_new_index()

    def _create_new_index(self):
        """创建空索引（内部辅助方法）"""
        base_index = faiss.IndexFlatIP(self._dim)
        self._index = faiss.IndexIDMap(base_index)
        self._metadata = {"files": {}, "next_id": 0, "total_chunks": 0}
        self._chunk_texts = {}
        self._save()

    def _save(self):
        """持久化 FAISS 索引和元数据到磁盘"""
        faiss.write_index(self._index, str(self._index_path()))
        meta = dict(self._metadata)
        meta["chunk_texts"] = {str(k): v for k, v in self._chunk_texts.items()}
        with open(self._meta_path(), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # ── CRUD ────────────────────────────────────────

    def add_file(
        self, file_id: str, filename: str, text: str,
        file_type: str, file_size: int,
    ) -> int:
        """切分文本 → 向量化 → 添加到 FAISS 索引

        Returns: 切分的 chunk 数量
        Raises: RuntimeError 如果 file_id 已存在
        """
        if file_id in self._metadata["files"]:
            raise RuntimeError(f"文件 {file_id} 已存在")

        if not text or not text.strip():
            return 0

        # 1. 切分文本
        splitter = SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[。；！？]",
        )
        chunks = splitter.split_text(text)
        if not chunks:
            return 0

        # 2. 向量化（批处理）
        vectors = self._embed_model._get_text_embeddings(chunks)
        vectors_np = np.array(vectors, dtype=np.float32)

        # L2 归一化 — 确保 IndexFlatIP 内积 = 余弦相似度
        # (LocalEmbedding 已归一化，但 ModelScopeEmbedding 不归一化，此处统一处理)
        norms = np.linalg.norm(vectors_np, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)  # 避免除零
        vectors_np = vectors_np / norms

        # 3. 分配 ID 并添加
        start_id = self._metadata["next_id"]
        ids = list(range(start_id, start_id + len(chunks)))
        ids_np = np.array(ids, dtype=np.int64)

        self._index.add_with_ids(vectors_np, ids_np)

        # 4. 更新元数据
        self._metadata["files"][file_id] = {
            "filename": filename,
            "file_type": file_type,
            "chunk_count": len(chunks),
            "faiss_ids": ids,
            "upload_time": datetime.now().isoformat(),
            "file_size": file_size,
        }
        self._metadata["next_id"] = start_id + len(chunks)
        self._metadata["total_chunks"] += len(chunks)

        # 5. 缓存 chunk 文本（用于搜索时返回内容）
        for i, chunk in zip(ids, chunks):
            self._chunk_texts[i] = chunk

        self._save()
        return len(chunks)

    async def aadd_file(
        self, file_id: str, filename: str, text: str,
        file_type: str, file_size: int,
    ) -> int:
        """Async: 切分文本 → 向量化 → 添加到 FAISS 索引（不阻塞事件循环）"""
        if file_id in self._metadata["files"]:
            raise RuntimeError(f"文件 {file_id} 已存在")

        if not text or not text.strip():
            return 0

        # 1. 切分文本
        splitter = SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[。；！？]",
        )
        chunks = splitter.split_text(text)
        if not chunks:
            return 0

        # 2. 向量化（异步批处理）
        vectors = await self._embed_model._aget_text_embeddings(chunks)
        vectors_np = np.array(vectors, dtype=np.float32)

        # L2 归一化
        norms = np.linalg.norm(vectors_np, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        vectors_np = vectors_np / norms

        # 3. 分配 ID 并添加
        start_id = self._metadata["next_id"]
        ids = list(range(start_id, start_id + len(chunks)))
        ids_np = np.array(ids, dtype=np.int64)

        self._index.add_with_ids(vectors_np, ids_np)

        # 4. 更新元数据
        self._metadata["files"][file_id] = {
            "filename": filename,
            "file_type": file_type,
            "chunk_count": len(chunks),
            "faiss_ids": ids,
            "upload_time": datetime.now().isoformat(),
            "file_size": file_size,
        }
        self._metadata["next_id"] = start_id + len(chunks)
        self._metadata["total_chunks"] += len(chunks)

        # 5. 缓存 chunk 文本
        for i, chunk in zip(ids, chunks):
            self._chunk_texts[i] = chunk

        self._save()
        return len(chunks)

    def delete_file(self, file_id: str):
        """删除文件及其所有向量

        Raises: KeyError 如果 file_id 不存在
        """
        if file_id not in self._metadata["files"]:
            raise KeyError(f"文件 {file_id} 不存在")

        file_entry = self._metadata["files"][file_id]

        # 删除 FAISS 向量
        if file_entry["chunk_count"] > 0:
            ids_np = np.array(file_entry["faiss_ids"], dtype=np.int64)
            self._index.remove_ids(ids_np)

        # 清理 chunk_texts 缓存
        for fid in file_entry["faiss_ids"]:
            self._chunk_texts.pop(fid, None)

        # 更新元数据
        self._metadata["total_chunks"] -= file_entry["chunk_count"]
        del self._metadata["files"][file_id]

        self._save()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """搜索 FAISS 索引

        Returns:
            [{"score": float, "content": str, "file_id": str,
              "filename": str, "file_type": str}, ...]
        """
        if self._metadata["total_chunks"] == 0:
            return []

        # 嵌入查询文本
        query_vec = self._embed_model._get_query_embedding(query)
        query_np = np.array([query_vec], dtype=np.float32)

        # L2 归一化查询向量（与存储向量一致，确保内积 = 余弦相似度）
        query_norm = np.linalg.norm(query_np)
        if query_norm > 0:
            query_np = query_np / query_norm

        distances, indices = self._index.search(query_np, top_k)

        results = []
        seen = set()
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx in seen:
                continue
            seen.add(idx)

            # 查找该 chunk 属于哪个文件
            file_id = None
            file_info = None
            for fid, finfo in self._metadata["files"].items():
                if idx in finfo["faiss_ids"]:
                    file_id = fid
                    file_info = finfo
                    break

            content = self._chunk_texts.get(int(idx), "")
            results.append({
                "score": round(float(dist), 4),
                "content": content,
                "file_id": file_id or "",
                "filename": file_info["filename"] if file_info else "",
                "file_type": file_info["file_type"] if file_info else "",
            })

        return results

    async def asearch(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Async: 搜索 FAISS 索引（不阻塞事件循环）"""
        if self._metadata["total_chunks"] == 0:
            return []

        # 嵌入查询文本（异步）
        query_vec = await self._embed_model._aget_query_embedding(query)
        query_np = np.array([query_vec], dtype=np.float32)

        # L2 归一化查询向量
        query_norm = np.linalg.norm(query_np)
        if query_norm > 0:
            query_np = query_np / query_norm

        distances, indices = self._index.search(query_np, top_k)

        results = []
        seen = set()
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx in seen:
                continue
            seen.add(idx)

            # 查找该 chunk 属于哪个文件
            file_id = None
            file_info = None
            for fid, finfo in self._metadata["files"].items():
                if idx in finfo["faiss_ids"]:
                    file_id = fid
                    file_info = finfo
                    break

            content = self._chunk_texts.get(int(idx), "")
            results.append({
                "score": round(float(dist), 4),
                "content": content,
                "file_id": file_id or "",
                "filename": file_info["filename"] if file_info else "",
                "file_type": file_info["file_type"] if file_info else "",
            })

        return results

    def list_files(self) -> list[dict[str, Any]]:
        """列出所有已索引文件（按上传时间倒序）"""
        files = []
        for file_id, info in self._metadata["files"].items():
            files.append({
                "file_id": file_id,
                "filename": info["filename"],
                "file_type": info["file_type"],
                "chunk_count": info["chunk_count"],
                "upload_time": info["upload_time"],
                "file_size": info["file_size"],
            })
        files.sort(key=lambda f: f["upload_time"], reverse=True)
        return files

    def get_file_count(self) -> int:
        """返回已索引文件数"""
        return len(self._metadata["files"])

    def has_files(self) -> bool:
        """是否有已索引文件"""
        return self._metadata["total_chunks"] > 0
