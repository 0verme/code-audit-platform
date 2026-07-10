# DB / Runtime / Metadata Migration Plan

## 1. 迁移总原则

本文件是“阶段 1.5：可执行但不落地的迁移清单”。本轮只定义执行方案，不迁移文件，不修改 import，不修改业务代码，不修改测试断言。

### 1.1 边界定义

- `runtime db`：由 `backend/db` 负责，面向审计平台运行期持久化，包括任务、报告、问题明细、运行状态。
- `metadata compat db`：由 `backend/svn_check/shared/db` 负责，面向 `svn_check` 兼容路径的在线元数据查询适配。
- `metadata init sql`：由 `backend/svn_check/migrate/postgres_schema.sql` 负责，面向 metadata 侧初始化，不等于 runtime schema。
- `lineage`：由 `backend/svn_check/shared/lineage/mapping_sqlite.py` 承载，当前混合了 metadata 在线查询、SQLite cache、Excel 导入、registered result tables 加载、lineage 遍历、兼容入口。
- `legacy graph`：`backend/svn_check/shared/graph` 当前只能标注为“未发现主流程引用的候选遗留模块”，不能写成“确定无用”。

### 1.2 执行顺序

- 先保兼容：先明确旧路径、旧默认参数、旧 cache 行为、旧入口导入路径仍可工作。
- 后迁移：仅在兼容壳和测试到位后，再迁移文件或拆职责。
- 再收敛：当新路径稳定、引用点已切换、测试覆盖充分后，再让旧路径退化为 shim 或归档说明。

### 1.3 强制约束

- 每一步都必须先有兼容壳，再有路径切换。
- 每一步都必须有测试保护，至少覆盖默认 profile、cache 新鲜度判断、registered result tables 查询、runtime schema 初始化、metadata schema 初始化。
- `runtime db` 与 `metadata compat db` 可以共用同一个物理数据库引擎或实例，但不能因此把 schema、职责、SQL 入口混为一谈。
- `runtime_store`、`mapping_sqlite.py`、`shared/db`、`shared/graph` 在测试和兼容壳未完备前都不得直接删除。

## 2. 文件级迁移清单

| 当前路径 | 当前职责 | 当前依赖方 | 建议目标位置 | 是否需要兼容壳 | 兼容壳保留方式 | 需要补充或保留的测试 | 风险等级 | 是否本阶段可迁移 | 回滚方式 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/db/connection.py` | runtime 连接建立、`CompatConnection`、占位符适配、SQL 分句 | `db.schema`、`db.sql_runner`、`db.runtime_store`、脚本 | 保持 `backend/db/connection.py`，后续可拆到 `backend/db/runtime/connection.py` | 是 | 原路径保留 re-export 或代理函数 | 保留 `tests/test_database_compat.py`、`tests/test_sql_runner.py`；补 PG/DWS 连接参数回归 | 高 | 否 | 保留原文件为主入口，撤回新代理引用 |
| `backend/db/errors.py` | runtime DB 异常定义 | `db.connection`、`db.sql_runner` | 保持原位，后续如拆分仅内部移动 | 否 | 不需要；最多原路径 re-export | 保留异常类型导入回归 | 低 | 否 | 恢复原路径导出 |
| `backend/db/profiles.py` | 统一 profile 解析、默认 profile、环境变量配置 | runtime DB、metadata compat DB、`init_pg.py` | 保持 `backend/db/profiles.py`，作为共享基础能力 | 否 | 不建议迁移；它本身就是收敛点 | 保留 `tests/test_db_profiles.py`、`tests/integration/test_db_profiles_integration.py` | 高 | 否 | 保持单一入口不变 |
| `backend/db/runtime_store.py` | runtime 持久化读写、报告和任务状态更新 | `backend/app.py`、`backend/audit/engine.py`、`backend/audit/run_registry.py` | 保持原位；后续可文档化为 `backend/db/runtime/store.py` 目标 | 是 | 若未来移动，原路径保留全量函数代理 | 保留 `tests/test_database_compat.py`、`tests/test_local_audit_task.py`；禁止放宽断言 | 高 | 否 | 恢复到原入口，保留旧函数签名 |
| `backend/db/schema.py` | runtime schema SQL 加载、migration SQL 加载、runtime 初始化 | `dev_seed.py`、`dev_selfcheck.py`、测试、运行期启动 | 保持 `backend/db/schema.py`，后续可拆为 `backend/db/runtime/schema.py` | 是 | 原路径保留 `init_db()`/`ensure_runtime_tables()` 代理 | 保留 `tests/test_database_compat.py`；补 schema/migration 路径解析测试 | 高 | 否 | 恢复到原文件路径和原 API |
| `backend/db/sql_runner.py` | runtime SQL 查询执行、事务、`?`/`%s` 兼容 | `migrate_sqlite_to_profile.py`、测试 | 保持原位，并作为 shared/db 未来复用目标 | 否 | 不先迁移；先让 compat 层代理到这里 | 保留 `tests/test_sql_runner.py`、`tests/test_migrate_sqlite_to_profile.py` | 中 | 否 | 保持原能力不动 |
| `backend/db/tables.py` | runtime 逻辑表名到物理表名映射、token 渲染 | `schema.py`、`sql_runner.py`、`connection.py` | 保持原位，后续只允许在 runtime 显式化阶段再讨论目录 | 是 | 若未来重组，原路径保留完整 token API | 保留 `tests/test_database_compat.py` 和 SQL token 回归；禁止单点改动 | 高 | 否 | 恢复旧 token 渲染路径 |
| `backend/db/sql/sqlite/schema.sql` | SQLite runtime schema | `db.schema` | 保持原位 | 否 | 不需要 | 保留 runtime schema 初始化回归 | 高 | 否 | 恢复原 SQL 文件 |
| `backend/db/sql/postgresql/schema.sql` | PostgreSQL runtime schema | `db.schema` | 保持原位 | 否 | 不需要 | 保留 runtime schema 初始化回归 | 高 | 否 | 恢复原 SQL 文件 |
| `backend/db/sql/postgresql/migrate_runtime_tables.sql` | PostgreSQL runtime migration 合约 | `db.schema` | 保持原位 | 否 | 不需要 | 保留 migration 执行顺序回归 | 高 | 否 | 恢复原 SQL 文件 |
| `backend/db/sql/dws/schema.sql` | DWS runtime schema | `db.schema` | 保持原位 | 否 | 不需要 | 保留 DWS schema 加载回归 | 高 | 否 | 恢复原 SQL 文件 |
| `backend/svn_check/migrate/postgres_schema.sql` | metadata 初始化 SQL | `backend/scripts/init_pg.py` | 未来可移至 `backend/db/metadata/legacy_init/postgres_schema.sql` | 是 | 原路径保留同内容壳文件，注明“compat entry, do not edit independently” | 需要新增 `init_pg.py` 路径兼容测试、metadata 表存在性校验测试 | 高 | 否 | `init_pg.py` 切回原路径，保留原 SQL 文件为权威入口 |
| `backend/scripts/init_pg.py` | 读取 metadata SQL 并初始化 metadata 表 | 运维手工初始化、开发环境 | 未来切到 `backend/scripts/init_metadata_pg.py` 或继续保留原名 | 是 | 先支持双路径查找，再切默认路径，最后原路径仅代理 | 必须新增脚本级测试：读取 SQL 路径、打印目标 profile、校验 `EXPECTED_TABLES` | 高 | 否 | 回退到只读取 `backend/svn_check/migrate/postgres_schema.sql` |
| `backend/svn_check/shared/db/router.py` | metadata compat DB 路由；按 profile type 分派 PG/DWS 模块 | `audit_metadata_service.py`、`db_service.py`、`mapping_sqlite.py` | 未来保持原路径为 shim，内部复用 `backend/db/profiles.py`、`backend/db/sql_runner.py` | 是 | 原函数名保留，内部代理新实现 | 必须补 router 分派测试、异常类型测试、profile 透传测试 | 高 | 否 | 恢复直接分派到 `shared/db/postgres.py`、`gaussdb.py` |
| `backend/svn_check/shared/db/postgres.py` | metadata compat PG 查询和执行 | `router.py` | 未来变成对 shared shim 核心或 `backend/db` 适配层的代理 | 是 | 保留 `select_sql_with_profile`/`run_sql_with_profile` 函数签名 | 必须补查询失败降级和 profile type 校验测试 | 中 | 否 | 恢复当前独立实现 |
| `backend/svn_check/shared/db/gaussdb.py` | metadata compat DWS 查询和执行 | `router.py` | 未来变成对 shared shim 核心或 `backend/db` 适配层的代理 | 是 | 保留 `select_sql_with_profile`/`run_sql_with_profile` 函数签名 | 必须补 DWS 路径与 PG 路径等价行为测试 | 中 | 否 | 恢复当前独立实现 |
| `backend/svn_check/shared/lineage/mapping_sqlite.py` | lineage 全量兼容入口；混合在线查询、cache、Excel、遍历、registered tables | `backend/audit/engine.py`、`fine_runner.py`、`hcyt_program_runner.py`、测试 | 未来可拆为 `backend/svn_check/shared/lineage/{metadata_query,cache_store,xlsx_loader,registered_tables,traversal,compat}.py` | 是 | 原模块必须长期保留 compat import，逐函数转发 | 必须先补 `tests/test_lineage_registered_tables_profile.py` 之外的 cache/Excel/traversal 测试 | 高 | 否 | 保留原单模块实现并撤回拆分导入 |
| `backend/svn_check/shared/graph/dependency.py` | 旧依赖图构建与循环查找工具 | 当前未发现主流程引用；仅目录文档标注 candidate | 保持原位；未来仅在归档评估后转 `archive/` 或保留 README | 是 | 若归档，原路径保留 README 和导入说明，必要时保留薄代理 | 先做引用扫描；若发现测试缺口，先补图算法单测 | 中 | 否 | 恢复原文件并撤销归档 README |
| `backend/scripts/migrate_sqlite_to_profile.py` | runtime SQLite 到 profile 的迁移脚本 | 手工迁移、测试 | 保持原位；仅在 runtime 显式化阶段更新文档引用 | 否 | 不需要 | 保留 `tests/test_migrate_sqlite_to_profile.py` | 中 | 否 | 保持原脚本不变 |
| `backend/scripts/dev_selfcheck.py` | 离线跑真实 engine，自检 runtime 写入路径 | 开发自检 | 保持原位 | 否 | 不需要 | 保留脚本可编译；如未来切路径，补最小 smoke test | 中 | 否 | 保持原脚本不变 |
| `backend/scripts/dev_seed.py` | 初始化并填充 runtime demo 数据 | 开发演示 | 保持原位 | 否 | 不需要 | 保留可编译；如未来切路径，补最小 seed smoke test | 中 | 否 | 保持原脚本不变 |

## 3. `mapping_sqlite.py` 拆分方案

本节只写方案，不实施。

### 3.1 未来职责拆分

- metadata 在线查询
  - 当前主要是 `load_registered_result_tables()` 通过 `shared.db.router.select_sql_with_profile()` 查询 metadata。
  - 建议目标：`backend/svn_check/shared/lineage/metadata_query.py`
  - 风险：默认参数 `profile='czcb'` 已有现成测试约束，不能先动。
- SQLite cache 构建与读取
  - 当前主要是 `ensure_db_parent()`、`recreate_mapping_sqlite()`、`load_mapping_meta()`、`get_mapping_db_status()`。
  - 建议目标：`backend/svn_check/shared/lineage/cache_store.py`
  - 风险：`MAPPING_DB_PATH`、`lineage_edge`/`lineage_meta` 表结构、`source_xlsx_mtime_ns` 和 `source_xlsx_size` 新鲜度判断必须保持。
- Excel 导入能力
  - 当前主要是 `detect_header_row()`、`load_lineage_edges_from_xlsx()`。
  - 建议目标：`backend/svn_check/shared/lineage/xlsx_loader.py`
  - 风险：中文表头 alias、空行过滤、只取首个有效 sheet 的行为要先锁定测试。
- registered result tables 加载
  - 当前主要是 `normalize_registered_table_name()`、`load_registered_result_tables()`、`filter_registered_result_nodes()`。
  - 建议目标：`backend/svn_check/shared/lineage/registered_tables.py`
  - 风险：`profile='czcb'`、结果去重、大写归一化、去掉空格后缀的行为不能先改。
- lineage 遍历算法
  - 当前主要是 `parse_input_table_name()`、`normalize_identifier()`、`compact_identifier()`、`find_start_nodes_in_sqlite()`、`walk_downstream_in_sqlite()`。
  - 建议目标：`backend/svn_check/shared/lineage/traversal.py`
  - 风险：BFS 顺序、`max_depth` 语义、`relation_rows` 排序规则、`ordered_nodes` 排序规则要先有单测。
- 与 `audit.engine` 的兼容入口
  - 当前主要是模块级导入路径 `shared.lineage.mapping_sqlite`，以及 engine/fine/hcyt runner 对 `load_registered_result_tables()` 的调用假设。
  - 建议目标：保留 `backend/svn_check/shared/lineage/mapping_sqlite.py` 作为 compat facade。
  - 风险：不能先改 import；必须让旧模块继续导出原函数名。

### 3.2 必须先补测试的函数

- `detect_header_row()`
- `load_lineage_edges_from_xlsx()`
- `recreate_mapping_sqlite()`
- `get_mapping_db_status()`
- `find_start_nodes_in_sqlite()`
- `walk_downstream_in_sqlite()`
- `filter_registered_result_nodes()`
- `load_registered_result_tables()`

### 3.3 不能先动的默认参数

- `load_registered_result_tables(profile='czcb')`
- `filter_registered_result_nodes(..., profile='czcb')`
- `MAPPING_XLSX_PATH`
- `MAPPING_DB_PATH`
- `walk_downstream_in_sqlite(max_depth=None)` 的默认全量遍历语义

### 3.4 必须保持的 cache 行为

- 当 DB 文件不存在时，`load_mapping_meta()` 返回空 dict。
- `get_mapping_db_status()` 只基于 DB 是否存在、XLSX 是否存在、meta 是否存在、`mtime_ns` 和 `size` 判断 `is_fresh`。
- `recreate_mapping_sqlite()` 会重建 `lineage_edge` 和 `lineage_meta`，并写入 `imported_at`、`edge_count`、源文件路径与时间戳信息。
- SQLite cache 路径仍位于 `runtime/sqlite/mapping_lineage.db`，在兼容阶段不能擅自迁移。

### 3.5 必须保留的兼容导入路径

- `from shared.lineage.mapping_sqlite import load_registered_result_tables`
- `from shared.lineage import mapping_sqlite`
- 若未来拆分内部模块，`mapping_sqlite.py` 必须继续导出当前公共函数名，直到调用方全部切换且测试稳定。

## 4. `shared/db` 收敛为 shim 的方案

本节只写方案，不实施。

### 4.1 总体方向

目标不是删除 `shared/db`，而是让它逐步收敛为 metadata compat shim：外部仍走 `shared/db`，内部尽量复用 `backend/db` 的 profile、connection、sql_runner 能力。

### 4.2 哪些文件先保持原样

- `backend/svn_check/shared/db/router.py`
- `backend/svn_check/shared/db/postgres.py`
- `backend/svn_check/shared/db/gaussdb.py`
- `backend/svn_check/shared/db/__init__.py`

原因：

- 这些路径仍被 `audit_metadata_service.py`、`db_service.py`、`mapping_sqlite.py` 直接依赖。
- 当前没有针对 `shared/db` 的完整测试矩阵，直接合并会把 metadata 查询风险引入 runtime 层。

### 4.3 哪些函数可以逐步变成代理

- `router.get_backend(profile)`：继续保留，但内部只做 `db.profiles.resolve_profile()` 代理。
- `router.select_sql_with_profile(profile, sql_str)`：未来可代理到一个 metadata-safe runner。
- `router.run_sql_with_profile(profile, sql_str)`：未来可代理到一个 metadata-safe runner。
- `postgres.select_sql_with_profile()` / `gaussdb.select_sql_with_profile()`：未来可用 `backend/db/sql_runner.py` 或 `backend/db/connection.py` 封装执行。
- `postgres.run_sql_with_profile()` / `gaussdb.run_sql_with_profile()`：未来可代理到统一执行器。

### 4.4 哪些测试必须先覆盖

- router 按 `profile.type` 正确分派 PG / DWS。
- metadata 查询失败时，调用层仍能按现有降级约定工作。
- `profile=None` 时默认 profile 解析行为稳定。
- PG / DWS 对 `?`/`%s` 占位符差异不会误伤 metadata 查询。
- `audit_metadata_service.py` 端到端查询仍只读，不误写 runtime 表。

### 4.5 如何避免 metadata 查询和 runtime 持久化混淆

- `shared/db` 只承担 metadata compat 查询，不暴露 runtime 表 token 渲染接口给老调用方。
- 未来若复用 `backend/db/sql_runner.py`，也要通过单独的 metadata adapter 包装，避免调用方误传 `{{table:...}}` runtime token。
- 文档中持续强调：
  - `backend/db` 负责 runtime persistence。
  - `backend/svn_check/shared/db` 负责 metadata compat query。
  - 同一个 profile 解析入口不代表同一个 schema 语义。

## 5. metadata SQL 未来移动方案

本节只写方案，不实施。

### 5.1 建议目标位置

- 未来可引入 `backend/db/metadata/legacy_init/postgres_schema.sql`

该目标位置只表达“metadata 初始化资产被显式整理”，不表示与 runtime schema 合并。

### 5.2 原路径如何保留兼容

- `backend/svn_check/migrate/postgres_schema.sql` 在兼容阶段必须保留。
- 保留方式：
  - 首选：原路径继续保留同内容文件，并在文件头部或 README 标注“compat path”。
  - 次选：如果未来脚本允许读取新路径，原路径仍保留说明文件和同步策略，禁止立即删除。

### 5.3 `init_pg.py` 如何分阶段切换

- 阶段 A：仅补测试，`init_pg.py` 仍只读原路径。
- 阶段 B：`init_pg.py` 支持优先读新路径，找不到再回退原路径；日志中打印实际使用路径。
- 阶段 C：新路径成为默认路径，但原路径仍保留兼容文件。
- 阶段 D：只有在外部文档、脚本、测试全部切换后，才讨论是否将原路径降为纯兼容说明。

### 5.4 为什么不能和 `backend/db/sql/*/schema.sql` 合并

- runtime schema 负责平台运行期 5 张 runtime 表及其迁移契约。
- metadata init SQL 负责 `svn_check` 兼容元数据表初始化。
- 两者变更频率、调用入口、回滚对象、测试焦点都不同。
- runtime schema 还受 `tables.py` 与 `migrate_runtime_tables.sql` 共同约束；metadata init SQL 不受这一套 token/migration contract 约束。
- 直接合并会让 runtime 持久化与 metadata 初始化互相污染，回滚粒度也会失控。

### 5.5 如何验证 metadata 初始化不受影响

- 脚本层验证 `init_pg.py` 打印的 profile 和 schema 不变。
- 初始化后校验 `EXPECTED_TABLES` 全部存在。
- 在 PG / DWS 两种 profile 下分别跑 metadata 初始化 smoke test。
- 保持 `D:\miniconda3\python.exe -m compileall backend` 和全量单测通过。

## 6. `shared/graph` 归档评估方案

本节只写方案，不实施。

### 6.1 当前结论边界

- 当前只能写成“未发现主流程引用的候选遗留模块”。
- 不能写成“确定无用”。
- 不能直接删除 `backend/svn_check/shared/graph`。

### 6.2 归档前必须做的引用扫描

- `rg` 扫描代码、测试、脚本、文档中的 `shared.graph`、`dependency.py`、函数名引用。
- 检查运行期动态导入、字符串反射、文档脚本示例是否还会触达该路径。
- 检查是否存在工作区外部调用约定；若无法确认，则维持候选遗留状态。

### 6.3 归档后需要保留的说明

- 目录级 README，说明：
  - 该模块未纳入当前主流程。
  - 归档原因是“未发现主流程引用”，不是“证明无用”。
  - 如外部仍有调用，应回退归档并恢复兼容导入。
- 若未来移动到归档目录，原路径至少保留 README 或薄兼容文件，告知新位置。

### 6.4 如果未来发现仍有引用，如何回滚

- 恢复原路径文件或兼容代理。
- 将归档说明改回“候选遗留，继续保留”。
- 补新增引用场景的测试或最小复现用例。
- 在回滚提交中明确标注“误判主流程引用，恢复兼容路径”。

## 7. 分阶段执行计划

### 阶段 1. metadata SQL 兼容路径准备

- 目标：为 metadata init SQL 未来移动建立兼容路径和测试基线。
- 允许修改的文件类型：文档、测试、脚本路径解析逻辑。
- 禁止事项：不改 metadata 表结构；不改 runtime schema；不删原 SQL 路径。
- 需要新增或保留的测试：
  - `init_pg.py` 读取路径测试。
  - `EXPECTED_TABLES` 存在性测试。
  - PG / DWS metadata 初始化 smoke test。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：`init_pg.py` 切回只读原路径，保留原 SQL 为唯一入口。
- 是否建议单独 commit：是。

### 阶段 2. `shared/graph` 引用扫描和归档预案

- 目标：确认 `shared/graph` 仅能标注为候选遗留，并形成归档说明模板。
- 允许修改的文件类型：文档、README、测试。
- 禁止事项：不删除 `shared/graph`；不改主流程导入。
- 需要新增或保留的测试：
  - 如保留算法单测，则补图构建和 cycle 检测最小单测。
  - 保留主流程全量单测，确保无隐式依赖破坏。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：撤回归档 README 或候选说明，恢复“保留现状”。
- 是否建议单独 commit：是。

### 阶段 3. `shared/db` shim 化预案

- 目标：先补测试，再让 `shared/db` 内部逐步代理 `backend/db` 公共能力。
- 允许修改的文件类型：测试、文档、`shared/db` 内部实现。
- 禁止事项：不改变对外函数名；不把 metadata 查询和 runtime token 渲染混用；不删除 `shared/db`。
- 需要新增或保留的测试：
  - router 分派测试。
  - PG / DWS 查询一致性测试。
  - metadata 查询异常降级测试。
  - `audit_metadata_service.py` 端到端回归。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：恢复 `shared/db/postgres.py` 和 `gaussdb.py` 的独立实现。
- 是否建议单独 commit：是。

### 阶段 4. `mapping_sqlite.py` 测试补强

- 目标：先把混合职责模块的现有行为锁定，再谈拆分。
- 允许修改的文件类型：测试、文档。
- 禁止事项：不拆模块；不改默认 profile；不改 cache 路径；不改 Excel 表头解析规则。
- 需要新增或保留的测试：
  - `load_registered_result_tables()` 默认 `czcb`。
  - `filter_registered_result_nodes()` 行为。
  - `recreate_mapping_sqlite()` 的表重建和 meta 写入。
  - `get_mapping_db_status()` 新鲜度判断。
  - `walk_downstream_in_sqlite()` BFS 和排序行为。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：测试回滚即可，生产代码不变。
- 是否建议单独 commit：是。

### 阶段 5. `mapping_sqlite.py` 职责拆分

- 目标：在 compat facade 保留的前提下，逐函数迁移到子模块。
- 允许修改的文件类型：`shared/lineage` 内部 Python、测试、文档。
- 禁止事项：不改旧导入路径；不删 `mapping_sqlite.py`；不改默认参数；不改 cache 行为。
- 需要新增或保留的测试：
  - 所有旧入口函数仍可从 `shared.lineage.mapping_sqlite` 导入。
  - engine/fine/hcyt 合同测试继续通过。
  - cache、Excel、traversal 子模块单测全部通过。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：compat facade 切回直接内联原实现，或恢复单文件版本。
- 是否建议单独 commit：是。

### 阶段 6. runtime DB 目录显式化

- 目标：仅在前述兼容层稳定后，再讨论 `backend/db` 内部目录显式化，如 `runtime/`、`metadata/`、`shared/` 语义整理。
- 允许修改的文件类型：`backend/db` 内部 Python、文档、测试。
- 禁止事项：不单点修改 `tables.py`、`schema.sql`、`migrate_runtime_tables.sql`；不改 `runtime_store` 行为；不改表名字段名。
- 需要新增或保留的测试：
  - runtime 初始化测试。
  - runtime store 行为回归。
  - SQL token 渲染回归。
  - 脚本 `dev_seed.py` / `dev_selfcheck.py` / `migrate_sqlite_to_profile.py` smoke test。
- 验收命令：
  - `git diff --check`
  - `D:\miniconda3\python.exe -m compileall backend`
  - `D:\miniconda3\python.exe -m unittest discover -s tests`
- 回滚策略：保留旧入口文件，恢复原目录导出。
- 是否建议单独 commit：是。

## 8. 高风险禁止项

- 禁止直接合并 runtime schema 和 metadata schema。
- 禁止直接删除 `shared/db`。
- 禁止直接删除 `mapping_sqlite.py`。
- 禁止直接删除 `shared/graph`。
- 禁止单点修改 `tables.py`、`schema.sql`、`migrate_runtime_tables.sql`。
- 禁止先改默认 profile 或 cache 行为。
- 禁止没有兼容壳就移动路径。
- 禁止把 metadata 查询适配层改造成 runtime 持久化入口。
- 禁止在测试未补齐前拆 `mapping_sqlite.py`。

## 9. 验收命令

本轮虽然只改文档，仍执行以下命令：

- `git diff --check`
- `D:\miniconda3\python.exe -m compileall backend`
- `D:\miniconda3\python.exe -m unittest discover -s tests`

## 10. 本轮产出边界

- 本轮新增文档：`docs/db_runtime_metadata_migration_plan.md`
- 本轮不迁移任何文件。
- 本轮不修改任何 Python 业务代码。
- 本轮不修改任何 import 路径。
- 本轮不修改任何数据库 schema SQL。
- 本轮不修改任何测试断言。
