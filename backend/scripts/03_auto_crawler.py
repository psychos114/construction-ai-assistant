"""
自动化规范爬取器 v2 — 从 gf.cabr-fire.com 批量抓取标准全文

流程: 搜索标准 → 匹配list页面 → 提取所有章节ID → 批量下载 → 合并保存

用法:
  python scripts/03_auto_crawler.py --batch --priority S,A --missing-only
  python scripts/03_auto_crawler.py --dry-run --priority S
"""
import csv
import re
import sys
import argparse
import time
from pathlib import Path
import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
DOCUMENTS_DIR = BACKEND_DIR / "src" / "data" / "documents"
CSV_PATH = ROOT_DIR / "规范清单-200项.csv"

BASE = "https://gf.cabr-fire.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StandardCrawler/2.0)",
    "Accept": "text/html,application/xhtml+xml,*/*",
}


# ==================== 加载 ====================

def load_standards(priority_filter: str, missing_only: bool) -> list[dict]:
    priorities = set(priority_filter.upper().split(","))
    result = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["优先级"] not in priorities:
                continue
            if missing_only and _has_content(row):
                continue
            result.append(row)
    return result


def _has_content(item: dict) -> bool:
    sid = item["标准编号"].replace("/", "-").replace(" ", "")
    for txt in DOCUMENTS_DIR.rglob("*.txt"):
        if sid[:6] in txt.stem[:10]:
            if len(txt.read_text(encoding="utf-8")) > 500 and \
               "[此标准尚未收录全文" not in txt.read_text(encoding="utf-8"):
                return True
    return False


# ==================== 核心：搜索 + 匹配 ====================

def find_list_page(client: httpx.Client, standard_id: str, standard_name: str) -> str | None:
    """搜索标准，找到 gf.cabr-fire.com 上的 list 目录页ID"""
    try:
        resp = client.get(f"{BASE}/m/search.htm",
                          params={"keyword": standard_id},
                          headers=HEADERS, timeout=15)
    except Exception:
        return None

    # 提取所有 list-XXX.htm
    list_ids = set(re.findall(r'list-(\d+)\.htm', resp.text))
    if not list_ids:
        return None

    # 检查每个 list 页面的标题，匹配标准名称
    clean_id = standard_id.replace(" ", "").replace("-", "").replace("/", "").replace("(", "").replace(")", "")
    # 取标准编号中的数字部分作为核心匹配key
    id_digits = re.search(r'(\d[\d.]+)', clean_id)
    id_key = id_digits.group(1).replace(".", "") if id_digits else clean_id[:6]

    for lid in list_ids:
        try:
            lresp = client.get(f"{BASE}/m/list-{lid}.htm",
                               headers=HEADERS, timeout=10)
            title_match = re.search(r'<title>([^<]+)</title>', lresp.text)
            if title_match:
                title = title_match.group(1)
                title_clean = title.upper().replace(" ", "").replace("-", "").replace("（", "").replace("）", "")
                # 精确匹配：标准编号的数字部分出现在标题中
                if id_key in title_clean:
                    return f"list-{lid}.htm"
                # 名称关键词匹配（前6个字）
                name_kw = standard_name[:6]
                if name_kw in title:
                    return f"list-{lid}.htm"
        except Exception:
            continue

    return None


def extract_articles(client: httpx.Client, list_page: str) -> list[str]:
    """从list页面提取所有章节 article ID"""
    try:
        resp = client.get(f"{BASE}/m/{list_page}", headers=HEADERS, timeout=15)
    except Exception:
        return []

    articles = set()
    for m in re.finditer(r'article-(\d+)\.htm', resp.text):
        articles.add(m.group(1))

    return sorted(articles, key=int)


def fetch_article(client: httpx.Client, article_id: str) -> str | None:
    """下载单个章节的文本内容"""
    try:
        resp = client.get(f"{BASE}/m/article-{article_id}.htm",
                          headers=HEADERS, timeout=15)
    except Exception:
        return None

    html = resp.text

    # 提取 <body>
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if not body_m:
        return None
    body = body_m.group(1)

    # 清理
    for tag in ['script', 'style', 'nav', 'footer', 'header']:
        body = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', body, flags=re.DOTALL)

    body = re.sub(r'<br\s*/?>', '\n', body)
    body = re.sub(r'</?p[^>]*>', '\n', body)
    body = re.sub(r'<[^>]+>', ' ', body)

    # HTML实体
    for entity, char in [('&nbsp;', ' '), ('&mdash;', '—'), ('&lt;', '<'),
                          ('&gt;', '>'), ('&amp;', '&'), ('&quot;', '"')]:
        body = body.replace(entity, char)

    # 清理空白
    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n{3,}', '\n\n', body)

    # 过滤导航行
    skip_words = {'目录', '上节', '下节', '查找', '检索', '返回', '字变小', '字变大',
                  '白底字', '搜索', '手机版', '设为首页', '收藏本站'}
    lines = []
    for line in body.split('\n'):
        s = line.strip()
        if not s:
            lines.append('')
        elif s not in skip_words and '消防规范网' not in s:
            lines.append(s)

    result = '\n'.join(lines).strip()
    return result if len(result) > 100 else None


# ==================== 保存 ====================

def _find_dir(item: dict) -> Path:
    cat, sub = item["类别"].strip(), item["子类"].strip()
    if "国家标准" in cat:
        prefix = sub.split("-")[0]
        m = {"结构设计": "结构设计", "施工验收": "施工验收", "安全规范": "安全规范",
             "材料标准": "材料标准", "检测与试验": "检测与试验"}
        return DOCUMENTS_DIR / "国家标准GB" / m.get(prefix, "")
    if "行业标准" in cat:
        m = {"JGJ": "JGJ建筑行业", "JTG": "JTG交通行业", "SL": "SL水利行业",
             "TB": "TB铁路行业", "DL": "DL电力行业"}
        return DOCUMENTS_DIR / "行业标准" / m.get(sub[:3], "")
    if "法律法规" in cat:
        return DOCUMENTS_DIR / "法律法规"
    if "技术" in cat:
        return DOCUMENTS_DIR / "技术规程"
    if "地方" in cat:
        return DOCUMENTS_DIR / "地方标准"
    return DOCUMENTS_DIR / "其他"


def save_standard(item: dict, chapters: list[tuple[str, str]], source: str):
    """合并章节并保存"""
    sid = item["标准编号"].strip().replace("/", "-").replace(" ", "")
    target_dir = _find_dir(item)
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / f"{sid}_{item['文件名称']}.txt"

    header = f"""# {item['文件名称']}
# 标准编号: {item['标准编号']}
# 类别: {item['类别']}/{item['子类']}
# 发布部门: {item['发布部门']}
# 来源: {source}
# 章节数: {len(chapters)}
# ============================================================
"""
    parts = [header]
    for title, text in chapters:
        parts.append(f"\n## {title}\n\n{text}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


# ==================== 批量主流程 ====================

def batch_crawl(standards: list[dict], dry_run: bool = False, delay: float = 2.0):
    """批量爬取主流程"""
    total = len(standards)
    ok = 0
    fail = []

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for i, item in enumerate(standards, 1):
            sid = item["标准编号"].strip()
            name = item["文件名称"].strip()
            pct = f"[{i}/{total}]"

            # Step 1: 查找 list 页
            if dry_run:
                list_page = find_list_page(client, sid, name)
                if list_page:
                    articles = extract_articles(client, list_page)
                    print(f"{pct} 🔍 {sid} → {list_page} ({len(articles)}章)")
                else:
                    print(f"{pct} ❌ {sid} → 未找到")
                continue

            list_page = find_list_page(client, sid, name)
            if not list_page:
                print(f"{pct} ❌ {sid}: {name} — 未找到")
                fail.append(sid)
                continue

            # Step 2: 提取章节列表
            article_ids = extract_articles(client, list_page)
            if not article_ids:
                print(f"{pct} ❌ {sid}: 无章节")
                fail.append(sid)
                continue

            # Step 3: 下载所有章节
            chapters = []
            for j, aid in enumerate(article_ids):
                text = fetch_article(client, aid)
                if text:
                    chapters.append((f"章节{aid}", text[:3000] if len(text) > 3000 else text))
                if j < len(article_ids) - 1:
                    time.sleep(delay)

            if chapters:
                save_standard(item, chapters, f"{BASE}/m/{list_page}")
                total_chars = sum(len(t) for _, t in chapters)
                print(f"{pct} ✅ {sid}: {name} → {len(chapters)}章 {total_chars}字")
                ok += 1
            else:
                print(f"{pct} ❌ {sid}: 下载失败")
                fail.append(sid)

            if i < total:
                time.sleep(delay)

    print(f"\n{'='*50}")
    print(f"✅ {ok}/{total}  |  ❌ {len(fail)}")
    if fail:
        print(f"失败: {', '.join(fail[:20])}")


# ==================== Main ====================

def main():
    parser = argparse.ArgumentParser(description="自动化规范爬取器 v2")
    parser.add_argument("--batch", action="store_true", help="批量模式")
    parser.add_argument("--priority", type=str, default="S", help="S/A/B/C")
    parser.add_argument("--missing-only", action="store_true", help="只爬缺失的")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--max", type=int, default=0, help="最大数量")
    parser.add_argument("--delay", type=float, default=2.0, help="请求间隔")
    args = parser.parse_args()

    standards = load_standards(args.priority, args.missing_only)
    if args.max > 0:
        standards = standards[:args.max]

    print(f"待处理: {len(standards)} 个标准")
    print(f"模式: {'预览' if args.dry_run else '下载'}")
    print()

    if args.batch:
        batch_crawl(standards, dry_run=args.dry_run, delay=args.delay)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
