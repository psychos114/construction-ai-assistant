"""
索引构建模块 — 文档加载、切分、向量化、构建索引
"""
import json
from pathlib import Path
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline

from src.config import (
    CHUNK_SIZE, CHUNK_OVERLAP, INDEX_STORAGE_DIR, DOCUMENTS_DIR,
    EMBEDDING_MODE, EMBEDDING_DIM, EMBEDDING_MODEL, LOCAL_EMBEDDING_MODEL,
)
from src.rag.llm import get_llm
from src.rag.embedding import get_embedding


def load_documents(docs_dir: Path | None = None):
    """加载文档目录中的所有支持格式文件"""

    from src.rag.file_parser import parse_file
    from llama_index.core import Document

    source_dir = docs_dir or DOCUMENTS_DIR

    if not source_dir.exists():
        source_dir.mkdir(parents=True, exist_ok=True)
        print(f"文档目录 {source_dir} 为空，请放入文档后重新运行。")
        return []


    documents = []

    # 递归扫描所有文件
    for file_path in source_dir.rglob("*"):

        # 跳过文件夹
        if not file_path.is_file():
            continue


        # 支持格式
        suffix = file_path.suffix.lower()

        if suffix not in [
            ".txt",
            ".pdf",
            ".md",
            ".docx",
            ".pptx",
            ".xlsx",
        ]:
            continue


        try:
            print(f"正在解析: {file_path.name}")


            text = parse_file(file_path, suffix)


            doc = Document(
                text=text,
                metadata={
                    "file_name": file_path.name,
                    "file_type": suffix,
                    "file_path": str(file_path),
                }
            )


            documents.append(doc)


        except Exception as e:
            print(
                f"解析失败: {file_path.name}, 原因:{e}"
            )


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

    # Embedding 模型
    embed_model = get_embedding()

    # 如果索引已存在且不强制重建，直接加载
    if persist_dir.exists() and any(persist_dir.iterdir()) and not force_rebuild:
        # 验证存储的 embedding 配置与当前配置是否匹配
        config_path = persist_dir / "embedding_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                current_model = EMBEDDING_MODEL if EMBEDDING_MODE == "api" else LOCAL_EMBEDDING_MODEL
                if (stored.get("dim") != EMBEDDING_DIM
                        or stored.get("mode") != EMBEDDING_MODE
                        or stored.get("model") != current_model):
                    raise ValueError(
                        f"索引 embedding 配置不匹配！\n"
                        f"  存储: dim={stored.get('dim')}, mode={stored.get('mode')}, "
                        f"model={stored.get('model')}\n"
                        f"  当前: dim={EMBEDDING_DIM}, mode={EMBEDDING_MODE}, "
                        f"model={current_model}\n"
                        f"  请使用 --rebuild 重建索引。"
                    )
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[WARN] embedding_config.json 读取失败 ({e})，跳过配置校验。")

        print(f"从 {persist_dir} 加载已有索引...")
        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
            index = load_index_from_storage(
                storage_context, embed_model=embed_model
            )
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

    # 保存 embedding 配置元数据，供下次加载时校验
    config_path = persist_dir / "embedding_config.json"
    current_model = EMBEDDING_MODEL if EMBEDDING_MODE == "api" else LOCAL_EMBEDDING_MODEL
    config_data = {
        "dim": EMBEDDING_DIM,
        "mode": EMBEDDING_MODE,
        "model": current_model,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    print(f"索引已保存到 {persist_dir}（embedding: {current_model}, dim={EMBEDDING_DIM}）")

    return index
