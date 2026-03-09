# Docs Index

> **作者**: GitHub Copilot (GPT-5.4)
> **创建日期**: 2026-03-09
> **文档目标**: 为 `docs/` 目录提供总览索引、使用建议和归档管理规则

## 1. 目录结论

当前 `docs/` 最适合按下面四类管理：

- `docs/designs/`
  - 放“仍然对当前架构或产品方向有指导意义”的设计文档
  - 这些文档回答的是“为什么这么设计”和“目标结构是什么”

- `docs/plans/`
  - 放“可以按步骤执行的实施计划”
  - 这些文档回答的是“下一步具体怎么做”

- `docs/archive/`
  - 放“历史分析、阶段性研究、外部模型生成的参考材料”
  - 这些文档可以提供背景和启发，但不应默认视为当前权威方案

- `docs/README.md`
  - 作为 docs 总入口
  - 帮助快速判断某份文档是“当前有效依据”还是“历史参考”

## 2. 为什么不把 Kimi 文档放进 `designs/` 或 `plans/`

这次整理后，我不建议把以下两份文档放进 `designs/` 或 `plans/`：

- `docs/archive/optimization-guide-kimi25.md`
- `docs/archive/project-analysis-kimi25.md`

原因如下：

1. 它们的性质更接近“阶段性分析”和“外部建议合集”
- 内容里有大量方向性建议、优先级判断和示例代码
- 但并没有严格绑定当前代码实现状态
- 其中部分结论已经被后续代码演进或新设计覆盖

2. 它们不是稳定设计决策
- `designs/` 里的文档应该偏“当前仍有效的架构或产品设计基线”
- Kimi 这两份文档更像历史分析快照，不适合和当前设计文档并列

3. 它们也不是可直接执行的实施计划
- `plans/` 里的文档应该能指导开发按步骤落地
- Kimi 文档虽然有建议，但不是按当前仓库状态编写的执行计划

因此，把它们单独放进 `docs/archive/` 最合适。

## 3. 当前推荐结构

```text
docs/
├── README.md
├── archive/
│   ├── optimization-guide-kimi25.md
│   └── project-analysis-kimi25.md
├── designs/
│   ├── 2026-03-01-role-based-interview-framework.md
│   └── 2026-03-09-agent-orchestration-migration-strategy.md
└── plans/
    └── 2026-03-09-langgraph-migration-plan.md
```

## 4. 当前文档索引

### 4.1 Active Designs

- `docs/designs/2026-03-01-role-based-interview-framework.md`
  - 主题：岗位针对性面试框架、四维能力模型、主题-维度映射
  - 用途：作为当前评估体系和岗位化设计的重要参考
  - 状态：`Active Design Reference`

- `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md`
  - 主题：自定义状态机 vs LangChain vs LangGraph 的迁移选型
  - 用途：作为后续 Agent 编排重构的主设计文档
  - 状态：`Draft`

### 4.2 Active Plans

- `docs/plans/2026-03-09-langgraph-migration-plan.md`
  - 主题：LangGraph-first 工作流迁移实施计划
  - 用途：作为后续分阶段重构的执行蓝图
  - 状态：`Draft`

### 4.3 Archived References

- `docs/archive/optimization-guide-kimi25.md`
  - 主题：历史优化建议、测试、重构、功能扩展方向
  - 用途：提供思路参考，不作为当前权威实施计划
  - 状态：`Archived Reference`

- `docs/archive/project-analysis-kimi25.md`
  - 主题：项目定位、市场分析、演进建议
  - 用途：提供历史背景和外部视角，不作为当前架构基线
  - 状态：`Archived Reference`

## 5. 后续管理规则

建议以后统一遵守下面的归档规则。

### 5.1 什么时候放进 `designs/`

满足任意大部分条件时放进 `designs/`：
- 讨论的是架构、数据流、模块边界、设计取舍
- 会影响后续多个 PR 或多阶段开发
- 可以被视作一段时间内的“当前设计基线”
- 阅读者主要关心“为什么这样设计”

### 5.2 什么时候放进 `plans/`

满足任意大部分条件时放进 `plans/`：
- 已经有明确目标和实现路径
- 文档包含阶段、任务、文件、测试、验证方法
- 读者拿到文档后可以直接开始开发
- 阅读者主要关心“下一步怎么做”

### 5.3 什么时候放进 `archive/`

满足任意大部分条件时放进 `archive/`：
- 是阶段性分析、复盘、竞品研究、外部模型建议
- 内容不一定和当前代码状态完全同步
- 有参考价值，但不能默认视为当前事实
- 阅读者主要关心“历史上怎么分析过这个问题”

### 5.4 顶层目录尽量只保留索引

建议未来不要继续把独立文档直接放在 `docs/` 根目录。

更好的规则是：
- `docs/` 根目录只保留 `README.md`
- 具体文档一律进入 `designs/`、`plans/`、`archive/`
- 如果后续出现运行手册，再新增 `docs/runbooks/`
- 如果后续出现 ADR，可新增 `docs/decisions/`

## 6. 推荐的下一步

如果继续整理文档体系，我建议按下面顺序推进：

1. 给 `PROJECT-PLAN.md` 加一个“文档索引”小节，指向 `docs/README.md`
2. 后续新增运行手册时建立 `docs/runbooks/`
3. 如果 LangGraph 重构开始落地，再把关键架构决策拆成 `docs/decisions/` 下的 ADR 文档

## 7. 一句话建议

- Kimi 的两份文档不应该放进 `designs/` 或 `plans/`
- 最合适的做法是单独放进 `docs/archive/`
- `docs/designs/` 保留当前有效设计
- `docs/plans/` 保留可执行计划
- `docs/README.md` 作为整个文档系统的唯一总入口
