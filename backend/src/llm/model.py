from crewai import LLM
import os
from dotenv import load_dotenv


load_dotenv()


def get_llm():

    llm = LLM(

        model="deepseek-chat",

        api_key=os.getenv("DEEPSEEK_API_KEY"),

        base_url="https://api.deepseek.com"

    )

    return llm