# InterviewSim - 从 0 到 1 开发计划
创建日期：2026-02-22  
当前版本：v0.5（Chat-MVP + STT + 10 分制评估）  
最后更新：2026-03-12

# AI 模拟面试系统 - 核心架构与开发计划 (Master Plan)

## 当前迁移状态（2026-03-12）

- LangGraph 迁移的最新实现与测试基线继续维护在 `feat/langgraph-migration` worktree：`/Users/chenhaoxin/ccProjects/mockInterview/.worktrees/langgraph-migration`。
- 当前已完成：workflow flags、shadow mode、golden tests、resume readiness 门控、`training_guidance` 报告语义、mission guard 与 runbook。
- 当前验证状态：自动化测试通过；**人工未测试**。
- `main` 仍作为稳定基线，不默认视为已完成 LangGraph 主路径切换。

## 1. 产品愿景与核心定义
### 1.0 项目立意（北极星）

> **本系统的核心目标不是「考倒候选人」，而是「帮助候选人成长」。**

- 每一个提问引导候选人暴露真实的能力边界。
- 每一次评估指出具体可改进的方向。
- 每一份反馈让候选人比面试前更清楚自己该学什么、怎么练。
- 始终以「提升候选人能力」为第一优先级。

**功能决策判据**：如果新功能不能帮候选人更精准地知道"该补什么、怎么补"，就不值得做。
系统目标是打造一个具备“真实压迫感”和“高度专业性”的 AI 模拟面试官。MVP 阶段垂直聚焦“后端转 Agent 工程师”场景。

### 1.1 当前活跃计划入口（2026-03-09）

`PROJECT-PLAN.md` 仍然是项目总计划和长期路线图，但当前正在推进的 Agent 编排迁移方案已经拆分到 `docs/` 下的专门文档中。

- 当前总入口：`docs/README.md`
- 当前架构选型文档：`docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`
- 当前执行计划文档：`docs/plans/2026-03-09-langgraph-migration-plan.md`

阅读顺序建议：

1. 先看本文件，理解项目立意、当前能力边界和长期路线
2. 再看 `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`，理解为什么后续推荐 `LangGraph`
3. 最后看 `docs/plans/2026-03-09-langgraph-migration-plan.md`，按任务顺序推进实现

### 1.2 v0.5 范围声明
- **本阶段目标：** 可演示、可复盘的 MVP，已具备语音输入能力。
- **交互方式：** Web Chat + 语音输入（本地 Whisper STT）。
- **已实现能力：** 简历上传与解析（OCR/LLM/规则三级）、大纲驱动追问、10 分制城市薪资感知评估、结构化报告与薪资匹配、暗色模式与隐身模式、语音录入。
- **延后能力：** TTS 语音合成、全双工实时音频、前端 VAD、Go 音频网关。

## 2. 架构决策（MVP 优先）

### 2.1 当前架构（v0.5）
- **单后端服务：** Python FastAPI，面试状态机在 `InterviewEngine.process_turn()` 中手动实现。
- **前端：** Vanilla HTML/JS/CSS Web Chat 页面，由 FastAPI 静态挂载。
- **存储：** SQLite 本地持久化（SQLModel ORM，JSON 列存储嵌套数据）。
- **STT：** 本地 `faster-whisper`（Whisper small），前端 MediaRecorder 录音 + 浏览器 WAV 编码 + 后端推理。
- **OCR：** 本地 Ollama `deepseek-ocr` 用于 PDF 简历文字提取（可选）。
- **收益：** 最小联调成本，最快端到端交付，语音输入零云端依赖。

### 2.2 后续演进（v0.4+）
- 恢复 Go 网关（WebSocket 实时双向流）用于语音与高并发连接层。
- Python 服务保持业务大脑定位，Go 负责流量与音视频编排。

### 2.3 当前推荐的近期演进方向（2026-03-09）

- `main` 继续保留为“自定义状态机稳定基线”，用于回归验证、效果对照和日常修复
- 新功能主方向不再继续堆叠到单体 `InterviewEngine` 中，而是逐步迁移到 `LangGraph-first` 工作流架构
- `LangChain` 不作为主流程控制器使用，只在结构化输出、Prompt 模板、检索和工具封装等场景按需引入
- 所有迁移都必须保持三条红线：
  - 不削弱“帮助候选人成长”的反馈质量
  - 不移除现有规则兜底与非 LLM 回退路径
  - 不破坏当前 FastAPI API 契约

当前推荐的开发方式：

- `main` 工作目录：`/Users/chenhaoxin/ccProjects/mockInterview`
- LangGraph 独立工作区：`/Users/chenhaoxin/ccProjects/mockInterview/.worktrees/langgraph-migration`
- 对应远程分支：`origin/feat/langgraph-migration`

## 3. Python 环境与依赖管理（uv 规范）
- 统一使用 `uv` 管理 Python 版本、虚拟环境和依赖。
- 推荐 Python 版本：`3.12`（最低 `3.10`）。
- 依赖定义：`pyproject.toml`，可选组：`dev`（测试）、`stt`（faster-whisper）。
- 常用命令：

```bash
cd backend/python-brain
uv sync --extra dev --extra stt
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest -q
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
- `LLM_MODEL_DEFAULT=MiniMax-M2.5`
- `LLM_MODEL_CANDIDATES=MiniMax-M2.5,glm-5`
- `LLM_KIMI_API_KEY=`（可选，暂不启用）

### 4.3 运行策略
- 默认模型：`MiniMax-M2.5`。
- 会话级可选择：`MiniMax-M2.5` 或 `glm-5`。
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

6. `POST /api/v1/stt`
- 上传音频文件（WAV/webm），返回 `{"text": "..."}` 转写结果。
- 使用本地 `faster-whisper` 推理，无云端依赖。

7. `DELETE /api/v1/resumes/cache`
- 按文件名清除简历解析缓存。

## 7. 数据结构（单一真源）
使用 Pydantic 作为接口层单一真源类型：
- `CandidateProfile`：候选人画像（简历解析产物）
- `InterviewOutline`：面试大纲（模块 → 主题 → 关键词）
- `TurnEvaluation`：回合评估，含 `score`、`evidence`、`gaps`、`score_rationale`、`reference_answer`；v0.6+ 新增 `dimension_scores: dict[str, int]`（按维度评分）和 `primary_dimension: str`
- `FinalReport`：结构化报告；v0.6+ 新增 `dimension_scores`（维度聚合分）、`radar_chart`（雷达图数据）、`action_plan_30d.by_dimension`（分维度行动计划）

## 8. 评分 Rubric（MVP）

### 8.1 四维能力评估模型

面试评估采用四维交叉模型——每一轮回答不只打"知识点对错"的单一分，还从多个能力维度评价，帮助候选人精确定位薄弱能力方向。

| 维度 | ID | 权重 | 评估重点 |
|------|-----|------|----------|
| 技术深度 | `technical_depth` | 30% | LLM/RAG/Agent 技术栈原理与实践经验 |
| 架构设计 | `architecture_design` | 30% | 系统设计、技术选型、权衡分析 |
| 工程实践 | `engineering_practice` | 25% | 生产环境稳定性、监控、工程化能力 |
| 沟通表达 | `communication` | 15% | 项目展示、逻辑清晰、量化成果 |

> **实施说明**：沟通表达维度在语音模式就绪后启用（v0.9+），当前文本面试阶段使用前三维度评估（权重归一化为 35/35/30）。

#### 大纲模块（Agent Engineer 岗位）
- LLM 基础（Transformer 原理、Prompt 设计）
- RAG 架构（索引与召回、检索优化）
- Agent 编排（状态机与工具调用、多 Agent 协作）
- 工程化与可观测性（稳定性与回退、监控告警）
- 项目实战深挖

#### 主题-维度映射

每个面试主题映射到主维度和辅助维度，用于分维度聚合评分：

| 主题 | 主维度 | 辅助维度 |
|------|--------|----------|
| Transformer 原理 | 技术深度 | 架构设计 |
| Prompt 设计 | 技术深度 | 工程实践 |
| 索引与召回 | 技术深度 | 架构设计、工程实践 |
| 检索优化 | 架构设计 | 技术深度、工程实践 |
| 状态机与工具调用 | 架构设计 | 技术深度 |
| 稳定性与回退 | 工程实践 | 架构设计 |
| 项目实战深挖 | 工程实践 | 全维度 |

#### 设计决策记录
- **采纳**：四维模型 + 分维度评分标准 + 主题-维度映射 + 雷达图 + 分维度行动计划。
- **不采纳**：百分位排名（缺乏人群数据，易误导）、独立 `evaluation_service.py`（当前规模无需拆分，评估逻辑保留在 `interview_engine.py`）、`roles/` 注册表模式（过度抽象，单个 YAML 配置足矣）。
- **来源**：`docs/designs/2026-03-01-role-based-interview-framework.md`

### 8.2 分维度评分标准（10 分制）

#### 技术深度
| 分数 | 水平 |
|------|------|
| 1-2 | 关键概念错误或无法回答，仅提到名词无法解释原理 |
| 3-4 | 有基本理解但缺少细节，或理解准确能举简单例子 |
| 5-6 | 理解到位有实际经验，能做 tradeoff 分析 |
| 7-8 | 深度好有架构思维，体系化思考有生产案例 |
| 9-10 | 有独到见解和深入优化经验，专家级有行业影响力的认知 |

#### 架构设计
| 分数 | 水平 |
|------|------|
| 1-2 | 无法进行系统设计，或只能描述单一组件 |
| 3-4 | 能画出基本架构图，考虑了主要组件和交互 |
| 5-6 | 能分析关键 tradeoff，考虑了性能和扩展性 |
| 7-8 | 有完整的技术选型逻辑，考虑了容错和降级 |
| 9-10 | 有大规模系统设计经验，架构师级别有创新设计 |

#### 工程实践
| 分数 | 水平 |
|------|------|
| 1-2 | 无工程实践意识，或知道基本概念但无实践 |
| 3-4 | 有简单项目经验，了解常见问题和解决方案 |
| 5-6 | 有生产环境部署经验，能处理常见线上问题 |
| 7-8 | 有完整的监控和告警体系，有故障排查和复盘经验 |
| 9-10 | 有高可用系统建设经验，SRE 级别的工程能力 |

### 8.3 分支规则（决策优先级从高到低）
1. `turn_count >= max_turns(12)` → 强制结束
2. LLM 评估超时 & `score >= 3` & `depth < 1` → 保守追问一次
3. LLM 推荐 `end` → 结束
4. LLM 推荐 `deepen` & `score >= 5` → 同 topic 深挖（`depth + 1`）
5. LLM 推荐 `next_topic` → 切换话题
6. `score >= 7` & 未达深挖上限 → 同 topic 深挖（规则兜底）
7. `score <= 2` → 标记短板并跳到下一模块
8. 其余 → 常规推进到下一 topic

### 8.4 评估输出字段
每轮评估包含：`score`(1-10)、`score_rationale`(200-400 字评分依据)、`evidence[]`(亮点)、`gaps[]`(不足)、`reference_answer`(300-500 字参考答案)、`recommend_action`(deepen/next_topic/end)。
评分感知 `city` + `expected_salary`，月薪越高对回答深度要求越严格。

### 8.5 报告声明
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

### Phase F（当前活跃计划）LangGraph 迁移准备与分阶段重构
- 目标：在不破坏现有面试体验和报告质量的前提下，把自定义状态机逐步迁移为可恢复、可观测、可灰度切换的工作流架构
- 当前主计划文档：`docs/plans/2026-03-09-langgraph-migration-plan.md`
- 当前设计依据：`docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`

Phase F 当前分为 5 个近期里程碑：

1. 用 golden tests 冻结现有行为，建立迁移前基线
2. 引入强类型 workflow state，补齐状态边界和版本字段
3. 增加 workflow runtime flags，支持 legacy / shadow / langgraph 切换
4. 抽出 workflow facades，把现有领域服务改造成可复用节点能力
5. 引入 LangGraph skeleton graphs，为报告、简历、面试三个流程建立编排骨架

说明：

- Phase F 是当前最优先的增量开发方向
- 实际编码优先在 `feat/langgraph-migration` worktree 中进行
- `main` 只接收已经验证过的稳定方案或文档基线更新

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

## 12. 当前目录规划（v0.5）

```text
mockInterview/
├── backend/
│   └── python-brain/
│       ├── app/
│       │   ├── main.py              ← FastAPI 入口、CORS、request_id 中间件、静态挂载
│       │   ├── api/routes.py        ← 所有 REST 端点（/api/v1 前缀）
│       │   ├── core/                ← config、database、logging、request_context
│       │   ├── models/
│       │   │   ├── db.py            ← SQLModel 表（Resume、InterviewSession、InterviewMessage 等）
│       │   │   └── schemas.py       ← 纯 Pydantic 模型（API 契约单一真源）
│       │   ├── services/
│       │   │   ├── interview_engine.py ← 大纲生成 + 状态机 + 评估 + 追问
│       │   │   ├── llm_client.py     ← OpenAI 兼容中转调用
│       │   │   ├── resume_parser.py  ← PDF/OCR 解析 + 画像提取
│       │   │   ├── report_service.py ← 报告聚合与薪资匹配
│       │   │   └── stt_service.py    ← faster-whisper 本地语音转写
│       │   └── workflow/state.py     ← InterviewState TypedDict
│       ├── tests/
│       └── pyproject.toml
├── frontend/
│   └── web-chat/                    ← Vanilla HTML/JS/CSS（暗色模式 + 隐身模式 + 语音）
├── .github/copilot-instructions.md
└── PROJECT-PLAN.md
```

---

## 13. 产品演进路线图（v0.6 → v1.0）

### 13.1 定位升级

```
v0.5 定位：模拟技术知识问答（有价值但易被替代）
v1.0 目标：AI-Native 技术面试全流程训练系统（独特壁垒）
```

核心差异化三板斧：
1. **不只考知识，更考判断力** → 系统设计 + Code Review + Coding 模式
2. **不只面试，更帮复盘** → 逐轮复盘 + 参考答案对比 + 薄弱点追踪
3. **不只通用，更贴实况** → 城市薪资感知 + 岗位能力模型可配置 + 难度自适应

### 13.2 行业背景：技术岗位面试的演变

| 阶段 | 面试核心 | 考法 | 特征 |
|---|---|---|---|
| 2020 前 | "你知不知道" | 八股文、算法背诵、框架 API | 有标准答案，答对就行 |
| 2023-2025 | "你做没做过" | 项目深挖、系统设计、场景 tradeoff | 无唯一答案，考思维过程 |
| 2026（当前） | "你能不能用 AI 解决问题" | Agent 架构、Prompt 工程、RAG 管线、AI 工具链 | 旧知识变基线，AI 能力变筛选器 |
| 2027-2030（趋势） | "你能不能定义问题并审查 AI 的输出" | Code Review > 编码速度、架构判断 > API 记忆、问题定义 > 问题求解 | AI-Native 工程师 |

三个确定性趋势：
- **Agent 编排成为核心技能**：不只是会用 LangChain，而是理解多 Agent 协作的可靠性工程（状态管理、Tool-use 安全边界、评估体系）
- **全栈 → AI-Full-Stack**：应用层 + 模型层 + 数据层 + 评估层融合，能写 prompt、能跑 fine-tune、能搭 RAG、能做 eval pipeline
- **代码生产方式根本性变化**：AI 生成代码成常态，面试考"能不能审出问题"而非"能不能写出来"

---

## 14. v0.6 — 面试复盘系统（Tier 1 优先）

**核心价值**：真实面试最大痛点不是面试本身，而是面完不知道哪里答得差。竞品几乎没有做好这个功能。

### 14.1 逐轮复盘回放
- 前端增加"复盘"页面，时间轴视图展示每一轮：问题 → 用户回答 → 评分 → 参考答案 → 差距分析
- 支持筛选："只看低分轮" / "只看某模块"
- 数据源：已有 `evaluations[]` + `decision_traces[]` 全程记录，无需后端改动

### 14.2 结构化报告 UI（维度驱动）
- 将报告从 raw JSON → 结构化报告卡片

#### 雷达图
- 数据结构：`{ labels: ["技术深度", "架构设计", "工程实践"], values: [7.0, 6.5, 6.0], benchmarks: [6.0, 6.0, 6.0] }`
- `benchmarks` 为岗位基准线（可配置），默认 6.0
- 前端使用 Canvas 或 SVG 渲染，支持暗色模式

#### 分维度评估
- 每个维度独立展示：得分、亮点（strengths）、不足（gaps）
- 取代当前单一 `avg_score`，帮候选人精确定位"哪个能力方向薄弱"

#### 分维度行动计划（30 天）
```json
{
  "action_plan_30d": {
    "overall": ["针对薄弱维度建立复盘卡片，梳理核心概念并进行模拟演练"],
    "by_dimension": {
      "engineering_practice": ["学习 LLM 调用的容错和重试策略", "搭建基础监控告警体系"],
      "architecture_design": ["练习系统设计题，关注 tradeoff 表达"]
    }
  }
}
```
- 行动计划按维度拆分，候选人一眼看到"该补什么、怎么补"
- 改进建议精确到具体轮次："你在 X 话题第 N 轮的回答暴露了 Y 问题"

### 14.3 历史对比
- 同一用户多次面试的分数趋势折线图
- 薄弱模块追踪：哪些知识点反复失分

---

## 15. v0.7 — 系统设计面试模式（Tier 1）

**核心价值**：2026 年几乎所有高级技术岗的终面都有系统设计环节。当前系统只覆盖"知识点问答"，缺失最关键考核维度。

### 15.1 设计题生成
- 新增面试模式：`system_design`（与现有 `knowledge_qa` 并行）
- 基于候选人简历 + 岗位自动生成开放式设计题
- 题目范例："设计一个日活千万的消息推送系统" / "设计一个支持多租户的 RAG 平台"

### 15.2 多阶段追问
系统设计面试的标准追问流程：
1. **需求澄清**：功能范围、用户规模、SLA 要求
2. **容量估算**：QPS、存储量、带宽
3. **核心架构**：组件拆分、技术选型、数据流
4. **数据模型**：表设计、索引策略、缓存方案
5. **深入设计**：某个子系统的详细方案
6. **扩展性与可用性**：故障处理、扩容策略、监控体系

### 15.3 评估维度
- 需求澄清能力（是否在动手前先问清边界）
- 估算合理性（数量级是否正确）
- 架构完整性（核心组件是否覆盖）
- 技术选型合理性（是否能解释 tradeoff）
- 扩展性考量（是否考虑了 scale 和故障）

---

## 16. v0.8 — Coding / Code Review 模式（Tier 1）

**核心价值**：纯靠嘴说的技术面试正在退出历史舞台，2026 年技术面几乎必考 coding。更重要的是，AI 生成代码成为常态后，Code Review 能力比编码速度更重要。

### 16.1 Coding 模式
- 前端增加代码编辑器区域（Monaco Editor 或 CodeMirror）
- 面试官出算法/设计题 → 候选人现场编码
- LLM 评估：正确性 + 时间/空间复杂度 + 代码风格 + 异常处理
- 可从"伪代码描述"起步，降低实现门槛

### 16.2 Code Review 模式
- 给候选人一段 AI 生成的代码（含故意埋入的 bug/架构问题/安全隐患）
- 候选人需找出问题并给出改进方案
- 评估维度：bug 发现率、架构判断力、安全意识、改进方案质量
- **这是对"AI 时代工程师"最核心的考核**——你能不能审查和修正 AI 的输出

### 16.3 评估维度
- 代码正确性（功能是否实现）
- 复杂度分析（时间/空间是否最优）
- 工程质量（命名、结构、错误处理、边界条件）
- 审查能力（Code Review 模式特有：发现了多少问题、改进方案是否可行）

---

## 17. v0.9 — 体验与智能增强（Tier 2）

### 17.1 TTS 语音合成输出
- 面试官的问题和反馈从文字变成语音，营造真实对话感
- 方案选型：Edge TTS（零成本）/ CosyVoice / ChatTTS（本地推理）
- 支持中文男声/女声可选，语速可调
- 与 STT 配合形成完整语音闭环：说话 → 转写 → 回答 → 语音播放

### 17.2 面试难度自适应（CAT 策略）
- 参考 GRE 的计算机自适应测试设计
- 前 3 题出中等难度（基准测试）
- 根据得分动态调整后续题目难度：连续高分→升级到架构/tradeoff 题；连续低分→回退到基础概念题
- `max_depth` 从固定值变为动态值：高分候选人允许追到 4-5 层深度
- 累积评估：前几轮同 topic 的 score 趋势影响当前决策（持续高分→该停了；持续走低→该换了）

### 17.3 多岗位能力模型
- 将当前硬编码的"后端转 Agent 工程师"知识点抽象为可配置的岗位能力模型 JSON
- 内置模板：
  - **后端工程师**：分布式、数据库、微服务、性能优化
  - **AI/Agent 工程师**：LLM 基础、RAG、Agent 编排、评估体系
  - **前端工程师**：框架原理、浏览器机制、性能优化、工程化
  - **算法工程师**：ML 基础、模型训练、推理优化、数据处理
  - **SRE / 平台工程师**：Linux、网络、K8s、监控告警、故障排查
- 用户可选择或自定义岗位模型
- 相同候选人简历 + 不同岗位模型 = 不同面试大纲和评估标准

### 17.4 录音时长与转写确认
- 录音中显示实时时长计时器
- 转写完成后弹出确认浮层，用户可编辑修正后再填入
- 支持"重新录制"一键清除重来

---

## 18. v1.0 — 全流程模拟与数据飞轮（Tier 3）

### 18.1 完整面试流程模拟
真实技术面试包含 6 个环节，当前仅覆盖"知识考核"。v1.0 目标：完整模拟全流程。

| 环节 | 时长 | 考察点 | 状态 |
|---|---|---|---|
| 自我介绍 | 3-5 min | 表达能力、项目亮点提炼 | 🔲 未实现 |
| 项目深挖 | 10-15 min | 技术深度、问题解决、复盘能力 | ✅ 已实现（大纲中的项目模块） |
| 知识考核 | 10-15 min | 技术基础、概念理解、实战经验 | ✅ 已实现 |
| 系统设计 | 15-20 min | 架构能力、估算、扩展性 | 🔲 v0.7 规划 |
| Coding | 15-20 min | 编码能力、代码质量 | 🔲 v0.8 规划 |
| 反问环节 | 5 min | 对公司/团队的了解度、职业规划 | 🔲 未规划 |

### 18.2 自我介绍环节
- 候选人语音或文字做自我介绍
- AI 评估：是否突出亮点、逻辑是否清晰、时间控制、是否与简历匹配
- 即时反馈：你的自我介绍缺少了 X、建议加入 Y

### 18.3 反问环节模拟
- 模拟候选人向面试官提问的场景
- 评估：问题质量（"你们用什么技术栈" vs "团队未来半年的技术方向是什么"）
- 提供优质反问示范和评分

### 18.4 面试数据飞轮
- 匿名收集用户面试表现数据
- 构建"高频薄弱点"知识图谱：哪些知识点最多人答不好
- 智能推荐：你在 RAG 检索优化上的得分低于 80% 的用户，建议针对性练习
- 长期形成数据壁垒：用得越多 → 数据越准 → 推荐越精准 → 用户越多

### 18.5 面试官人格系统
- 不同面试官风格：
  - **严厉型**：步步紧逼，不给喘息机会，追问极细
  - **引导型**：给提示，循循善诱
  - **压力型**：故意挑战你的回答，模拟 stress interview
- 让用户选择面试官风格，适应不同公司文化

---

## 19. 当前已知优化项（技术债）

| 问题 | 现状 | 改进方向 | 优先级 |
|---|---|---|---|
| **LLM 核心依赖阻断** | 调用超时报错时降级为僵硬的关键字评分，不仅反馈突兀，也破坏了"真实 AI 面试官"的体验一致性 | **废除评价兜底降级**：不再进行人机规则切换。LLM 调用失败直接从接口返回 503 等明确错误（如"由于网络波动或模型过载，考官开小差了，请重试"），由前端负责提示并保留现场上下文支持一键重发。 | **P0** |
| **回答风格统一僵硬** | 缺乏约束，无论题目倾向，系统常向长篇大论倾斜或追问过多延伸点，不符合真实面试看重"精确干练"的诉求 | **增加「答题风格（Answer Style）」偏好全量配置**。在首页（与薪资等并列）提供：①「精准干练」(直击痛点，不讲冗余)；②「深度发散」(连点成线，考察全面性)。该参数传入系统 prompt 进行实时评估和后续生成的策略调整。 | **P0** |
| STT 同步阻塞 | `transcribe_audio()` 在 uvicorn 线程池同步运行 | `run_in_executor` 或改 async | P1 |
| Whisper 首次加载慢 | 第一次请求才加载模型（~10s） | startup 事件预加载 | P1 |
| 规则 fallback 评分粗糙 | keyword match | 已规划废弃（升级为 P0 错误直抛） | 废弃 |
| 追问可能重复 | LLM 生成追问时可能重复之前问过的角度 | prompt 附上已问过的问题列表 | P1 |
| 报告只有单一 avg_score | 无模块级维度分 | 每模块独立评分 + 雷达图数据 | P2 |
| LLM 超时硬编码 | 评估 15s、追问 15s、大纲 25s 写死 | 根据模型和网络动态调整 | P3 |
| `max_depth` 固定为 2 | 所有候选人深挖上限一样 | 按候选人水平动态调 | P2 |
