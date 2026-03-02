# InterviewSim (Chat-MVP)

[English](#english) | [中文](#中文)

---

## 项目简介 / Project Overview

AI 模拟面试系统，基于 LLM 的智能面试训练平台。

An AI-powered mock interview system for interview training.

---

## 功能特性 / Features

| 中文 | English |
|------|---------|
| 📄 简历解析 - 自动解析 PDF 简历 | 📄 Resume Parsing - Auto-parse PDF resumes |
| 🤖 AI 面试官 - 智能追问和深入探讨 | 🤖 AI Interviewer - Smart follow-up questions |
| 📊 多维度评估 - 技术深度、架构设计、工程实践、沟通表达 | 📊 Multi-dimensional Evaluation - Technical depth, architecture design, engineering practice, communication |
| 🎙️ 语音输入 - 支持语音转文字面试 | 🎙️ Voice Input - Speech-to-text interview support |
| 📝 详细报告 - 雷达图、改进建议 | 📝 Detailed Reports - Radar charts, improvement suggestions |
| 🎯 岗位定制 - 支持 Agent Engineer 等岗位框架 | 🎯 Role-based Framework - Agent Engineer, etc. |

---

## 目录结构 / Directory Structure

```
- backend/python-brain  后端服务 / Backend service
- frontend/web-chat     前端页面资源 / Frontend assets
```

---

## 环境配置 / Configuration

### 后端配置文件 / Backend Config File

`backend/python-brain/.env`

### 已配置模型 / Pre-configured Models

| 变量 / Variable | 值 / Value |
|-----------------|------------|
| LLM_BASE_URL | `https://v1.cdks.work` |
| LLM_MODEL_DEFAULT | `MiniMax-M2.5` |
| LLM_MODEL_CANDIDATES | `MiniMax-M2.5,glm-5` |

### 可选开关 / Optional Flags

默认关闭，开启后才会实际调用 LLM / Disabled by default, enables actual LLM calls when enabled:

| 变量 / Variable | 描述 / Description |
|-----------------|-------------------|
| `RESUME_PARSER_USE_LLM=true` | 简历解析使用 LLM / Resume parsing with LLM |
| `INTERVIEW_ENGINE_USE_LLM=true` | 面试引擎使用 LLM / Interview engine with LLM |
| `INTERVIEW_TURN_USE_LLM=true` | 逐轮评分/追问（延迟更高）/ Per-turn scoring/follow-up (higher latency) |
| `RESUME_OCR_ENABLED=true` | 本地 Ollama OCR 解析 PDF / Local Ollama OCR for PDF parsing |

### 语音输入 / Voice Input

默认开启，使用本地 Whisper 推理 / Enabled by default, using local Whisper inference:

| 变量 / Variable | 描述 / Description |
|-----------------|-------------------|
| `STT_ENABLED=true` | 启用语音输入 / Enable voice input |
| `STT_MODEL=small` | Whisper 模型大小 / Whisper model size (可选: tiny/base/small/medium/large) |

### 日志配置 / Logging Config

| 变量 / Variable | 描述 / Description |
|-----------------|-------------------|
| `LOG_DIR=logs` | 日志目录 / Log directory |
| `LOG_FILE=interviewsim.log` | 日志文件 / Log file |
| `SUMMARY_LOG_FILE=interviewsim.summary.log` | 摘要日志文件 / Summary log file |

默认落盘路径 / Default log path: `backend/python-brain/logs/`

---

## 快速开始 / Quick Start

### 1) 安装后端依赖 / Install Backend Dependencies

```bash
cd backend/python-brain
uv sync --extra dev --extra stt
```

### 2) 启动后端 / Start Backend

后端同时托管前端页面 / Backend hosts frontend pages:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) 打开页面 / Access

| 服务 / Service | 地址 / URL |
|----------------|------------|
| Web Chat | http://127.0.0.1:8000/ |
| API 文档 / API Docs | http://127.0.0.1:8000/docs |

---

## 快速验证 / Quick Test

```bash
cd backend/python-brain
uv run pytest -q
```

---

## 说明 / Notes

- 前端当前不需要单独启动进程（由后端 `app.main` 挂载并提供）。
- Frontend doesn't require a separate process (served by backend `app.main`).
- 语音输入需要 `faster-whisper`（通过 `--extra stt` 安装）和 `ffmpeg`（`brew install ffmpeg`，WAV 格式可免）。
- Voice input requires `faster-whisper` (install with `--extra stt`) and `ffmpeg` (`brew install ffmpeg`, WAV format exempt).
- 若后续拆分前后端独立部署，可增加 `frontend` 独立 dev server。
- For separate frontend/backend deployment, add a separate `frontend` dev server.

---

## 技术栈 / Tech Stack

| 类别 / Category | 技术 / Technology |
|-----------------|-------------------|
| 后端 / Backend | FastAPI + Python |
| 前端 / Frontend | 静态页面 (后端托管) / Static pages (backend hosted) |
| LLM | MiniMax, GLM 等 / etc. |
| 语音 / STT | Faster-Whisper |

---

## License

MIT License