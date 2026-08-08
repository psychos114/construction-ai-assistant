"""
百度搜索 MCP Tool 封装
作用：
把老师提供的 baidu_search() 包装成大模型可以调用的工具
"""

from .baidu_tools import baidu_search


def search_baidu(keyword: str):
    """
    百度搜索工具

    参数:
        keyword: 用户想搜索的内容

    返回:
        百度搜索结果
    """

    result = baidu_search(keyword)

    return result