"""
FastAPI 应用入口 — 建筑行业 AI 智能助手
"""
import sys
from pathlib import Path

# 确保 backend/src 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.files import router as files_router
from src.config import BACKEND_PORT, APP_ENV, validate_config

app = FastAPI(
    title="土木工程智能助手 API",
    description="基于 RAG 技术的建筑行业 AI 知识库问答系统",
    version="0.1.0",
    docs_url="/docs" if APP_ENV == "development" else None,
    redoc_url=None,
)

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(router)
app.include_router(files_router)

# 启动时检查
@app.on_event("startup")
async def startup():
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请检查 .env 文件中的 API Key 配置。")
        import sys
        sys.exit(1)
    print(f"🚀 土木工程智能助手 API 启动 (端口 {BACKEND_PORT})")
    print(f"📄 API 文档: http://localhost:{BACKEND_PORT}/docs")


def main():
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=BACKEND_PORT,
        reload=APP_ENV == "development",
    )


if __name__ == "__main__":
    main()
