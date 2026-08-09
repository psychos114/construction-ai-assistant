from fastmcp import FastMCP

from .baidu_tool import search_baidu
from .tavily_tool import tavily_search


# 创建MCP服务

mcp = FastMCP(
    "civil-engineering-mcp"
)


# ======================
# 百度搜索工具
# ======================

@mcp.tool()
def baidu_search(
    keyword:str
):

    """
    百度搜索工具
    用于搜索互联网信息
    """

    result = search_baidu(keyword)

    return result



# ======================
# Tavily搜索工具
# ======================

@mcp.tool()
def tavily_search(
    keyword:str
):

    """
    Tavily网络搜索工具
    获取最新互联网信息
    """

    result = tavily_search(keyword)

    return result



# 启动

if __name__ == "__main__":

    mcp.run()