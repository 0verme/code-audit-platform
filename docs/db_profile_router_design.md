# DB Profile / DB Router 统一设计

适用 round：P0-4。本文只做设计，不修改旧平台或新平台业务代码，不迁移真实配置。

## 只读盘点结论

### 旧平台 DB Profile

涉及文件：

| 文件 | 职责 |
|---|---|
| `services/db_profile.py` | 读取上层 `configs/audit_datasource.yaml`，解析 active audit profile，并提供 backend 判断函数。 |
| `services/db_service.py` | 旧平台统一 SQL 查询入口，按 active profile 和 legacy profile 参数分发到 Postgres native 或 Gauss JDBC。 |
| `services/audit_metadata_service.py` | 元数据查询服务，封装词根、视图、函数、参数表、outfile、recv mapping、结果表来源系统等查询。 |
| 上层 `configs/audit_datasource.yaml` | audit profile 解析配置，包含 resolver、profiles、backend、dialect、capabilities 等结构。 |
| 上层 `configs/database.yaml` | Gauss JDBC profile 配置，包含 defaults、profiles、driver、jar path、JDBC 连接项等结构。 |

函数清单：

| 文件 | 函数 |
|---|---|
| `services/db_profile.py` | `load_audit_datasource_config()`, `get_active_audit_profile_name()`, `get_active_audit_profile()`, `get_active_backend()`, `is_postgres_profile()`, `is_gauss_jdbc_profile()` |
| `services/db_service.py` | `select_sql(sql, profile='czcb')` |
| `services/audit_metadata_service.py` | `_get_gauss_profile_name()`, `_normalize_single_column_rows()`, `list_term_roots()`, `list_view_names()`, `list_function_names()`, `list_para_table_names()`, `list_upstream_system_ids()`, `list_job_outfiles()`, `list_result_table_sys_names()` |

配置项类型：

- `audit_datasource.yaml`：resolver 类配置、profile 映射、backend 类型、legacy `db_profile` 引用、dialect、capabilities、Postgres 本地连接字段引用。
- `database.yaml`：JDBC defaults、JDBC profiles、driver、jar path、连接 URL、账号、密码。
- 敏感字段只应被读取，不应进入文档、日志、报告 JSON 或仓库示例。

profile 语义：

- `audit profile` 是审计元数据访问的运行时画像，不等同于单个数据库连接串。
- active profile 通过环境变量优先选择，其次按应用环境映射，最后 fallback。
- profile 同时表达 backend、方言能力、是否使用 legacy JDBC profile、是否是本地演示数据源。

backend 类型判断逻辑：

- 旧平台用 `get_active_backend()` 读取 active profile 的 `backend`。
- `is_postgres_profile()` 判断 backend 是否为 Postgres native。
- `is_gauss_jdbc_profile()` 判断 backend 是否为 Gauss JDBC。
- metadata service 内部按该判断选择 Postgres SQL 或 Gauss JDBC SQL。

Postgres / Gauss / JDBC profile 差异：

- Postgres native profile 直接携带本地连接字段或环境变量引用，查询结果在服务层做大小写、单列结果归一。
- Gauss JDBC profile 不直接携带 JDBC 连接细节，而是通过 `db_profile` 指向 `database.yaml` 中的 legacy profile。
- Gauss JDBC 依赖 JDBC driver、jar path、JVM/JDBC 桥；Postgres native 依赖 psycopg 类驱动。
- 两者 SQL 方言存在差异，尤其是系统目录、schema 过滤、分区目录、函数/视图查询等。

依赖 active profile 的地方：

- `services/db_service.py` 的 Postgres/Gauss 分支。
- `services/audit_metadata_service.py` 的全部查询函数。
- 间接依赖元数据查询的 `core/public_data.py`、规则函数、宽表链路摘要和报告字段生成逻辑。

敏感配置风险：

- 上层 `audit_datasource.yaml` 和 `database.yaml` 存在真实连接配置风险。
- 旧平台 JDBC profile 中的连接 URL、账号、密码属于高敏感配置。
- Postgres profile 中的主机、端口、库名、账号、密码环境变量映射也应按敏感配置处理。
- 异常日志不能打印 DSN、JDBC URL、账号、密码、token、内网地址或真实连接串。

### 新平台 DB Router

涉及文件：

| 文件 | 职责 |
|---|---|
| `backend/svn_check/shared/db/router.py` | 当前 DB router 入口，按环境变量或 `configs/database.yaml` 的 backend 选择 Postgres 或 GaussDB adapter。 |
| `backend/svn_check/shared/db/postgres.py` | Postgres adapter，读取 `database.yaml` 的 postgres 段并允许环境变量覆盖。 |
| `backend/svn_check/shared/db/gaussdb.py` | GaussDB JDBC adapter，读取 `database.yaml` 中 defaults 和 profiles，使用 JDBC 桥执行查询。 |
| `backend/svn_check/services/db_service.py` | 新平台查询降级保护层，把 adapter 返回的 `None` 归一为空列表。 |
| `backend/svn_check/configs/database.yaml` | 当前随包配置，包含全局 backend、postgres 段、JDBC defaults 和 profiles。 |
| `backend/svn_check/core/public_data.py` | 当前业务口径查询函数，直接拼 SQL 并调用 `services.db_service.select_sql()`。 |
| `backend/svn_check/services/audit_metadata_service.py` | 当前不存在，P0-5 可新增。 |

当前 DB router 入口：

- `shared/db/router.py:get_backend()` 读取 `SVN_CHECK_DB_BACKEND`，否则读取 `configs/database.yaml` 的 `backend`，失败时默认 GaussDB。
- `select_sql_with_profile(profile, sql_str)` 和 `run_sql_with_profile(profile, sql_str)` 是对外兼容入口。

当前 Postgres / GaussDB 适配方式：

- Postgres adapter 暴露 `select_sql_with_profile()` / `run_sql_with_profile()`，但 profile 参数只用于兼容签名，实际使用单库配置。
- GaussDB adapter 暴露同名函数，profile 参数用于从 `profiles` 中选择 JDBC profile。
- router 只按 backend 选择 adapter，不理解 audit profile 语义。

配置读取方式：

- router 读取全局 backend。
- Postgres adapter 读取 postgres 段，并允许环境变量覆盖连接字段。
- GaussDB adapter 合并 defaults 和 profiles，并补默认 driver、jar path。
- 当前 `database.yaml` 同时承担示例、本地、运行时连接配置职责，后续应拆分安全边界。

查询函数调用链：

`core/public_data.py` -> `services/db_service.py` -> `shared/db/router.py` -> `shared/db/postgres.py` 或 `shared/db/gaussdb.py`

降级和异常处理方式：

- router 读取 backend 失败时回退 GaussDB。
- Postgres / GaussDB adapter 查询失败时返回 `None` 或 `False`，同时当前实现会打印异常。
- `services/db_service.select_sql()` 将 `None` 归一为空列表，避免规则函数迭代时报错。
- 后续应把异常日志统一改为仅包含 profile 名称、backend 类型和错误类别，不包含连接细节。

与旧平台 profile 模型的差异：

- 旧平台先解析 audit profile，再按 backend 与 dialect 做语义分流。
- 新平台先按全局 backend 选 adapter，再把 legacy profile 名称透传给 adapter。
- 旧平台 metadata service 已屏蔽部分方言差异；新平台 public_data 仍直接持有 SQL 和业务口径。
- 旧平台配置路径依赖上层仓库；新平台配置随包部署，敏感配置入仓风险更直接。

## 1. 设计目标

统一 DB Profile / DB Router 的目标：

- 保留旧平台 DB Profile 语义：active profile、backend、dialect、capabilities、demo/local/production 差异。
- 保留新平台 DB Router 语义：统一入口、adapter 分发、查询降级、可替换后端。
- 为 P0-5 的 audit metadata service 和宽表链路摘要提供稳定的元数据访问层。
- 不能把旧平台真实配置直接搬到新平台。
- 不能在规则函数里散落数据库类型判断逻辑。
- 报告 JSON、前端展示、日志中均不得暴露连接细节。

## 2. 名词定义

- `audit profile`：审计元数据访问画像，描述当前运行应使用哪个 backend、方言、能力集和安全配置引用。
- `backend`：数据库后端类型，例如 `postgres` 或 `gauss_jdbc`。
- `db router`：新平台统一分发层，根据 active audit profile 选择具体 adapter。
- `metadata service`：元数据查询语义层，提供词根、视图、函数、outfile、recv mapping、sys names 等业务查询函数。
- `runtime config`：运行时配置集合，来自环境变量、本地安全配置或 demo fallback，不等同于仓库示例。
- `demo profile`：仓库可保留的无敏感演示 profile，只允许指向本地 mock、空实现或占位环境变量。
- `local_pg`：本地 Postgres profile 名称，适合开发或测试，不应包含真实连接值。
- `gauss_jdbc`：通过 JDBC profile 访问 GaussDB 的 backend 类型。
- `postgres`：通过 Postgres native driver 访问元数据的 backend 类型。

## 3. 配置优先级

推荐加载优先级：

1. 环境变量：用于选择 active profile、DSN、账号、密码、JDBC URL、driver/jar 覆盖等敏感或部署相关配置。
2. 新平台安全配置文件：部署时挂载，不提交仓库，例如本地私有 `database.local.yaml` 或集群 secret 渲染文件。
3. demo / local fallback：仓库内只允许保留脱敏示例、disabled profile、本地空口径或 mock 配置。
4. 空实现降级：配置缺失、驱动缺失、连接失败或元数据表缺失时返回空集合，不中断审计主流程。

允许进入仓库：

- profile 名称、backend 类型、enabled 默认值、能力开关、环境变量名、脱敏示例。
- 业务表名和查询语义说明，例如 `dwp.p_job_hjj`。
- `database.example.yaml` 或文档示例。

只能放本地或部署 secret：

- 真实主机、端口、库名、schema 连接细节、JDBC URL、账号、密码、token、driver 私有路径。
- 生产、测试、内网环境的真实 profile 值。

只能通过环境变量或 secret 注入：

- DSN、JDBC URL、密码、token、临时凭证。
- 生产 active profile 选择值。

## 4. 推荐配置结构

脱敏示例：

```yaml
resolver:
  active_profile_env: AUDIT_DB_PROFILE
  app_env_env: APP_ENV
  default_by_env:
    local: local_pg
    demo: demo_empty
    prod: gauss_prod
  fallback: demo_empty

profiles:
  demo_empty:
    backend: empty
    enabled: true
    dialect: generic
    capabilities:
      partition_catalog: false
      live_catalog_truth: false

  local_pg:
    backend: postgres
    enabled: true
    dsn_env: AUDIT_LOCAL_PG_DSN
    schema_env: AUDIT_LOCAL_PG_SCHEMA
    dialect: postgres
    capabilities:
      partition_catalog: false
      live_catalog_truth: false

  gauss_prod:
    backend: gauss_jdbc
    enabled: false
    dsn_env: AUDIT_GAUSS_DSN
    jdbc_profile_env: AUDIT_GAUSS_PROFILE
    dialect: gaussdb
    capabilities:
      partition_catalog: true
      live_catalog_truth: true
```

约束：

- 示例不得写真实 IP、真实域名、真实库名、真实账号、真实密码、真实端口或真实连接串。
- profile 可以引用环境变量名，但不能包含环境变量值。
- `enabled: false` 可用于生产 profile 的仓库占位，实际启用由部署配置覆盖。

## 5. 统一接口设计

建议后续新平台暴露以下接口：

| 接口 | 归属 | 说明 |
|---|---|---|
| `get_active_audit_profile_name()` | router/profile resolver | 兼容旧平台 active profile 语义，只返回 profile 名称。 |
| `get_active_backend()` | router/profile resolver | 兼容旧平台 backend 判断语义，但 backend 值以新平台统一枚举为准。 |
| `get_metadata_connection()` | router/adapter | 以新平台 router 为准，返回后端连接或上下文；不向规则函数暴露。 |
| `run_metadata_query()` | metadata service 或 router | 统一查询入口，负责降级、日志脱敏、方言选择。 |
| `list_term_roots()` | metadata service | 迁移旧平台语义，用于词根缺失检查。 |
| `list_view_names()` | metadata service | 迁移旧平台语义，用于视图识别。 |
| `list_function_names()` | metadata service | 迁移旧平台语义，用于函数识别。 |
| `list_job_outfiles()` | metadata service | 迁移旧平台语义，用于 outfile 和宽表链路。 |
| `list_result_table_sys_names()` | metadata service | 迁移旧平台语义，用于来源系统标注。 |

兼容旧平台语义：

- active profile 选择。
- backend 判断。
- metadata 查询函数的返回形态尽量保持 list of tuple。
- 元数据不可用时降级为空集合。

以新平台 router 为准：

- adapter 选择、连接创建、异常处理、日志策略。
- backend 枚举统一为 `postgres`、`gauss_jdbc`、`empty`，不继续扩散旧名称。
- 配置加载优先级和安全边界。

不建议迁移的旧函数或模式：

- 不建议原样迁移 `is_postgres_profile()` / `is_gauss_jdbc_profile()` 到规则函数使用。
- 不建议迁移规则层直接拼接 backend 判断的模式。
- 不建议让 `db_service.select_sql(sql, profile='czcb')` 继续承担 metadata 语义。
- 不建议把旧平台 `database.yaml` 真实 profiles 复制到新平台。

应该合并到 metadata service 的函数：

- `core/public_data.py` 中所有元数据表集合查询函数。
- 旧平台 `audit_metadata_service.py` 中 list 系列函数。
- P0-5 宽表链路摘要需要的 outfile、recv mapping、sys names 查询。

## 6. 调用链建议

推荐调用链：

规则函数
-> `core/public_data.py`
-> `services/audit_metadata_service.py`
-> `shared/db/router.py`
-> `shared/db/postgres.py` 或 `shared/db/gaussdb.py`

分层职责：

- 规则函数不直接关心数据库类型。
- `core/public_data.py` 只保留业务口径和返回结构兼容，不承担连接选择。
- `services/audit_metadata_service.py` 负责元数据查询语义、SQL 方言选择、结果归一和降级。
- `shared/db/router.py` 负责 active profile 解析、backend 选择、adapter 分发和脱敏日志上下文。
- `shared/db/postgres.py` / `shared/db/gaussdb.py` 只处理各自连接方式和方言执行差异。

## 7. P0-5 落地约束

P0-5 可以做：

- 新增 `backend/svn_check/services/audit_metadata_service.py`。
- 逐函数迁移旧平台 metadata 查询。
- 增加 mock DB 或空实现测试。
- 让宽表链路摘要通过 metadata service 获取 outfile、recv mapping、sys names。

P0-5 不允许做：

- 整文件覆盖 `core/public_data.py`。
- 真实配置入仓。
- 把 DSN、JDBC URL、账号、密码、token、内网地址写入报告 JSON、日志、文档或注释。
- 让规则函数直接判断 Postgres/GaussDB。

强制降级要求：

- 元数据查询失败必须降级为空集合或空摘要，不中断审计主流程。
- 报告 JSON 不能输出连接信息。
- 日志只能输出 profile 名称、backend 类型、查询语义名称和错误类别，不能输出 DSN、JDBC URL 或连接参数。

## 8. 风险与回滚

| 风险 | 影响 | 处理策略 |
|---|---|---|
| 旧平台配置路径依赖上层仓库 | 迁移时容易误复制真实配置 | 只迁移 schema 和语义，不迁移值。 |
| 新平台配置随包部署 | 真实配置入仓风险更高 | 仓库只保留 example 和环境变量名。 |
| GaussDB / Postgres 方言差异 | 元数据查询结果不一致 | 方言 SQL 留在 metadata service 或 adapter，不进入规则函数。 |
| 本地 demo 和生产配置差异 | 本地可用不代表生产可用 | 引入 `empty` / `demo` profile，生产启用必须由部署配置覆盖。 |
| 敏感配置泄露 | 安全风险高 | 文档、日志、报告统一脱敏；验证阶段扫描敏感关键词和连接形态。 |
| 元数据表缺失 | 审计任务失败或报告缺字段 | 所有 list 查询失败时返回空集合，并记录脱敏 warning。 |

回滚方式：

- P0-4 仅回滚设计文档。
- P0-5 若实现异常，可禁用 metadata service 接入，保留空实现降级。
- 生产切换失败时回退 active profile 到 `demo_empty` 或本地安全 fallback，不回退业务规则代码。

## 9. 实施路线

- P0-5A：新增 metadata service 空壳和降级实现。
- P0-5B：迁移 `list_term_roots` / `list_view_names` / `list_function_names`。
- P0-5C：迁移 outfile / recv mapping / sys names 查询。
- P0-5D：接入 wide table lineage summary。
- P0-5E：补测试和 mock DB。
