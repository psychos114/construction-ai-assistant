"""
共享索引单例 — 供 RAG API 路由和 CrewAI 工具共用

双重检查锁定，避免并发请求触发多次索引构建。
"""
import sys
import threading
from pathlib import Path

# 确保 backend/ 和 backend/src/ 都在 sys.path 中
# backend/ → 支持 "src.xxx" 绝对导入（web server 模式）
# backend/src/ → 支持直接包导入（test_crew.py 从 src/ 运行）
_SRC_DIR = Path(__file__).resolve().parent.parent       # backend/src/
_BACKEND_DIR = _SRC_DIR.parent                           # backend/
for _d in (_BACKEND_DIR, _SRC_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

from llama_index.core import VectorStoreIndex

from src.config import INDEX_STORAGE_DIR
from src.rag.indexing import build_index

# 全局索引实例（懒加载，线程安全）
_index: VectorStoreIndex | None = None
_index_lock = threading.Lock()


def get_index() -> VectorStoreIndex:
    """获取或初始化向量索引（双重检查锁定）

    Raises:
        ValueError: 索引目录不存在或为空（首次构建时文档目录无文件）
    """
    global _index
    if _index is not None:
        return _index
    with _index_lock:
        if _index is not None:
            return _index
        _index = build_index()
        return _index


def reset_index() -> None:
    """重置索引单例（测试用）"""
    global _index
    with _index_lock:
        _index = None
