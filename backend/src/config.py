"""
建筑行业 AI 智能助手 — 全局配置
从项目根目录 .env 读取所有配置项
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（backend/ 的上级）
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 加载 .env
load_dotenv(ROOT_DIR / ".env")

# ==================== DeepSeek (LLM) ====================
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ==================== ModelScope (Embedding + Rerank) ====================
MODELSCOPE_API_KEY: str = os.getenv("MODELSCOPE_API_KEY", "")
MODELSCOPE_BASE_URL: str = os.getenv("MODELSCOPE_BASE_URL", "https://api.modelscope.cn")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
RERANK_MODEL: str = os.getenv("RERANK_MODEL", "Qwen/Qwen3-Reranker-8B")

# Embedding 模式: "local" (离线, 默认) 或 "api" (需网络)
EMBEDDING_MODE: str = os.getenv("EMBEDDING_MODE", "local")
LOCAL_EMBEDDING_MODEL: str = os.getenv(
    "LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"
)

# ==================== 应用配置 ====================
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "3000"))
APP_ENV: str = os.getenv("APP_ENV", "development")

# ==================== RAG 配置 ====================
# 文本切分
CHUNK_SIZE: int = 512
CHUNK_OVERLAP: int = 64

# 检索
TOP_K_RETRIEVE: int = 10    # 初次检索数量
TOP_K_RERANK: int = 5       # 重排序后保留数量

# 索引存储路径
INDEX_STORAGE_DIR: Path = ROOT_DIR / "backend" / "storage"
DOCUMENTS_DIR: Path = ROOT_DIR / "backend" / "src" / "data" / "documents"

# 确保目录存在
INDEX_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_config() -> bool:
    """检查必要的 API Key 是否已配置"""
    missing = []
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if EMBEDDING_MODE == "api" and not MODELSCOPE_API_KEY:
        missing.append("MODELSCOPE_API_KEY (EMBEDDING_MODE=api)")
    if missing:
        raise ValueError(
            f"缺少必要的 API Key: {', '.join(missing)}。"
            f"请在项目根目录的 .env 文件中配置。"
        )
    return True
