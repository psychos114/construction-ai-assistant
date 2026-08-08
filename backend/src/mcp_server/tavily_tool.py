import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient


# 加载项目根目录 .env（backend/ 的上上级）
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")


client = TavilyClient(
    api_key=os.getenv(
        "TAVILY_API_KEY"
    )
)


def tavily_search(query: str):

    response = client.search(
        query=query,
        max_results=5
    )

    return response["results"]