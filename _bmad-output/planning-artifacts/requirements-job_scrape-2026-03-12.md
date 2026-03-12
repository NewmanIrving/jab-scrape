---
date: 2026-03-12
author: Hans
project: job_scrape
status: baseline-draft
language: chinese
references:
  - _bmad-output/planning-artifacts/product-brief-job_scrape-2026-03-12.md
  - _bmad-output/planning-artifacts/research/technical-51job-liepin-anti-crawl-playwright-stealth-research-2026-03-12.md
---

# job_scrape 需求定义（FR / NFR）

## 1. 目标与范围

### 1.1 产品目标（MVP）

构建面向 TOP 客户的招聘情报自动化系统，实现：
- 对 51job、猎聘的低频定向采集
- 岗位变化检测（新增/持续/疑似下线）
- 情报卡输出，支持销售/FAE 跟进

### 1.2 MVP 范围

- 平台：51job（主线）+ 猎聘（PoC）
- 对象：TOP10 客户白名单公司
- 数据：岗位列表与详情核心字段 + 证据留存（HTML/截图）
- 输出：结构化岗位表、基础信号卡

### 1.3 非范围（Out of Scope）

- 全站高并发抓取
- 验证码复杂识别自动破解
- 非招聘平台数据源（如社媒、工商）
- 实时秒级推送

---

## 2. Functional Requirements（FR）

### FR-01 平台任务调度
**描述**：系统可按平台、客户公司、关键词生成采集任务并定时执行。  
**优先级**：P0  
**验收标准**：
- 支持每日多时段调度（至少 2 个时段）
- 支持平台级并发上限配置
- 支持任务状态追踪（pending/running/success/failed/manual）

### FR-02 51job 采集能力
**描述**：可稳定采集 51job 的岗位列表与详情核心字段。  
**优先级**：P0  
**验收标准**：
- 能按公司/关键词获取岗位列表
- 能进入详情页采集 JD 与关键字段
- 能保存 source_url 并关联采集时间

### FR-03 猎聘采集能力（PoC）
**描述**：完成猎聘最小可用采集流程验证。  
**优先级**：P1  
**验收标准**：
- 至少支持 1 条稳定查询链路（搜索→列表→详情）
- 能记录 challenge/captcha 事件
- 7 日内可重复执行并产出有效岗位数据

### FR-04 证据留存
**描述**：每条岗位采集可追溯到原始证据。  
**优先级**：P0  
**验收标准**：
- 保存原始 HTML 文件路径
- 保存页面截图路径
- 支持按岗位记录回查原文证据

### FR-05 数据标准化与去重
**描述**：将不同平台职位数据标准化并去重。  
**优先级**：P0  
**验收标准**：
- 统一输出字段：platform/company/job_title/location/salary/publish_time/job_desc/source_url
- 生成 job_fingerprint
- 可识别重复岗位并合并更新 last_seen_at

### FR-06 岗位状态跟踪
**描述**：系统需跟踪岗位新增、持续、疑似下线状态。  
**优先级**：P0  
**验收标准**：
- 维护 first_seen_at / last_seen_at / disappear_count
- 支持 active / suspected_removed / inactive 状态
- 提供按公司维度的状态变化统计

### FR-07 风控事件记录
**描述**：记录采集过程中验证码、挑战、封禁等事件。  
**优先级**：P0  
**验收标准**：
- 记录 event_type、severity、occurred_at、task_id
- 支持按平台汇总 challenge_rate / captcha_rate
- 支持触发告警阈值判断

### FR-08 重试与人工兜底
**描述**：失败任务自动重试，超限进入人工审核队列。  
**优先级**：P0  
**验收标准**：
- 至少 3 次指数退避重试
- 重试耗尽后状态置为 manual
- 支持人工重放任务

### FR-09 情报卡生成（基础版）
**描述**：基于岗位变化输出基础情报卡。  
**优先级**：P1  
**验收标准**：
- 支持 signal_type（new_project/expansion/switch/risk）
- 情报卡包含证据岗位引用
- 可输出 pending/reviewed/actioned/ignored 状态

### FR-10 外部协作输出
**描述**：支持将情报或统计结果导出到协作系统（钉钉/飞书表格）。  
**优先级**：P1  
**验收标准**：
- 支持批量导出结构化记录
- 支持幂等更新（避免重复写入）
- 导出失败有重试与日志

### FR-11 配置中心
**描述**：采集参数、阈值、白名单可配置。  
**优先级**：P0  
**验收标准**：
- 支持平台参数独立配置
- 支持并发、间隔、页数、重试策略配置
- 支持无需改代码更新白名单公司

### FR-12 审计与可观测
**描述**：关键链路需要日志、指标、追踪信息。  
**优先级**：P0  
**验收标准**：
- 记录任务级结构化日志
- 提供 success_rate/challenge_rate/latency 指标
- 故障可定位到 task_id + session_id

---

## 3. Non-Functional Requirements（NFR）

### NFR-01 合规与数据最小化
- 仅采集业务必要字段，限制个人敏感信息处理
- 存在数据留存周期与删除策略
- 支持访问控制与操作审计
- **验收**：有书面数据字段清单、留存策略与权限模型

### NFR-02 稳定性
- 采集任务具备失败重试、降频、熔断能力
- 平台异常时系统可退化运行，不全局崩溃
- **验收**：连续 7 天运行，任务成功率达到目标区间

### NFR-03 可维护性
- 平台采集器模块化，互不耦合
- 解析规则可快速替换并回归验证
- **验收**：新增或修复一个字段解析不影响其它平台

### NFR-04 可扩展性
- 支持新增平台 collector（低改动接入）
- 支持任务量增长时横向扩展 worker
- **验收**：新增平台接入仅需实现 collector + parser + 配置

### NFR-05 性能（MVP 级）
- 单任务应在可控超时内结束
- 调度系统在峰值下不丢任务
- **验收**：95% 任务执行时长 < 7 分钟（MVP 默认配置）

### NFR-06 可观测性
- 提供核心业务与技术指标面板
- 指标异常可自动告警
- **验收**：challenge_rate、captcha_rate、success_rate 可按日查看

### NFR-07 安全性
- 账号、代理凭据加密存储
- 不在日志明文打印敏感凭据
- **验收**：凭据仅通过受控配置读取，日志脱敏

### NFR-08 成本约束
- 代理与运维成本需可度量并纳入预算
- 单条有效岗位采集成本在可接受阈值内
- **验收**：有成本报表，按平台统计有效采集成本

---

## 4. 优先级总览（MVP）

### P0（必须）
FR-01, FR-02, FR-04, FR-05, FR-06, FR-07, FR-08, FR-11, FR-12  
NFR-01, NFR-02, NFR-03, NFR-06, NFR-07

### P1（应做）
FR-03, FR-09, FR-10  
NFR-04, NFR-05, NFR-08

---

## 5. 需求追踪矩阵（简版）

| 需求 | 对应模块 |
|---|---|
| FR-01/08/11 | Scheduler + Queue + Config |
| FR-02/03 | Collector-51job + Collector-猎聘 |
| FR-04 | Raw Evidence Store |
| FR-05/06 | Parser + Normalizer + DB |
| FR-07/12 | Metrics + Risk Event + Logging |
| FR-09/10 | Signal Engine + Export Adapter |
| NFR-01/07 | Data Governance + Security Controls |

---

## 6. 里程碑验收门槛（MVP）

- M1（51job 主链路）：FR-01/02/04/05/08/11/12 达标
- M2（稳定性）：NFR-02/06 达标，具备降频熔断
- M3（猎聘 PoC）：FR-03 可重复执行，输出有效样本
- M4（情报输出）：FR-09/10 可供销售/FAE 试运行

---

## 7. 决策结论

本文件作为 job_scrape MVP 的需求基线文档。后续技术设计、任务拆解与开发实现均以本 FR/NFR 为准；若范围调整，需更新版本并同步追踪矩阵。
