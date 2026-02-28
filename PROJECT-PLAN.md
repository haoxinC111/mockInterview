# InterviewSim - 从 0 到 1 开发计划
创建日期：2026-02-22  
当前版本：v0.3（Chat-MVP 快速交付版）  
最后更新：2026-02-23

# AI 模拟面试系统 - 核心架构与开发计划 (Master Plan)

## 1. 产品愿景与核心定义
系统目标是打造一个具备“真实压迫感”和“高度专业性”的 AI 模拟面试官。MVP 阶段垂直聚焦“后端转 Agent 工程师”场景。

### 1.1 v0.3 范围声明（Chat-Only）
- **本阶段目标：** 以最快速度交付可演示、可复盘的 MVP。
- **交互方式：** 暂不实现语音，采用 Web Chat。
- **保留能力：** 简历上传与解析、大纲驱动追问、结构化报告与薪资匹配建议。
- **延后能力：** ASR/TTS、全双工实时音频、前端 VAD、Go 音频网关。

## 2. 架构决策（MVP 优先）

### 2.1 当前架构（v0.3）
- **单后端服务：** Python FastAPI + LangGraph（面试流程状态机）。
- **前端：** 轻量 Web Chat 页面。
- **存储：** SQLite 本地持久化（会话、消息、报告、简历解析结果）。
- **收益：** 最小联调成本，最快端到端交付。

### 2.2 后续演进（v0.4+）
- 恢复 Go 网关（WebSocket 实时双向流）用于语音与高并发连接层。
- Python 服务保持业务大脑定位，Go 负责流量与音视频编排。

## 3. Python 环境与依赖管理（uv 规范）
- 统一使用 `uv` 管理 Python 版本、虚拟环境和依赖。
- 推荐 Python 版本：`3.11`（最低 `3.10`）。
- 依赖定义：`pyproject.toml`。
- 常用命令：

```bash
cd backend/python-brain
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

## 4. 模型接入策略（中转站）

### 4.1 已确认输入
- 你当前拥有中转站 `API Key` 与 `Base URL`。
- 本阶段可用模型：`glm-5`、`MiniMax-M2.5`。
- 后续预留：接入 `Kimi coding plan key`。

### 4.2 配置项
- `LLM_PROVIDER=relay`
- `LLM_BASE_URL=<your relay base url>`
- `LLM_API_KEY=<your relay key>`
- `LLM_MODEL_DEFAULT=glm-5`
- `LLM_MODEL_CANDIDATES=glm-5,MiniMax-M2.5`
- `LLM_KIMI_API_KEY=`（可选，暂不启用）

### 4.3 运行策略
- 默认模型：`glm-5`。
- 会话级可选择：`glm-5` 或 `MiniMax-M2.5`。
- 失败策略：同模型最多重试 2 次；仍失败则降级到另一个候选模型。

## 5. 核心工作流（大纲驱动）
1. `Context Builder`: 解析简历并抽取结构化候选人画像。
2. `Outline Generator`: 基于岗位能力模型生成模块化面试大纲。
3. `Interviewer`: 根据当前模块和历史回答生成问题。
4. `Evaluator`: 按 rubric 对用户回答评分并决策深挖/切题/结束。
5. `Reporter`: 汇总回合记录，生成结构化报告与薪资匹配建议。

## 6. API 契约（Chat-MVP）
1. `POST /api/v1/resumes`
- 上传 PDF 简历，返回 `resume_id + parsed_profile`。

2. `POST /api/v1/interviews`
- 基于 `resume_id + 目标岗位 + 期望薪资` 启动会话。
- 可选 `model`：`glm-5` / `MiniMax-M2.5`。

3. `POST /api/v1/interviews/{session_id}/messages`
- 提交用户消息，返回面试官回复、本轮评估、下一步动作。

4. `POST /api/v1/interviews/{session_id}/finish`
- 主动结束面试并产出报告。

5. `GET /api/v1/reports/{report_id}`
- 查询结构化报告。

## 7. 数据结构（单一真源）
使用 Pydantic 作为接口层单一真源类型：
- `CandidateProfile`
- `InterviewOutline`
- `TurnEvaluation`
- `FinalReport`

## 8. 评分 Rubric（MVP）

### 8.1 维度
- LLM 基础
- RAG 架构
- Agent 编排
- 工程化与可观测性
- 项目表达与复盘能力

### 8.2 分值说明
- `0-1`：关键概念错误或无法回答
- `2-3`：有基础理解，但深度/边界不足
- `4-5`：结构清晰、权衡完整、可落地

### 8.3 分支规则
- `score >= 4`：同 topic 深挖（`depth + 1`）
- `score 2-3`：切换到同模块下一个 topic
- `score <= 1`：标记短板并切下一模块/topic

### 8.4 报告声明
- 报告用于训练与自我评估，不作为真实招聘决策唯一依据。

## 9. 阶段开发计划（可执行）

### Phase A（0.5-1 天）基础骨架
- FastAPI 工程、SQLite、核心类型、健康检查。
- 验收：`/health` 可用，API 空壳联通。

### Phase B（1 天）简历与大纲
- PDF 解析、候选人画像抽取、大纲生成。
- 验收：样例简历可稳定产出 `profile + outline`。

### Phase C（1-1.5 天）多轮面试闭环
- 问题生成、回答评估、分支推进、会话持久化。
- 验收：10+ 轮文本面试闭环可完成并生成报告。

### Phase D（1 天）Web Chat 与报告页
- 简历上传、聊天界面、报告展示与历史会话。
- 验收：从上传到报告的端到端流程可演示。

### Phase E（0.5-1 天）稳定性
- 超时重试、降级策略、日志、样例演示脚本。
- 验收：连续 20 次回放无阻断错误。

## 10. 测试策略与出门标准

### 10.1 测试层次
- 单元测试：评分、分支、结束条件、schema 校验。
- 集成测试：`resume -> interview -> report` 全链路。
- 人工回放：强/弱候选人、异常输入场景。

### 10.2 MVP 发布门槛
- 端到端成功率 `>= 90%`
- 单轮响应 `P95 < 6s`（外部模型正常）
- 报告关键字段完整率 `100%`

## 11. 日志设计（全流程可追踪）
- 日志格式：JSON 行日志（单行一事件），便于 `grep/jq/ELK` 检索。
- 关联主键：
  - `request_id`：HTTP 请求级（中间件生成并回传 `x-request-id`）。
  - `session_id`：面试会话级（业务事件携带）。
  - `report_id`：报告级。
- 事件分层：
  - HTTP 层：`http.request.start/end/error`
  - 业务层：`resume.upload.*`, `interview.start.*`, `interview.turn.*`, `interview.finish.*`, `report.get.*`
  - 引擎层：`engine.outline.*`, `engine.turn.*`, `report.build.*`
- 关键字段：
  - 请求：`method/path/status_code/duration_ms`
  - 回合：`topic/score/decision/next_action/turn_count/module_idx/topic_idx`
  - 报告：`overall_score/strengths_count/risks_count/salary_fit`
- 目标：任意一条请求可通过 `request_id` 串联完整链路；任意一场面试可通过 `session_id` 回放全过程。

## 12. 当前目录规划（v0.3）

```text
mockInterview/
├── backend/
│   └── python-brain/
│       ├── app/
│       │   ├── main.py
│       │   ├── api/
│       │   ├── core/
│       │   ├── models/
│       │   ├── services/
│       │   └── workflow/
│       ├── tests/
│       └── pyproject.toml
├── frontend/
│   └── web-chat/
└── PROJECT-PLAN.md
```
