from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .baidu_tool import search_baidu
from .tavily_tool import tavily_search

server = Server(
    "civil-engineering-mcp"
)


# =========================
# 1. 工具列表
# =========================

async def list_tools_handler(params):

    return types.ListToolsResult(
    tools=[
        types.Tool(
            name="baidu_search",
            description="百度搜索工具，用于搜索互联网信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": [
                    "keyword"
                ]
            }
        ),

        types.Tool(
            name="tavily_search",
            description="Tavily网络搜索工具，用于获取互联网最新信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": [
                    "keyword"
                ]
            }
        )
    ]
)


# =========================
# 2. 工具调用
# =========================

async def call_tool_handler(request):

    name = request.params.name

    arguments = request.params.arguments


    if name == "baidu_search":

        keyword = arguments["keyword"]

        result = search_baidu(keyword)


        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=str(result)
                )
            ]
        )
    
    if name=="tavily_search":

        keyword = arguments["keyword"]

        result = tavily_search(keyword)

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=str(result)
                )
            ]
        )

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text="未知工具"
            )
        ]
    )


# 注册请求处理器

server.add_request_handler(
    "tools/list",
    types.ListToolsRequest,
    list_tools_handler
)


server.add_request_handler(
    "tools/call",
    types.CallToolRequest,
    call_tool_handler
)

async def main():

    async with stdio_server() as streams:

        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())