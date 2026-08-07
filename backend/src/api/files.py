"""
用户文件管理 API — 上传、列表、详情、删除、搜索
"""
import uuid
import threading
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query

from src.api.schemas import (
    FileUploadResponse, FileInfo, FileListResponse,
    FileSearchRequest, FileSearchResponse, FileSearchResult,
    MessageResponse,
)
from src.config import (
    USER_UPLOADS_DIR, USER_FAISS_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE,
)
from src.rag.file_parser import parse_file
from src.rag.user_index import UserFAISSIndex
from src.rag.embedding import get_embedding

router = APIRouter(prefix="/api/files", tags=["用户文件"])

# 全局单例（惰性初始化，线程安全）
_user_index: UserFAISSIndex | None = None
_user_index_lock = threading.Lock()


def get_user_index() -> UserFAISSIndex:
    """获取或初始化用户文件 FAISS 索引（双重检查锁定）"""
    global _user_index
    if _user_index is not None:
        return _user_index
    with _user_index_lock:
        if _user_index is not None:
            return _user_index
        embed_model = get_embedding()
        _user_index = UserFAISSIndex(USER_FAISS_DIR, embed_model)
        return _user_index


# ── 文件存储路径 ─────────────────────────────────

def _file_path(file_id: str) -> Path:
    """根据 file_id 获取物理文件路径"""
    return USER_UPLOADS_DIR / file_id


# ── 端点 ──────────────────────────────────────────

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文档文件 → 解析文本 → 向量化 → 存入 FAISS 索引

    支持格式: PDF / Word(.docx) / PowerPoint(.pptx) / Excel(.xlsx) / TXT / Markdown(.md)
    最大文件大小: 50MB
    """
    # 1. 校验扩展名
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的文件类型: {ext}。支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大（{len(content)} 字节，上限 {MAX_FILE_SIZE} 字节）")

    file_size = len(content)

    # 3. 生成 file_id 并保存到磁盘
    file_id = uuid.uuid4().hex
    file_path = _file_path(file_id)
    file_path.write_bytes(content)

    # 4. 保存原文件名的后缀，供解析器识别
    save_path = file_path.with_suffix(ext)
    if save_path != file_path:
        file_path.rename(save_path)

    # 5. 解析文本
    try:
        text = parse_file(save_path, ext)
    except Exception as e:
        # 解析失败时清理已保存的文件
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(500, f"文件解析失败: {e}")

    if not text or not text.strip():
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(400, "无法从文件中提取文本内容，文件可能为空或仅含图片。")

    # 6. 向量化 + 存入 FAISS
    user_index = get_user_index()
    try:
        chunk_count = await user_index.aadd_file(
            file_id=file_id,
            filename=file.filename,
            text=text,
            file_type=ext,
            file_size=file_size,
        )
    except Exception:
        # FAISS 索引失败时清理物理文件，避免孤儿文件
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(500, "文件索引失败，请稍后重试。")

    return FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        chunk_count=chunk_count,
        message=f"文件 {file.filename} 上传成功，已切分为 {chunk_count} 个片段并索引。",
    )


@router.get("", response_model=FileListResponse)
async def list_files():
    """获取已上传文件列表（按上传时间倒序）"""
    user_index = get_user_index()
    files = user_index.list_files()
    return FileListResponse(files=[FileInfo(**f) for f in files], total=len(files))


@router.get("/{file_id}", response_model=FileInfo)
async def get_file_detail(file_id: str):
    """获取单个文件的索引详情"""
    user_index = get_user_index()
    files = user_index.list_files()
    for f in files:
        if f["file_id"] == file_id:
            return FileInfo(**f)
    raise HTTPException(404, f"文件 {file_id} 不存在")


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(file_id: str):
    """删除文件及其索引向量"""
    user_index = get_user_index()

    # 1. 从 FAISS 索引中删除
    try:
        user_index.delete_file(file_id)
    except KeyError:
        raise HTTPException(404, f"文件 {file_id} 不存在")

    # 2. 删除物理文件
    for ext in ALLOWED_EXTENSIONS:
        p = _file_path(file_id).with_suffix(ext)
        if p.exists():
            p.unlink()
            break

    return MessageResponse(message=f"文件 {file_id} 已删除")


@router.post("/search", response_model=FileSearchResponse)
async def search_files(request: FileSearchRequest):
    """在用户文件中搜索内容"""
    user_index = get_user_index()
    results = await user_index.asearch(request.query, top_k=request.top_k)
    return FileSearchResponse(
        results=[FileSearchResult(**r) for r in results],
        query=request.query,
    )
