# `svn_check` 退场盘点

## 盘点范围与结论

本清单对应退场阶段 1。盘点范围为 `backend/svn_check`、`backend/audit`、`backend/db`、`backend/scripts`、`tests` 和 `docs`，未删除或迁移文件，未修改业务代码或测试断言。

当前结论：`backend/svn_check` 不是可以整体删除的旧代码。审计主流程仍动态加载其中的 HCYT、NUPS、FineReport 规则与服务；metadata 初始化和查询、lineage 缓存与遍历也仍在运行路径上。退场必须先把真实实现迁到新命名空间，再收敛兼容入口并切换调用方。

分类口径：

- **删除**：仅旧迁移资料或无生产调用的历史辅助模块；阶段 2 删除前仍须逐项复核。
- **迁移到 metadata**：metadata 查询、DB 兼容访问和独立 metadata schema 初始化。
- **迁移到 lineage**：标识符、登记结果表、Excel 导入、SQLite cache 和遍历。
- **迁移到 audit rules/checks**：现役审计规则、issue 结构、规则辅助逻辑及其直接服务。
- **暂留兼容壳**：迁移后需要继续支持旧 import 的包或模块。
- **待确认**：目标目录不在本任务推荐结构中，或是否仍属产品能力需要在后续阶段结合调用链决定。

## 文件级去向

“当前引用方”只列直接或代表性调用方；完整调用路径以后续阶段的 `rg` 复核为准。

| 当前路径 | 文件类型 | 当前职责 | 当前引用方 | 现役能力 | 分类 | 目标路径 | 需要兼容壳 | 保留或新增测试 | 风险 | 删除或迁移前置条件 |
|---|---|---|---|---|---|---|---|---|---|---|
| `backend/svn_check/__init__.py` | 生产代码 | 旧顶层包标记 | 旧路径导入 | 是 | 暂留兼容壳 | 最终删除 | 是，至阶段 8 | 旧包兼容导入；阶段 8 改为退役断言 | 中 | 所有实现、调用方和兼容测试已迁出 |
| `backend/svn_check/configs/database.example.yaml` | fixture | metadata DB 脱敏配置模板 | `backend/db/profiles.py` 的默认配置约定、部署文档 | 是 | 迁移到 metadata | `backend/metadata/configs/database.example.yaml` | 视配置路径兼容策略 | profile/config 路径解析 | 高 | 不改 profile 默认值；同步代码与部署文档 |
| `backend/svn_check/configs/svn.example.yaml` | fixture | SVN 脱敏配置模板 | `services/svn_service.py`、部署文档 | 是 | 迁移到 audit checks | `backend/audit/configs/svn.example.yaml` | 是 | SVN 配置解析与环境变量展开 | 中 | 先迁移 SVN 服务并保持配置优先级 |
| `backend/svn_check/configs/svn.yaml` | fixture | 仓库内 SVN 默认/示例配置 | `services/svn_service.py` | 是 | 迁移到 audit checks | `backend/audit/configs/svn.yaml` | 是 | SVN 配置 fallback | 高 | 复核无凭据；保持现有默认行为 |
| `backend/svn_check/core/__init__.py` | 生产代码 | 旧规则包标记 | `core.*` 导入 | 是 | 暂留兼容壳 | `backend/audit/rules/__init__.py` | 是 | 新旧规则包导入 | 中 | 规则实现全部迁移 |
| `backend/svn_check/core/asset_issue.py` | 生产代码 | issue 构造、key/hash、去重和统一 issue 转换 | `backend/audit/engine.py`、issue/portal tests | 是 | 迁移到 audit rules | `backend/audit/rules/asset_issue.py` | 是 | `test_asset_issue`、报告契约 | 高 | 保持 issue、`unifiedAssetIssues`、`assetIssues` 结构 |
| `backend/svn_check/core/fine_rule.py` | 生产代码 | FineReport XML、菜单、权限、模板和 SQL 检查 | `backend/audit/engine.py`、Fine runner | 是 | 迁移到 audit checks | `backend/audit/checks/fine_rule.py` | 是 | Fine runner/contract 回归 | 高 | 保持命中语义和报告字段 |
| `backend/svn_check/core/hcyt/__init__.py` | 生产代码 | 汇总导出 HCYT 规则 API | engine 与 HCYT runners | 是 | 迁移到 audit rules | `backend/audit/rules/hcyt/__init__.py` | 是 | HCYT runner/report/program/schedule contracts | 高 | 子模块全部迁移且导出集合不变 |
| `backend/svn_check/core/hcyt/_sql_parser.py` | 生产代码 | HCYT SQL 解析辅助 | HCYT SQL/DDL 规则 | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/_sql_parser.py` | 是 | SQL/DDL 规则契约 | 高 | 保持解析与排序语义 |
| `backend/svn_check/core/hcyt/ddl_rule.py` | 生产代码 | DDL、词根和资产问题检查 | engine、HCYT rule runner | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/ddl_rule.py` | 是 | HCYT rule/report contract | 高 | metadata 注入与 issue 输出不变 |
| `backend/svn_check/core/hcyt/file_utils.py` | 生产代码 | HCYT 文件读取、分类和文本辅助 | HCYT 规则模块 | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/file_utils.py` | 是 | HCYT runner/program tests | 中 | 保持编码与路径处理语义 |
| `backend/svn_check/core/hcyt/python_rule.py` | 生产代码 | DWO/DWF/DWS Python 与 recv 检查 | engine、program runner | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/python_rule.py` | 是 | program/subworkflow contracts | 高 | 保持问题结构和结果表判断 |
| `backend/svn_check/core/hcyt/schedule_rule.py` | 生产代码 | PLAN/SEQ/CALE/JOB 调度规则 | schedule runner | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/schedule_rule.py` | 是 | schedule runner/program contracts | 高 | 保持依赖、禁用和排序语义 |
| `backend/svn_check/core/hcyt/sql_rule.py` | 生产代码 | DWS/Hive SQL 静态检查 | engine、HCYT rule runner | 是 | 迁移到 audit checks | `backend/audit/checks/hcyt/sql_rule.py` | 是 | HCYT rule/report contracts | 高 | 保持命中与返回结构 |
| `backend/svn_check/core/hcyt_rule.py` | 生产代码 | 旧 HCYT 聚合导入入口 | `core.nups_rule` 及旧调用方 | 是 | 暂留兼容壳 | `backend/audit/rules/hcyt_rule.py` | 是 | 聚合导入兼容 | 中 | `core.hcyt` 新实现就位 |
| `backend/svn_check/core/nups_rule.py` | 生产代码 | NUPS SQL/Python/结果表规则 | engine、NUPS runner | 是 | 迁移到 audit checks | `backend/audit/checks/nups_rule.py` | 是 | NUPS runner/contract | 高 | 保持规则命中和前端字段 |
| `backend/svn_check/core/public_data.py` | 生产代码 | 规则使用的 metadata 查询口径 facade | Fine/NUPS/HCYT 规则 | 是 | 迁移到 metadata | `backend/metadata/services/public_data.py` | 是 | 查询返回结构与降级回归 | 高 | metadata service/db service 先迁移；SQL 语义不变 |
| `backend/svn_check/migrate/README.md` | 文档 | metadata schema 边界说明 | 开发者文档 | 是 | 迁移到 metadata | `backend/metadata/init/README.md` | 否 | 文档路径扫描 | 低 | SQL 与 init 入口迁移后更新 |
| `backend/svn_check/migrate/postgres_schema.sql` | SQL | 独立 metadata 表初始化 | `backend/scripts/init_pg.py` | 是 | 迁移到 metadata | `backend/metadata/init/postgres_schema.sql` | 旧文件暂作资源兼容 | init SQL 路径解析、schema 内容一致性 | 高 | 禁止与 runtime schema 合并或改语义 |
| `backend/svn_check/services/__init__.py` | 生产代码 | 旧服务包标记 | `from services ...` | 是 | 暂留兼容壳 | 按服务拆分后最终删除 | 是 | 新旧服务导入 | 中 | 所有服务实现迁出 |
| `backend/svn_check/services/ai_service.py` | 生产代码 | SQL LLM 调用占位/节流入口 | `backend/audit/engine.py` | 是 | 迁移到 audit checks | `backend/audit/checks/ai_service.py` | 是 | AI review 降级/契约测试 | 中 | 保持当前返回和异常行为 |
| `backend/svn_check/services/audit_metadata_service.py` | 生产代码 | metadata 查询、归一和安全降级 | engine、public_data、re_service、tests | 是 | 迁移到 metadata | `backend/metadata/services/audit_metadata_service.py` | 是 | 新旧导入、全部查询契约 | 高 | profile、SQL、返回结构、日志降级不变 |
| `backend/svn_check/services/db_service.py` | 生产代码 | metadata 查询 DB facade | `core/public_data.py`、tests | 是 | 迁移到 metadata | `backend/metadata/services/db_service.py` | 是 | 新旧导入、空结果降级 | 高 | 不改变 runtime_store；profile 默认行为不变 |
| `backend/svn_check/services/diag_service.py` | 生产代码 | SVN/旧 UI 诊断日志兼容接口 | `services/svn_service.py` | 是 | 迁移到 audit checks | `backend/audit/checks/diag_service.py` | 是 | 日志与 no-op 兼容 | 低 | SVN 服务迁移并确认无旧 UI 隐藏调用 |
| `backend/svn_check/services/portal_link_builder.py` | 生产代码 | 资产门户链接生成 | portal tests、issue 展示链路 | 是 | 迁移到 audit rules | `backend/audit/rules/portal_link_builder.py` | 是 | `test_portal_link_builder` | 中 | 保持环境变量、空链接和 URL 参数语义 |
| `backend/svn_check/services/re_service.py` | 生产代码 | 文件/SQL 辅助、宽表 lineage 汇总和导出工具 | engine、Fine/NUPS rules、lineage tests | 是 | 待确认 | 拆到 `backend/audit/checks` 与 `backend/lineage` | 是 | re_service lineage、engine summary、规则回归 | 高 | 按职责拆分；不可整体归为旧工具 |
| `backend/svn_check/services/svn_service.py` | 生产代码 | SVN 配置、diff、export 和工作区生成 | engine、workspace_service | 是 | 迁移到 audit checks | `backend/audit/checks/svn_service.py` | 是 | SVN 命令/配置/路径契约 | 高 | 不执行真实 SVN；配置路径兼容 |
| `backend/svn_check/services/workspace_service.py` | 生产代码 | 本地/SVN 工作区统一结构与校验 | engine、workspace tests | 是 | 迁移到 audit checks | `backend/audit/checks/workspace_service.py` | 是 | `test_workspace_service`、local audit | 高 | source type、workspace 字段和校验不变 |
| `backend/svn_check/shared/__init__.py` | 生产代码 | 旧 shared 包标记 | `shared.db/graph/lineage` 导入 | 是 | 暂留兼容壳 | 最终删除 | 是 | 旧 shared 导入 | 中 | 三类 shared 能力均迁出 |
| `backend/svn_check/shared/db/README.md` | 文档 | 旧 metadata DB 兼容边界 | 开发者文档 | 是 | 迁移到 metadata | `backend/metadata/services/README.md` | 否 | 文档路径扫描 | 低 | DB adapter 迁移完成后更新 |
| `backend/svn_check/shared/db/__init__.py` | 生产代码 | 旧 DB adapter 包入口 | metadata/lineage 服务 | 是 | 暂留兼容壳 | `backend/db/metadata/compat/__init__.py` | 是 | 新旧 DB imports | 高 | adapter 实现先迁入 compat 边界 |
| `backend/svn_check/shared/db/gaussdb.py` | 生产代码 | profile 驱动的 Gauss/DWS 查询兼容 adapter | shared DB router、tests | 是 | 迁移到 metadata | `backend/db/metadata/compat/gaussdb.py` | 是 | shared DB router contracts | 高 | 连接/profile/异常降级不变 |
| `backend/svn_check/shared/db/postgres.py` | 生产代码 | profile 驱动的 PostgreSQL 查询兼容 adapter | shared DB router、tests | 是 | 迁移到 metadata | `backend/db/metadata/compat/postgres.py` | 是 | shared DB router contracts | 高 | 不改变连接与事务语义 |
| `backend/svn_check/shared/db/router.py` | 生产代码 | metadata DB 类型和 profile 分派 | metadata service、lineage、tests | 是 | 迁移到 metadata | `backend/db/metadata/compat/router.py` | 是 | 新旧 router、profile contracts | 高 | 不修改 runtime DB 行为或 profile 默认值 |
| `backend/svn_check/shared/graph/README.md` | 文档 | 无生产调用的历史依赖图模块说明 | 迁移计划、功能同步登记 | 待确认 | 待确认 | 待定 | 待定 | 保留扫描记录与 graph 契约测试 | 中 | 既有迁移计划解除“不能直接删除”约束，调度能力完成去向确认 |
| `backend/svn_check/shared/graph/__init__.py` | 生产代码 | 历史依赖图包标记 | graph 契约测试 | 待确认 | 待确认 | 待定 | 待定 | 保留旧 graph 导入和算法契约 | 中 | 确认无外部/隐藏调用，并为仍需能力建立新路径 |
| `backend/svn_check/shared/graph/dependency.py` | 生产代码 | 内存依赖图、环检测和反向依赖 | `test_shared_graph_dependency.py`；功能登记将其列为调度依赖参考 | 待确认 | 待确认 | 倾向 `backend/audit/checks/dependency.py` | 是（若迁移） | 保留 5 个算法入口的现有断言 | 高 | 不删除覆盖点；阶段 5 结合 schedule 规则决定迁移或退役 |
| `backend/svn_check/shared/lineage/README.md` | 文档 | lineage 混合职责与风险说明 | 开发者文档 | 是 | 迁移到 lineage | `backend/lineage/README.md` | 否 | 文档路径扫描 | 低 | lineage 实现迁移后更新 |
| `backend/svn_check/shared/lineage/__init__.py` | 生产代码 | 旧 lineage 包入口 | engine、lineage tests | 是 | 暂留兼容壳 | `backend/lineage/__init__.py` | 是 | 新旧 lineage imports | 高 | 所有实现先迁至新包 |
| `backend/svn_check/shared/lineage/cache_store.py` | 生产代码 | SQLite cache 创建、meta 与新鲜度判断 | mapping_sqlite、contract tests | 是 | 迁移到 lineage | `backend/lineage/cache_store.py` | 是 | cache/meta/freshness contracts | 高 | 路径、建表、时间与新鲜度语义不变 |
| `backend/svn_check/shared/lineage/identifiers.py` | 生产代码 | 表/列标识符解析与归一 | mapping_sqlite、registered_tables、tests | 是 | 迁移到 lineage | `backend/lineage/identifiers.py` | 是 | identifiers contracts | 中 | 保持大小写、空值和 compact 语义 |
| `backend/svn_check/shared/lineage/mapping_sqlite.py` | 生产代码 | lineage 兼容 facade、SQLite 查询与 BFS | engine、lineage tests | 是 | 暂留兼容壳 | `backend/lineage/mapping_compat.py`、`traversal.py` | 是 | 新旧 imports、BFS/排序/cache/Excel contracts | 高 | 新实现完整承载；默认 profile/path 不变 |
| `backend/svn_check/shared/lineage/registered_tables.py` | 生产代码 | 登记结果表读取与节点过滤 | mapping_sqlite、tests | 是 | 迁移到 lineage | `backend/lineage/registered_tables.py` | 是 | 默认 `profile='czcb'` 与过滤契约 | 高 | profile 和 SQL 不变 |
| `backend/svn_check/shared/lineage/xlsx_loader.py` | 生产代码 | Excel 表头识别与 lineage edge 加载 | mapping_sqlite、tests | 是 | 迁移到 lineage | `backend/lineage/xlsx_loader.py` | 是 | 临时 workbook、表头/edge contracts | 高 | 不依赖生产 Excel；识别语义不变 |

## 未跟踪与生成文件

工作目录中还可能存在被 Git 忽略的本地文件：`backend/svn_check/configs/database.yaml` 以及各级 `__pycache__/*.pyc`。它们不属于提交清单：前者是本地配置，迁移配置路径时只能保留兼容或由用户自行搬迁，不能提交其内容；后者是 Python 生成物，随旧目录退场自然消失，不建立兼容壳。

## 现役调用链摘要

- `backend/audit/engine.py` 把 `backend/svn_check` 插入 `sys.path`，直接导入 `services.*`、`core.*` 和 `shared.lineage.mapping_sqlite`。
- `backend/scripts/init_pg.py` 直接读取 `backend/svn_check/migrate/postgres_schema.sql`。
- `backend/db/profiles.py` 的默认配置路径仍指向 `backend/svn_check/configs/database.yaml`。
- 多组 HCYT、NUPS、FineReport、metadata、lineage、workspace 和 DB router 测试仍通过旧路径导入真实实现。
- `shared.graph` 没有生产调用方；当前唯一代码调用来自该历史模块自身的契约测试。

## 阶段 2 候选与保护项

阶段 2 已重新检索 `backend/svn_check/shared/graph` 的目录名、模块名以及 `parse_job_dependencies`、`build_dependency_graph`、`find_cycles`、`build_reverse_dependency_graph`、`find_all_dependent_jobs`。没有发现生产代码调用，但发现以下删除阻断条件：

- `docs/db_runtime_metadata_migration_plan.md` 明确要求不能直接删除该目录，必须先完成归档评估。
- `docs/feature_sync_register.md` 把 `shared/graph/dependency.py` 记录为 HCYT 调度审计的依赖参考，能力去向尚未最终确认。
- `tests/test_shared_graph_dependency.py` 对 5 个算法入口保留行为契约；删除模块必然同时删除现有测试覆盖点，违反本任务全局约束。

因此阶段 2 **无安全删除项**。本阶段只记录复核结论，不删除文件、不迁移文件、不修改业务代码或测试断言。`shared/graph` 改列为“待确认”，在阶段 5 结合调度规则迁移决定其去向；若能力仍需保留，应先迁移实现和测试，再处理旧路径。

下列项目明确受保护，不能在阶段 2 删除：

- `backend/svn_check/shared/db`
- `backend/svn_check/shared/lineage/*`
- `backend/svn_check/migrate/postgres_schema.sql`
- `backend/svn_check/services/*` 与 `backend/svn_check/core/*` 中的现役实现
- 任何只因旧路径命名而显得“legacy”、但仍被 `backend/audit`、`backend/scripts` 或 tests 调用的文件

## 迁移顺序与共同前置条件

1. metadata：先建立 `backend/metadata` 与 `backend/db/metadata/compat` 的真实实现和新路径测试，再将旧 service/shared DB 文件变为 facade。
2. lineage：迁移现有已拆分 helpers，再把 SQLite 查询/BFS 迁到 `backend/lineage/traversal.py`，以 `mapping_compat.py` 汇总公开 API；旧 `mapping_sqlite.py` 只转发。
3. audit rules/checks：按 engine 动态导入集合迁移规则及直接依赖，保持报告、issue 和前端字段契约。
4. 旧路径收敛：兼容壳不得新增业务逻辑，且要标明真实实现位置。
5. 调用方切换：生产代码和绝大多数测试改用新路径，只保留最小兼容测试。
6. 最终删除：全仓确认没有必须保留的 `svn_check`/`shared` 引用，全量测试通过后才能删除旧目录。
