from crewai import Agent


def create_engineer_agent(llm, tools):

    engineer = Agent(
        role="土木工程专家",

        goal="""
        解决建筑工程、结构工程、
        施工管理相关问题。
        """,

        backstory="""
        你是一名拥有多年经验的土木工程师，
        熟悉混凝土结构、施工规范、
        工程质量控制和安全管理。
        """,

        llm=llm,

        tools=tools,

        verbose=True
    )

    return engineer