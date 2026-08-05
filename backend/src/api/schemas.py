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
    """规范来源引用"""
    standard_id: str = Field(default="", description="标准编号，如 GB 50010-2010")
    standard_name: str = Field(default="", description="标准名称")
    chapter: str = Field(default="", description="章节，如 '4 材料'")
    clause: str = Field(default="", description="条款，如 '4.1.2'")
    content: str = Field(default="", description="原文片段（截断）")
    score: float = Field(default=0.0, description="相关性得分")


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
