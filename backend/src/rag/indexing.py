"""
索引构建模块 — 文档加载、切分、向量化、构建索引
"""
from pathlib import Path
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline

from src.config import CHUNK_SIZE, CHUNK_OVERLAP, INDEX_STORAGE_DIR, DOCUMENTS_DIR
from src.rag.llm import get_llm
from src.rag.embedding import ModelScopeEmbedding


def load_documents(docs_dir: Path | None = None):
    """加载文档目录中的文本文件"""
    from llama_index.core import SimpleDirectoryReader

    source_dir = docs_dir or DOCUMENTS_DIR

    if not source_dir.exists():
        source_dir.mkdir(parents=True, exist_ok=True)
        print(f"文档目录 {source_dir} 为空，请放入 .txt/.pdf 文件后重新运行。")
        return []

    reader = SimpleDirectoryReader(
        input_dir=str(source_dir),
        recursive=True,
        required_exts=[".txt", ".pdf", ".md"],
    )
    documents = reader.load_data()
    print(f"已加载 {len(documents)} 个文档")
    return documents


def build_index(
    docs_dir: Path | None = None,
    persist_dir: Path | None = None,
    force_rebuild: bool = False,
) -> VectorStoreIndex:
    """构建向量索引

    Args:
        docs_dir: 文档目录路径
        persist_dir: 索引持久化目录
        force_rebuild: 是否强制重建（删除旧索引）

    Returns:
        VectorStoreIndex 实例
    """
    persist_dir = persist_dir or INDEX_STORAGE_DIR

    # 如果索引已存在且不强制重建，直接加载
    if persist_dir.exists() and any(persist_dir.iterdir()) and not force_rebuild:
        print(f"从 {persist_dir} 加载已有索引...")
        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
            index = load_index_from_storage(storage_context)
            print("索引加载成功。")
            return index
        except Exception as e:
            print(f"加载失败 ({e})，将重新构建索引。")

    # 加载文档
    documents = load_documents(docs_dir)
    if not documents:
        raise ValueError(f"文档目录 {docs_dir or DOCUMENTS_DIR} 中没有可用的文档。")

    # 节点解析器：中文友好的文本切分
    node_parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        paragraph_separator="\n\n",
        secondary_chunking_regex="[。；！？]",
    )

    # Embedding 模型
    embed_model = ModelScopeEmbedding()

    # 使用 IngestionPipeline 流程化处理
    print(f"正在处理 {len(documents)} 个文档...")
    pipeline = IngestionPipeline(
        transformations=[node_parser, embed_model],
    )
    nodes = pipeline.run(documents=documents)
    print(f"已切分为 {len(nodes)} 个节点并完成向量化")

    # 构建索引
    print("正在构建向量索引...")
    index = VectorStoreIndex(nodes=nodes, embed_model=embed_model)

    # 持久化到磁盘
    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    print(f"索引已保存到 {persist_dir}")

    return index
