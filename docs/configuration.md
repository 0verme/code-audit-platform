# Configuration

项目数据库配置已收敛为单一 profile 驱动模式。

## 配置文件

- 模板文件：`backend/configs/database.example.yaml`
- 实际文件：`backend/configs/database.yaml`
- 可选环境变量：
  - `AUDIT_DATABASE_CONFIG`（绝对路径覆盖）
  - `CODE_AUDIT_DB_PROFILE`
  - `CODE_AUDIT_METADATA_DB_PROFILE`（可选，只读审计元数据；未配置时回退运行库 profile）

## 统一约束

- 只支持两种数据库类型：`postgresql`、`dws`
- 平台运行表与元数据查询共用同一个 profile
- 不再支持 `sqlite`
- 不再支持旧结构：
  - `backend: postgres|gaussdb`
  - `postgres:`
  - `defaults:`
  - `jdbc_url/user/password`

## 标准格式

```yaml
default_profile: local_pg

profiles:
  local_pg:
    type: postgresql
    host: 127.0.0.1
    port: 5432
    database: code_audit
    username: demo_user
    password: demo_password
    schema: dwp
```

每个 profile 必须包含以下字段：

- `type`
- `host`
- `port`
- `database`
- `username`
- `password`
- `schema`

## 切换方式

- 默认使用 `default_profile`
- 如需切换，设置 `CODE_AUDIT_DB_PROFILE=<profile-name>`
- 运行表和任务持久化始终由 `CODE_AUDIT_DB_PROFILE` 控制；`inner`/`production` 模式仍要求 `inner_dws`。
- 可设置 `CODE_AUDIT_METADATA_DB_PROFILE=local_pg`，让视图、函数、参数表、JOB outfile、来源系统、结果表目录等只读查询走本地 PostgreSQL 镜像。
- 镜像缺少 `dba_tab_partitions` 时配置 `metadata.partition_catalog: false`；仅分区目录查询会安全回退运行库 DWS。日志只记录 profile 名称、类型、回退标记、策略和耗时，不记录地址或凭据。

## 启动失败行为

以下情况会直接报错并终止启动：

- `default_profile` 指向不存在的 profile
- profile 缺少 `type`
- profile 缺少必填字段
- `type` 不是 `postgresql` 或 `dws`

错误信息会包含：

- 当前 profile 名称
- 缺失字段名
- 当前支持的 type 列表
## 审计业务规则

`backend/configs/audit_rules.yaml` 是 HCYT、DWS、NUPS、FineReport、工作流及输入分类规则的唯一事实来源，并随代码提交。Python 加载器不包含业务默认值，也不会把多份配置进行合并。

- 所有字段均为必填，`schema_version` 当前必须为 `1`。
- 空列表表示确实没有配置值，不表示继承或恢复默认值。
- 规则在进程内缓存；修改后需要重启所有后端进程。
- 可用 `AUDIT_RULES_CONFIG` 指定另一份 `.yaml`/`.yml` 文件，但该文件必须包含完整配置。
- 文件缺失、YAML 无法解析、存在未知或缺失字段、字段类型错误时，后端会直接启动失败；错误信息包含配置绝对路径和具体字段路径。

该文件只能包含非敏感声明式规则。不得写入 SQL、密码、Token、JDBC URL、连接串、生产凭据或任意文件系统路径。

## Profile metadata mappings

Schema/table/column identifiers belong in each database profile's `metadata`
section in `backend/configs/database.yaml`; see the example. SQL templates stay
in code and only identifiers matching `[A-Za-z_][A-Za-z0-9_]*` are rendered.
Invalid mappings safely fall back to built-in compatibility values. The active
profile is used for registered result-table queries; `czcb` is not implicit.
