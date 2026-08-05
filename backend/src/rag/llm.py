"""
LLM 模块 — DeepSeek 大语言模型
通过 OpenAI 兼容接口接入 LlamaIndex
"""
from llama_index.llms.openai_like import OpenAILike
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def get_llm() -> OpenAILike:
    """获取 DeepSeek LLM 实例"""
    return OpenAILike(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        api_base=f"{DEEPSEEK_BASE_URL}/v1",
        temperature=0.1,
        max_tokens=2048,
        is_chat_model=True,
        context_window=65536,
    )
