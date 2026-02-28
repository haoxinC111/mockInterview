# InterviewSim (Chat-MVP)

本项目当前为 **Chat-MVP**：后端 FastAPI + 前端静态页面（由后端托管）。

## 目录结构

- `backend/python-brain`：后端服务
- `frontend/web-chat`：前端页面资源

## 已配置模型中转

后端配置文件：`backend/python-brain/.env`

已设置：
- `LLM_BASE_URL=https://v1.cdks.work`
- `LLM_MODEL_DEFAULT=MiniMax-M2.5`
- `LLM_MODEL_CANDIDATES=MiniMax-M2.5,glm-5`

可选开关（默认关闭，开启后才会在解析/对话中实际调用 LLM）：
- `RESUME_PARSER_USE_LLM=true`
- `INTERVIEW_ENGINE_USE_LLM=true`
- `INTERVIEW_TURN_USE_LLM=true`（逐轮评分/追问，开启后延迟更高）
- `RESUME_OCR_ENABLED=true`（本地 Ollama OCR 解析 PDF）

语音输入（默认开启，本地 Whisper 推理）：
- `STT_ENABLED=true`
- `STT_MODEL=small`（可选 tiny/base/small/medium/large）

日志落盘：
- `LOG_DIR=logs`
- `LOG_FILE=interviewsim.log`
- `SUMMARY_LOG_FILE=interviewsim.summary.log`
- 默认落盘路径：`backend/python-brain/logs/interviewsim.log`
  - 全量日志（request/response 全量体）：`backend/python-brain/logs/interviewsim.log`
  - 关键摘要日志（human 输入 / LLM 输出 / 决策原因）：`backend/python-brain/logs/interviewsim.summary.log`

## 从项目根目录启动

### 1) 安装后端依赖

```bash
cd backend/python-brain
uv sync --extra dev --extra stt
```

### 2) 启动后端（同时托管前端页面）

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) 打开页面

- Web Chat：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

## 快速验证

```bash
cd backend/python-brain
uv run pytest -q
```

## 说明

- 前端当前不需要单独启动进程（由后端 `app.main` 挂载并提供）。
- 语音输入需要 `faster-whisper`（通过 `--extra stt` 安装）和 `ffmpeg`（`brew install ffmpeg`，WAV 格式可免）。
- 若你后续拆分前后端独立部署，再增加 `frontend` 独立 dev server。
