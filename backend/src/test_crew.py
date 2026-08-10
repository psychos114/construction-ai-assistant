import sys
import io

# 修复 Windows GBK 终端输出 Unicode 字符时的编码错误
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from crew.agents import create_engineer_agent
from crew.tasks import create_engineering_task
from crew.crew import run_crew

from llm.model import get_llm

from tools.rag_tool import RAGKnowledgeBaseTool

from tools.mcp_tools import (
    MCPBaiduSearchTool,
    MCPTavilySearchTool
)


def main():

    llm = get_llm()


    tools = [
        RAGKnowledgeBaseTool(),
        MCPBaiduSearchTool(),
        MCPTavilySearchTool()
    ]

    agent = create_engineer_agent(llm,tools)

    task = create_engineering_task(
        agent,
        "混凝土裂缝产生的主要原因是什么？"
    )

    result = run_crew(
        agent,
        task
    )

    print(result)


if __name__ == "__main__":
    main()