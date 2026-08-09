from crewai import Task


def create_engineering_task(agent, question):

    task = Task(

        description=f"""
        请分析以下工程问题：

        {question}

        要求：

        1. 分析原因
        2. 给出解决方案
        3. 使用专业工程语言
        """,

        agent=agent,

        expected_output="""
        一份结构清晰的工程分析报告
        """
    )

    return task