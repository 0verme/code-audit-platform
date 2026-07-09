# Configuration

项目数据库配置已收敛为单一 profile 驱动模式。

## 配置文件

- 模板文件：`backend/svn_check/configs/database.example.yaml`
- 实际文件：`backend/svn_check/configs/database.yaml`
- 可选环境变量：
  - `CODE_AUDIT_DB_CONFIG_PATH`
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
