# 🏗️ 土木工程智能助手

基于 RAG（检索增强生成）技术的建筑行业 AI 智能问答系统。以中国国家标准 (GB)、行业标准 (JGJ/JTG/SL) 和工程建设法律法规为知识库，为建筑工程从业人员提供专业规范查询与智能解答。

## ✨ 特性

- **规范知识库**：收录 200+ 项土木工程标准规范，31+ 项 S 级核心标准全文
- **RAG 检索增强**：LlamaIndex + 本地 Embedding (BAAI/bge-small-zh-v1.5) + ModelScope Rerank
- **结构化输出**：分析摘要（规范检索 → 推理过程 → 结论）+ Markdown 格式回答
- **用户文件上传**：支持 PDF/Word/PPT/Excel/TXT/Markdown，独立 FAISS 向量索引
- **流式响应**：SSE (Server-Sent Events) 实时逐字输出
- **Slate 设计系统**：Inter 字体 + Slate 色系，专业简洁

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- （可选）ModelScope API Key（使用云端 Embedding/Rerank 时需要）

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/construction-ai-assistant.git
cd construction-ai-assistant
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必填项：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxx    # 必填：DeepSeek API Key
EMBEDDING_MODE=local             # local（默认离线）或 api（需 ModelScope Key）
```

> 使用 `EMBEDDING_MODE=local` 时无需 ModelScope API Key，首次启动自动下载约 100MB 的本地 Embedding 模型。

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 准备知识库文档（可选）

将 `.txt` / `.pdf` 规范文件放入 `backend/src/data/documents/` 对应分类目录。

已有预置的文档目录结构和占位文件。

### 6. 构建知识库索引

```bash
cd backend
python scripts/build_index.py          # 首次构建
python scripts/build_index.py --rebuild # 强制重建
python scripts/build_index.py --status  # 查看状态
```

### 7. 启动服务

**终端 1 — 后端：**
```bash
cd backend
python -m src.main
# → http://localhost:8000 (API) + http://localhost:8000/docs (Swagger)
```

**终端 2 — 前端：**
```bash
cd frontend
npm run dev
# → http://localhost:3000
```

访问 http://localhost:3000 开始提问。

## 📖 使用指南

### 标准规范问答

输入土木工程相关问题，系统自动检索相关规范条文并生成回答：

- "梁钢筋搭接长度是多少？"
- "地下室外墙防水规范要求？"
- "深基坑施工安全注意事项？"

### 上传用户文件

点击左侧"我的文件"面板，上传 PDF/Word/PPT/Excel/TXT/Markdown 文件。问答时系统会**优先检索用户文件内容**。

> 注意：用户文件检索目前仅在结构化输出模式 (`USE_REASONING=true`) 下生效。

### 结构化输出模式

在 `.env` 中设置 `USE_REASONING=true`，回答将分为：

- 📊 **分析摘要**：问题概括 → 规范检索 → 分析推理 → 结论
- 📝 **最终回答**：Markdown 格式，标注标准编号 + 章节号

## 🏛️ 架构

```
文档 (.txt/.pdf)
  → SimpleDirectoryReader → SentenceSplitter → Embedding
  → VectorStoreIndex (LlamaIndex, 持久化到 backend/storage/)
                    ↓
用户提问 → POST /api/chat/stream
  → 标准知识库检索 (top_k=10) + 用户文件 FAISS 检索 (top_k=5)
  → ModelScopeReranker 重排序 (top_n=5)
  → DeepSeek LLM 生成 → SSE 流式响应
```

| 层级 | 技术 |
|------|------|
| LLM | DeepSeek (`deepseek-chat`) |
| RAG 框架 | LlamaIndex |
| Embedding | `BAAI/bge-small-zh-v1.5` (本地) |
| Rerank | `Qwen/Qwen3-Reranker-8B` (ModelScope API) |
| 后端 | FastAPI + uvicorn |
| 前端 | React 18 + Vite 5 |
| 向量库 | FAISS (用户文件) |

## 📁 项目结构

```
.
├── backend/
│   ├── src/
│   │   ├── api/          # FastAPI 路由 + Schema
│   │   ├── rag/          # RAG 核心：Embedding/Rerank/LLM/查询
│   │   ├── config.py     # 全局配置
│   │   └── main.py       # 应用入口
│   └── scripts/          # 数据管线脚本
├── frontend/
│   └── src/
│       ├── api/          # 后端 API 封装
│       └── components/   # React 组件
├── design-system/        # 设计系统规范
├── .env.example          # 环境变量模板
└── 规范清单-200项.csv     # 标准目录（200 项）
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。详细开发指南见 `CLAUDE.md`。

## 📄 许可

MIT License

## ⚠️ 免责声明

本系统提供的答案仅供参考，实际工程请以官方发布的最新标准规范为准。
