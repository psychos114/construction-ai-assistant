"""
API 数据模型 — Pydantic 请求/响应 Schema
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""
    question: str = Field(
        ...,
        description="用户问题",
        min_length=1,
        max_length=2000,
        examples=["梁钢筋搭接长度是多少？"],
    )


class SourceDoc(BaseModel):
    """规范来源引用 / 用户文件来源引用"""
    standard_id: str = Field(default="", description="标准编号，如 GB 50010-2010")
    standard_name: str = Field(default="", description="标准名称")
    chapter: str = Field(default="", description="章节，如 '4 材料'")
    clause: str = Field(default="", description="条款，如 '4.1.2'")
    content: str = Field(default="", description="原文片段（截断）")
    score: float = Field(default=0.0, description="相关性得分")
    source_type: str = Field(default="standard", description="来源类型: standard | user")
    file_id: str = Field(default="", description="用户文件 ID（source_type=user 时）")
    filename: str = Field(default="", description="用户文件名（source_type=user 时）")


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str = Field(..., description="AI 回答文本")
    sources: list[SourceDoc] = Field(default_factory=list, description="引用来源列表")
    question: str = Field(default="", description="原始问题（回显）")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "0.1.0"
    llm_model: str = ""
    embedding_model: str = ""
    rerank_model: str = ""
    index_ready: bool = False
    user_files_count: int = Field(default=0, description="已索引的用户文件数")


# ── 用户文件管理 ────────────────────────────────

class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    message: str


class FileInfo(BaseModel):
    """文件信息"""
    file_id: str
    filename: str
    file_type: str
    chunk_count: int
    upload_time: str
    file_size: int


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: list[FileInfo]
    total: int


class FileSearchRequest(BaseModel):
    """文件内搜索请求"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20, description="返回数量")


class FileSearchResult(BaseModel):
    """单条搜索结果"""
    score: float
    content: str
    file_id: str
    filename: str
    file_type: str


class FileSearchResponse(BaseModel):
    """文件搜索响应"""
    results: list[FileSearchResult]
    query: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
