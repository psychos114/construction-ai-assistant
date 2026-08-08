from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    published_at: str = ""


@dataclass
class Evidence:
    source: str
    claim: str
    verdict: str
    url: str
    published_at: str = ""
    excerpt: str = ""
    source_type: str = ""