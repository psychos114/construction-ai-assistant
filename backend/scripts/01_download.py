"""
规范文档下载器 — 从官方来源下载土木工程标准规范

策略:
  1. 法律法规 (flk.npc.gov.cn) → HTML 页面 → 提取正文 → 存为 .txt
  2. 国家标准 (openstd.samr.gov.cn) → 尝试获取 PDF/在线文本
  3. 行业标准 → 各主管部门网站

用法:
  python scripts/01_download.py                # 下载全部（交互式）
  python scripts/01_download.py --type law     # 只下载法律法规
  python scripts/01_download.py --dry-run      # 预检，不实际下载
  python scripts/01_download.py --id GB50010   # 下载指定标准
"""
import json
import sys
import argparse
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# 路径设置
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DOCUMENTS_DIR = BACKEND_DIR / "src" / "data" / "documents"
SOURCES_FILE = SCRIPT_DIR / "sources.json"

# 分类子目录
CATEGORY_DIRS = {
    "国家标准": DOCUMENTS_DIR / "国家标准GB",
    "法律法规": DOCUMENTS_DIR / "法律法规",
    "行业标准": DOCUMENTS_DIR / "行业标准",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_sources() -> list[dict]:
    """加载规范来源列表"""
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["sources"]


def ensure_dirs():
    """确保分类目录存在"""
    for d in CATEGORY_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)


def download_law_page(session: httpx.Client, source: dict) -> str | None:
    """下载法律法规页面并提取正文

    flk.npc.gov.cn 的法律法规页面是 HTML，
    正文在特定的 div 容器中。
    """
    for url in source["urls"]:
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 尝试多种正文容器
            content_selectors = [
                ".con_article",       # 正文区
                ".article_content",   # 备选
                "#content",           # 备选
                ".TRS_Editor",        # 备选
            ]

            content = None
            for selector in content_selectors:
                container = soup.select_one(selector)
                if container:
                    # 提取所有段落的纯文本
                    paragraphs = container.find_all(["p", "div", "h2", "h3", "h4"])
                    if paragraphs:
                        content = "\n\n".join(
                            p.get_text(strip=True) for p in paragraphs
                            if p.get_text(strip=True)
                        )
                        break
                    else:
                        content = container.get_text("\n\n", strip=True)
                        if content:
                            break

            if not content or len(content) < 100:
                # 兜底：提取 body 中所有文本
                body = soup.find("body")
                if body:
                    # 排除 script/style/nav/footer
                    for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    content = body.get_text("\n\n", strip=True)

            if content and len(content) > 100:
                return content
            else:
                print(f"  ⚠️ 未能提取正文: {url}")
        except Exception as e:
            print(f"  ❌ 请求失败: {url} — {e}")
            continue

    return None


def download_gb_page(session: httpx.Client, source: dict) -> str | None:
    """尝试从 openstd.samr.gov.cn 获取标准基本信息

    注意: 大部分国标只提供在线阅读，不提供完整 PDF 下载。
    此函数获取标准的基本信息页 + 尝试获取可用的文本。
    """
    for url in source["urls"]:
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 提取标准元数据
            metadata_lines = [f"标准编号: {source['id']}",
                              f"标准名称: {source['name']}",
                              f"标准类型: {source['type']}"]

            # 尝试提取页面上的元数据
            info_items = soup.select(".info-item, .info_value, td")
            info_text = "\n".join(
                item.get_text(strip=True) for item in info_items
                if item.get_text(strip=True)
            )
            if info_text:
                metadata_lines.append(f"\n--- 页面元数据 ---\n{info_text}")

            # 尝试查找正文或在线文本
            content_selectors = [".con_article", "#content", ".main-text", ".text-content", "article"]
            body_text = ""
            for sel in content_selectors:
                container = soup.select_one(sel)
                if container:
                    body_text = container.get_text("\n", strip=True)
                    break

            if body_text and len(body_text) > 200:
                return "\n".join(metadata_lines) + "\n\n--- 正文 ---\n" + body_text
            elif len(metadata_lines) > 3:
                # 至少返回元数据
                full_text = "\n".join(metadata_lines)
                full_text += "\n\n[注意] 此标准在 openstd.samr.gov.cn 上仅提供在线阅览，"
                full_text += "未提供完整 PDF 下载。请手动获取标准全文后放入对应目录。"
                return full_text

        except Exception as e:
            print(f"  ❌ 请求失败: {url} — {e}")
            continue

    return None


def save_document(source: dict, text: str):
    """保存文档到对应分类目录"""
    category = source.get("category", "")
    if "法律法规" in category:
        target_dir = CATEGORY_DIRS["法律法规"]
    elif "行业标准" in category:
        target_dir = CATEGORY_DIRS["行业标准"]
    else:
        target_dir = CATEGORY_DIRS["国家标准"]

    target_dir.mkdir(parents=True, exist_ok=True)

    # 文件命名: 标准编号_名称.txt
    safe_name = source["id"].replace("/", "-").replace("\\", "-")
    filepath = target_dir / f"{safe_name}_{source['name']}.txt"

    # 写入带元数据的文本
    header = f"""# {source['name']}
# 标准编号: {source['id']}
# 类别: {source.get('category', '')}
# 类型: {source.get('type', '')}
# 下载时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
# ============================================================

"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + text)

    print(f"  ✅ 已保存: {filepath.name}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="土木规范下载器")
    parser.add_argument("--type", choices=["law", "gb", "industry", "all"],
                        default="all", help="下载类型")
    parser.add_argument("--id", type=str, help="下载指定标准编号")
    parser.add_argument("--dry-run", action="store_true", help="预检模式")
    parser.add_argument("--sleep", type=float, default=2.0, help="请求间隔（秒）")
    args = parser.parse_args()

    ensure_dirs()
    sources = load_sources()

    # 按类型筛选
    if args.type == "law":
        sources = [s for s in sources if s.get("type") in ("law", "regulation")]
    elif args.type == "gb":
        sources = [s for s in sources if s.get("type") == "GB"]

    if args.id:
        sources = [s for s in sources if s["id"] == args.id]
        if not sources:
            print(f"未找到标准: {args.id}")
            sys.exit(1)

    if args.dry_run:
        print(f"=== 预检模式：将下载 {len(sources)} 个文档 ===")
        for s in sources:
            print(f"  [{s['type']}] {s['id']}: {s['name']}")
            print(f"    来源: {s['urls'][0][:80]}...")
        return

    print(f"=== 开始下载 {len(sources)} 个文档 ===")
    success = 0
    failed = []

    with httpx.Client(timeout=30, follow_redirects=True) as session:
        for i, source in enumerate(sources, 1):
            print(f"\n[{i}/{len(sources)}] {source['type']} {source['id']}: {source['name']}")

            if source.get("type") in ("law", "regulation"):
                text = download_law_page(session, source)
            else:
                text = download_gb_page(session, source)

            if text and len(text) > 100:
                save_document(source, text)
                success += 1
            else:
                print(f"  ⚠️ 未获取到有效文本")
                failed.append(source["id"])

            if i < len(sources):
                time.sleep(args.sleep)

    print(f"\n=== 下载完成 ===")
    print(f"✅ 成功: {success}/{len(sources)}")
    if failed:
        print(f"❌ 失败: {', '.join(failed)}")
        print("提示: 这些标准可能需要手动获取 PDF，然后放入对应目录。")


if __name__ == "__main__":
    main()
