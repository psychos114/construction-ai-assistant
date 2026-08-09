"""
Agent API 路由 — CrewAI Agent + RAG 知识库 + MCP 搜索 → SSE 流式输出
"""
import json
import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatRequest
from src.llm.model import get_llm as get_crew_llm
from src.crew.agents import create_engineer_agent
from src.crew.tasks import create_engineering_task
from src.tools.mcp_tools import (MCPBaiduSearchTool,MCPTavilySearchTool)
from src.tools.rag_tool import RAGKnowledgeBaseTool
from crewai import Crew

logger = logging.getLogger(__name__)

agent_router = APIRouter()


@agent_router.post("/api/chat/agent")
async def chat_agent(request: ChatRequest):

    llm = get_crew_llm()

    tools = [
        RAGKnowledgeBaseTool(),
        MCPBaiduSearchTool(),
        MCPTavilySearchTool()
    ]


    agent = create_engineer_agent(
        llm,
        tools
    )


    task = create_engineering_task(
        agent,
        request.question
    )


    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True
    )


    result = await asyncio.to_thread(
        crew.kickoff
    )


    return {
        "answer": str(result)
    }