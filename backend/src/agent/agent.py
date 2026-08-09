from crewai import Agent


def create_agents(llm, tools):

    engineer_agent = Agent(
        role="土木工程专家",
        
        goal="""
        解决土木工程问题。
        根据问题类型选择合适工具：

        - 国内资料查询使用百度搜索
        - 国际技术资料和最新资料使用Tavily搜索
        - 结合已有知识生成专业回答
        """

        tools=tools,

        llm=llm,

        verbose=True
    )


    return engineer_agent