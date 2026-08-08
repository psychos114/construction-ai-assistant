from dataclasses import dataclass


@dataclass
class Article:
    source: str
    content: str


def fetch_article(url: str):

    return Article(
        source=url,
        content=""
    )