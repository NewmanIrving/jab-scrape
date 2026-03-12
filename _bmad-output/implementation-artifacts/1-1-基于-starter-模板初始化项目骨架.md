# Story 1.1: 基于 Starter 模板初始化项目骨架

Status: in-progress

## Story

As a 开发者,
I want 使用架构指定的 starter 模板初始化项目并完成最小可运行配置,
so that 后续故事可以在统一工程基线上持续实现和验证。

## Acceptance Criteria

1. Given 架构文档已指定 `arthurhenrique/cookiecutter-fastapi` 为 starter，When 执行项目初始化，Then 生成可运行后端工程骨架。
2. 完成依赖安装、环境变量模板（`.env.example`）与最小启动验证。
3. 仅创建当前故事所需最小基础结构；不预创建后续业务表与复杂业务模块。
4. 产出基础工程规范：代码风格、测试入口、迁移工具可用。

## Tasks / Subtasks

- [x] 使用指定 starter 初始化项目
  - [x] 执行：`cookiecutter gh:arthurhenrique/cookiecutter-fastapi`
  - [x] 统一项目名与包名为 `job_scrape`（按模板交互项）
  - [x] 提交初始目录结构（仅保留 MVP 必要骨架）
- [x] 建立最小依赖与运行基线
  - [x] 安装并锁定基础开发依赖（FastAPI/Uvicorn/SQLAlchemy/Alembic/Pydantic/Pytest/Ruff）
  - [x] 生成 `.env.example`（数据库连接、基础运行参数占位）
  - [x] 提供本地启动命令与健康检查验证
- [x] 建立最小数据库迁移能力
  - [x] 初始化 Alembic 配置可执行
  - [x] 创建“空基线”或最小初始迁移（不引入后续故事业务表）
- [x] 建立基础质量门禁
  - [x] 配置 `ruff` 与 `pytest` 的最小可运行命令
  - [x] 增加最小 smoke test（应用可启动 / health endpoint 可访问）

## Dev Notes

### Story Foundation

- 本故事是 Epic 1 的起点，目标是“统一工程基线”，不是业务功能交付。
- 当前不实现任务状态机、采集器、导出、证据层等后续故事能力。
- 本故事完成后，后续所有故事都应复用该骨架，不重复初始化工程。

### Technical Requirements

- 指定 starter：`arthurhenrique/cookiecutter-fastapi`。
- 运行环境：Windows + PowerShell 场景可执行。
- 使用 Python 工程规范（lint/test/migration 基础可用）。
- 不引入非 MVP 必需组件（如消息队列、复杂前端、多服务拆分）。

### Architecture Compliance

- 架构决策要求单体后端 + 模块化边界，MVP 单实例部署。
- 目录组织应对齐架构文档建议：`app/api`、`app/core`、`app/db`、`tests` 等基础域。
- 数据库演进仅通过 Alembic；禁止手工改表。
- 统一响应包装、统一错误处理规范在后续故事实现时落地，本故事先准备基础承载结构。

### Library & Framework Requirements

建议按架构文档版本锚点初始化（允许小版本补丁更新）：
- `fastapi` 0.135.x
- `uvicorn` 0.41.x
- `sqlalchemy` 2.0.x
- `alembic` 1.18.x
- `pydantic` 2.12.x
- `pytest`（稳定版）
- `ruff`（稳定版）

### File Structure Requirements

初始化后至少应具备以下最小结构（可按模板实际略有差异）：
- `app/main.py`
- `app/core/`
- `app/api/`
- `app/db/`
- `tests/`
- `alembic/` 与 `alembic.ini`
- `pyproject.toml`
- `.env.example`
- `README.md`

### Testing Requirements

- 必须可执行 `ruff check`。
- 必须可执行 `pytest`（至少 1 个 smoke test）。
- 必须可启动应用并验证健康接口（如 `/health`）。
- 验收以“可启动、可测试、可迁移”为通过标准。

### Anti-Reinvention Guardrails

- 不要重新设计项目脚手架；优先沿用 starter 默认结构并做最小必要调整。
- 不要提前实现后续故事的数据表和业务服务。
- 不要在本故事引入 Playwright 采集细节、风控策略或导出业务逻辑。
- 不要创建与架构文档冲突的目录命名与分层。

### Scope Boundaries

本故事包含：
- 工程初始化
- 依赖与环境模板
- 最小运行验证
- 最小测试与 lint 验证

本故事不包含：
- 任务触发 API 业务实现
- 采集器实现
- evidence/risk/manual 流程实现
- 导出与统计实现

## Project Structure Notes

- 以“可持续增量开发”为目标，保持结构轻量但可扩展。
- 若模板默认结构与架构文档存在轻微差异，优先保证命名与边界一致性，不做大规模重构。

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 / Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md#MVP Scope]
- [Source: _bmad-output/planning-artifacts/research/technical-51job-liepin-anti-crawl-playwright-stealth-research-2026-03-12.md#Executive Summary]

## Story Completion Status

- Story ID: 1.1
- Story Key: 1-1-基于-starter-模板初始化项目骨架
- Story File: _bmad-output/implementation-artifacts/1-1-基于-starter-模板初始化项目骨架.md
- Final Status: in-progress
- Completion Note: 工程骨架初始化、最小运行基线、Alembic 基线迁移、质量门禁均已完成并通过验证。

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- cookiecutter gh:arthurhenrique/cookiecutter-fastapi --no-input -o . project_name=job_scrape project_slug=job_scrape package_name=job_scrape
- python -m pip install -e ".[dev]"
- alembic init alembic
- alembic revision -m "baseline"
- alembic upgrade head
- ruff check .
- pytest -q

### Completion Notes List

- 使用指定 starter 完成项目初始化，项目目录生成为 `job_scrape/`。
- 对模板进行最小化裁剪，移除 ML 相关示例模块，保留 MVP 所需骨架结构。
- 收敛依赖到故事要求版本区间，并配置 `ruff` 与 `pytest` 最小可用基线。
- 新增 `/health` 健康检查与 smoke test，验证应用可访问。
- 初始化 Alembic，生成空基线迁移并执行 `upgrade head` 验证可迁移。
- 质量门禁通过：`ruff check .` 与 `pytest -q` 全部通过。
- 代码评审修复：将核心依赖改为显式锁定版本，满足“安装并锁定基础开发依赖”要求。
- 代码评审修复：移除 `app/core/config.py` 中与 ML 模块相关的遗留配置项，收敛为 Story 1.1 最小骨架范围。
- 代码评审修复：统一 `DATABASE_URL` 默认值为 `sqlite:///./job_scrape.db`，与 `.env.example`、`alembic.ini` 一致。
- 代码评审修复：统一 Python 版本约束为 3.11+（README 与 pyproject 对齐）。

### File List

- _bmad-output/implementation-artifacts/1-1-基于-starter-模板初始化项目骨架.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- job_scrape/.env.example
- job_scrape/README.md
- job_scrape/pyproject.toml
- job_scrape/alembic.ini
- job_scrape/alembic/README
- job_scrape/alembic/env.py
- job_scrape/alembic/script.py.mako
- job_scrape/alembic/versions/51aa0ae6bba7_baseline.py
- job_scrape/app/main.py
- job_scrape/app/api/routes/api.py
- job_scrape/app/core/config.py
- job_scrape/app/db/__init__.py
- job_scrape/app/db/base.py
- job_scrape/app/db/session.py
- job_scrape/tests/test_health_smoke.py
- job_scrape/app/core/events.py (deleted)
- job_scrape/app/core/paginator.py (deleted)
- job_scrape/app/db.py (deleted)
- job_scrape/app/api/routes/predictor.py (deleted)
- job_scrape/app/models/log.py (deleted)
- job_scrape/app/models/prediction.py (deleted)
- job_scrape/app/services/predict.py (deleted)
- job_scrape/tests/test_api_predictor.py (deleted)
- job_scrape/tests/test_config_and_errors.py (deleted)
- job_scrape/tests/test_events_and_main.py (deleted)
- job_scrape/tests/test_pagination_behavior.py (deleted)
- job_scrape/tests/test_predict_service.py (deleted)
- job_scrape/tests/test_predictor.py (deleted)
- job_scrape/tests/test_request_logging.py (deleted)
- job_scrape/ml/__init__.py (deleted)
- job_scrape/ml/data/__init__.py (deleted)
- job_scrape/ml/data/make_dataset.py (deleted)
- job_scrape/ml/features/__init__.py (deleted)
- job_scrape/ml/features/build_features.py (deleted)
- job_scrape/ml/model/.gitkeep (deleted)
- job_scrape/ml/model/examples/example.json (deleted)
- job_scrape/notebooks/.gitkeep (deleted)

### Change Log

- 2026-03-13: 完成 Story 1.1 实现，初始化并裁剪 starter 工程，补齐最小运行/迁移/测试门禁。
- 2026-03-13: 执行 adversarial code review，修复高/中优先级代码问题（依赖锁定、配置最小化、版本与数据库默认值一致性）。

## Senior Developer Review (AI)

- Review Date: 2026-03-13
- Reviewer: Hans（AI Assistant）
- Outcome: Changes Requested（部分环境问题待处理）
- 已修复（代码侧）:
  - `pyproject.toml`：核心依赖与开发依赖改为显式固定版本；`requires-python` 调整为 `>=3.11`。
  - `app/core/config.py`：移除 ML 遗留配置项；默认数据库 URL 与工程文档统一。
- 已验证:
  - `ruff check .` 通过
  - `pytest -q` 通过（1 passed）
- 未完全闭环项:
  - 当前工作区未检测到 `.git` 仓库，无法执行“故事 File List 与 git 真实改动”对账审计（属于环境/仓库初始化问题，非应用代码缺陷）。
- 建议后续动作:
  - 在项目根目录初始化并连接 Git 仓库后，补跑一次 code review 审计流程以完成变更可追溯性核验。
