# Agent Orchestration Migration Strategy

> **文档状态**: Draft
> **作者**: GitHub Copilot (GPT-5.4)
> **创建日期**: 2026-03-09
> **文档定位**: Agent 编排迁移对比、选型与重构策略

## 1. 背景

InterviewSim 当前使用自定义 `InterviewEngine` 状态机驱动整个面试闭环：
- 简历解析后生成候选人画像
- 基于画像和岗位构建面试大纲
- 逐轮生成问题、评估回答、推进 topic/module/depth
- 汇总回合数据生成成长导向报告

这套方案在 MVP 和单主流程阶段是合理的，因为它具备三个关键优点：
- 强可控：流程顺序、深挖逻辑、结束条件全部显式编码
- 强降级：LLM 失败时可回退到规则路径，避免系统失效
- 强业务贴合：逻辑围绕“帮助候选人成长”这一立意编写，不是通用 Agent demo

但随着系统要支持更多岗位、更复杂评估链路、多 Agent 协作、知识检索、人工介入和可恢复执行，自定义状态机会越来越难承载：
- 流程分支会持续膨胀，`InterviewEngine` 会变成超级控制器
- `state_json` 结构会越来越松散，类型边界和迁移成本上升
- 可视化执行、节点级调试、断点恢复、异步任务拆分都要重复自研
- 多功能线并存时，新增需求会不断侵入现有主流程，回归风险增大

因此，后续优化目标不是“把框架换得更潮”，而是建立一个更适合长期演进的编排底座，同时不牺牲当前系统最重要的能力：
- 结构化、专业、成长导向的面试体验
- LLM 不可用时依然可工作
- 输出质量可追踪、可回放、可验证

## 2. 评估标准

迁移方案必须服务于项目立意，而不是相反。判断标准按优先级如下：

1. 成长导向是否更强
- 是否更容易沉淀“证据、差距、参考答案、行动建议”
- 是否更容易在多轮流程中保持反馈一致性，而不是只追求答题正确率

2. 稳定性是否更高
- 是否支持节点级失败处理、重试、回退和人工接管
- 是否能保留当前规则兜底能力，而不是把所有步骤都强绑定到 LLM

3. 扩展性是否更强
- 是否能更容易增加岗位模板、评估节点、工具节点、知识检索、报告增强
- 是否能避免所有新需求继续塞进单个 `InterviewEngine`

4. 开发与维护成本是否可接受
- 是否引入过多抽象，导致小改动也需要跨层理解
- 是否容易测试、回放和灰度迁移

5. 效果是否可验证
- 是否可以通过 shadow mode、黄金样本、回归测试验证“迁移后至少不差于现在”

## 3. 三种可选方案

### 方案 A：继续维持自定义状态机，仅做局部重构

做法：
- 保留 `InterviewEngine` 作为总控制器
- 继续把流程推进、状态更新、问题生成、评分决策集中在现有服务中
- 仅通过拆类、补类型、抽适配层和增强测试来缓解复杂度

优点：
- 改动最小，短期风险最低
- 当前测试体系和 API 契约几乎不受影响
- 对现有团队认知最友好

缺点：
- 只能延缓复杂度，不解决编排模型问题
- 未来多 Agent、多工具、可恢复工作流仍然要自己实现
- 会继续堆积“业务规则 + 编排逻辑 + 状态迁移”耦合

适用条件：
- 未来 3 个月仍只做单岗位、单主流程优化
- 不准备引入更复杂的检索、工具使用或人工审核链路

结论：
- 不是长期最优，仅适合作为短期止血方案

### 方案 B：全面迁移到 LangChain，以 Agent/Chain 为主编排

做法：
- 使用 LangChain 的 prompt、parser、chain、agent 抽象统一 LLM 交互
- 让更多步骤通过 LangChain runnable/agent 形式串联

优点：
- Prompt、结构化输出、模型切换、检索接入会更标准化
- 部分组件复用效率较高，适合快速接 RAG、retriever、tool

缺点：
- LangChain 更像工具箱，不是最佳的流程图编排内核
- 对当前这种显式状态推进、强业务分支场景，Agent 抽象不一定更自然
- 容易出现“为了框架而框架”，把原本清晰的业务逻辑藏进 runnable 链
- 对最终面试效果的直接提升有限

适用条件：
- 项目核心诉求是快速集成更多模型、向量库、工具和 prompt 组件
- 而不是首先解决复杂工作流编排

结论：
- 可作为组件层，不建议作为 InterviewSim 的主编排方式

### 方案 C：以 LangGraph 作为工作流底座，选择性使用 LangChain 组件

做法：
- 使用 LangGraph 管理状态、节点、边、checkpoint 和恢复
- 保留现有领域服务思想，把 `resume_parser`、`report_service`、`evaluation` 等包装成 graph node
- 只选择性使用 LangChain 的 PromptTemplate、structured output、retriever/tool 抽象
- 不采用“全自动 agent 自主规划”作为主路径，而是坚持“成长导向、可控分支”的工作流编排

优点：
- 最贴合当前系统从“状态机”向“可扩展工作流”演进的方向
- 节点、边和状态天然适合表达面试主流程
- 更容易引入暂停/恢复、人工介入、异步任务、节点级追踪
- 可以保留当前显式业务规则和规则兜底，不必把流程控制权交给黑盒 agent
- 更适合逐步迁移，不需要一次性推翻重写

缺点：
- 需要引入新的运行时和状态 schema 设计
- 迁移初期会有双轨维护成本
- 团队需要学习 graph state、checkpoint 和 node contract

适用条件：
- 明确要继续扩展岗位、流程和工具链
- 希望工作流可视化、可恢复、可分阶段演进

结论：
- 这是 InterviewSim 后续最优选型

## 4. 推荐架构

推荐采用：`LangGraph 作为编排内核 + LangChain 作为可选组件层 + 现有领域服务保留并下沉为节点能力`。

核心原则：
- 不用 LangChain AgentExecutor 替代业务流程
- 不把“让 LLM 自己决定一切”当作高级能力
- 仍然坚持“显式状态、成长导向、规则兜底”

### 4.1 分层结构

1. Interface Layer
- FastAPI routes 保持不变，继续承担 HTTP 契约、会话装配和鉴权

2. Application Workflow Layer
- 新增 LangGraph workflows，成为真正的流程编排入口
- 例如：`interview_session_graph`、`resume_ingestion_graph`、`report_generation_graph`

3. Domain Services Layer
- 保留现有领域能力：`resume_parser`、`report_service`、评估逻辑、题纲生成逻辑
- 它们不再承担“大流程推进者”角色，而是变成 node 内可调用的纯业务能力

4. Infrastructure Layer
- `llm_client`、SQLite/SQLModel、日志、OCR/STT 等基础设施继续保留
- 未来可扩展 checkpoint store、trace store、experiment store

### 4.2 为什么这种方式最符合项目立意

项目北极星不是“尽量像一个通用 Agent 平台”，而是“帮助候选人成长”。这意味着：
- 系统必须能稳定地产出高质量反馈，而不是只追求自由推理
- 每个节点都应围绕“问题质量、证据提取、差距识别、行动建议”设计
- 当模型失败时，系统仍应给出保守但有价值的引导，而不是卡死

LangGraph 恰好适合把这些要求固化为可验证的工作流：
- 用显式节点封装成长导向逻辑
- 用条件边保证低分、超时、无效回答等场景下的保守推进
- 用 checkpoint 和 trace 保留完整成长轨迹

## 5. 迁移后的目标工作流

### 5.1 Resume Ingestion Graph

节点建议：
- `load_resume_content`
- `extract_text_via_ocr`
- `extract_text_via_pdf`
- `parse_candidate_profile`
- `validate_profile`
- `persist_resume_cache`

目标：
- 保留当前 OCR 优先、pypdf 降级、规则/LLM 混合解析能力
- 让失败路径显式可见
- 为后续加入图片简历、多模态简历、知识补全留接口

### 5.2 Interview Session Graph

节点建议：
- `load_session_context`
- `build_or_load_outline`
- `select_current_topic`
- `generate_question`
- `collect_answer_context`
- `evaluate_answer`
- `decide_next_action`
- `advance_state`
- `persist_turn`
- `emit_growth_feedback`

条件边建议：
- `llm_unavailable` -> rule-based evaluator
- `score_high` and `depth_remaining` -> deepen
- `score_low` -> next_topic or next_module
- `max_turns_reached` -> end
- `human_review_required` -> pause_for_review

目标：
- 把当前 `InterviewEngine.process_turn()` 拆成可观测节点
- 保留当前分支逻辑，但让每个决策点都能独立测试和替换

### 5.3 Report Generation Graph

节点建议：
- `aggregate_turn_evaluations`
- `compute_dimension_scores`
- `build_strengths_and_risks`
- `generate_action_plan`
- `validate_report_mission`
- `persist_report`

目标：
- 报告不再只是最终函数，而是一条可增强的工作流
- 后续可插入“参考答案补全”“学习资源推荐”“岗位对标建议”等节点

## 6. LangChain 在新架构中的合理用法

推荐使用：
- PromptTemplate 或等价模板机制，统一 prompt 维护
- Structured output/schema parser，减少手写 JSON 抽取脆弱性
- Retriever/VectorStore 抽象，为后续题库和知识库做准备
- Tool abstraction，用于受控接入题库查询、知识检索、参考答案生成

不推荐使用：
- 让通用 agent 自主决定 interview 主流程
- 用 AgentExecutor 替代显式的面试状态推进
- 过早引入 multi-agent conversation 作为默认路径

原因：
- 主流程必须可控、可解释、可回退
- 面试系统不应把“自由代理行为”置于“候选人成长体验”之上

## 7. 效果保障原则

迁移不是只看代码是否能跑，而要保证效果不倒退。

### 7.1 业务效果守护线

必须保持：
- 问题始终单点聚焦，避免并列多问
- 低质量回答时，系统优先给出成长导向追问或切题，而不是简单判死
- 报告必须保留 evidence、gaps、reference_answer、action_plan
- 当 LLM 不可用时，仍有保守可用的 fallback 路径

### 7.2 迁移验证机制

1. Golden dataset
- 建立一批固定简历、固定回答、固定预期分支和报告快照
- 迁移前后跑同一数据集，对比输出差异

2. Shadow mode
- 线上继续使用旧引擎返回结果
- 同时后台运行 LangGraph 新链路，记录差异但不影响用户

3. Side-by-side review
- 对比 question、score、decision、report 的差异
- 重点人工审查是否弱化了成长导向

4. Feature flags
- 通过配置控制新旧 workflow 切换
- 可以按 resume parsing、turn evaluation、report generation 分段切换

## 8. 分阶段重构路线

### Phase 0：解耦现有引擎
目标：在不引入框架的前提下先把可迁移边界切出来

输出：
- `InterviewEngine` 变成 orchestration facade，而不是所有逻辑都写在一个方法里
- 问题生成、评分、状态推进、报告聚合等逻辑可单独调用

### Phase 1：引入 LangGraph 骨架，但不改 API
目标：先把 graph runtime 接入工程

输出：
- 新增 workflow 模块和 state schema
- `routes.py` 仍调用相同应用层入口
- 默认仍走旧逻辑，新 graph 仅做 shadow execution

### Phase 2：先迁移最稳定的子流程
目标：降低迁移风险

推荐顺序：
1. report generation graph
2. resume ingestion graph
3. interview turn graph

原因：
- 报告链路最容易验证，不直接影响实时交互
- 简历解析链路已有清晰 fallback，适合 graph 化
- 面试 turn 是最敏感核心，最后迁移

### Phase 3：双轨运行与灰度切换
目标：确保效果不倒退

输出：
- 新旧路径都可执行
- 对比差异、补齐缺口
- 逐步切换生产流量

### Phase 4：高级能力扩展
目标：释放 LangGraph 的真正价值

候选能力：
- 人工审核/人工接管节点
- 题库检索节点
- 学习资源推荐节点
- 语音转写纠偏节点
- 多岗位专属 workflow 变体

## 9. 关键设计决策

### 决策 1：不采用“全面 LangChain 化”
因为 LangChain 更适合作为组件层，不适合作为 InterviewSim 的核心状态编排内核。

### 决策 2：优先 LangGraph，但保留领域服务
因为业务价值在现有服务逻辑中，框架应承载流程，而不是替代业务判断。

### 决策 3：保留规则兜底，不追求全链路 LLM
因为项目立意要求“帮助候选人成长”，系统必须可靠、连续、能在模型波动时依然工作。

### 决策 4：先做兼容迁移，不做一次性重写
因为一次性切换风险最高，也最难证明效果没有退化。

## 10. 最终建议

最佳方案是：
- 主编排迁移到 LangGraph
- 组件层选择性采用 LangChain
- 坚持显式状态、明确边界、规则兜底、成长导向
- 以 shadow mode 和 golden dataset 保证迁移质量

一句话总结：

> InterviewSim 不应该迁移成“一个更自由的 Agent 系统”，而应该迁移成“一个更可扩展、可恢复、可验证的成长型面试工作流系统”。
