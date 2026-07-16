# P0-5 迁移闭环报告

## 1. 背景

P0-5 的目标是把审计元数据读取、outfile、recv plan、结果表来源系统和宽表链路摘要能力迁移到新平台，并以报告 JSON 和结果页最小展示形成可回归闭环。本轮 P0-5E 只做迁移结果复核、文档收口和登记表状态复核，不新增业务功能，不修改后端、前端、测试、旧平台业务代码或真实配置文件。

复核依据包括冻结规则、功能同步登记表、P0 迁移计划、函数差异快照和 DB profile router 设计文档。本文只记录字段语义、能力状态和验证命令，不输出真实业务数据、真实路径、真实连接信息、账号、密码、token 或内网 IP。

## 2. 本轮迁移范围

本轮复核 P0-5A 到 P0-5D4 的提交链路：

- P0-5A：审计元数据 service 空壳、安全降级和 public_data 包装入口。
- P0-5B：词根、视图、函数、参数表等轻量元数据查询。
- P0-5C：outfile、recv mapping、结果表来源系统、recv 明细等中等风险元数据查询。
- P0-5D1：re_service 宽表链路摘要服务层 helper。
- P0-5D2：engine HCYT 报告 JSON 接入 lineageSummary。
- P0-5D3：ResultsPage 宽表链路摘要最小展示。
- P0-5D4：前端 lineageSummary 边界回放、安全降级和敏感字符串遮罩。

本轮只允许修改：

- `docs/p0_5_migration_closure.md`
- `docs/feature_sync_register.md`

## 3. 提交链路

| 提交 | 解决的问题 | 涉及文件 | 是否属于 P0-5 范围 | 越界修改 | 未闭环点 |
|---|---|---|---|---|---|
| `2e1db2b feat: add audit metadata service fallback` | 新增审计元数据 service，提供统一 DB router 查询入口；查询异常时降级为空列表；public_data 改为调用 service 包装函数；补充安全日志测试，避免异常文本泄漏敏感信息。 | `backend/svn_check/core/public_data.py`, `backend/svn_check/services/audit_metadata_service.py`, `docs/feature_sync_register.md`, `tests/test_audit_metadata_service.py` | 是。对应 P0-5A。 | 未见旧平台修改；修改新平台服务、测试和登记文档，符合当轮范围。 | 该提交只完成 service 空壳与降级，尚未完成后续轻量/中等查询、engine 和前端闭环。 |
| `714accd feat: add lightweight metadata queries` | 加固单列元数据归一化，支持 tuple、dict、SQLAlchemy row-like 等行形态；去重；补充轻量查询和 public_data 包装回归。 | `backend/svn_check/services/audit_metadata_service.py`, `docs/feature_sync_register.md`, `tests/test_audit_metadata_service.py` | 是。对应 P0-5B。 | 未见旧平台修改；未改真实配置。 | 轻量查询已闭环，仍依赖后续提交补齐 lineage 输入查询。 |
| `e40635d feat: add metadata queries for lineage inputs` | 为 outfile、recv mapping、结果表来源系统、recv 明细增加字段别名、按字段名解析和多列归一化；补充 tuple、dict、row-like、attr row 测试。 | `backend/svn_check/services/audit_metadata_service.py`, `docs/feature_sync_register.md`, `tests/test_audit_metadata_service.py` | 是。对应 P0-5C。 | 未见旧平台修改；未改真实配置。 | 查询层已闭环，尚需服务层消费和报告字段接入。 |
| `4212656 feat: add wide table lineage service helpers` | 在 re_service 增加 `build_job_outfile_lookup` 和 `build_wide_table_lineage_summary`；聚合结果表、作业、recv plan、来源系统、outfile；提供空值降级、去重、统计字段、敏感值过滤和 metadata service 异常降级。 | `backend/svn_check/services/re_service.py`, `docs/feature_sync_register.md`, `tests/test_re_service_lineage.py` | 是。对应 P0-5D1。 | 未见旧平台修改；只改新平台服务、测试和登记文档。 | 服务层已闭环，尚需 engine 报告 JSON 接入。 |
| `f535573 feat: add lineage summary to audit reports` | 在 HCYT 报告中构造 `lineageSummary`；对 metadata service、job/program merge 和摘要构建异常做降级；保证报告 JSON 可序列化；补充 engine 回归。 | `backend/engine.py`, `docs/feature_sync_register.md`, `tests/test_engine_lineage_summary.py` | 是。对应 P0-5D2。 | 未见旧平台修改；未改真实配置。 | 后端报告字段已闭环，尚需前端展示和边界回放。 |
| `9ffa53f feat: show lineage summary in results page` | 在 ResultsPage 增加宽表链路摘要区域；展示 resultTables、jobs、recvPlans、sysNames、outfiles、warnings、stats；mock 数据补充最小展示样例。 | `docs/feature_sync_register.md`, `frontend/src/mock/data.js`, `frontend/src/pages/ResultsPage.jsx` | 是。对应 P0-5D3。 | 未见旧平台修改；前端展示属于 P0-5 范围。 | 已有最小展示，仍需非标准字段形态和敏感字符串边界回放。 |
| `8d76266 test: harden lineage summary frontend rendering` | 加固前端展示：lineageSummary 非对象降级、列表字段非数组降级、对象数组兼容、stats 非对象降级、敏感字符串遮罩；mock 增加边界回放样例。 | `docs/feature_sync_register.md`, `frontend/src/mock/data.js`, `frontend/src/pages/ResultsPage.jsx` | 是。对应 P0-5D4。 | 未见旧平台修改；前端测试样例和展示加固属于 P0-5 范围。 | P0-5D4 后功能闭环；剩余事项应进入文档收口、公开版敏感信息清理清单或 P1/单独 round。 |

总体判断：上述提交均属于 P0-5 范围，未发现旧平台业务代码修改，未发现真实配置文件修改，未发现超出 P0-5 的生产配置适配或完整治理口径实现。

## 4. 已完成能力

| 能力 | 闭环状态 | 说明 |
|---|---|---|
| `audit_metadata_service.py` 空壳和安全降级 | 已闭环 | service 提供统一查询入口，DB/router 异常时返回空列表；日志只记录 profile、backend、函数名和异常类型，不输出异常原文。 |
| `list_term_roots` | 已闭环 | 轻量元数据查询，返回稳定 tuple 列表，支持空值降级和去重。 |
| `list_view_names` | 已闭环 | 轻量元数据查询，兼容多种 DB row 形态。 |
| `list_function_names` | 已闭环 | 轻量元数据查询，兼容多种 DB row 形态。 |
| `list_para_table_names` | 已闭环 | 轻量元数据查询，兼容 public_data 包装入口。 |
| `list_job_outfiles` | 已闭环 | 中等风险元数据查询，提供 job/outfile 二列结构，支持字段别名解析。 |
| `list_upstream_system_ids` | 已闭环 | 中等风险元数据查询，提供有效上游系统 ID 单列结构。 |
| `list_result_table_sys_names` | 已闭环 | 中等风险元数据查询，提供结果表到来源系统映射。 |
| `build_job_outfile_lookup` | 已闭环 | 将 job/outfile rows 归一化为查找表，处理空值、重复和敏感值。 |
| `build_wide_table_lineage_summary` | 已闭环 | 汇总结果表、作业、recv plan、来源系统、outfile、warnings 和 stats；支持 metadata service 异常降级。 |
| `engine.py` 报告字段 `lineageSummary` | 已闭环 | HCYT 报告已接入稳定字段结构，异常时输出空摘要和 warning。 |
| ResultsPage 宽表链路摘要 | 已闭环 | 结果页已展示宽表链路摘要和统计信息。 |
| 前端空值降级 | 已闭环 | 空对象、缺失字段和空数组展示为暂无数据或空摘要。 |
| 前端非数组兼容 | 已闭环 | 列表字段非数组时按空列表处理。 |
| 前端对象数组兼容 | 已闭环 | 对象数组优先读取安全展示字段，无法读取时输出脱敏后的有限 JSON。 |
| 前端敏感字符串遮罩 | 已闭环 | 对连接串、DSN、URL、IP、password、token、secret 等文本做遮罩或替换。 |

## 5. 报告 JSON 字段

当前新平台 HCYT 报告已具备以下关键字段。这里只描述字段语义，不包含真实业务数据、真实路径或真实连接信息。

- `assetIssues`：结构化资产问题列表，用于承载资产待维护、词根缺失、门户链接等问题项。
- `sourceType`：审计任务来源类型，用于区分 SVN 来源、本地工作区来源等来源形态。
- `workspaceRoot`：审计工作区标识，用于定位本次任务的工作区来源；对外文档不应输出真实本机路径。
- `changes`：本次审计识别到的变更文件列表和分类信息。
- `lineageSummary`：宽表链路摘要对象，用于承载结果表、作业、recv plan、来源系统、outfile、警告和统计信息。

`lineageSummary` 子字段语义：

- `resultTables`：链路相关结果表名称列表。
- `jobs`：链路相关作业名称列表。
- `recvPlans`：链路相关上游卸数计划列表。
- `sysNames`：链路相关来源系统名称列表。
- `outfiles`：链路相关下游 outfile 列表。
- `warnings`：元数据不可用、解析失败或摘要为空时的降级提示列表。
- `stats`：摘要统计信息，例如结果表、作业、recv plan、来源系统、outfile 的计数。

## 6. 前端展示状态

ResultsPage 已接入 `lineageSummary` 的最小展示：

- 宽表链路摘要面板展示结果表、作业、上游卸数计划、来源系统、下游 outfile。
- 展示 `stats` 统计信息。
- 展示 `warnings` 降级提示。
- 缺失、空值、非数组、非对象 stats 均稳定降级。
- 支持字符串数组和对象数组。
- 对敏感 key 和敏感字符串做遮罩，避免连接串、账号口令、token、IP 等文本直接出现在 UI 中。

## 7. 测试与验证命令

P0-5 各轮已归档的验证命令如下：

| 命令 | 状态 | 说明 |
|---|---|---|
| `D:\miniconda3\python.exe -m unittest tests.test_audit_metadata_service` | 已通过 | 覆盖 audit metadata service 降级、轻量查询、中等查询、public_data 包装和敏感异常文本不泄漏。 |
| `D:\miniconda3\python.exe -m unittest tests.test_re_service_lineage` | 已通过 | 覆盖 job/outfile lookup、宽表链路摘要、空值降级、去重、metadata service 异常降级和敏感值过滤。 |
| `D:\miniconda3\python.exe -m unittest tests.test_engine_lineage_summary` | 已通过 | 覆盖 HCYT 报告 `lineageSummary`、JSON 可序列化、metadata 异常降级和既有报告字段稳定性。 |
| `D:\miniconda3\python.exe -m unittest discover -s tests` | 已通过 | P0-5 全量单测回归建议命令。 |
| `D:\miniconda3\python.exe backend\dev_selfcheck.py` | 已通过 | 开发自检建议命令。 |
| `npm run build` | 已通过 | 前端构建建议命令。 |

已知 warning：

- PowerShell 中执行 git 或 Python 相关命令时可能出现 `RequestsDependencyWarning`，指向本机 Python 环境中 requests 依赖版本组合不匹配。该 warning 是既有环境 warning，不代表 P0-5 代码或文档变更失败。
- 当前系统默认 `python` / Codex bundled Python 环境可能与项目依赖不一致。P0/P1 回归建议统一使用 `D:\miniconda3\python.exe`，避免解释器差异造成误判。

## 8. 敏感信息与配置风险

本轮复核未输出真实账号、密码、token、内网 IP、真实连接串或真实配置值。P0-5 提交链路未修改真实配置文件。

已形成的防护点：

- metadata service 查询失败时只记录异常类型，不记录异常原文。
- re_service 摘要构建会过滤疑似连接串、口令、token、IP 等敏感值。
- ResultsPage 对敏感 key、连接串、DSN、URL、IP、口令和 token 做遮罩。

仍建议后续补充公开版敏感信息清理清单，用于统一检查文档、示例数据、mock 数据、日志和发布材料。

## 9. 未完成事项

仍属于 P0 可选收尾：

- P0-5E 文档闭环。
- 迁移登记表状态复核。
- 公开版敏感信息清理清单。

不建议继续塞进 P0-5 的事项：

- 结果表禁用完整治理口径。
- 来源系统完整治理口径。
- outfile 完整下游推送校验。
- 更复杂的血缘图谱展示。
- 权限控制。
- 用户操作日志重构。
- 配置中心化实现。
- DB Profile 完整生产配置适配。

## 10. 不应继续扩张的事项

P0-5 已经完成从元数据读取、服务层摘要、报告 JSON 到前端最小展示和边界回放的闭环。继续在 P0-5 中扩张 FS-008 或 FS-009 会把范围从“迁移链路摘要”扩大到“治理口径和生产校验”，风险和验证成本都会显著上升。

因此以下事项应进入 P1 或单独 round：

- FS-008 的结果表登记、禁用、来源系统完整治理口径。
- FS-009 的 outfile 完整下游推送校验。
- DB Profile 完整生产配置适配。
- 权限、操作日志、配置中心等平台治理能力。
- 图谱化、交互式或跨系统的复杂血缘展示。

## 11. 后续建议 round

建议下一个 round 为 P0 文档和安全收尾，内容只包括：

- 公开版敏感信息清理清单。
- P0 总登记表复核。
- P0 已完成能力的回归命令固化。

FS-008、FS-009、DB Profile 生产适配、权限、操作日志和配置中心化建议进入 P1 或独立 round，不继续扩大 P0-5。
