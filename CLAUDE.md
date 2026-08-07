# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

建筑行业 AI 智能助手 — 基于 RAG（检索增强生成）的土木工程规范问答系统。前端 React + Vite，后端 FastAPI + LlamaIndex，LLM 使用 DeepSeek，Embedding/Rerank 使用魔搭社区 (ModelScope) 或本地模型。

## 常用命令

### 后端

```bash
# 启动后端开发服务器 (端口 8000, 热重载)
cd backend && python -m src.main

# 构建/重建知识库索引
cd backend && python scripts/build_index.py              # 构建（已有则加载）
cd backend && python scripts/build_index.py --rebuild    # 强制重建
cd backend && python scripts/build_index.py --status     # 查看索引状态
cd backend && python scripts/build_index.py --docs-dir custom/path  # 指定文档目录

# 安装 Python 依赖
pip install -r backend/requirements.txt
```

### 前端

```bash
# 安装依赖
cd frontend && npm install

# 启动前端开发服务器 (端口 3000, 自动代理 /api → 后端 8000)
cd frontend && npm run dev

# 生产构建
cd frontend && npm run build
```

### 数据管道

```bash
# 初始化知识库目录 + PDF 文本提取
cd backend && python scripts/02_setup_knowledge_base.py
cd backend && python scripts/02_setup_knowledge_base.py --convert-pdf --ocr   # 含OCR
cd backend && python scripts/02_setup_knowledge_base.py --stats               # 知识库统计

# 从 gf.cabr-fire.com 自动爬取标准全文
cd backend && python scripts/03_auto_crawler.py --batch --priority S,A --missing-only
cd backend && python scripts/03_auto_crawler.py --dry-run --priority S        # 预览不下载

# 从官方来源下载规范（flk.npc.gov.cn / openstd.samr.gov.cn）
cd backend && python scripts/01_download.py --type law
```

## 架构

### 整体数据流

```
文档 (.txt/.pdf) → SimpleDirectoryReader → IngestionPipeline (SentenceSplitter + Embedding) → VectorStoreIndex (持久化到 backend/storage/)
                                                                              ↓
用户提问 → POST /api/chat/stream → VectorStoreIndex 检索 (top_k=10)
         → ModelScopeReranker 重排序 (top_n=5) → DeepSeek LLM 生成 → SSE 流式响应

USE_REASONING=true 时额外增加：
         用户文件 FAISS 检索 (top_k=5) → 合并上下文（用户文件在前）→ httpx 直连 DeepSeek → JSON 解析 → 伪流式输出
```

**重要**：用户文件 FAISS 检索**仅在 `USE_REASONING=true` 模式**下生效。标准模式（`USE_REASONING=false`）只检索标准知识库。

### 结构化输出模式（USE_REASONING=true）

当 `USE_REASONING=true` 时，流式接口使用 `astream_query_structured()`。该函数**绕过 LlamaIndex 的 LLM 抽象层**，直接通过 `httpx` 请求 DeepSeek Chat API（非流式，保证 JSON 完整），要求 LLM 返回结构化 JSON。注意：此模式仍使用 `DEEPSEEK_MODEL`（默认 `deepseek-chat`），而非 `DEEPSEEK_REASONING_MODEL`：

```json
{
  "analysis_summary": {
    "question": "用户问题概括",
    "retrieval": "检索到的规范条文摘要",
    "reasoning": "分析推理过程",
    "conclusion": "分析结论"
  },
  "answer": "最终回答（Markdown 格式）"
}
```

前端收到后先展示 `analysis` 事件（可折叠的分析摘要面板），再逐字渲染 `answer`。此模式使用 `CONSTRUCTION_JSON_SYSTEM_PROMPT` + `CONSTRUCTION_JSON_QA_TMPL` 提示词模板。

`USE_REASONING=false`（默认）时使用标准 LlamaIndex 流式查询引擎，走 `CONSTRUCTION_SYSTEM_PROMPT` + `CONSTRUCTION_QA_PROMPT`。

启用方式：`.env` 中设置 `USE_REASONING=true`。

### 用户文件管理

用户可上传文档（PDF/Word/PPT/Excel/TXT/Markdown），系统解析后存入独立的 FAISS 向量索引。问答时同时检索标准知识库和用户文件，用户文件内容在 context 中优先排列。

- 上传 → `POST /api/files/upload` → 解析文本 → 切分 → 向量化 → 存入 `backend/storage/user_faiss/`
- 物理文件存 `backend/uploads/`
- 前端通过侧边栏 `FilePanel` + `FileUploadZone` 管理文件

### 后端 (backend/)

| 模块 | 文件 | 职责 |
|------|------|------|
| 入口 | `src/main.py` | FastAPI 应用，CORS 配置（硬编码 `localhost:3000` / `127.0.0.1:3000`），启动时 `validate_config()` 校验 API Key；`APP_ENV=development` 时启用 `/docs` |
| 配置 | `src/config.py` | 所有环境变量和 RAG 参数，从项目根目录 `.env` 读取；含 `validate_config()` 校验必填 API Key |
| API 路由 | `src/api/routes.py` | `GET /api/health`、`POST /api/chat`、`POST /api/chat/stream`；索引懒加载；`USE_REASONING` 分支选择结构化 JSON 或标准流式模式 |
| API Schema | `src/api/schemas.py` | Pydantic 请求/响应模型（含用户文件相关 schema） |
| 文件 API | `src/api/files.py` | `POST /api/files/upload`、`GET /api/files`、`GET /api/files/{id}`、`DELETE /api/files/{id}`、`POST /api/files/search` |
| LLM | `src/rag/llm.py` | `get_llm()` 工厂函数，通过 OpenAI 兼容接口 (`OpenAILike`) 接入 DeepSeek-Chat，默认 max_tokens=2048。支持可选参数 `model`、`temperature`、`max_tokens`。**注意**：结构化 JSON 模式 (`USE_REASONING=true`) 不经过此模块，而是直接用 `httpx` 请求 DeepSeek API，max_tokens=4096 |
| Embedding | `src/rag/embedding.py` | 双模式：`LocalEmbedding` (sentence-transformers + BAAI/bge-small-zh-v1.5，离线) 和 `ModelScopeEmbedding` (API，Qwen3-Embedding-8B)；由 `EMBEDDING_MODE` 控制 |
| Reranker | `src/rag/reranker.py` | `ModelScopeReranker` 封装 ModelScope Rerank API；失败时打印警告 + 降级为原始排序 |
| 索引 | `src/rag/indexing.py` | 文档加载、SentenceSplitter 中文切分、IngestionPipeline 处理、索引构建与持久化 |
| 查询 | `src/rag/query.py` | `get_query_engine()` 非流式、`get_streaming_query_engine()` 流式、`query_with_sources()` 非流式便捷封装、`astream_query_structured()` 结构化 JSON 模式（httpx 直连 DeepSeek，输出 analysis/token/source 事件） |
| Prompt | `src/rag/prompts.py` | 两套提示词：标准模式 (`CONSTRUCTION_SYSTEM_PROMPT` + `CONSTRUCTION_QA_PROMPT`) 和 JSON 结构化模式 (`CONSTRUCTION_JSON_SYSTEM_PROMPT` + `CONSTRUCTION_JSON_QA_TMPL`) |
| 文件解析 | `src/rag/file_parser.py` | 多格式解析：PDF (PyMuPDF)、Word (python-docx)、PPT (python-pptx)、Excel (openpyxl)、TXT/Markdown；统一入口 `parse_file()` |
| 用户索引 | `src/rag/user_index.py` | `UserFAISSIndex` 类：管理用户上传文件的 FAISS 索引（增删查 + 持久化），使用 `IndexFlatIP` + `IndexIDMap` 支持按 ID 删除 |

**关键配置常量** (在 `config.py` 中):
- `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`
- `TOP_K_RETRIEVE=10` (初次检索), `TOP_K_RERANK=5` (重排后保留), `USER_TOP_K=5` (用户文件检索数量)
- `EMBEDDING_MODE`: `"local"` (默认，离线) 或 `"api"` (需网络 + `MODELSCOPE_API_KEY`)
- `EMBEDDING_DIM=512` — **必须与 Embedding 模型输出维度一致**（当前匹配 BAAI/bge-small-zh-v1.5）
- `ALLOWED_EXTENSIONS`: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`
- `MAX_FILE_SIZE`: 50MB
- `USE_REASONING`: `"false"` (默认，标准 LlamaIndex 流式) 或 `"true"` (结构化 JSON 输出)
- 索引存 `backend/storage/`，用户 FAISS 索引存 `backend/storage/user_faiss/`，用户上传文件存 `backend/uploads/`，文档存 `backend/src/data/documents/`

### 前端 (frontend/)

| 文件 | 职责 |
|------|------|
| `src/main.jsx` | React 入口，挂载 App |
| `src/App.jsx` | 根组件：header（状态指示灯）+ FilePanel 侧边栏 + ChatWindow 主区域 |
| `src/components/ChatWindow.jsx` | 对话主体：消息列表、SSE 流式渲染（含 analysis 事件处理）、建议问题、输入框 |
| `src/components/MessageBubble.jsx` | 单条消息：用户/助手气泡、`marked` 库渲染 GFM、分析摘要折叠面板（琥珀色、流式时自动展开、完成后自动折叠）、来源引用卡片 |
| `src/components/SourceCard.jsx` | 引用卡片：支持标准规范引用和用户文件引用两种样式 |
| `src/components/FilePanel.jsx` | 文件管理侧边栏：可折叠、文件列表（含图标/大小/时间）、删除确认 |
| `src/components/FileUploadZone.jsx` | 文件上传区：拖拽/点击上传、多状态（default/dragging/uploading/success/error）、客户端校验 |
| `src/api/chat.js` | 对话 API：`sendMessage()` 非流式、`sendMessageStream()` SSE 流式（AsyncGenerator）、`healthCheck()` |
| `src/api/files.js` | 文件 API：`uploadFile()`、`listFiles()`、`deleteFile()` |

**数据流**: Vite 开发服务器 (port 3000) 代理 `/api/*` → FastAPI (port 8000)。前端使用 SSE (`text/event-stream`) 接收流式响应，事件类型：`analysis`（结构化分析摘要）、`token`（逐字文本）、`source`（引用来源）、`done`、`error`。

### 数据管道脚本

| 脚本 | 用途 |
|------|------|
| `scripts/01_download.py` | 从官方源 (flk.npc.gov.cn, openstd.samr.gov.cn) 下载法律法规和标准元数据 |
| `scripts/02_setup_knowledge_base.py` | 初始化文档目录结构，PDF→TXT 提取 (PyMuPDF + OCR 支持)，知识库统计 |
| `scripts/03_auto_crawler.py` | 从 gf.cabr-fire.com 批量抓取标准全文：搜索→匹配→提取章节→合并保存 |
| `scripts/build_index.py` | CLI 工具：构建/重建/查看向量索引状态 |

**知识库文档组织**: `backend/src/data/documents/` 下按分类存放：
- `国家标准GB/结构设计/`, `施工验收/`, `安全规范/`, `材料标准/`, `检测与试验/`
- `行业标准/JGJ建筑行业/`, `JTG交通行业/`, 等
- `法律法规/`, `技术规程/`, `地方标准/`

文档名格式: `{标准编号}_{名称}.txt`，文件头包含标准元数据注释。

## 重要架构约束

- **无数据库** — 知识库全部为 `.txt` 文件，标准向量索引 + 用户 FAISS 索引均持久化为文件 (`backend/storage/`)。无 PostgreSQL/Redis。
- **无用户认证** — 无登录、无用户管理。API Key（DeepSeek/ModelScope）在服务启动时由 `validate_config()` 校验。
- **单用户设计** — `routes.py` 中全局 `_index` 单例，`files.py` 中全局 `_user_index` 单例，无会话管理、无对话历史持久化。
- **无测试** — 项目当前无 pytest/Vitest 测试文件。修改代码后需手动启动服务验证。
- **索引懒加载** — 首次 API 调用时才构建/加载索引，非启动时加载。
- **Reranker 降级 + 日志** — ModelScope Rerank API 失败时自动回退到原始检索排序，同时打印 `[WARN]` 日志提示检查 API Key 和网络。
- **文件解析惰性导入** — `file_parser.py` 中各格式解析库（PyMuPDF、python-docx 等）在函数内部惰性导入，按需加载。
- **Swagger 条件启用** — `APP_ENV=development` 时启用 `/docs`，非开发环境隐藏。
- **CORS 硬编码** — `main.py` 仅允许 `localhost:3000` 和 `127.0.0.1:3000`。修改 `FRONTEND_PORT` 时需同步更新 CORS origins 和 `vite.config.js` 的 proxy target。
- **EMBEDDING_DIM 固定** — FAISS 向量维度硬编码为 512，必须与 Embedding 模型输出维度一致。更换 Embedding 模型时需同步修改此值。
- **config.py 导入即创建目录** — `INDEX_STORAGE_DIR`、`DOCUMENTS_DIR`、`USER_UPLOADS_DIR`、`USER_FAISS_DIR` 在模块导入时自动 `mkdir()`。任何导入 config 的脚本都会触发此副作用。
- **用户文件仅在 USE_REASONING 模式生效** — 标准流式模式 (`USE_REASONING=false`) 不检索用户上传文件，仅检索标准知识库。

## 主数据文件

| 文件 | 用途 |
|------|------|
| `规范清单-200项.csv` | 200 项标准的主目录（标准编号、名称、分类、优先级 S/A/B/C、官方来源），是数据管线的唯一真源 |
| `backend/scripts/sources.json` | 14 项标准的 URL 清单，供 `01_download.py` 使用 |
| `项目详情.md` | 384 行项目全景文档：架构详解、数据流、逐文件说明、设计决策、环境变量（中文） |
| `design-system/default/MASTER.md` | 前端设计系统规范：Slate `#475569` 色系、Inter 字体、密度 8/10、组件 CSS 规格 |

**知识库覆盖状态**：`backend/src/data/documents/` 下共 231 个 `.txt` 文件。S 级标准 56 项中已收录 31 项（截至 2025-12），部分文件为占位符（仅含元数据，无全文）。数据管线 (`03_auto_crawler.py`) 正在持续扩充中。

## 环境变量

所有配置在 `.env` 中（模板见 `.env.example`）。必须配置 `DEEPSEEK_API_KEY`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填**，DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 标准对话模型 |
| `DEEPSEEK_REASONING_MODEL` | `deepseek-reasoner` | 推理模型（已定义但当前未使用；`USE_REASONING=true` 仍用 `DEEPSEEK_MODEL`） |
| `USE_REASONING` | `false` | 启用结构化 JSON 输出模式（含 analysis_summary）；不影响模型选择 |
| `MODELSCOPE_API_KEY` | — | Embedding/Rerank API 密钥（local embedding 模式不需要） |
| `MODELSCOPE_BASE_URL` | `https://api.modelscope.cn` | ModelScope API 地址 |
| `EMBEDDING_MODE` | `local` | `"local"` 离线或 `"api"` 云端 embedding |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 本地 embedding 模型名 |
| `EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-8B` | ModelScope embedding 模型 |
| `RERANK_MODEL` | `Qwen/Qwen3-Reranker-8B` | ModelScope rerank 模型 |
| `BACKEND_PORT` | `8000` | 后端端口 |
| `FRONTEND_PORT` | `3000` | 前端端口（修改后需同步 CORS 配置和 `vite.config.js` proxy target） |
| `APP_ENV` | `development` | 应用环境，影响 Swagger 可见性和热重载 |

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | DeepSeek (`deepseek-chat`)，通过 OpenAI-compatible API |
| RAG 框架 | LlamaIndex (`llama-index-core>=0.11.0`) |
| Embedding | 本地 `BAAI/bge-small-zh-v1.5` (sentence-transformers) 或 API `Qwen/Qwen3-Embedding-8B` |
| Rerank | `Qwen/Qwen3-Reranker-8B` via ModelScope API |
| 用户文件向量库 | FAISS (`IndexFlatIP` + `IndexIDMap`，内积 = 余弦相似度) |
| 后端 | FastAPI + uvicorn |
| 前端 | React 18 + Vite 5，Inter 字体，Slate 色系，`marked` 库渲染 GFM |
| 文件解析 | PDF: PyMuPDF / Word: python-docx / PPT: python-pptx / Excel: openpyxl |
