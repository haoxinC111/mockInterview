# 岗位针对性面试框架设计文档

> **文档状态**: Active Design Reference
> **原始提出**: glm-5
> **原始创建日期**: 2026-03-01
> **最新整理**: GitHub Copilot (GPT-5.4)
> **整理日期**: 2026-03-09
> **文档目标**: 提升面试系统的“真实性”和“专业性”

## 一、背景与目标

### 1.1 问题定义
当前面试系统存在以下不足：
- 评估维度单一（仅 `technical_depth`）
- 问题与岗位关联度不够精准
- 报告缺乏针对性的改进建议
- 不同岗位使用相同的面试大纲和评估标准

### 1.2 改进目标
提升面试的"真实性"和"专业性"，核心关注点：
1. **问题质量** - 有层次、有追问、考察思维深度
2. **评估专业性** - 多维度评估、专业反馈
3. **岗位针对性** - 问题贴合具体岗位（如 Agent Engineer）

### 1.3 设计原则
- **可扩展性**：设计框架支持多岗位，先做好 Agent Engineer，后续可快速添加其他岗位
- **向后兼容**：所有新增字段为可选，现有 API 消费者无需修改
- **配置驱动**：岗位定义使用 YAML 配置，便于维护和扩展

---

## 二、核心设计

### 2.1 四维能力评估模型（Agent Engineer）

| 维度 | 权重 | 评估重点 | 核心能力项 |
|------|------|----------|------------|
| 技术深度 | 30% | LLM/RAG/Agent 技术栈原理与实践 | Transformer 原理、Prompt Engineering、Embedding 与向量检索、RAG 架构、Agent 编排、框架掌握 |
| 架构设计 | 30% | 系统设计、技术选型、权衡分析 | RAG 系统架构、Agent 状态机、向量数据库选型、LLM 调用策略、可观测性、成本与性能权衡 |
| 工程实践 | 25% | 生产环境、稳定性、工程化 | LLM 调用容错、Prompt 版本管理、延迟优化、成本控制、A/B 测试、监控告警 |
| 沟通表达 | 15% | 项目展示、逻辑清晰、技术影响力 | 项目背景描述、技术方案解释、问题解决方案阐述、量化成果展示、应对追问 |

### 2.2 维度评分标准（10分制）

#### 技术深度
| 分数 | 描述 |
|------|------|
| 1-2 | 完全不理解相关技术概念，或仅知道名词无法解释原理 |
| 3-4 | 有基本理解但缺少细节，或理解准确能举简单例子 |
| 5-6 | 理解到位有实际经验，能做 tradeoff 分析 |
| 7-8 | 深度好有架构思维，体系化思考有生产案例 |
| 9-10 | 有独到见解和深入优化经验，专家级别有行业影响力的认知 |

#### 架构设计
| 分数 | 描述 |
|------|------|
| 1-2 | 无法进行系统设计，或只能描述单一组件 |
| 3-4 | 能画出基本架构图，考虑了主要组件和交互 |
| 5-6 | 能分析关键 tradeoff，考虑了性能和扩展性 |
| 7-8 | 有完整的技术选型逻辑，考虑了容错和降级 |
| 9-10 | 有大规模系统设计经验，架构师级别有创新设计 |

#### 工程实践
| 分数 | 描述 |
|------|------|
| 1-2 | 无工程实践意识，或知道基本概念但无实践 |
| 3-4 | 有简单项目经验，了解常见问题和解决方案 |
| 5-6 | 有生产环境部署经验，能处理常见线上问题 |
| 7-8 | 有完整的监控和告警体系，有故障排查和复盘经验 |
| 9-10 | 有高可用系统建设经验，SRE 级别的工程能力 |

#### 沟通表达
| 分数 | 描述 |
|------|------|
| 1-2 | 无法清晰表达，或表达混乱缺乏逻辑 |
| 3-4 | 能说清基本概念，有一定逻辑性 |
| 5-6 | 表达清晰有结构，能有效传达技术决策 |
| 7-8 | 能应对追问和质疑，有技术影响力 |
| 9-10 | 能引导讨论方向，卓越的技术沟通能力 |

### 2.3 主题-维度映射

面试主题映射到评估维度，每个主题有主维度和可选的辅助维度：

| 主题 | 主维度 | 辅助维度 |
|------|--------|----------|
| Transformer 原理 | 技术深度 | 架构设计 |
| Prompt 设计 | 技术深度 | 工程实践 |
| 索引与召回 | 技术深度 | 架构设计、工程实践 |
| 检索优化 | 架构设计 | 技术深度、工程实践 |
| 状态机与工具调用 | 架构设计 | 技术深度 |
| 稳定性与回退 | 工程实践 | 架构设计 |
| 项目实战深挖 | 沟通表达 | 全维度 |

---

## 三、架构设计

### 3.1 目录结构

```
app/
├── roles/                              # 新增：岗位定义模块
│   ├── __init__.py
│   ├── base.py                         # 数据类定义
│   ├── registry.py                     # 岗位注册表
│   ├── agent_engineer.py               # Agent Engineer 定义
│   └── data/
│       └── agent_engineer.yaml         # 能力矩阵配置
├── services/
│   ├── interview_engine.py             # 修改：集成多维度评估
│   ├── report_service.py               # 修改：多维度报告
│   └── evaluation_service.py           # 新增：维度评估逻辑
├── models/
│   └── schemas.py                      # 修改：添加维度模型
└── api/
    └── routes.py                       # 修改：新增岗位端点
```

### 3.2 数据模型

```python
# app/roles/base.py

from dataclasses import dataclass, field
from typing import Literal

@dataclass
class CompetencyDimension:
    """单一评估维度"""
    id: str                              # e.g., "technical_depth"
    name: str                            # e.g., "技术深度"
    description: str                     # 详细描述
    weight: float = 1.0                  # 权重
    scoring_rubric: dict[int, str] = field(default_factory=dict)
    evaluation_focus: list[str] = field(default_factory=list)

@dataclass
class TopicMapping:
    """主题到维度的映射"""
    topic_name: str
    primary_dimension: str
    secondary_dimensions: list[str] = field(default_factory=list)

@dataclass
class RoleDefinition:
    """完整岗位定义"""
    role_id: str                         # e.g., "agent_engineer"
    role_name: str                       # e.g., "Agent Engineer"
    description: str
    dimensions: list[CompetencyDimension]
    topic_mappings: list[TopicMapping]
    default_outline_modules: list[dict]
    evaluation_prompts: dict[str, str]
```

```python
# app/models/schemas.py 新增

class DimensionScore(BaseModel):
    """单维度评分"""
    dimension_id: str
    dimension_name: str
    score: float
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

class TurnEvaluation(BaseModel):
    """回合评估（修改版）"""
    topic: str
    score: int
    # 新增字段
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    primary_dimension: str | None = None
    # 原有字段
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    depth_delta: int = 0
    decision: Literal["deepen", "next_topic", "next_module", "end"]
```

### 3.3 新报告结构

```json
{
  "target_role": "Agent Engineer",
  "overall_score": 6.5,
  "dimension_scores": {
    "technical_depth": {
      "score": 7.0,
      "percentile": 75,
      "strengths": ["Transformer 原理理解深入", "有 RAG 实践经验"],
      "gaps": ["Agent 编排经验不足"]
    },
    "architecture_design": {
      "score": 6.5,
      "percentile": 68,
      "strengths": ["能做 tradeoff 分析"],
      "gaps": ["缺少大规模系统设计经验"]
    },
    "engineering_practice": {
      "score": 6.0,
      "percentile": 60,
      "strengths": ["有生产环境部署经验"],
      "gaps": ["监控告警体系不完善", "缺少故障复盘经验"]
    },
    "communication": {
      "score": 6.5,
      "percentile": 70,
      "strengths": ["表达清晰有结构"],
      "gaps": ["量化成果展示不够"]
    }
  },
  "radar_chart": {
    "labels": ["技术深度", "架构设计", "工程实践", "沟通表达"],
    "values": [7.0, 6.5, 6.0, 6.5],
    "benchmarks": [6.0, 6.0, 6.0, 6.0]
  },
  "strengths": {
    "overall": ["技术基础扎实", "有实际项目经验"],
    "by_dimension": {
      "technical_depth": ["Transformer 原理理解深入"],
      "architecture_design": ["能做 tradeoff 分析"]
    }
  },
  "risks": {
    "overall": ["工程实践能力需加强"],
    "by_dimension": {
      "engineering_practice": ["监控告警体系不完善"]
    }
  },
  "salary_fit": {
    "level": "部分匹配",
    "advice": "对标期望薪资仍有缺口，建议补齐工程实践能力"
  },
  "action_plan_30d": {
    "overall": [
      "针对「工程实践」建立复盘卡片，梳理核心概念并进行模拟演练",
      "补齐每个模块的标准答题框架（定义-原理-权衡-落地）"
    ],
    "by_dimension": {
      "engineering_practice": [
        "学习 LLM 调用的容错和重试策略",
        "搭建基础监控告警体系"
      ],
      "communication": [
        "练习量化成果的表达方式"
      ]
    }
  },
  "disclaimer": "该报告仅用于训练与自我评估，不作为真实招聘决策唯一依据。"
}
```

---

## 四、实施计划

### Phase 1: 核心框架（第1-2天）
**目标**：建立岗位定义的基础设施

| 步骤 | 任务 | 产出 |
|------|------|------|
| 1.1 | 创建 `app/roles/base.py` | 数据类定义 |
| 1.2 | 创建 `app/roles/registry.py` | 岗位注册表 |
| 1.3 | 创建 `app/roles/data/agent_engineer.yaml` | Agent Engineer 能力矩阵 |
| 1.4 | 创建 `app/roles/agent_engineer.py` | Python 包装器 |

### Phase 2: Schema 更新（第2天）
**目标**：更新数据模型支持多维度

| 步骤 | 任务 | 产出 |
|------|------|------|
| 2.1 | 更新 `schemas.py` | DimensionScore、MultiDimensionEvaluation |
| 2.2 | 更新 `TurnEvaluation` | 添加 dimension_scores 字段 |

### Phase 3: 评估服务（第2-3天）
**目标**：实现多维度评估逻辑

| 步骤 | 任务 | 产出 |
|------|------|------|
| 3.1 | 创建 `evaluation_service.py` | 维度映射、评估逻辑 |
| 3.2 | 更新 `interview_engine.py` | 集成新评估服务 |

### Phase 4: 报告服务（第3-4天）
**目标**：生成多维度报告

| 步骤 | 任务 | 产出 |
|------|------|------|
| 4.1 | 更新 `report_service.py` | 多维度聚合 |
| 4.2 | 添加雷达图数据生成 | radar_chart 字段 |
| 4.3 | 分维度建议生成 | by_dimension 字段 |

### Phase 5: API 更新（第4天）
**目标**：暴露新功能

| 步骤 | 任务 | 产出 |
|------|------|------|
| 5.1 | 新增 `GET /api/v1/roles` | 列出可用岗位 |
| 5.2 | 新增 `GET /api/v1/roles/{role_id}` | 获取岗位能力矩阵 |
| 5.3 | 更新现有端点响应 | 包含维度数据 |

### Phase 6: 测试与验证（第5天）
**目标**：确保功能正确

| 步骤 | 任务 | 产出 |
|------|------|------|
| 6.1 | 单元测试 | RoleRegistry、EvaluationService |
| 6.2 | 集成测试 | 完整面试流程 |
| 6.3 | 手动验证 | 端到端演示 |

---

## 五、API 变更

### 新增端点

```
GET /api/v1/roles
响应: {"roles": ["agent_engineer", ...]}

GET /api/v1/roles/{role_id}
响应: RoleDefinition 完整结构
```

### 修改端点

```
POST /api/v1/interviews
请求: 新增可选 role_config 字段

POST /api/v1/interviews/{id}/messages
响应: turn_eval 包含 dimension_scores

POST /api/v1/interviews/{id}/finish
响应: 报告包含 dimension_scores、radar_chart

GET /api/v1/reports/{id}
响应: 同上
```

---

## 六、验证方案

### 单元测试
- `RoleRegistry` 加载和查询功能
- `EvaluationService` 维度映射正确性
- 多维度评分计算准确性

### 集成测试
- 完整面试流程（12轮）多维度评估
- 报告生成包含所有维度数据
- 向后兼容性验证

### 手动验证步骤
1. 启动服务：`uv run uvicorn app.main:app --reload`
2. 调用 `GET /api/v1/roles` 确认返回 Agent Engineer
3. 上传简历并开始面试
4. 完成面试后检查报告中的 `dimension_scores` 和 `radar_chart`
5. 确认分维度建议内容合理

---

## 七、向后兼容性

- 所有新增字段为可选，默认值与现有行为一致
- `technical_depth` 作为 `overall_score` 的别名保留
- 现有 API 消费者无需修改即可继续使用

---

## 八、扩展指南

### 添加新岗位
1. 创建 `app/roles/data/{role_id}.yaml`
2. 定义能力维度、主题映射、评估提示词
3. 创建 `app/roles/{role_id}.py` 包装器（可选）
4. 注册到 `RoleRegistry`

### 示例：添加后端工程师岗位
```yaml
role_id: backend_engineer
role_name: "后端工程师"
dimensions:
  - id: technical_depth
    name: "技术深度"
    weight: 0.35
    # ...
  - id: system_design
    name: "系统设计"
    weight: 0.30
    # ...
  - id: engineering_practice
    name: "工程实践"
    weight: 0.25
    # ...
  - id: communication
    name: "沟通表达"
    weight: 0.10
    # ...
```

---

## 附录：关键文件路径

| 文件 | 用途 |
|------|------|
| `backend/python-brain/app/roles/base.py` | 岗位数据结构定义 |
| `backend/python-brain/app/roles/registry.py` | 岗位注册表 |
| `backend/python-brain/app/roles/data/agent_engineer.yaml` | Agent Engineer 能力矩阵 |
| `backend/python-brain/app/services/interview_engine.py` | 核心面试引擎 |
| `backend/python-brain/app/services/report_service.py` | 报告生成服务 |
| `backend/python-brain/app/services/evaluation_service.py` | 多维度评估服务 |
| `backend/python-brain/app/models/schemas.py` | 数据模型定义 |
| `backend/python-brain/app/api/routes.py` | API 路由定义 |