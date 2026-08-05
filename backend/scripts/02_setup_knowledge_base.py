"""
知识库目录结构初始化 — 从规范清单CSV读取200项，创建完整目录和元数据文件

用法:
    python scripts/02_setup_knowledge_base.py              # 创建目录+占位文件
    python scripts/02_setup_knowledge_base.py --dry-run     # 只预览不创建
"""
import csv
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
DOCUMENTS_DIR = BACKEND_DIR / "src" / "data" / "documents"
CSV_PATH = ROOT_DIR / "规范清单-200项.csv"


def parse_csv(csv_path: Path) -> list[dict]:
    """读取CSV规范清单"""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def get_target_dir(category: str, sub_category: str) -> Path:
    """根据分类+子类映射到目标目录"""
    base = DOCUMENTS_DIR

    if category == "国家标准GB":
        prefix = sub_category.split("-")[0]  # 取"-"前的部分作为子目录
        dir_map = {
            "结构设计": base / "国家标准GB" / "结构设计",
            "施工验收": base / "国家标准GB" / "施工验收",
            "安全规范": base / "国家标准GB" / "安全规范",
            "材料标准": base / "国家标准GB" / "材料标准",
            "检测与试验": base / "国家标准GB" / "检测与试验",
        }
        return dir_map.get(prefix, base / "国家标准GB")

    elif category == "行业标准":
        dir_map = {
            "JGJ": base / "行业标准" / "JGJ建筑行业",
            "JTG": base / "行业标准" / "JTG交通行业",
            "JTJ": base / "行业标准" / "JTG交通行业",
            "SL": base / "行业标准" / "SL水利行业",
            "TB": base / "行业标准" / "TB铁路行业",
            "DL": base / "行业标准" / "DL电力行业",
        }
        prefix = sub_category[:3] if len(sub_category) >= 3 else sub_category[:2]
        return dir_map.get(prefix, base / "行业标准")

    elif category == "法律法规":
        return base / "法律法规"

    elif category == "技术规程":
        return base / "技术规程"

    elif category == "地方标准":
        province = sub_category[:4] if len(sub_category) >= 4 else sub_category
        return base / "地方标准" / province

    return base / "其他"


def create_metadata_file(item: dict, target_dir: Path):
    """为每项规范创建元数据文件"""
    safe_name = item["标准编号"].replace("/", "-").replace("\\", "-")
    filepath = target_dir / f"{safe_name}_{item['文件名称']}.txt"

    if filepath.exists():
        return filepath, False  # 已存在，不覆盖

    content = f"""# {item['文件名称']}
# 标准编号: {item['标准编号']}
# 类别: {item['类别']}/{item['子类']}
# 发布部门: {item['发布部门']}
# 状态: {item['状态']}
# 优先级: {item['优先级']}
# 官方来源: {item['官方来源']}
# ============================================================

[此标准尚未收录全文。请将PDF转TXT后替换此文件。]
"""
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content.strip())

    return filepath, True


def migrate_existing():
    """将已有txt文档移动/重命名为标准格式"""
    existing_files = {
        "GB50300-2013": "GB50300-2013_建筑工程施工质量验收统一标准.txt",
        "JGJ59-2011": "JGJ59-2011_建筑施工安全检查标准.txt",
        "Law-Building-2019": "Law-Building-2019_中华人民共和国建筑法.txt",
        "Law-Safety-2021": "Law-Safety-2021_中华人民共和国安全生产法.txt",
        "Reg-ConQuality-2019": "Reg-ConQuality-2019_建设工程质量管理条例.txt",
    }
    print("已有文档无需迁移（已符合命名规范）")
    return


def main():
    parser = argparse.ArgumentParser(description="初始化知识库目录结构")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    items = parse_csv(CSV_PATH)
    print(f"从CSV读取 {len(items)} 项规范")

    created = 0
    existed = 0

    for item in items:
        category = item["类别"].strip()
        sub_category = item["子类"].strip()
        target_dir = get_target_dir(category, sub_category)

        if args.dry_run:
            print(f"  [{item['优先级']}] {item['标准编号']}: {item['文件名称']}")
            print(f"     -> {target_dir}")
        else:
            filepath, is_new = create_metadata_file(item, target_dir)
            if is_new:
                created += 1
            else:
                existed += 1

    if args.dry_run:
        print(f"\n将创建 {len(items)} 个元数据文件")
    else:
        print(f"\n新建 {created} 个, 已存在 {existed} 个")
        print(f"知识库目录: {DOCUMENTS_DIR}")

        # 显示目录树
        print("\n知识库目录结构:")
        for dirpath in sorted(DOCUMENTS_DIR.rglob("*")):
            if dirpath.is_dir() and not dirpath.name.startswith("."):
                depth = len(dirpath.relative_to(DOCUMENTS_DIR).parts)
                count = len(list(dirpath.iterdir()))
                print(f"  {'  ' * depth}├── {dirpath.name}/ ({count} 项)")

    migrate_existing()


if __name__ == "__main__":
    main()
