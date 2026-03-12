---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
  - _bmad-output/planning-artifacts/product-brief-job_scrape-2026-03-12.md
  - _bmad-output/planning-artifacts/research/technical-51job-liepin-anti-crawl-playwright-stealth-research-2026-03-12.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-03-12'
project_name: 'job_scrape'
user_name: 'Hans'
date: '2026-03-12'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
当前需求共 33 条，MVP 重点集中在 FR1-FR29：任务触发与状态管理、51job 全链路采集、猎聘最小 PoC、统一字段标准化、岗位去重与生命周期跟踪、证据留存、配置化运营控制与多格式导出。  
从架构角度看，这意味着系统至少需要：任务编排层、平台采集执行层、解析标准化层、状态与证据存储层、运营控制与导出层。  
FR30-FR33 属于 Growth（AI 信号与反馈闭环），应通过边界清晰的扩展接口预留，而非挤入 MVP 主链路。

**Non-Functional Requirements:**
NFR 共 19 条，且多数为可量化约束：  
- 性能：任务总时长与接口响应需达 P95 目标；并发约束下避免任务丢失/重复。  
- 可靠性：固定指数退避（1/3/9 分钟）、失败隔离、7 日滚动成功率告警。  
- 安全：凭据加密、最小权限、TLS 传输、日志敏感信息零明文暴露。  
- 数据治理：白名单字段采集、证据完整率、task_id/session_id 双键追溯。  
- 可维护性与集成：平台模块化扩展、配置零硬编码、三格式导出一致性。  
这些要求将直接驱动架构中的可观测性设计、错误分级处理、数据模型与配置治理策略。

**Scale & Complexity:**
项目不是高并发分布式场景，但对“稳定运行与可追溯”要求高，属于中等复杂度的工程系统。  
其难点在于反爬对抗与运营可恢复性，而不是吞吐量扩展。MVP 采用单实例、低并发、分平台解耦是合理边界。

- Primary domain: backend automation + data pipeline + internal operations tooling
- Complexity level: medium
- Estimated architectural components: 8-10

### Technical Constraints & Dependencies

- 明确平台依赖：51job 为主链路，猎聘为 PoC，均依赖浏览器自动化能力与登录态管理。
- 部署边界：单实例、并发 ≤ 2、无分布式队列、无多租户需求。
- 数据边界：需要统一字段模型、岗位指纹、状态演进字段与证据路径关联。
- 运行边界：允许验证码与 challenge 触发，必须支持自动重试、降级到 manual、人工重放。
- 输出边界：CSV/Excel/JSON 三格式一致性与幂等导出要求明确。
- 组织边界：MVP 用户规模小（1-5 人），RBAC 仅需运营员/管理员两级。

### Cross-Cutting Concerns Identified

- Reliability by design：重试、熔断、失败隔离、manual 队列与重放机制。
- Observability first：任务、会话、挑战事件、证据完整率与成功率全链路监控。
- Security & compliance baseline：凭据加密、字段最小化、审计追溯、TLS 强制。
- Data quality governance：标准化与去重一致性、状态字段正确演进、导出一致性校验。
- Extensibility with control：平台采集器模块化与适配层边界，支持后续平台与 AI 层扩展。

## Starter Template Evaluation

### Primary Technology Domain

Backend/API + automation workflow（以采集执行与数据管线为主），并带轻量运营管理能力。

### Starter Options Considered

1) fastapi/full-stack-fastapi-template  
- 优点：工程化完整（前后端、部署、环境配置）  
- 风险：对当前 MVP 偏重，前端与运维复杂度可能超过“先稳采集”的目标

2) s3rius/FastAPI-template  
- 优点：后端导向、结构化较好  
- 风险：需要自行核对其默认工程决策与本项目 NFR 的贴合度

3) arthurhenrique/cookiecutter-fastapi  
- 优点：轻量、快速起步、便于按模块拆分 collector/parser/normalizer  
- 风险：仍需手动补齐 Playwright 采集器、任务编排、证据留存与风控监控模块

### Selected Starter: arthurhenrique/cookiecutter-fastapi

**Rationale for Selection:**
- 与当前 MVP 目标最一致：先交付稳定采集主链路，不引入不必要的全栈负担
- 便于按平台采集器模块化扩展，符合“51job 主链路 + 猎聘 PoC”节奏
- 可在保持简洁的同时，逐步补齐 NFR 要求（重试、追溯、安全、可观测）

**Initialization Command:**

```bash
cookiecutter gh:arthurhenrique/cookiecutter-fastapi
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 后端服务基础骨架，可快速接入 FastAPI 最新稳定线

**Styling Solution:**
- 不预设前端样式体系，符合当前“后端与采集优先”策略

**Build Tooling:**
- 提供基础项目结构，建议补充 uv + ruff + pytest 作为统一工程标准

**Testing Framework:**
- 模板级测试基础可用，需补充采集链路回归与任务状态流转测试

**Code Organization:**
- 适合按领域拆分：scheduler、collectors、parsers、normalizer、evidence、exports

**Development Experience:**
- 启动成本低，适合中等经验团队快速进入可运行状态并持续演进

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- 单体后端架构：FastAPI 单服务 + 模块化边界（scheduler/collectors/parsers/normalizer/evidence/exports）
- 主数据库：PostgreSQL（采用 15 主线）
- 数据模型策略：任务域、岗位域、证据域、风控域分表；以 job_fingerprint 做幂等更新
- 迁移策略：Alembic 版本化迁移，禁止手工改表
- 认证策略：MVP 采用最小可用会话认证（JWT 作为后续可替换方案）
- API 规范：REST + OpenAPI 自动文档
- 观测基线：结构化日志 + 指标采集 + challenge/captcha 事件追踪
- 部署基线：Docker Compose 单实例部署，多环境配置隔离

**Important Decisions (Shape Architecture):**
- 缓存策略：Redis 条件启用（默认可不启用）；用于任务去重锁、短期状态与限流计数
- 安全中间件：统一请求审计、敏感字段脱敏、失败重试链路追踪
- 错误处理：统一错误码与可恢复/不可恢复分级
- 导出策略：CSV/Excel/JSON 单一同源查询管线，确保字段一致性
- 反爬策略：低频增量 + 指数退避 + manual 队列兜底

**Deferred Decisions (Post-MVP):**
- 多服务拆分与消息队列
- 多租户隔离
- AI 情报卡流水线编排与外部协作平台深度集成

### Data Architecture

- Database: PostgreSQL 15
- ORM/Validation: SQLAlchemy 2.0.48 + Pydantic 2.12.5
- Migration: Alembic 1.18.4
- Core tables:
  - tasks / task_runs / task_events
  - job_postings / job_snapshots
  - evidence_records (html_path/screenshot_path/source_url/timestamps)
  - risk_events (captcha/challenge/timeout/block)
  - config_profiles / whitelist_companies
- Idempotency:
  - unique(platform, source_job_id) + job_fingerprint
  - upsert 更新 last_seen_at、disappear_count、record_status
- Caching:
  - Redis 8（条件启用）：任务锁、限流计数、短期会话辅助状态

### Authentication & Security

- Auth method:
  - MVP：内部账号 + 会话认证
  - Growth：可演进至 JWT（短期 access token）
- Authorization:
  - RBAC 双角色：operator / admin
- Secrets:
  - 平台凭据与代理凭据加密存储（环境变量 + 密钥管理文件）
- API Security:
  - HTTPS 强制（反向代理层）
  - 请求级审计日志（脱敏）
  - 基础速率限制（按用户与接口）

### API & Communication Patterns

- API style:
  - REST first（任务触发、状态查询、manual 重放、导出）
- API docs:
  - FastAPI OpenAPI 自动生成
- Error standards:
  - 统一错误码（validation/platform/network/risk/internal）
- Rate limiting:
  - Redis 计数器 + 窗口限速（与 Redis 开关联动）
- Internal communication:
  - 进程内服务层调用（MVP 不拆微服务）

### Frontend Architecture

- MVP 前端定位：
  - 轻量运营控制台（触发任务、查看状态、处理 manual、导出）
- State:
  - 服务端为主，前端仅做薄状态缓存
- Performance:
  - 优先接口稳定性与可观测性，UI 不引入重交互框架

### Infrastructure & Deployment

- Runtime:
  - Python（FastAPI 0.135.1 + Uvicorn 0.41.0）
- Execution:
  - Playwright 1.58.0 + 持久化浏览器会话
- Deployment:
  - Docker Compose（api + postgres + worker，redis 按需启用）
- CI/CD:
  - lint/test/build 三段流水（ruff + pytest）
- Monitoring:
  - prometheus-client 0.24.1 指标暴露
  - 结构化日志 + task_id/session_id 全链路追踪
- Scaling:
  - MVP 固定并发 ≤ 2；通过配置限流而非横向扩容

### Decision Impact Analysis

**Implementation Sequence:**
1. 初始化工程与迁移体系（starter + Alembic + 基础模型）
2. 建立任务执行主链路（scheduler/worker/status）
3. 接入 51job collector + parser + evidence
4. 完成去重/状态演进与导出能力（单一查询源）
5. 补猎聘 PoC 与风控事件策略
6. 完成观测与安全基线收口

**Cross-Component Dependencies:**
- 数据模型决定任务编排、导出和审计能力边界
- 认证授权影响控制台操作面与审计字段
- 缓存与限流策略直接影响采集稳定性与风控命中率
- 观测标准决定后续 NFR 验收可执行性

### Validation Checkpoints (for Acceptance)

- 重试链路：验证 1/3/9 分钟指数退避是否按状态机真实触发
- manual 兜底：验证失败任务可人工重放且记录可追溯
- 证据完整性：验证 source_url + timestamp + html_path 完整率可统计
- 失败注入：验证超时、挑战页、字段缺失场景下的降级与告警行为
- Redis 开关：验证关闭 Redis 时主链路可运行；达到阈值后可无缝启用

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
12 个高风险冲突点（命名、目录结构、API 格式、错误处理、任务状态流转、日志字段、证据路径、导出格式等）

### Naming Patterns

**Database Naming Conventions:**
- 表名：`snake_case` 复数（如 `job_postings`, `task_runs`）
- 列名：`snake_case`（如 `job_fingerprint`, `last_seen_at`）
- 主键：统一 `id`（UUID 或 bigint 在同一表系内保持一致）
- 外键：`<entity>_id`（如 `task_id`, `job_posting_id`）
- 索引命名：`idx_<table>_<column>`；唯一约束：`uq_<table>_<column_set>`

**API Naming Conventions:**
- REST 资源：复数名词（如 `/tasks`, `/jobs`, `/exports`）
- 路径参数：`{id}` 形式（OpenAPI 语义一致）
- 查询参数：`snake_case`（如 `company_id`, `time_range_start`）
- Header：标准头保持原样；自定义头统一 `X-JobScrape-*`

**Code Naming Conventions:**
- Python 文件：`snake_case.py`
- 类名：`PascalCase`（如 `TaskScheduler`, `LiepinCollector`）
- 函数/变量：`snake_case`
- 常量：`UPPER_SNAKE_CASE`
- 枚举值：小写 `snake_case`（如 `suspected_removed`）

### Structure Patterns

**Project Organization:**
- 按领域组织而非按技术层平铺：
  - `app/scheduler`
  - `app/collectors/{platform}`
  - `app/parsers/{platform}`
  - `app/normalizer`
  - `app/evidence`
  - `app/exports`
  - `app/api`
  - `app/security`
- 测试目录统一集中在 `tests/`，并固定为：`tests/unit`、`tests/integration`、`tests/e2e`

**File Structure Patterns:**
- 配置：`app/core/config.py` + `.env` 分层（`.env.example` 必须存在）
- 数据迁移：`alembic/versions/`
- 文档：架构/接口规范放 `_bmad-output` 与 `docs/`，避免散落

### Format Patterns

**API Response Formats:**
- 成功响应统一：
  - 列表：`{ "data": [...], "meta": {...}, "error": null }`
  - 单对象：`{ "data": {...}, "meta": null, "error": null }`
- 失败响应统一：
  - `{ "data": null, "meta": null, "error": { "code": "...", "message": "...", "details": {...} } }`
- 状态码规则：
  - `2xx` 成功，`4xx` 客户端错误，`5xx` 服务端错误，不混用

**Data Exchange Formats:**
- JSON 字段统一 `snake_case`（内部模型与外部 API 均一致，不使用 alias 混配）
- 时间统一 ISO 8601 UTC（如 `2026-03-12T10:30:00Z`）
- 布尔统一 `true/false`
- 空值统一 `null`，禁止空字符串表示缺失

### Communication Patterns

**Event System Patterns:**
- 事件命名：`domain.action`（如 `task.started`, `task.retried`, `job.normalized`, `risk.captcha_hit`）
- 事件载荷最小字段：
  - `event_name`, `event_time`, `task_id`, `session_id`, `platform`, `payload`
- 事件版本：`event_version` 默认 `1`

**State Management Patterns:**
- 任务状态机固定：`pending -> running -> success|failed|manual`
- 合法人工动作仅：`replay | skip`
- 非法状态跳转（如 `pending -> success`）禁止，必须通过状态机校验
- 重试状态显式记录 `retry_count` 与 `next_retry_at`
- 任何状态变更必须写审计事件（`task_events`）

### Process Patterns

**Error Handling Patterns:**
- 错误分级：`validation_error`, `platform_error`, `network_error`, `risk_error`, `internal_error`
- 错误码前缀：`VAL_* / NET_* / RISK_* / INT_*`
- 用户可见错误与内部日志错误分离
- 日志脱敏强制：账号、cookie、token、代理凭据不可明文输出

**Loading State Patterns:**
- API 层统一返回任务实时状态，不由前端猜测
- 长任务采用轮询状态端点（MVP 不引入 websocket）
- `manual` 队列必须可见且可重放/跳过

### Enforcement Guidelines

**All AI Agents MUST:**
- 严格遵守上述命名、响应格式与状态机规则
- 新增模块必须放入既定领域目录，不得自创平行目录
- 所有新接口必须提供 OpenAPI 注释与统一错误码
- 任何跨模块字段必须复用已有 schema，禁止重复定义
- 所有日志必须包含 `task_id` 或 `session_id` 至少其一

**Pattern Enforcement:**
- 通过 lint + schema 校验 + API contract test 自动检查
- PR 审查清单加入“命名/格式/状态机一致性”项
- CI 增加日志敏感字段门禁（命中 `cookie|token|password` 明文即失败）
- 发现违规时记录在 architecture decision log，并在下一迭代统一修正

### Pattern Examples

**Good Examples:**
- `GET /tasks/{id}` 返回：`{data, meta, error}` 包装结构
- `job_postings.last_seen_at` 使用 UTC ISO 字符串
- `risk.captcha_hit` 事件包含 `task_id/session_id/platform`
- 证据路径遵循 `platform/date/task_id` 分层目录规范
- 幂等写入接口对重复请求返回一致结果

**Anti-Patterns:**
- 同一语义同时出现 `jobId` 与 `job_id`
- 部分接口返回裸数组，部分接口返回包装对象
- 把 `manual` 当成错误码而不是合法任务状态
- 日志打印完整 cookie/token

## Project Structure & Boundaries

### Complete Project Directory Structure

job_scrape/
├── README.md
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security-scan.yml
├── docs/
│   ├── architecture/
│   │   └── decisions/
│   └── api/
├── scripts/
│   ├── bootstrap.ps1
│   ├── run-dev.ps1
│   └── run-worker.ps1
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── main.py
│   ├── worker.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   ├── security.py
│   │   └── constants.py
│   ├── api/
│   │   ├── deps.py
│   │   ├── router.py
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── task.py
│   │   │   ├── job.py
│   │   │   ├── export.py
│   │   │   └── risk.py
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── tasks.py
│   │       ├── jobs.py
│   │       ├── exports.py
│   │       ├── manual_queue.py
│   │       └── health.py
│   ├── db/
│   │   ├── session.py
│   │   ├── base.py
│   │   ├── models/
│   │   │   ├── task.py
│   │   │   ├── job_posting.py
│   │   │   ├── evidence_record.py
│   │   │   ├── risk_event.py
│   │   │   ├── config_profile.py
│   │   │   └── whitelist_company.py
│   │   └── repositories/
│   │       ├── task_repo.py
│   │       ├── job_repo.py
│   │       ├── evidence_repo.py
│   │       └── risk_repo.py
│   ├── scheduler/
│   │   ├── service.py
│   │   ├── retry_policy.py
│   │   ├── rate_limit.py
│   │   └── state_machine.py
│   ├── collectors/
│   │   ├── base.py
│   │   ├── session_manager.py
│   │   ├── anti_bot_guard.py
│   │   ├── job51/
│   │   │   ├── collector.py
│   │   │   ├── selectors.py
│   │   │   └── adapter.py
│   │   └── liepin/
│   │       ├── collector.py
│   │       ├── selectors.py
│   │       └── adapter.py
│   ├── parsers/
│   │   ├── common.py
│   │   ├── job51_parser.py
│   │   └── liepin_parser.py
│   ├── normalizer/
│   │   ├── fingerprint.py
│   │   ├── status_tracker.py
│   │   └── mapper.py
│   ├── evidence/
│   │   ├── storage.py
│   │   ├── path_policy.py
│   │   └── retention.py
│   ├── exports/
│   │   ├── query_service.py
│   │   ├── csv_exporter.py
│   │   ├── excel_exporter.py
│   │   └── json_exporter.py
│   ├── manual/
│   │   ├── service.py
│   │   └── actions.py
│   ├── observability/
│   │   ├── metrics.py
│   │   ├── tracing.py
│   │   └── audit.py
│   └── integrations/
│       └── notifier_stub.py
├── storage/
│   └── evidence/
│       └── {platform}/{date}/{task_id}/
│           ├── page.html
│           └── screenshot.png
└── tests/
  ├── unit/
  │   ├── scheduler/
  │   ├── normalizer/
  │   ├── parsers/
  │   └── core/
  ├── integration/
  │   ├── api/
  │   ├── db/
  │   └── collectors/
  ├── e2e/
  │   ├── task_flow/
  │   ├── manual_queue/
  │   └── export_flow/
  ├── contract/
  │   ├── api_response_contract_test.py
  │   └── error_code_contract_test.py
  └── fixtures/
    ├── html_samples/
    └── risk_pages/

### Architectural Boundaries

**API Boundaries:**
- 外部仅通过 `app/api/v1/*` 访问业务能力。
- 认证与授权边界在 `auth.py + deps.py`，业务路由不直接处理权限细节。
- `manual_queue.py` 仅暴露 `replay/skip` 两类动作。

**Component Boundaries:**
- `collectors` 只负责采集，不做业务状态判断。
- `parsers` 只做字段提取与清洗，不做持久化。
- `normalizer` 负责指纹、去重、状态演进。
- `repositories` 负责数据访问，禁止在路由层直写 SQL。

**Service Boundaries:**
- `scheduler/service.py` 统一编排任务生命周期与重试策略。
- `manual/service.py` 统一人工兜底流程。
- `exports/query_service.py` 作为 CSV/Excel/JSON 单一数据源。

**Data Boundaries:**
- 业务主数据在 PostgreSQL（任务、岗位、证据索引、风险事件）。
- 原始证据文件在 `storage/evidence`，路径策略由 `path_policy.py` 统一。
- Redis（若启用）仅用于锁/限流/短期状态，不作为业务事实源。

### Requirements to Structure Mapping

**FR Category Mapping:**
- 任务与执行管理（FR1-5）→ `scheduler/`, `api/v1/tasks.py`, `db/models/task.py`
- 平台采集能力（FR6-10）→ `collectors/`, `parsers/`, `manual/`
- 数据标准化与状态跟踪（FR11-15）→ `normalizer/`, `db/models/job_posting.py`
- 证据与审计（FR16-20）→ `evidence/`, `observability/audit.py`, `risk_event.py`
- 配置与运营控制（FR21-24）→ `config_profile.py`, `whitelist_company.py`, `api/v1/auth.py`
- 结果消费与导出（FR25-29）→ `exports/`, `api/v1/exports.py`

**Cross-Cutting Concerns:**
- 安全：`core/security.py`, `api/deps.py`
- 可观测：`observability/metrics.py`, `core/logging.py`
- 状态一致性：`scheduler/state_machine.py`, `tests/contract/*`

### Integration Points

**Internal Communication:**
- 路由 → service → repository 单向调用。
- 采集链路：scheduler → collector → parser → normalizer → repository/evidence。

**External Integrations:**
- 招聘平台访问通过 `collectors/{platform}` 适配层。
- 通知集成预留 `integrations/notifier_stub.py`（MVP 可空实现）。

**Data Flow:**
- 触发任务 → 采集列表/详情 → 字段解析 → 指纹去重/状态更新 → 证据落盘 → 导出消费。

### File Organization Patterns

**Configuration Files:**
- 根目录统一管理 `pyproject.toml`, `alembic.ini`, `.env.example`, `docker-compose.yml`。

**Source Organization:**
- 按业务域分目录，禁止平铺 `utils.py` 大杂烩。

**Test Organization:**
- 固定 `unit/integration/e2e/contract` 四类，不混放。

**Asset Organization:**
- 证据文件按 `platform/date/task_id` 分层存放，满足追溯与清理策略。

### Development Workflow Integration

**Development Server Structure:**
- `app/main.py` 提供 API 服务，`app/worker.py` 提供后台执行。

**Build Process Structure:**
- CI 依次执行 lint → unit/integration → contract，最后构建镜像。

**Deployment Structure:**
- `docker-compose.yml` 支持 API + PostgreSQL + Worker（Redis 按需开关）。

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- 已确认技术栈兼容：FastAPI + Uvicorn + SQLAlchemy + Alembic + Playwright + PostgreSQL 的组合无冲突。
- “会话认证优先、JWT 后续演进”与 MVP 范围一致，避免过早复杂化。
- Redis 条件启用与当前低并发约束一致，不阻塞主链路。

**Pattern Consistency:**
- 命名规范（snake_case）、响应包装、错误码前缀、状态机规则在 API/DB/测试层保持一致。
- 一致性规则与第 4 步决策对齐，未发现相互矛盾条款。
- 证据路径、日志脱敏、manual 动作边界均已形成可执行约束。

**Structure Alignment:**
- 目录结构对齐模块边界（collector/parser/normalizer/repository）并避免职责重叠。
- requirements→structure 映射完整，FR 主类别均有落点目录与关键文件。
- 内部通信链路（router→service→repository）与状态机治理策略一致。

### Requirements Coverage Validation ✅

**Feature Coverage:**
- 已覆盖任务编排、平台采集、数据标准化、证据留存、manual 队列与导出链路。
- Growth 能力（AI 情报卡、反馈闭环）已明确为后续扩展，不与 MVP 混线。

**Functional Requirements Coverage:**
- FR1-FR29 在结构与决策中均有显式承载模块。
- Cross-cutting FR（审计、配置、导出一致性）具备专门组件支撑。

**Non-Functional Requirements Coverage:**
- 性能：低并发与限流策略明确。
- 可靠性：1/3/9 重试、失败隔离、manual 兜底已定义。
- 安全与合规：脱敏、凭据保护、字段最小化、追溯链路已覆盖。
- 可维护性：模块化平台采集器、统一规则与契约测试已定义。

### Implementation Readiness Validation ✅

**Decision Completeness:**
- 关键决策均有“选择 + 理由 + 影响”。
- 版本锚点已校验并写入，满足实现阶段参考。

**Structure Completeness:**
- 项目树完整到关键文件粒度（非泛化占位）。
- 边界、集成点、数据流均可直接指导实现拆分。

**Pattern Completeness:**
- 命名、格式、通信、流程模式完整。
- 冲突高发点（状态机跳转、字段命名混用、导出分叉）均有预防规则。

### Gap Analysis Results

**Critical Gaps:** 无

**Important Gaps:**
- 建议在实现阶段补一个 `ARCHITECTURE_ENFORCEMENT.md`，把 CI 门禁与审查清单固化为操作项。
- 建议补充“Redis 启用阈值”数值化标准（例如锁冲突率/重复任务率阈值）到运行手册。

**Nice-to-Have Gaps:**
- 可增加一份“collector 适配器开发模板”降低新平台接入偏差。
- 可补充错误码字典文档供前后端协作。

### Validation Issues Addressed

- 已解决：认证复杂度过高风险（改为会话优先）。
- 已解决：缓存是否强依赖的不确定性（改为条件启用）。
- 已解决：导出实现分叉风险（统一同源查询层）。
- 已解决：多代理实现风格漂移（统一命名/响应/状态机/测试结构）。

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** high

**Key Strengths:**
- MVP 边界清晰，复杂度控制得当
- 规则可执行且可验证，适合多 AI 代理协作开发
- 数据与证据链设计满足“可信采集”目标

**Areas for Future Enhancement:**
- Growth 阶段 AI 分析与外部推送接口契约
- 运行手册与阈值策略进一步量化

### Implementation Handoff

**AI Agent Guidelines:**
- 严格遵循本架构文档中的命名、响应格式、状态机与目录边界
- 新功能优先复用既有模块，不新增平行实现路径
- 所有接口与日志必须满足契约测试与脱敏门禁

**First Implementation Priority:**
- 先执行 starter 初始化：
  `cookiecutter gh:arthurhenrique/cookiecutter-fastapi`
- 随后建立 Alembic 基础模型与任务主链路（scheduler + worker + task state machine）
