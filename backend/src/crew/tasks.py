from crewai import Task
from datetime import datetime


def create_engineering_task(agent, question):

    today = datetime.now().strftime("%Y年%m月%d日")

    task = Task(

        description=f"""
        用户提问：

        {question}

        当前日期：{today}（如果用户问日期相关的问题，以这个日期为准，不需要搜索）

        要求：
        - 如果问题与土木工程、建筑规范相关，优先使用知识库检索，分析原因并给出解决方案，使用专业工程语言。
        - 如果问题是通用知识或需要实时信息（如天气、新闻等），使用搜索工具获取最新信息后直接回答。
        - 如果用户问日期/时间，直接告诉我上述"当前日期"，不需要搜索。
        """,

        agent=agent,

        expected_output="""
        一份清晰、有用的回答
        """
    )

    return task