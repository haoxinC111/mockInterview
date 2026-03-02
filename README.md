# InterviewSim (Chat-MVP)

[English](./README_en.md) | 中文

---

## 项目简介

AI 模拟面试系统，基于 LLM 的智能面试训练平台。

## 功能特性

- 📄 **简历解析** - 自动解析 PDF 简历
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
| `RESUME_OCR_ENABLED=true` | 本地 Ollama OCR 解析 PDF |

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

## 说明

- 前端当前不需要单独启动进程（由后端 `app.main` 挂载并提供）。
- 语音输入需要 `faster-whisper`（通过 `--extra stt` 安装）和 `ffmpeg`（`brew install ffmpeg`，WAV 格式可免）。
- 若后续拆分前后端独立部署，可增加 `frontend` 独立 dev server。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | FastAPI + Python |
| 前端 | 静态页面 (后端托管) |
| LLM | MiniMax, GLM 等 |
| 语音 | Faster-Whisper |

## License

MIT License