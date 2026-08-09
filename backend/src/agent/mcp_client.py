import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# MCP Server启动参数
server_params = StdioServerParameters(
    command="python",
    args=[
        "-m",
        "src.mcp_server.server"
    ],
)


async def main():

    print("正在连接 MCP Server...")

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # 初始化连接
            await session.initialize()

            print("MCP Server连接成功")


            # 获取工具列表
            tools = await session.list_tools()


            print("\n当前可用工具:")

            for tool in tools.tools:
                print(
                    "-",
                    tool.name
                )
            result = await session.call_tool(
                name="baidu_search",
                arguments={
                    "keyword":"混凝土裂缝原因"
                }
            )

            print(result)

if __name__ == "__main__":
    asyncio.run(main())