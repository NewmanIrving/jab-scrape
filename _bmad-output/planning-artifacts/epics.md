---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - docs/原始需求.md
---

# job_scrape - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for job_scrape, decomposing the requirements from the PRD, Architecture, and original user requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: 运营员可以手动触发指定客户范围的采集任务。
FR2: 运营员可以查看任务执行状态（pending/running/success/failed/manual）。
FR3: 运营员可以查看单任务执行日志与失败原因。
FR4: 运营员可以对 manual 任务执行重放或跳过处理。
FR5: 系统支持为每次任务生成可追溯的 task_id 与执行记录。
FR6: 系统支持按客户名称在 51job 执行岗位搜索与列表采集。
FR7: 系统支持对 51job 列表结果执行详情采集并提取岗位核心字段。
FR8: 系统支持在猎聘执行最小可用采集链路（搜索→列表→详情）。
FR9: 系统支持记录采集过程中平台挑战事件（如 captcha/challenge）。
FR10: 系统支持在采集失败后按策略重试并在超限后转入 manual。
FR11: 系统支持将多平台岗位数据标准化为统一字段结构。
FR12: 系统支持为岗位生成唯一指纹用于去重与合并更新。
FR13: 系统支持维护岗位的 first_seen_at 与 last_seen_at。
FR14: 系统支持维护岗位 disappear_count 并支持状态变更标记。
FR15: 系统支持保留岗位历史状态变化用于趋势回查。
FR16: 系统支持为每条岗位记录保留 source_url。
FR17: 系统支持为每条岗位记录保留采集时间戳。
FR18: 系统支持为每条岗位记录关联原始 HTML 证据路径。
FR19: 系统支持在关键字段缺失时生成可追溯告警记录。
FR20: 系统支持按 task_id/session_id 定位采集证据与日志。
FR21: 运营员可以维护公司监控白名单而无需改代码。
FR22: 运营员可以调整采集参数与阈值（如频率、重试相关配置）。
FR23: 系统支持在配置变更后将新配置应用到后续任务。
FR24: 管理员可以维护系统级配置（环境变量、部署参数、凭据）。
FR25: 运营员可以按客户、平台、时间范围筛选采集结果。
FR26: 运营员可以导出采集结果为 CSV。
FR27: 运营员可以导出采集结果为 Excel。
FR28: 运营员可以导出采集结果为 JSON。
FR29: 系统支持在导出结果中提供用于人工分析的完整核心字段集。

### NonFunctional Requirements

NFR1: 在默认配置（TOP10 客户、2 平台、并发 ≤ 2）下，单次任务执行总时长 P95 ≤ 7 分钟；以任务运行日志按周统计。
NFR2: 任务触发、状态查询、日志查看等关键操作接口响应时间 P95 ≤ 2 秒；以应用监控按日统计。
NFR3: 在并发 ≤ 2 的运行约束下，任务丢失率应为 0%，重复执行率 ≤ 0.5%；以 task_id 去重审计按周统计。
NFR4: 任务失败后系统应自动执行 3 次指数退避重试（1min/3min/9min），重试耗尽后自动转为 manual；以任务状态流转日志校验。
NFR5: 单平台或单客户任务失败不应中断同批次其他任务，批次级中断率应为 0%；以批次运行日志按周统计。
NFR6: 7 天滚动任务成功率（success / total）应 ≥ 85%；当连续 2 天低于阈值时触发告警。
NFR7: 平台账号、代理配置与系统凭据必须加密存储，日志中敏感字段明文暴露率应为 0%；以每周日志抽样审计（≥200 条）验证。
NFR8: 访问控制至少区分"运营员（任务与参数）"和"管理员（系统配置）"，未授权操作拦截率应为 100%；以权限测试用例验证。
NFR9: 控制台与服务间数据传输应全部使用 TLS 通道，非加密连接占比应为 0%；以网络抓包抽检与网关日志验证。
NFR10: 仅采集白名单字段，非白名单字段落库率应为 0%；以每日入库字段审计任务验证。
NFR11: 原始岗位数据默认永久保留；同时系统需支持按 30/90/180 天策略切换归档或删除，策略变更在 24 小时内生效并可审计。
NFR12: 岗位记录证据完整率（source_url + 采集时间戳 + HTML 路径）应 ≥ 99.5%；以每日数据质量报表验证。
NFR13: 操作与采集日志需支持 task_id/session_id 双键追溯，指定任务 5 分钟内可定位完整链路；以故障演练记录验证。
NFR14: 平台采集器需模块化，新增平台改动不应触及现有平台核心逻辑文件（允许公共组件）；以代码变更范围审计验证。
NFR15: 字段解析规则变更应可独立发布，回归测试通过率应 ≥ 95%，且不影响其他平台主流程；以回归报告验证。
NFR16: 白名单、阈值、重试策略应配置化管理，硬编码配置项占比应为 0%；以配置扫描脚本按版本校验。
NFR17: CSV/Excel/JSON 导出字段一致性应为 100%，编码统一为 UTF-8；以每次发布后的三格式对比测试验证。
NFR18: 相同筛选条件在 24 小时内重复导出，记录主键重复率应为 0%，导出失败重试成功率应 ≥ 95%；以导出任务日志验证。
NFR19: Growth 阶段外部集成应通过可替换适配层接入，适配层变更不应影响核心采集流程回归通过率（≥95%）；以模块化回归测试验证。

### Additional Requirements

**来自架构文档的技术需求：**

- **Starter 模板初始化**：架构指定使用 `arthurhenrique/cookiecutter-fastapi` 作为工程底座，初始化命令为 `cookiecutter gh:arthurhenrique/cookiecutter-fastapi`。这将是 Epic 1 Story 1 的唯一内容。
- **数据库迁移**：使用 Alembic 版本化迁移，禁止手工改表。核心数据表：tasks/task_runs/task_events、job_postings/job_snapshots、evidence_records、risk_events、config_profiles/whitelist_companies。
- **认证**：MVP 使用内部账号 + 会话认证；RBAC 双角色 operator/admin。
- **部署基线**：Docker Compose 单实例部署（api + postgres + worker，redis 按需启用）。
- **CI/CD 流水**：lint（ruff）→ unit/integration 测试（pytest）→ contract 测试 → 构建镜像。
- **可观测性基线**：prometheus-client 指标暴露；结构化日志 + task_id/session_id 全链路追踪。
- **状态机约束**：任务状态机固定 `pending → running → success|failed|manual`；合法人工动作仅 `replay|skip`；任何状态变更必须写审计事件（task_events）。
- **API 规范**：REST + OpenAPI 自动文档；统一响应包装 `{data, meta, error}`；统一错误码前缀 `VAL_*/NET_*/RISK_*/INT_*`。
- **Redis 条件启用**：用于任务去重锁、限流计数、短期会话状态；主链路不强依赖 Redis。
- **证据路径规范**：`storage/evidence/{platform}/{date}/{task_id}/page.html`（可含 screenshot.png）。
- **日志脱敏**：账号、cookie、token、代理凭据不可明文输出；CI 增加敏感字段门禁。
- **Playwright 集成**：Playwright 1.58.0 + 持久化浏览器会话；会话过期自动检测，触发人工重新登录提示。

**来自原始需求文档的业务参考约束：**

- **分析入口模型**：保留“四入口扫描”业务模型（大客户、场景拓新、芯片机会、竞对预警）作为后续扩展方向，MVP 仅落地大客户主链路。
- **统一证据层目标**：数据应沉淀为“公司/主体—岗位—标签—历史特征”可追溯结构；原始层优先保真，衍生层规则化计算。
- **信号分类基线**：维持五类核心信号（新项目/新方向、扩产/放量、供应链切换、组织/决策链变动、业务收缩/风险预警）作为 Growth 分析层输入框架。
- **分析四层职责**：坚持“代码保数据准确、Prompt1 保不漏报、Prompt2 保不误报、人类做行动决策”的分层原则，避免职责耦合。
- **采集流程约束**：沿用“两阶段采集”（列表页→详情页）并保持“仅采页面明示字段，不做推断补写”的数据治理原则。
- **平台扩展路线**：MVP 聚焦 51job + 猎聘；BOSS、智联、脉脉、公司官网与搜索引擎作为后续 collector 扩展对象。
- **调度与输出方向**：保留“调度层→采集层→存储加工层→AI 分析层→输出层”目标链路，MVP 先完成采集、加工与基础导出。
- **UI 设计边界**：控制台保持轻量运营形态，不做过多 UI 细节设计；优先任务触发、状态查询、manual 处理和导出能力。
- **原始采集字段基线（raw_job_postings）**：MVP 采集与落库至少覆盖 `source_platform`、`source_url_raw`、`company_name`、`job_title`、`salary_text`、`posted_at`、`updated_at`、`job_description_text`、`location_text`、`experience_requirement_text`、`education_requirement_text`、`company_industry_text`、`headcount_text`；未展示字段保持空值，不做推断填充。
- **衍生字段基线**：规则任务必须生成并维护 `crawled_at`、`source_url_canonical`、`source_job_id`、`first_seen_at`、`last_seen_at`、`times_seen`、`consecutive_misses`、`disappeared_at`、`record_status`。
- **状态判定规则**：`record_status` 严格按优先级判定：`CLOSED`（`disappeared_at` 有值）→ `JD_CHANGED`（JD 变更）→ `NEW`（首次出现）→ `ACTIVE`（其余在招）。
- **下架判定阈值**：当 `consecutive_misses >= 3` 时写入 `disappeared_at` 并置 `record_status=CLOSED`；若岗位重新出现需清空 `disappeared_at` 并回到在招状态判定流程。
- **时序统计口径**：为后续信号分析预留统一指标口径：本月新增岗位数（`first_seen_at`）、本月关闭岗位数（`disappeared_at`）、当前在招总数（`record_status=ACTIVE`）。

### FR Coverage Map
### FR Coverage Map

FR1: Epic 1 - 手动触发指定客户采集任务
FR2: Epic 1 - 查看任务执行状态
FR3: Epic 1 - 查看任务日志与失败原因
FR4: Epic 1 - 对 manual 任务执行重放/跳过
FR5: Epic 1 - 生成并追溯 task_id 与执行记录
FR6: Epic 2 - 51job 搜索与列表采集
FR7: Epic 2 - 51job 详情采集与字段提取
FR8: Epic 4 - 猎聘最小可用采集链路
FR9: Epic 4 - 平台 challenge/captcha 事件记录
FR10: Epic 4 - 失败重试后转 manual 兜底
FR11: Epic 3 - 多平台字段标准化
FR12: Epic 3 - 岗位唯一指纹与去重合并
FR13: Epic 3 - 维护 first_seen_at / last_seen_at
FR14: Epic 3 - disappear_count 与状态变更标记
FR15: Epic 3 - 岗位历史状态追踪
FR16: Epic 2 - 保留 source_url 证据
FR17: Epic 2 - 保留采集时间戳证据
FR18: Epic 2 - 关联原始 HTML 证据路径
FR19: Epic 3 - 关键字段缺失告警（规则层）
FR20: Epic 3 - task_id/session_id 证据与日志追溯
FR21: Epic 5 - 维护监控白名单无需改代码
FR22: Epic 5 - 调整采集参数与阈值
FR23: Epic 5 - 配置变更自动应用后续任务
FR24: Epic 5 - 管理员维护系统级配置
FR25: Epic 5 - 按客户/平台/时间筛选结果
FR26: Epic 5 - CSV 导出
FR27: Epic 5 - Excel 导出
FR28: Epic 5 - JSON 导出
FR29: Epic 5 - 导出完整核心字段用于人工分析

## Epic List

### Epic 1: 任务执行与运行可观测
运营员可以触发采集任务、跟踪执行状态、查看失败原因，并对 manual 队列进行重放或跳过处理，形成可审计的任务运行闭环。
**FRs covered:** FR1, FR2, FR3, FR4, FR5
**NFRs covered:** NFR6, NFR8

### Epic 2: 51job 可信采集与原始证据落库
系统完成 51job 列表页与详情页两阶段采集，按原始字段基线保真落库，并沉淀 source_url/时间戳/HTML 路径证据，支持后续规则计算与审计回查。
**FRs covered:** FR6, FR7, FR16, FR17, FR18

### Epic 3: 标准化衍生字段与岗位生命周期追踪
系统基于原始数据计算规范链接、岗位ID与生命周期字段，执行状态优先级规则与缺失告警，确保岗位状态可持续跟踪且全链路可追溯。
**FRs covered:** FR11, FR12, FR13, FR14, FR15, FR19, FR20

### Epic 4: 猎聘 PoC 与失败恢复闭环
系统提供猎聘最小可用采集能力，并在挑战场景下记录风控事件、执行指数退避重试、自动转入 manual，保证整体任务链路可恢复。
**FRs covered:** FR8, FR9, FR10

### Epic 5: 配置化运营与多格式结果消费
运营员与管理员可维护白名单和运行阈值，并将配置稳定应用到任务执行；同时支持筛选与 CSV/Excel/JSON 一致导出，供业务侧直接消费。
**FRs covered:** FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR28, FR29

## Epic 1: 任务执行与运行可观测

运营员可以触发采集任务、跟踪执行状态、查看失败原因，并对 manual 队列进行重放或跳过处理，形成可审计的任务运行闭环。

### Story 1.1: 基于 Starter 模板初始化项目骨架

As a 开发者,
I want 使用架构指定的 starter 模板初始化项目并完成最小可运行配置,
So that 后续故事可以在统一工程基线上持续实现和验证。

**Acceptance Criteria:**

**Given** 架构文档已指定 `arthurhenrique/cookiecutter-fastapi` 为 starter
**When** 执行项目初始化
**Then** 生成可运行的后端工程骨架并完成依赖安装、环境变量模板与基础启动验证
**And** 仅创建当前故事所需的最小基础结构，不预先创建后续故事不需要的业务表与模块

### Story 1.2: 手动触发采集任务并生成追溯ID

As a 运营员,
I want 手动触发指定客户范围的采集任务,
So that 我可以发起可追溯的采集流程。

**Acceptance Criteria:**

**Given** 运营员已登录且提交有效客户范围
**When** 点击触发任务
**Then** 系统创建任务并返回唯一 `task_id`
**And** 初始状态为 `pending` 且写入创建时间与触发人信息

### Story 1.3: 查询任务状态与基础进度

As a 运营员,
I want 查看任务列表和单任务状态,
So that 我能实时掌握执行进展。

**Acceptance Criteria:**

**Given** 系统中存在已创建任务
**When** 运营员查看任务列表或详情
**Then** 系统返回 `pending/running/success/failed/manual` 状态
**And** 支持按时间范围与客户筛选并按最近更新时间排序

### Story 1.4: 查看任务日志与失败原因

As a 运营员,
I want 查看任务执行日志和失败原因,
So that 我能快速定位问题并判断是否需要人工介入。

**Acceptance Criteria:**

**Given** 任务已进入执行阶段
**When** 运营员打开任务日志
**Then** 系统按时间顺序展示关键事件和错误信息
**And** 每条日志至少包含 `task_id` 或 `session_id` 以支持追溯

### Story 1.5: Manual 队列处理（重放/跳过）

As a 运营员,
I want 对 `manual` 任务执行重放或跳过,
So that 我可以恢复失败流程并维持任务闭环。

**Acceptance Criteria:**

**Given** 某任务状态为 `manual`
**When** 运营员执行 `replay` 或 `skip`
**Then** 系统按状态机规则完成状态迁移并记录操作审计事件
**And** 非 `manual` 任务不允许执行该动作并返回明确错误码

### Story 1.6: 7 天滚动成功率监控与阈值告警

As a 管理员,
I want 系统持续计算 7 天滚动任务成功率并在连续低于阈值时告警,
So that 我能在采集质量持续下降前及时介入。

**Acceptance Criteria:**

**Given** 系统已有任务执行历史
**When** 系统按天计算最近 7 天滚动成功率
**Then** 生成并展示 `success/total` 成功率指标，默认阈值为 `85%`
**And** 当滚动成功率连续 2 天低于阈值时，系统创建可追溯告警事件并在任务监控界面可见

### Story 1.7: 基础角色权限控制与未授权拦截

As a 管理员,
I want 系统区分运营员与管理员权限并拦截未授权操作,
So that 系统级配置不会被非授权用户修改。

**Acceptance Criteria:**

**Given** 系统存在 `operator` 与 `admin` 两类已认证用户
**When** 用户访问任务执行、参数配置和系统配置相关能力
**Then** `operator` 可执行任务触发、状态查看、manual 处理、白名单与任务参数调整，但不可访问系统级凭据与部署配置
**And** 未授权访问必须被 100% 拦截，返回明确错误码并记录审计日志

## Epic 2: 51job 可信采集与原始证据落库

系统完成 51job 列表页与详情页两阶段采集，按原始字段基线保真落库，并沉淀 source_url/时间戳/HTML 路径证据，支持后续规则计算与审计回查。

### Story 2.1: 51job 列表页采集与原始记录首轮入库

As a 运营员,
I want 系统采集 51job 列表页岗位卡片并首轮写入原始表,
So that 我能尽早获得可追溯的基础岗位数据。

**Acceptance Criteria:**

**Given** 已配置客户名称与 51job 查询条件
**When** 执行列表页采集
**Then** 系统为每条岗位生成一条 `raw_job_postings` 原始记录
**And** 写入列表页可见字段，包括 `source_platform/source_url_raw/company_name/job_title/salary_text/location_text/headcount_text`，以及列表页可见的 `posted_at/updated_at/experience_requirement_text/education_requirement_text/company_industry_text`
**And** 若发生网络抖动、页面加载超时或可重试平台错误，则复用通用重试框架按统一策略重试，不将 51job 主链路视为“无重试特例”

### Story 2.2: 51job 详情页补全与字段冲突合并

As a 运营员,
I want 系统逐条访问详情页补全缺失字段并按规则合并同名字段,
So that 我能获得完整且一致的原始文本数据。

**Acceptance Criteria:**

**Given** 已存在列表页采集出的详情链接
**When** 执行详情页采集
**Then** 系统对缺失字段进行补全，并处理 `job_description_text/posted_at/updated_at/experience_requirement_text/education_requirement_text/company_industry_text`
**And** 若列表页与详情页同名字段同时有值，按配置项 `field_merge_priority`（默认 `detail_first`，可选 `list_first`）完成合并并记录字段来源（`list`/`detail`）

### Story 2.3: 证据落盘与证据索引关联

As a 运营员,
I want 系统保存采集证据并关联到岗位记录,
So that 我可以在问题排查时回看原始页面。

**Acceptance Criteria:**

**Given** 详情页采集成功
**When** 系统完成单岗位持久化
**Then** 系统保存 `source_url`、采集时间戳与 HTML 证据路径
**And** 证据路径符合 `storage/evidence/{platform}/{date}/{task_id}/` 规范

### Story 2.4: 原始字段质量校验与缺口报告

As a 运营员,
I want 系统输出原始字段覆盖情况,
So that 我能快速发现采集规则缺口。

**Acceptance Criteria:**

**Given** 一次任务执行完成
**When** 生成采集质量报告
**Then** 报告统计 raw 字段填充率与空值分布
**And** 能按字段区分“页面无该字段”与“采集规则缺失”两类原因

## Epic 3: 标准化衍生字段与岗位生命周期追踪

系统基于原始数据计算规范链接、岗位ID与生命周期字段，执行状态优先级规则与缺失告警，确保岗位状态可持续跟踪且全链路可追溯。

### Story 3.1: 规范链接与平台岗位ID生成

As a 运营员,
I want 系统自动生成 `source_url_canonical` 与 `source_job_id`,
So that 同一岗位可稳定识别与去重。

**Acceptance Criteria:**

**Given** 原始记录包含 `source_url_raw`
**When** 执行标准化任务
**Then** 系统生成去参数后的 `source_url_canonical`
**And** 系统按平台规则从 canonical URL 提取 `source_job_id`，提取失败时记录可追溯异常事件

### Story 3.2: 首次/最近出现与累计出现次数维护

As a 运营员,
I want 系统维护 `first_seen_at/last_seen_at/times_seen`,
So that 我能判断岗位是新增还是持续在招。

**Acceptance Criteria:**

**Given** 某岗位在本次采集结果中出现
**When** 系统执行生命周期更新
**Then** 首次出现时写入 `first_seen_at` 且后续不覆盖
**And** 每次出现均更新 `last_seen_at` 并使 `times_seen` 自增 1

### Story 3.3: 连续未出现与下架判定

As a 运营员,
I want 系统维护 `consecutive_misses/disappeared_at`,
So that 我能识别岗位是否下架。

**Acceptance Criteria:**

**Given** 系统有历史岗位记录
**When** 某岗位在本次结果中未出现
**Then** `consecutive_misses` 增加 1；若岗位出现则重置为 0
**And** 当 `consecutive_misses >= 3` 时写入 `disappeared_at`，岗位重现时清空 `disappeared_at`

### Story 3.4: 记录状态机与 JD 变更判定

As a 运营员,
I want 系统按统一优先级计算 `record_status`,
So that 岗位生命周期状态一致且可解释。

**Acceptance Criteria:**

**Given** 生命周期字段与 JD 文本均可用
**When** 系统进行状态计算
**Then** `record_status` 按 `CLOSED > JD_CHANGED > NEW > ACTIVE` 优先级判定
**And** 状态变更写入审计事件并可按 `task_id/session_id` 追溯

### Story 3.5: 关键字段缺失告警与双键追溯

As a 运营员,
I want 系统对关键字段缺失发告警并支持双键追溯,
So that 我能快速定位采集或解析问题。

**Acceptance Criteria:**

**Given** 已配置关键字段清单
**When** 系统检测到岗位关键字段缺失
**Then** 对默认关键字段集（`source_platform/source_url_raw/company_name/job_title/job_description_text/location_text`）任一缺失生成告警事件，并携带岗位标识、字段名、任务上下文
**And** 用户可在 5 分钟内通过 `task_id/session_id` 定位到对应日志与证据路径

### Story 3.6: 公司级时序指标计算

As a 运营员,
I want 系统按固定窗口计算公司级招聘核心时序指标,
So that 我能稳定获得用于趋势判断的基础数据。

**Acceptance Criteria:**

**Given** 已有稳定维护的 `first_seen_at/disappeared_at/record_status`
**When** 系统执行公司级时序统计任务
**Then** 按滚动窗口 `current=[T-30d,T)` 与 `previous=[T-60d,T-30d)`（UTC，左闭右开）计算并存储：最近30天新增岗位数、最近30天关闭岗位数、当前在招总数（`record_status=ACTIVE`）以及前30天新增/关闭岗位数
**And** 统计结果写入统一特征存储，供后续环比计算与标签判定直接复用

### Story 3.7: 环比率计算与趋势标签判定

As a 运营员,
I want 系统基于时序指标计算环比率并输出趋势标签,
So that 我能快速识别扩产、收缩或观望等趋势变化。

**Acceptance Criteria:**

**Given** Story 3.6 已产出当前窗口与前窗口的公司级时序指标
**When** 系统执行趋势分析任务
**Then** 计算新增环比 `new_mom_rate=(current_new-previous_new)/previous_new`；若 `previous_new=0` 且 `current_new=0` 则记为 `0`，若 `previous_new=0` 且 `current_new>0` 则记为 `null` 并打标 `newly_active`
**And** 趋势标签按阈值配置判定（默认：`rise>=30%`、`fall<=-30%`、`min_base_count=3`），输出 `expansion_suspected/shrink_risk/volatile_reorg/stable_observing/newly_active`

## Epic 4: 猎聘 PoC 与失败恢复闭环

系统提供猎聘最小可用采集能力，并在挑战场景下记录风控事件、执行指数退避重试、自动转入 manual，保证整体任务链路可恢复。

### Story 4.1: 猎聘最小链路采集（搜索→列表→详情）

As a 运营员,
I want 系统完成猎聘最小可用采集链路,
So that 我能验证第二平台采集可行性。

**Acceptance Criteria:**

**Given** 已配置猎聘客户查询任务
**When** 执行猎聘采集任务
**Then** 系统完成搜索、列表和详情三段流程，并产出至少 1 条包含非空 `job_description_text` 的完整可入库样本
**And** 样本写入统一原始结构，字段口径与 51job 主链路一致

### Story 4.2: 反爬挑战事件识别与记录

As a 运营员,
I want 系统识别并记录 captcha/challenge 风控事件,
So that 我能准确判断失败原因并选择恢复策略。

**Acceptance Criteria:**

**Given** 猎聘采集中出现挑战页或验证码
**When** 系统检测到风控特征
**Then** 写入 `risk_event`，包含平台、事件类型、时间戳、`task_id/session_id`
**And** 事件可在任务日志中按时间线查看并用于后续审计

### Story 4.3: 指数退避重试与 manual 兜底

As a 运营员,
I want 系统在失败后自动重试并转 manual,
So that 局部失败可恢复且不阻断整体任务执行。

**Acceptance Criteria:**

**Given** 某猎聘任务发生可重试失败
**When** 系统执行恢复策略
**Then** 按 `1/3/9` 分钟指数退避重试，耗尽后状态转为 `manual`
**And** 同批次其他任务不中断，重试过程保持幂等（同一岗位不重复写入快照），并保留后续 `replay/skip` 处理入口

## Epic 5: 配置化运营与多格式结果消费

运营员与管理员可维护白名单和运行阈值，并将配置稳定应用到任务执行；同时支持筛选与 CSV/Excel/JSON 一致导出，供业务侧直接消费。

### Story 5.1: 白名单与任务参数配置管理

As a 运营员,
I want 维护公司白名单与采集参数,
So that 我无需改代码即可调整监控范围和执行策略。

**Acceptance Criteria:**

**Given** 运营员拥有配置权限
**When** 新增/编辑白名单公司或调整任务参数
**Then** 配置通过界面保存并写入配置存储
**And** 无需重启服务即可在后续任务中生效（默认 5 分钟内），且该权限不包含系统级凭据修改

### Story 5.2: 系统级配置与凭据管理

As a 管理员,
I want 维护系统级配置与平台凭据,
So that 我能安全地管理运行环境与账号信息。

**Acceptance Criteria:**

**Given** 管理员访问系统配置模块
**When** 更新环境参数、凭据或部署相关配置
**Then** 系统按角色权限校验并记录配置变更审计日志
**And** 敏感信息以加密方式存储且日志中不输出明文，满足 NFR7 对凭据安全的要求
**And** 控制台与服务间的配置管理请求必须通过 TLS 通道传输，禁止非加密连接，满足 NFR9 对传输安全的要求

### Story 5.3: 结果筛选与统一查询视图

As a 运营员,
I want 按客户、平台、时间范围筛选采集结果,
So that 我能快速定位需要分析的数据集合。

**Acceptance Criteria:**

**Given** 系统已有结构化岗位与时序结果
**When** 用户提交筛选条件
**Then** 系统返回统一查询结果并包含核心分析字段，时间筛选按 UTC 左闭右开区间解释
**And** 同一筛选条件为三种导出格式提供同源数据集

### Story 5.4: CSV/Excel/JSON 一致导出

As a 运营员,
I want 将筛选结果导出为 CSV/Excel/JSON,
So that 我可以按不同场景分发和复核数据。

**Acceptance Criteria:**

**Given** 用户选择导出格式并确认筛选条件
**When** 系统生成导出文件
**Then** CSV/Excel/JSON 的字段集合、记录主键集合与记录总数保持一致且编码统一 UTF-8
**And** 导出结果包含人工分析所需核心字段并可追溯到任务上下文
