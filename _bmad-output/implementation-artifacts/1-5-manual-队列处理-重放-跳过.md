# Story 1.5: Manual 队列处理（重放/跳过）

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 运营员,
I want 对 `manual` 任务执行重放或跳过,
so that 我可以恢复失败流程并维持任务闭环。

## Acceptance Criteria

1. Given 某任务状态为 `manual`，When 运营员执行 `replay` 或 `skip`，Then 系统按状态机规则完成状态迁移并记录操作审计事件。
2. 非 `manual` 任务不允许执行该动作，并返回明确错误码。
3. 接口响应遵循统一包装 `{data, meta, error}`，错误码遵循 `VAL_*/INT_*` 约定。
4. replay/skip 必须记录 `task_id`、`operator`、时间戳，且事件可在 Story 1.4 的事件日志接口中查询。
5. 本故事仅实现 manual 动作控制，不扩展新的任务状态、不引入批量处理与自动重试策略重构。

## Tasks / Subtasks

- [x] 新增 manual 动作 API（AC: 1, 2, 3）
  - [x] 新增 `POST /api/tasks/{task_id}/actions/manual`（建议），请求体包含 `action: replay|skip` 与可选 `reason`
  - [x] 对非法 action 返回 422 + `VAL_MANUAL_ACTION_INVALID`
  - [x] 任务不存在返回 404 + `VAL_TASK_NOT_FOUND`
- [x] 增加状态机校验与动作服务（AC: 1, 2）
  - [x] 仅允许 `status == manual` 时执行动作
  - [x] `replay`：任务状态迁移到 `pending`
  - [x] `skip`：任务状态迁移到 `failed`（MVP 以"人工确认失败收口"解释 skip 结果）
  - [x] 非法状态执行动作返回 409 + `VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION`
- [x] 补齐审计与事件留痕（AC: 1, 4）
  - [x] 为 replay/skip 写入 `task_events`
  - [x] 事件类型建议：`task.manual.replay` / `task.manual.skip`
  - [x] payload 至少包含 `task_id`、`session_id`（可空）、`action`、`reason`、`from_status`、`to_status`、`timestamp`
- [x] 完善测试与回归（AC: 1, 2, 3, 4）
  - [x] 覆盖成功路径：manual + replay，manual + skip
  - [x] 覆盖失败路径：非 manual、非法 action、任务不存在
  - [x] 覆盖响应契约与错误码契约
  - [x] 回归 Story 1.2/1.3/1.4 现有测试全部通过

## Dev Notes

### Story Foundation

- Epic 1 目标是“任务执行与运行可观测闭环”，本故事是将 Story 1.4 的“可观测”推进到“可处置”。
- Story 1.4 已提供按时间线查询任务事件的能力，本故事新增动作后，必须能被 `GET /api/tasks/{task_id}/events` 读到。
- sprint-status 中本故事是当前第一条 backlog（1-5），应在完成后推动 Epic 1 进入更接近收口状态。

### Technical Requirements

- 推荐接口：`POST /api/tasks/{task_id}/actions/manual`
- 请求体建议：
  - `action`: `"replay" | "skip"`（必填）
  - `reason`: `string | null`（选填，最长建议 500）
- 成功响应 `data` 建议字段：
  - `task_id`, `previous_status`, `current_status`, `action`, `operator`, `updated_at`
- 错误码建议：
  - `VAL_TASK_NOT_FOUND`（404）
  - `VAL_MANUAL_ACTION_INVALID`（422）
  - `VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION`（409）
  - `INT_TASK_MANUAL_ACTION_FAILED`（500）

### Architecture Compliance

- 严格遵循状态机边界：合法人工动作仅 `replay|skip`，且仅对 `manual` 生效。
- 任何状态变更必须写审计事件（`task_events`），这是硬性要求。
- 保持统一 API 包装与统一错误码风格，不新增分叉响应结构。
- 日志和事件中继续保持可追溯键（`task_id` / `session_id`）。

### Library & Framework Requirements

- 保持现有版本：FastAPI `0.135.1`、SQLAlchemy `2.0.48`、Pydantic `2.12.5`、Pytest `8.4.2`、Ruff `0.13.0`。
- 不引入 Celery/Kafka/外部工作流引擎；manual 动作继续走当前同步服务层实现。

### File Structure Requirements

基于当前代码结构（`app/api/routes` + `app/services`）优先最小改动：

- `job_scrape/app/api/routes/tasks.py`
  - 新增 manual action 端点，或按需引入小型子路由
- `job_scrape/app/api/schemas/task.py`
  - 新增 manual action 请求/响应 schema
- `job_scrape/app/services/task_service.py`
  - 新增 `apply_manual_action(...)` 业务逻辑与状态校验
- `job_scrape/app/services/task_repository.py`
  - 新增任务状态更新与事件落库组合操作
- `job_scrape/tests/test_task_query_api.py`
  - 增加 manual action 测试，或拆分 `test_task_manual_api.py`

### Testing Requirements

- API 契约
  - replay/skip 成功返回 200，且 data 字段完整
  - 422/404/409 响应包装结构统一
- 状态机约束
  - `manual -> pending`（replay）
  - `manual -> failed`（skip）
  - 非 manual 状态拒绝动作
- 事件留痕
  - replay/skip 后 `task_events` 新增对应事件
  - 事件在 `GET /api/tasks/{task_id}/events` 可查询并顺序正确
- 回归
  - 全量 `pytest` 与 `ruff check .` 通过

## Definition of Done (DoD)

- 运营员可对 manual 任务执行 replay/skip。
- 非 manual 任务动作被拒绝并返回明确错误码。
- 状态迁移与审计事件都被持久化。
- Story 1.4 日志接口可展示 manual 动作事件。
- 回归测试与静态检查通过。

### Previous Story Intelligence

- Story 1.4 已沉淀统一错误包装与 `_error_response` 模式，可直接复用。
- 现有任务查询测试使用 SQLite 临时库，manual 动作实现需保持 SQLite 兼容。
- 当前服务分层清晰：路由只做编排，状态规则应收敛在 `task_service`。

### Git Intelligence Summary

- 最近提交以“按 story 增量推进 + sprint 状态同步”为主，适合继续最小增量策略。
- 仓库当前变更规模小，优先在既有 `tasks` 路由内扩展，避免过早重构目录层级。

### Latest Tech Information

- FastAPI `0.135.1` 已包含近期修复，继续维持 Python 3.11+ 约束即可。
- SQLAlchemy `2.0.48` 位于 2.0 最新稳定序列，保持 2.0 风格同步 Session 调用，不混用 1.4 旧式 Query 写法。
- 当前依赖中 `starlette>=0.46.2,<0.47` 与 FastAPI 版本兼容，避免手动升级打破锁定组合。

### Anti-Reinvention Guardrails

- 不重复实现新的任务状态机模块；复用既有 Task/TaskEvent 模型与仓储。
- 不新增“manual_queue”独立存储；manual 仍是 `tasks.status` 的状态。
- 不在本故事实现重试调度（1/3/9）细节；该能力属于 Epic 4 失败恢复链路。

### Scope Boundaries

本故事包含：
- manual 任务 replay/skip API
- 状态机校验与状态迁移
- 审计事件落库与日志可见性

本故事不包含：
- 自动重试策略改造
- 批量 manual 处理
- 成功率监控与告警（Story 1.6）
- RBAC 全量落地（Story 1.7）

### Project Structure Notes

- 当前项目采用 `app/api/routes/tasks.py` 聚合任务相关能力，manual 动作可先内聚实现。
- 若后续任务动作增多，再抽离子路由；本故事保持 MVP 最小改动。

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5]
- [Source: _bmad-output/planning-artifacts/architecture.md#State Management Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#API Response Formats]
- [Source: _bmad-output/implementation-artifacts/1-4-查看任务日志与失败原因.md]
- [Source: job_scrape/app/api/routes/tasks.py]
- [Source: job_scrape/app/services/task_service.py]
- [Source: job_scrape/app/services/task_repository.py]

## Story Completion Status

- Story ID: 1.5
- Story Key: 1-5-manual-队列处理-重放-跳过
- Story File: _bmad-output/implementation-artifacts/1-5-manual-队列处理-重放-跳过.md
- Final Status: done
- Completion Note: 代码实现与 AI Code Review 修复均完成，AC 全部满足并已同步 sprint 状态。

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- Loaded: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Loaded: `_bmad-output/planning-artifacts/epics.md` (via story Dev Notes)
- Inspected: `job_scrape/app/api/routes/tasks.py`
- Inspected: `job_scrape/app/services/task_service.py`
- Inspected: `job_scrape/app/services/task_repository.py`
- Inspected: `job_scrape/app/api/schemas/task.py`
- Inspected: `job_scrape/app/models/task.py` — 确认 CheckConstraint 含 `manual`/`pending`/`failed` 状态，SQLite 兼容
- Inspected: `job_scrape/tests/test_task_query_api.py` — 复用 fixture 模式

### Implementation Plan

- **schemas**: 新增 `ManualActionRequest`（action: str, reason: str|None max_length=500）和 `ManualActionData` 响应 schema
- **repository**: 新增 `update_task_status_with_event` — 原子性更新 task.status/task.updated_at 并追加审计事件，由调用方 commit
- **service**: 新增 `apply_manual_action` — 先校验 action 合法性、再查任务是否存在、再校验状态为 `manual`，然后执行迁移并写事件；返回 `(task, previous_status)`
- **route**: 新增 `POST /api/tasks/{task_id}/actions/manual`，将 3 类业务错误映射到 404/422/409，数据库异常映射到 500
- **tests**: 新建 `tests/test_task_manual_api.py`，25 个测试：成功路径（replay/skip）、错误路径（4 种）、审计留痕（7 个）

### Completion Notes List

- ✅ AC1: manual 任务 replay→pending、skip→failed，状态机规则已落地
- ✅ AC2: 非 manual 状态返回 409 + `VAL_TASK_STATUS_INVALID_FOR_MANUAL_ACTION`；非法 action 返回 422 + `VAL_MANUAL_ACTION_INVALID`
- ✅ AC3: 所有响应遵循 `{data, meta, error}` 统一包装
- ✅ AC4: replay/skip 均写入 `task_events`（task.manual.replay / task.manual.skip），payload 包含 `task_id/operator/timestamp` 等完整追溯字段，可通过 `GET /api/tasks/{task_id}/events` 查询
- ✅ AC5: 未新增状态、未引入批量处理与自动重试策略
- ✅ 全量 pytest 54/54 通过（含回归 Story 1.2/1.3/1.4）
- ✅ ruff check 全部通过

### File List

- `job_scrape/app/api/schemas/task.py` — 新增 `ManualActionRequest`、`ManualActionData`
- `job_scrape/app/services/task_repository.py` — 新增 `update_task_status_with_event`
- `job_scrape/app/services/task_service.py` — 新增 `_VALID_MANUAL_ACTIONS`、`apply_manual_action`
- `job_scrape/app/api/routes/tasks.py` — 新增 `manual_action_endpoint`、`_MANUAL_ERROR_STATUS` 映射，更新导入
- `job_scrape/tests/test_task_manual_api.py` — 新建，25 个测试用例
- `job_scrape/app/api/routes/api.py` — 挂载 tasks 路由
- `job_scrape/app/main.py` — 挂载 API 总路由并统一请求校验错误包装
- `job_scrape/app/api/deps.py` — 新增 `get_db`/`get_current_operator` 依赖
- `job_scrape/app/db/__init__.py` — 导出 `SessionLocal` 并确保模型加载
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 更新 1-5 状态为 done
- `_bmad-output/implementation-artifacts/1-5-manual-队列处理-重放-跳过.md` — 本故事文件（Task 标记 + 记录更新）

### Senior Developer Review (AI)

- 2026-03-13 审查结论：**Changes Requested → Resolved**
- 已修复高优先级问题：manual 事件 payload 缺少 `timestamp`（已补齐并新增断言测试）
- 已修复中优先级问题：故事状态字段冲突（`review` vs `ready-for-dev`）
- 已修复中优先级问题：File List 与实际实现文件不一致（已补全路由/依赖/DB 导出相关文件）
- 审查后结论：AC1-AC5 全满足，状态更新为 `done`

### Change Log

- 2026-03-13: 实现 Story 1.5 Manual 队列处理（重放/跳过）API — 新增端点、状态机服务、审计事件与测试
- 2026-03-13: AI Code Review 修复 — 补齐 manual 事件 `timestamp`，修正故事状态与 File List 对账信息
