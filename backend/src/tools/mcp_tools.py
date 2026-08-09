import asyncio
import os
import sys

from crewai.tools import BaseTool

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# 计算 backend/ 目录的绝对路径（此文件位于 backend/src/tools/）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MCPBaiduSearchTool(BaseTool):

    name: str = "baidu_search"

    description: str = """
    使用百度搜索查询工程相关资料。
    输入关键词，例如：
    混凝土裂缝原因
    建筑施工规范
    """

    def _run(self, keyword: str):

        return asyncio.run(
            self.search(keyword)
        )


    async def search(self, keyword):

        # 继承当前环境变量，追加 backend/ 到 PYTHONPATH
        # 确保 MCP 子进程能找到 src.mcp_server.server 模块
        env = os.environ.copy()
        existing_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{_BACKEND_DIR}{os.pathsep}{existing_path}" if existing_path else _BACKEND_DIR
        # 强制 UTF-8 输出，避免 Windows GBK 编码问题
        env["PYTHONIOENCODING"] = "utf-8"

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "src.mcp_server.server"],
            env=env,
        )


        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()


                result = await session.call_tool(
                    "baidu_search",
                    arguments={
                        "keyword": keyword
                    }
                )


                return str(result)

class MCPTavilySearchTool(BaseTool):

    name: str = "tavily_search"

    description: str = """
    使用 Tavily 搜索互联网资料。
    适用于：
    - 最新工程资料
    - 技术文章
    - 规范查询
    """

    def _run(self, keyword: str):

        return asyncio.run(
            self.search(keyword)
        )


    async def search(self, keyword):

        server_params = StdioServerParameters(
            command=sys.executable,

            args=[
                "-m",
                "src.mcp_server.server"
            ],

            env={
                **os.environ,
                "PYTHONPATH": _BACKEND_DIR,
                "PYTHONIOENCODING": "utf-8"
            }
        )


        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()


                result = await session.call_tool(
                    "tavily_search",
                    arguments={
                        "keyword": keyword
                    }
                )


                return str(result)