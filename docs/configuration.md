# Configuration

项目数据库配置已收敛为单一 profile 驱动模式。

## 配置文件

- 模板文件：`backend/configs/database.example.yaml`
- 实际文件：`backend/configs/database.yaml`
- 可选环境变量：
  - `AUDIT_DATABASE_CONFIG`（绝对路径覆盖）
  - `CODE_AUDIT_DB_PROFILE`

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
## Audit business rules

Copy `backend/configs/audit_rules.example.yaml` to the ignored
`backend/configs/audit_rules.yaml`, or set `AUDIT_RULES_CONFIG` to an absolute
YAML path. It contains declarative, non-secret HCYT, DWS, NUPS, FineReport,
workflow, and input-classification rules. Rules are process-cached. Missing or
invalid YAML logs a non-sensitive warning and falls back safely: display
highlighting is empty, calendar labels retain raw values, and audit decisions
keep built-in compatibility defaults. Never put SQL, passwords, tokens, JDBC
URLs, connection strings, or arbitrary paths in this file.

## Profile metadata mappings

Schema/table/column identifiers belong in each database profile's `metadata`
section in `backend/configs/database.yaml`; see the example. SQL templates stay
in code and only identifiers matching `[A-Za-z_][A-Za-z0-9_]*` are rendered.
Invalid mappings safely fall back to built-in compatibility values. The active
profile is used for registered result-table queries; `czcb` is not implicit.
