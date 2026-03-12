---
date: 2026-03-12
author: Hans
project: job_scrape
status: draft
prerequisite: _bmad-output/planning-artifacts/requirements-job_scrape-2026-03-12.md
references:
  - _bmad-output/planning-artifacts/research/technical-51job-liepin-anti-crawl-playwright-stealth-research-2026-03-12.md
  - _bmad-output/planning-artifacts/requirements-job_scrape-2026-03-12.md
---

# job_scrape MVP 技术设计（以 FR/NFR 为基线）

## 0. 依赖关系

本技术设计以需求基线为前置输入：
- FR/NFR 基线：`_bmad-output/planning-artifacts/requirements-job_scrape-2026-03-12.md`
- 技术研究输入：`_bmad-output/planning-artifacts/research/technical-51job-liepin-anti-crawl-playwright-stealth-research-2026-03-12.md`

若 FR/NFR 变更，本设计需同步更新。

## 1. 设计目标（对应 FR）

- 对应 FR-01/08/11：任务调度、重试兜底、配置中心
- 对应 FR-02/03：51job 主链路与猎聘 PoC 链路
- 对应 FR-04/05/06：证据留存、标准化去重、状态跟踪
- 对应 FR-07/12：风控事件记录与可观测
- 对应 FR-09/10：基础情报卡与外部导出

## 2. MVP 技术架构（概览）

- Scheduler + Queue：任务编排、限流、重试
- Collector（Playwright + Stealth）：平台采集执行
- Parser + Normalizer：字段提取、职位指纹、状态计算
- Evidence Store：HTML/截图证据留存
- PostgreSQL：任务、岗位、风险事件、情报卡
- Metrics & Alert：成功率、挑战率、验证码率监控

## 3. NFR 保障策略（映射）

- NFR-01/07：最小化采集 + 凭据安全 + 日志脱敏
- NFR-02：降频、熔断、会话冷却
- NFR-03/04：平台采集器模块化、可插拔扩展
- NFR-05/06：任务超时控制与指标告警
- NFR-08：代理与采集成本按平台统计

## 4. 实施顺序（按需求优先级）

1. P0：先交付 FR-01/02/04/05/06/07/08/11/12
2. 稳定性验收：满足 NFR-01/02/03/06/07
3. P1：补齐 FR-03/09/10 与 NFR-04/05/08

## 5. 当前状态

- 已完成：需求基线（FR/NFR）
- 下一步：基于 FR 拆解开发任务（epic/story/task）并建立实现 backlog
