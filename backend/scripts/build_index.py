"""
索引构建脚本 — 独立运行，用于构建/重建知识库索引

用法:
    python scripts/build_index.py               # 构建索引（如已存在则加载）
    python scripts/build_index.py --rebuild     # 强制重建
    python scripts/build_index.py --status      # 查看索引状态
"""
import sys
import argparse
from pathlib import Path

# 确保 backend/src 在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.config import INDEX_STORAGE_DIR, DOCUMENTS_DIR, validate_config
from src.rag.indexing import build_index


def main():
    parser = argparse.ArgumentParser(description="土木工程智能助手 — 知识库索引构建")
    parser.add_argument("--rebuild", action="store_true", help="强制重建索引")
    parser.add_argument("--status", action="store_true", help="查看索引状态")
    parser.add_argument("--docs-dir", type=str, default=None, help="文档目录路径")
    args = parser.parse_args()

    try:
        validate_config()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        sys.exit(1)

    docs_dir = Path(args.docs_dir) if args.docs_dir else DOCUMENTS_DIR

    if args.status:
        _show_status()
        return

    print("=" * 50)
    print("土木工程智能助手 — 知识库索引构建")
    print("=" * 50)
    print(f"文档目录: {docs_dir}")
    print(f"索引目录: {INDEX_STORAGE_DIR}")

    try:
        index = build_index(
            docs_dir=docs_dir,
            force_rebuild=args.rebuild,
        )
        print(f"\n✅ 索引就绪！共 {len(index.docstore.docs) if index.docstore else 0} 个文档片段")
    except ValueError as e:
        print(f"\n⚠️  {e}")
        print("请将规范文本文件(.txt)放入文档目录后重新运行。")


def _show_status():
    """显示索引状态"""
    if INDEX_STORAGE_DIR.exists() and any(INDEX_STORAGE_DIR.iterdir()):
        total_size = sum(f.stat().st_size for f in INDEX_STORAGE_DIR.rglob("*") if f.is_file())
        print(f"索引状态: ✅ 已构建")
        print(f"存储路径: {INDEX_STORAGE_DIR}")
        print(f"存储大小: {total_size / 1024:.1f} KB")
    else:
        print(f"索引状态: ❌ 未构建")
        print(f"运行 python scripts/build_index.py 来构建索引。")


if __name__ == "__main__":
    main()
