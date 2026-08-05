# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

建筑行业 AI 智能助手 — 前后端分离的 AI 对话应用，面向建筑行业场景。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| LLM | DeepSeek (`deepseek-chat`) | 大语言模型，对话与推理 |
| Embedding | 魔搭社区 (ModelScope) | 文本向量化，知识库检索 |
| Rerank | 魔搭社区 (ModelScope) | 检索结果重排序 |
| 后端 | Python（待初始化） | API 服务 |
| 前端 | 待定（待初始化） | Web 交互界面 |

## 项目结构

```
.
├── backend/              # 后端服务 (Python)
├── frontend/             # 前端应用
├── .env                  # 环境变量（含 API Key，不提交）
├── .env.example          # 环境变量模板（可提交）
└── .gitignore
```

## API 配置

API Key 统一在 `.env` 中管理，当前预留了以下配置项：

- **DeepSeek**: `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`
- **ModelScope**: `MODELSCOPE_API_KEY`、`MODELSCOPE_BASE_URL`、
  `EMBEDDING_MODEL`、`RERANK_MODEL`

`.env.example` 为模板文件，可提交到版本控制；`.env` 包含真实 Key，已在 `.gitignore` 中排除。

## 环境

- Windows 11，Shell 为 Git Bash
