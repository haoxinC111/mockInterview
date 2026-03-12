# InterviewSim (Chat-MVP)

[English](./README_en.md) | 中文

---

## 项目简介

AI 模拟面试系统，基于 LLM 的智能面试训练平台。

当前仓库正在从自定义状态机向 `LangGraph` 编排迁移。现状是“双轨运行”：
- 默认仍是 legacy（`InterviewEngine` + 规则/LLM 混合决策）
- 可按功能启用 `LangGraph`（报告、简历、逐轮面试）或 shadow mode 对比
- `LangChain` 仅用于结构化组件（prompt 模板/输出 schema），不接管主流程编排

当前建议把 `main` 分支视为“自定义状态机稳定基线”：用于保留现有可运行版本、验证回归行为和对比迁移效果。LangGraph 方向的重构建议放在独立分支和独立 worktree 中推进，避免把实验性改动直接混入主线。

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
| `WORKFLOW_USE_LANGGRAPH=true` | 启用 LangGraph 运行时总开关 |
| `WORKFLOW_SHADOW_MODE=true` | 启用 shadow 对比（用户结果仍走 legacy） |
| `WORKFLOW_REPORT_USE_LANGGRAPH=true` | 报告工作流走 LangGraph |
| `WORKFLOW_RESUME_USE_LANGGRAPH=true` | 简历解析工作流走 LangGraph |
| `WORKFLOW_TURN_USE_LANGGRAPH=true` | 逐轮面试工作流走 LangGraph |

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

## 本次更新（2026-03-12）

- 已新增 `resume readiness` 门控：过薄简历会在开始面试前被拦截，并返回 `quality_score` / `readiness`。
- 已调整 0 轮结束报告语义：无有效作答样本时输出 `training_guidance`，不再直接给出薪资不匹配结论。
- 已强化低信号报告兜底：低分但 `risks` 缺失时自动补齐成长导向风险提示。
- 已降低纯文本上传时的 PDF 解析噪音。
- 自动化验证已完成：当前 worktree 全量测试通过。
- 人工联调状态：**未人工测试**（尚未在浏览器中逐步走完真实上传/对话/报告流程）。

## 当前使用情况与后续方向

### 当前主线状态

- 默认用户路径仍保持 legacy，保证稳定和契约兼容
- 已接入 `LangGraph` 骨架与 runtime selector，可按模块逐步切换
- 已支持 shadow diff 日志，可对比 turn/report/resume 结果漂移

### 后续开发方向

- 后续推荐方向是 `LangGraph` 编排 + 规则兜底 + mission guard
- `LangChain` 仅作为可选组件层，用于结构化输出、Prompt 模板、检索/工具封装
- 重构目标是保留现有成长导向、规则兜底和 API 契约，同时提升可扩展性、可恢复性和节点级调试能力

### 推荐开发方式

- 保持当前目录停留在 `main`，用于查看自定义状态机版本
- 新建独立分支，例如 `feat/langgraph-migration`
- 使用独立 git worktree 在并行目录中开发 LangGraph 版本，便于与 `main` 实时对照
- 详细设计见 `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`
- 分阶段执行方案见 `docs/plans/2026-03-09-langgraph-migration-plan.md`
- 运行手册见 `docs/runbooks/langgraph-shadow-mode.md`

## 说明

- 前端当前不需要单独启动进程（由后端 `app.main` 挂载并提供）。
- PDF 解析链路当前是: `Ollama deepseek-ocr` -> `pypdf` 文本层提取 -> UTF-8 原文降级。
- 对扫描版、双栏、复杂排版或图片型 PDF，优先启用 `deepseek-ocr`。如果降级到 `pypdf`/原文解码，解析质量通常会明显变差，常见问题包括断行、漏字、顺序错乱和结构丢失。
- 当前为渐进迁移状态：legacy 默认，LangGraph 可按功能开关启用或 shadow 对比。
- 语音输入需要 `faster-whisper`（通过 `--extra stt` 安装）和 `ffmpeg`（`brew install ffmpeg`，WAV 格式可免）。
- 若后续拆分前后端独立部署，可增加 `frontend` 独立 dev server。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端 API | FastAPI + Python |
| 编排方式 | LangGraph + legacy 双轨（默认 legacy，按 feature flag 渐进切换） |
| 数据存储 | SQLModel + SQLite |
| 前端 | Vanilla JS / HTML / CSS（由 FastAPI 托管） |
| LLM 接入 | OpenAI 兼容 Relay，当前默认模型为 `MiniMax-M2.5`，候选模型含 `glm-5` |
| PDF 解析 | Ollama `deepseek-ocr`（优先）+ `pypdf`（降级）+ `pymupdf`（PDF 转图片供 OCR） |
| 语音 | `faster-whisper` |

## License

MIT License
