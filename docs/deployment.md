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

## Nginx reverse proxy

Production frontend builds use the same-origin API base `/api`. Install the
tracked Nginx template before enabling it:

```bash
sudo cp deploy/nginx/code-audit.conf /etc/nginx/sites-available/code-audit
sudo ln -sfn /etc/nginx/sites-available/code-audit /etc/nginx/sites-enabled/code-audit
sudo nginx -t
sudo systemctl reload nginx
```

The `proxy_pass` URL intentionally has no trailing slash. Flask registers its
routes under `/api/*`; adding a trailing slash would strip the `/api` prefix.
Verify both the backend listener and the public proxy after deployment:

```bash
curl -fsS http://127.0.0.1:5088/api/health
curl -fsS https://audit.overme.cn/api/health
curl -fsS "https://audit.overme.cn/api/publish-list?date=2026-08-01"
```

## Asset portal term roots

Term-root validation reads the asset portal API, rather than the audit
database. Set the existing `ASSET_PORTAL_BASE_URL` to the portal origin; it is
used both for audit-result links and for `GET /api/roots`. If the portal is
temporarily unavailable, the last in-process value is used. Set
`ASSET_PORTAL_ROOT_CACHE_FILE` to retain a JSON snapshot across restarts.
`ASSET_PORTAL_API_TOKEN` is optional and is sent as a Bearer token only when
configured. Do not commit a real token.

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

## DWS / GaussDB JDBC

DWS 使用 Huawei JDBC 驱动，而不是 PostgreSQL 的 psycopg 驱动。将部署方提供的
`gaussdb200.jar` 放在 `backend/resources/jars/gaussdb200.jar`，或在 profile 中通过
`jar_path` 指向该文件（也可用 `AUDIT_DWS_JAR_PATH` 覆盖）。示例配置保留对原有
`AUDIT_DWS_HOST`、`AUDIT_DWS_PORT`、`AUDIT_DWS_DATABASE`、`AUDIT_DWS_USER`、
`AUDIT_DWS_PASSWORD`、`AUDIT_DWS_SCHEMA` 环境变量的兼容，并自动生成：

```text
jdbc:gaussdb://<host>:<port>/<database>?currentSchema=<schema>
```

也可以在 profile 中直接设置 `jdbc_url`、`user`、`password`、`driver`、`jar_path`、
`connect_timeout`、`socket_timeout` 和 `statement_timeout_ms`。运行时会在 JDBC URL 中
补充未显式设置的 `loginTimeout`、`connectTimeout` 和 `socketTimeout` 参数。

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
export CODE_AUDIT_METADATA_DB_PROFILE=local_pg  # optional read-only metadata mirror
python backend/app.py
```

或：

```powershell
$env:CODE_AUDIT_DB_PROFILE = "prod_pg"
$env:CODE_AUDIT_METADATA_DB_PROFILE = "local_pg" # optional read-only metadata mirror
python backend\app.py
```

## 验证项

启动后确认：

1. 日志中没有 SQLite 创建或回退信息。
2. `projects`、`audit_tasks`、`audit_results`、`task_reports` 等运行表创建在当前 profile 的 `schema` 下。
3. 元数据查询也能在同一 profile 下访问 `dwp.p_*` 表。
## Audit-rule deployment

The tracked `backend/configs/audit_rules.yaml` is the complete, single source
of truth for audit business rules. Deploy it with the application, or set
`AUDIT_RULES_CONFIG` to another complete YAML file. Partial overrides are not
supported. Missing, malformed, incomplete, or incompatible rules block backend
startup and report the file and field path. Restart every backend process after
changing rules.

Do not put credentials, tokens, connection strings, arbitrary paths, or SQL in
this file. Put schema/table/column mappings under the selected database
profile's `metadata` key in `database.yaml`, not in audit-rule YAML.
