# InterviewSim (Chat-MVP)

[English](./README_en.md) | 中文

---

## 项目简介

AI 模拟面试系统，基于 LLM 的智能面试训练平台。

当前项目的面试流程编排并不是基于 `langchain` 或 `langgraph` 运行，而是使用项目内自定义的 `InterviewEngine`、结构化状态对象和规则/LLM 混合决策链路实现。仓库里虽然保留了 `app/nodes/` 作为未来扩展 LangGraph 的占位目录，但当前主流程没有引入这两个框架的依赖，也没有在运行时使用它们。

当前建议把 `main` 分支视为“自定义状态机稳定基线”：用于保留现有可运行版本、验证回归行为和对比迁移效果。LangGraph 方向的重构建议放在独立分支和独立 worktree 中推进，避免把实验性改动直接混入主线。
当前最新的 LangGraph 迁移实现位于 `feat/langgraph-migration` 对应的 worktree：`/Users/chenhaoxin/ccProjects/mockInterview/.worktrees/langgraph-migration`。

## 功能特性

- 📄 **简历解析** - 自动解析 PDF 简历，支持降级到纯文本提取
- 🤖 **AI 面试官** - 智能追问和深入探讨
- 📊 **多维度评估** - 技术深度、架构设计、工程实践、沟通表达
- 🎙️ **语音输入** - 支持语音转文字面试
- 📝 **详细报告** - 雷达图、改进建议
- 🎯 **岗位定制** - 支持 Agent Engineer 等岗位框架

## 目录结构

```
backend/python-brain  - 后端服务
frontend/web-chat     - 前端页面资源
```

## 环境配置

### 后端配置文件

`backend/python-brain/.env`

### 已配置模型

| 变量 | 值 |
|------|-----|
| LLM_BASE_URL | `https://v1.cdks.work` |
| LLM_MODEL_DEFAULT | `MiniMax-M2.5` |
| LLM_MODEL_CANDIDATES | `MiniMax-M2.5,glm-5` |

### 可选开关

默认关闭，开启后才会实际调用 LLM：

| 变量 | 描述 |
|------|------|
| `RESUME_PARSER_USE_LLM=true` | 简历解析使用 LLM |
| `INTERVIEW_ENGINE_USE_LLM=true` | 面试引擎使用 LLM |
| `INTERVIEW_TURN_USE_LLM=true` | 逐轮评分/追问（延迟更高）|
| `RESUME_OCR_ENABLED=true` | PDF 优先走本地 Ollama `deepseek-ocr` 解析 |

### 语音输入

默认开启，使用本地 Whisper 推理：

| 变量 | 描述 |
|------|------|
| `STT_ENABLED=true` | 启用语音输入 |
| `STT_MODEL=small` | Whisper 模型大小 (可选: tiny/base/small/medium/large) |

### 日志配置

| 变量 | 描述 |
|------|------|
| `LOG_DIR=logs` | 日志目录 |
| `LOG_FILE=interviewsim.log` | 日志文件 |
| `SUMMARY_LOG_FILE=interviewsim.summary.log` | 摘要日志文件 |

默认落盘路径: `backend/python-brain/logs/`

## 快速开始

### 1) 安装后端依赖

```bash
cd backend/python-brain
uv sync --extra dev --extra stt
```

### 2) 启动后端

后端同时托管前端页面：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) 打开页面

| 服务 | 地址 |
|------|------|
| Web Chat | http://127.0.0.1:8000/ |
| API 文档 | http://127.0.0.1:8000/docs |

## 快速验证

```bash
cd backend/python-brain
uv run pytest -q
```

## 当前使用情况与后续方向

### 当前主线状态

- `main` 当前仍以自定义 `InterviewEngine` 状态机作为正式实现
- 面试体验强调“帮助候选人成长”，所以当前流程仍优先采用显式规则、结构化状态和可降级的 LLM 调用
- 当前更适合做稳定性修复、文档整理、回归测试和效果基线维护

### 后续开发方向

- 后续推荐演进方向不是“把所有流程交给自由 Agent”，而是采用 `LangGraph` 作为工作流编排底座
- `LangChain` 更适合作为可选组件层，用于结构化输出、Prompt 模板、检索/工具封装，而不是直接替代主流程控制
- 重构目标是保留现有成长导向、规则兜底和 API 契约，同时提升可扩展性、可恢复性和节点级调试能力

### 推荐开发方式

- 保持当前目录停留在 `main`，用于查看自定义状态机版本
- 新建独立分支，例如 `feat/langgraph-migration`
- 使用独立 git worktree 在并行目录中开发 LangGraph 版本，便于与 `main` 实时对照
- 详细设计见 `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`
- 分阶段执行方案见 `docs/plans/2026-03-09-langgraph-migration-plan.md`

## 说明

- 前端当前不需要单独启动进程（由后端 `app.main` 挂载并提供）。
- PDF 解析链路当前是: `Ollama deepseek-ocr` -> `pypdf` 文本层提取 -> UTF-8 原文降级。
- 对扫描版、双栏、复杂排版或图片型 PDF，优先启用 `deepseek-ocr`。如果降级到 `pypdf`/原文解码，解析质量通常会明显变差，常见问题包括断行、漏字、顺序错乱和结构丢失。
- 当前并未接入 `langchain` / `langgraph` 作为 Agent 编排框架；实际实现是自定义状态机式面试引擎 + LLM JSON 输出约束。
- 语音输入需要 `faster-whisper`（通过 `--extra stt` 安装）和 `ffmpeg`（`brew install ffmpeg`，WAV 格式可免）。
- 若后续拆分前后端独立部署，可增加 `frontend` 独立 dev server。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端 API | FastAPI + Python |
| 编排方式 | 自定义 `InterviewEngine` 状态机 + 规则/LLM 混合决策 |
| 数据存储 | SQLModel + SQLite |
| 前端 | Vanilla JS / HTML / CSS（由 FastAPI 托管） |
| LLM 接入 | OpenAI 兼容 Relay，当前默认模型为 `MiniMax-M2.5`，候选模型含 `glm-5` |
| PDF 解析 | Ollama `deepseek-ocr`（优先）+ `pypdf`（降级）+ `pymupdf`（PDF 转图片供 OCR） |
| 语音 | `faster-whisper` |

## License

MIT License