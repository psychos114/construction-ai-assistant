"""
知识库管理工具 — 目录初始化 + PDF文本提取

用法:
    python scripts/02_setup_knowledge_base.py                    # 创建目录+占位文件
    python scripts/02_setup_knowledge_base.py --convert-pdf      # 扫描并提取所有PDF文本
    python scripts/02_setup_knowledge_base.py --convert-pdf --ocr  # PDF提取+扫描件OCR
    python scripts/02_setup_knowledge_base.py --dry-run          # 只预览不创建
    python scripts/02_setup_knowledge_base.py --stats            # 查看知识库统计
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


# ==================== 分类映射 ====================

def get_target_dir(category: str, sub_category: str) -> Path:
    """根据分类+子类映射到目标目录"""
    base = DOCUMENTS_DIR

    if category == "国家标准GB":
        prefix = sub_category.split("-")[0]
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


# ==================== CSV 读取 ====================

def parse_csv(csv_path: Path) -> list[dict]:
    """读取CSV规范清单"""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ==================== 元数据文件创建 ====================

def create_metadata_file(item: dict, target_dir: Path):
    """为每项规范创建元数据文件"""
    safe_name = item["标准编号"].replace("/", "-").replace("\\", "-").replace(" ", "")
    filepath = target_dir / f"{safe_name}_{item['文件名称']}.txt"

    if filepath.exists():
        return filepath, False

    content = f"""# {item['文件名称']}
# 标准编号: {item['标准编号']}
# 类别: {item['类别']}/{item['子类']}
# 发布部门: {item['发布部门']}
# 状态: {item['状态']}
# 优先级: {item['优先级']}
# 官方来源: {item['官方来源']}
# ============================================================

[此标准尚未收录全文。请将PDF放入对应目录后运行: python scripts/02_setup_knowledge_base.py --convert-pdf]
"""
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content.strip())

    return filepath, True


# ==================== PDF 文本提取 ====================

def extract_pdf_text(pdf_path: Path, use_ocr: bool = False) -> str | None:
    """提取PDF文本

    Args:
        pdf_path: PDF文件路径
        use_ocr: 是否对扫描件启用OCR

    Returns:
        提取的文本内容，失败返回None
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("  ❌ 需要安装 PyMuPDF: pip install pymupdf")
        return None

    try:
        doc = fitz.open(str(pdf_path))
        all_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            # 如果文本层几乎没有文字，可能是扫描件
            if len(text.strip()) < 50 and use_ocr:
                text = _ocr_page(page)
                if text:
                    all_text.append(f"\n--- 第 {page_num + 1} 页 (OCR) ---\n{text}")
            elif text.strip():
                all_text.append(f"\n--- 第 {page_num + 1} 页 ---\n{text}")

        doc.close()
        return "\n".join(all_text) if all_text else None

    except Exception as e:
        print(f"  ❌ 解析失败: {e}")
        return None


def _ocr_page(page) -> str:
    """对单页PDF进行OCR"""
    try:
        # 渲染为图片
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        import paddleocr
        ocr = paddleocr.PaddleOCR(lang="ch", show_log=False)
        result = ocr.ocr(img_bytes, cls=False)
        if result and result[0]:
            return "\n".join(line[1][0] for line in result[0])
        return ""
    except ImportError:
        pass  # PaddleOCR 未安装，跳过
    except Exception:
        pass
    return ""


def find_pdf_matches() -> list[tuple[Path, Path | None]]:
    """扫描documents目录中所有PDF，匹配到已有txt占位文件

    Returns:
        [(pdf_path, matched_txt_path_or_None), ...]
    """
    matches = []

    # 收集所有txt文件路径
    txt_files: dict[str, Path] = {}
    for txt in DOCUMENTS_DIR.rglob("*.txt"):
        txt_files[txt.stem] = txt

    # 扫描所有PDF
    for pdf in DOCUMENTS_DIR.rglob("*.pdf"):
        # 尝试匹配：PDF文件名包含在某个txt文件名中
        pdf_stem = pdf.stem
        matched = None

        # 精确匹配
        if pdf_stem in txt_files:
            matched = txt_files[pdf_stem]
        else:
            # 模糊匹配：PDF名含标准编号
            for txt_stem, txt_path in txt_files.items():
                if pdf_stem[:6] in txt_stem or txt_stem[:6] in pdf_stem:
                    matched = txt_path
                    break

        matches.append((pdf, matched))

    return matches


def convert_pdfs(use_ocr: bool = False):
    """扫描并转换documents目录下所有PDF为TXT

    策略:
      - 每个PDF提取文本后，保存为同名.txt（覆盖已有占位文件）
      - 自动处理电子版和扫描版PDF
    """
    print("正在安装/检查 PyMuPDF...")
    try:
        import fitz  # noqa: F401
    except ImportError:
        print("正在安装 pymupdf...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf", "-q"])
        print("✅ PyMuPDF 安装完成")

    pdf_files = list(DOCUMENTS_DIR.rglob("*.pdf"))
    if not pdf_files:
        print("知识库目录下未找到 PDF 文件。")
        print(f"请将规范 PDF 放入 {DOCUMENTS_DIR} 下的对应子目录。")
        _show_dirs()
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件\n")

    success = 0
    failed = 0
    skipped = 0

    for pdf_path in sorted(pdf_files):
        print(f"📄 {pdf_path.relative_to(DOCUMENTS_DIR)}")

        # 跳过临时文件（以 ~ 或 . 开头的隐藏文件）
        if pdf_path.name.startswith("~") or pdf_path.name.startswith("."):
            print("  ⏭️  跳过（临时/隐藏文件）")
            skipped += 1
            continue

        # 确定输出路径：同目录同名的 .txt
        txt_path = pdf_path.with_suffix(".txt")

        # 如果txt已有实质内容（非占位），提示确认
        if txt_path.exists():
            existing = txt_path.read_text(encoding="utf-8")
            if "[此标准尚未收录全文" not in existing:
                print(f"  ⚠️  已有内容，跳过。手动删除 {txt_path.name} 后重试以覆盖。")
                skipped += 1
                continue

        # 提取文本
        text = extract_pdf_text(pdf_path, use_ocr=use_ocr)
        if text and len(text.strip()) > 50:
            # 在文本前面加上元数据
            metadata = f"# {pdf_path.stem}\n# 来源: {pdf_path.name}\n# ============================================================\n\n"
            txt_path.write_text(metadata + text, encoding="utf-8")
            print(f"  ✅ → {txt_path.name} ({len(text)} 字符)")
            success += 1
        else:
            print(f"  ❌ 未能提取到有效文本（可能是扫描件，请加 --ocr 重试）")
            failed += 1

    print(f"\n✅ 成功: {success} | ❌ 失败: {failed} | ⏭️ 跳过: {skipped}")


def _show_dirs():
    """显示知识库目录结构"""
    print("\n期望的目录结构:")
    for d in sorted(DOCUMENTS_DIR.rglob("*")):
        if d.is_dir() and not d.name.startswith(".") and any(d.iterdir()):
            depth = len(d.relative_to(DOCUMENTS_DIR).parts)
            print(f"  {'  ' * depth}├── {d.name}/")


def show_stats():
    """统计知识库当前状态"""
    txt_files = list(DOCUMENTS_DIR.rglob("*.txt"))
    pdf_files = list(DOCUMENTS_DIR.rglob("*.pdf"))

    complete = 0
    placeholder = 0
    for txt in txt_files:
        content = txt.read_text(encoding="utf-8")
        if "[此标准尚未收录全文" in content:
            placeholder += 1
        elif len(content) > 200:
            complete += 1

    print(f"知识库统计:")
    print(f"  总条目:        {len(txt_files)}")
    print(f"  已有完整内容:  {complete}")
    print(f"  占位(待填充):  {placeholder}")
    print(f"  PDF待转换:     {len(pdf_files)}")


# ==================== Main ====================

def main():
    parser = argparse.ArgumentParser(description="土木工程知识库管理工具")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际创建")
    parser.add_argument("--convert-pdf", action="store_true", help="扫描并提取所有PDF文本")
    parser.add_argument("--ocr", action="store_true", help="对扫描版PDF启用OCR（需PaddleOCR）")
    parser.add_argument("--stats", action="store_true", help="查看知识库统计")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.convert_pdf:
        convert_pdfs(use_ocr=args.ocr)
        return

    # 默认模式：创建目录+占位文件
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
        else:
            _, is_new = create_metadata_file(item, target_dir)
            if is_new:
                created += 1
            else:
                existed += 1

    if args.dry_run:
        print(f"\n将创建 {len(items)} 个元数据文件")
    else:
        print(f"\n新建 {created} 个, 已存在 {existed} 个")
        show_stats()


if __name__ == "__main__":
    main()
