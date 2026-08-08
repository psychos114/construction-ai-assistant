import asyncio

from src.mcp_server.server import list_tools_handler


async def main():

    result = await list_tools_handler(None)

    for tool in result.tools:
        print(tool.name)


asyncio.run(main())