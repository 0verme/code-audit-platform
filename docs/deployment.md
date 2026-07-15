# Deployment Guide

## HTTP runtime security

Set `AUDIT_HOST`, `AUDIT_PORT`, and `AUDIT_DEBUG` explicitly for a deployment.

For local or single-machine deployments, these values may also be placed in
`backend/.env`; `backend/app.py` loads that file automatically. Process/system
environment variables always override `.env` values. Do not deploy or commit
`backend/.env`; use `backend/.env.example` as the template.
Their defaults are `127.0.0.1`, `5088`, and `false`. Configure
`AUDIT_CORS_ORIGINS` as a comma-separated list of exact frontend origins; the
default is an empty allowlist and wildcard origins are rejected. Keep
`AUDIT_LOCAL_SOURCE_ENABLED=false` in production. If a private development
deployment needs local workspaces, it must also set `AUDIT_LOCAL_SOURCE_ROOTS`
to existing allowed roots (a JSON array is recommended, especially on Windows).

## 数据库部署原则

- 整个平台只能选择一套数据库：
  - 全量 PostgreSQL
  - 全量 DWS
- 平台运行表和元数据查询必须使用同一个 profile
- 启动时不会再创建或回退到 SQLite

## 准备配置

```bash
cp backend/configs/database.example.yaml backend/configs/database.yaml
cp backend/configs/svn.example.yaml backend/configs/svn.yaml
```

编辑 `backend/configs/database.yaml`，只保留一个实际使用的 profile，并让 `default_profile` 指向它。

示例：

```yaml
default_profile: prod_pg

profiles:
  prod_pg:
    type: postgresql
    host: 10.0.0.10
    port: 5432
    database: code_audit
    username: code_audit_app
    password: change_me
    schema: dwp
```

## 初始化元数据表

`backend/init_pg.py` 现在会直接读取当前活动 profile，并在该库上执行元数据 DDL。

```bash
cd backend
python init_pg.py
```

## 启动后端

```bash
cd backend
python app.py
```

如果 profile 缺失、类型非法或字段不完整，进程会直接报错退出，不会创建本地 SQLite 文件。

## 使用环境变量切换 profile

```bash
export CODE_AUDIT_DB_PROFILE=prod_pg
python backend/app.py
```

或：

```powershell
$env:CODE_AUDIT_DB_PROFILE = "prod_pg"
python backend\app.py
```

## 验证项

启动后确认：

1. 日志中没有 SQLite 创建或回退信息。
2. `projects`、`audit_tasks`、`audit_results`、`task_reports` 等运行表创建在当前 profile 的 `schema` 下。
3. 元数据查询也能在同一 profile 下访问 `dwp.p_*` 表。
