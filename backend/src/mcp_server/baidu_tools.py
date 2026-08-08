from __future__ import annotations

import re
import threading
import time
from http.cookiejar import CookieJar
from html import unescape
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from ..shared.common import Evidence, SearchResult
from ..shared.crawler import fetch_article
from ..shared.config import (
    BAIDU_SEARCH_COUNT,
    BAIDU_SEARCH_DELAY_SECONDS,
    BAIDU_SEARCH_MAX_RETRIES,
    BAIDU_SEARCH_TIMEOUT_SECONDS,
)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional parser fallback
    BeautifulSoup = None


# ---------- 线程安全的错误状态 ----------

_thread_local = threading.local()


def _get_last_error() -> str:
    return getattr(_thread_local, "last_search_error", "")


def _set_last_error(message: str) -> None:
    _thread_local.last_search_error = message


def get_last_search_error() -> str:
    return _get_last_error()


class SearchUnavailableError(RuntimeError):
    pass


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_BAIDU_COOKIE_JAR = CookieJar()
_BAIDU_OPENER = build_opener(HTTPCookieProcessor(_BAIDU_COOKIE_JAR))


class BaiduResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._in_title = False
        self._in_snippet = False
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "") or ""
        tpl = attrs_dict.get("tpl")

        if tag == "div" and ("result" in class_name or tpl):
            self._flush_current()
            self._current = {"title": "", "url": "", "snippet": "", "publish_time": ""}

        if self._current is None:
            return

        if tag == "a" and attrs_dict.get("href") and not self._current["url"]:
            self._current["url"] = attrs_dict["href"] or ""

        if tag == "h3":
            self._in_title = True
            self._text_parts = []

        if tag in {"div", "span"} and (
            "c-abstract" in class_name
            or "summary" in class_name
            or "content-right" in class_name
            or "c-span-last" in class_name
        ):
            self._in_snippet = True
            self._text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return

        if tag == "h3" and self._in_title:
            self._current["title"] = _clean_text("".join(self._text_parts))
            self._in_title = False
            self._text_parts = []

        if tag in {"div", "span"} and self._in_snippet:
            snippet = _clean_text("".join(self._text_parts))
            if snippet and not self._current["snippet"]:
                self._current["snippet"] = snippet
                self._current["publish_time"] = _extract_time(snippet)
            self._in_snippet = False
            self._text_parts = []

        if tag == "div":
            self._flush_current()

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_snippet:
            self._text_parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush_current()

    def _flush_current(self) -> None:
        if not self._current:
            return
        if self._current["title"] and self._current["url"]:
            self.results.append(self._current)
        self._current = None


def _clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_time(text: str) -> str:
    match = re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}|\d+天前|\d+小时前|\d+分钟前", text)
    return match.group(0) if match else ""


def _request_baidu_page(query: str, pn: int) -> str:
    params = urlencode({"wd": query, "pn": pn, "ie": "utf-8"})
    request = Request(
        f"https://www.baidu.com/s?{params}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Host": "www.baidu.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    with _BAIDU_OPENER.open(
        request,
        timeout=BAIDU_SEARCH_TIMEOUT_SECONDS,
    ) as response:
        html = response.read().decode("utf-8", errors="ignore")

    if "百度安全验证" in html:
        raise SearchUnavailableError("遇到百度安全验证，无法自动搜索")
    return html


def _resolve_baidu_redirect(url: str) -> str:
    if not url.startswith("http://www.baidu.com/link") and not url.startswith("https://www.baidu.com/link"):
        return url

    opener = build_opener(
        NoRedirectHandler(),
        HTTPCookieProcessor(_BAIDU_COOKIE_JAR),
    )
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        opener.open(request, timeout=BAIDU_SEARCH_TIMEOUT_SECONDS)
    except Exception as exc:
        headers = getattr(exc, "headers", None)
        if headers and headers.get("Location"):
            return headers["Location"]
    return url


def baidu_search(query: str, count: int = BAIDU_SEARCH_COUNT) -> list[dict[str, str]]:
    _set_last_error("")

    if not query.strip():
        return []

    if count <= 0:
        _set_last_error("百度搜索结果数量必须大于 0")
        return []

    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    max_pages = max(1, min(10, (count // 10) + 2))
    consecutive_empty_pages = 0

    for page in range(max_pages):
        html = None
        for attempt in range(BAIDU_SEARCH_MAX_RETRIES):
            try:
                html = _request_baidu_page(query, page * 10)
                break
            except SearchUnavailableError as exc:
                _set_last_error(str(exc))
                html = None
                break
            except (URLError, TimeoutError, OSError) as exc:
                _set_last_error(f"百度搜索请求失败: {exc}")
                if attempt == BAIDU_SEARCH_MAX_RETRIES - 1:
                    html = None
                else:
                    time.sleep(2 ** attempt)

        if not html:
            continue

        results = _parse_with_bs4(html) or _parse_with_html_parser(html)

        if not results:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 3:
                break
        else:
            consecutive_empty_pages = 0

        for item in results:
            item["url"] = _resolve_baidu_redirect(item["url"])
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            all_results.append(item)
            if len(all_results) >= count:
                return all_results[:count]

        if BAIDU_SEARCH_DELAY_SECONDS > 0:
            time.sleep(BAIDU_SEARCH_DELAY_SECONDS)

    if not all_results and not _get_last_error():
        _set_last_error("百度搜索未返回可解析结果")
    return all_results[:count]


def _parse_with_html_parser(html: str) -> list[dict[str, str]]:
    parser = BaiduResultParser()
    parser.feed(html)
    parser.close()
    return parser.results


def _parse_with_bs4(html: str) -> list[dict[str, str]]:
    if BeautifulSoup is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    selectors = [
        "div[class*='result'][class*='c-container']:not([class*='wrapper']):not([class*='op'])",
        "div.result.c-container",
        "div[tpl]",
    ]

    result_divs = []
    for selector in selectors:
        result_divs = soup.select(selector)
        if result_divs:
            break

    for result in result_divs:
        title_tag = result.find("h3") or result.find("a")
        link_tag = result.find("a", href=True)
        if not title_tag or not link_tag:
            continue

        snippet = ""
        for selector in [
            "span[class*='summary-text']",
            "span.summary-text_560AW",
            "div[data-module='abstract'] span",
            "span[class*='content-right']",
            "div[class*='c-abstract']",
            "div[class*='c-span-last']",
        ]:
            desc_tag = result.select_one(selector)
            if desc_tag:
                snippet = _clean_text(desc_tag.get_text(" ", strip=True))
                break

        result_html = str(result)
        prefix_time = re.search(
            r'"prefixTime"\s*:\s*"([^"]+)"',
            result_html,
        )
        publish_time = prefix_time.group(1) if prefix_time else ""

        if not publish_time:
            for selector in [
                "span.cosc-source-text",
                "div.cosc-source span",
                "a.cosc-source-link span",
                "span[class*='c-color-gray']",
                "span.c-color-gray2",
                "span.c-color-gray",
            ]:
                source_tag = result.select_one(selector)
                if not source_tag:
                    continue
                source_text = _clean_text(source_tag.get_text(" ", strip=True))
                publish_time = _extract_time(source_text)
                if publish_time:
                    break

        results.append(
            {
                "title": _clean_text(title_tag.get_text(" ", strip=True)),
                "url": link_tag["href"],
                "snippet": snippet,
                "publish_time": publish_time or _extract_time(snippet),
            }
        )

    return results


def search_authoritative_sources(query: str) -> list[Evidence]:
    results = search_sources(query + " 官方 通报 权威 媒体")
    return [
        Evidence(
            source=item.title or item.url,
            claim=query,
            verdict="待核验",
            url=item.url,
            published_at=item.published_at,
        )
        for item in results
    ]


def search_sources(
    query: str,
    count: int = BAIDU_SEARCH_COUNT,
    claim: str = "",
) -> list[SearchResult]:
    """搜索候选页面。搜索摘要只用于发现线索，不直接作为证据。"""
    return [
        SearchResult(
            title=item["title"] or item["url"],
            url=item["url"],
            claim=claim or query,
            snippet=item["snippet"],
            published_at=item["publish_time"],
        )
        for item in baidu_search(query, count=count)
    ]


def read_search_result(result: SearchResult) -> Evidence:
    """读取候选网页正文，形成等待立场判断的证据。"""
    article = fetch_article(result.url)
    return Evidence(
        source=result.title or article.source,
        claim=result.claim,
        verdict="待判断",
        url=result.url,
        excerpt=article.content[:3000],
        published_at=result.published_at,
        source_type="unknown",
    )


def fetch_related_posts(query: str) -> list[str]:
    results = baidu_search(query + " 舆情 评论 转发 社交媒体")
    return [
        f"{item['title']}: {item['snippet']} ({item['url']})"
        for item in results
    ]


def analyze_propagation(posts: list[str]) -> list[str]:
    if not posts:
        return [
            "百度搜索未返回相关舆情结果，暂不生成传播分析",
        ]
    return [
        f"相关搜索结果数量: {len(posts)}",
        "传播特征: 已基于百度搜索摘要汇总，需进一步接入平台数据确认转发链路",
        "风险提示: 搜索摘要只能辅助发现线索，不能替代平台级传播链路分析",
    ]
