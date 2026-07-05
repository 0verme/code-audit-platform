# Configuration

本文档说明项目主要配置文件、模板提交规则和敏感信息规范。

## 主要配置文件

| 文件 | 用途 | 是否应提交真实值 |
| --- | --- | --- |
| `frontend/.env.example` | 前端 API 地址模板 | 可以提交模板 |
| `frontend/.env` | 前端本地配置 | 不提交 |
| `backend/svn_check/configs/database.example.yaml` | 规则元数据库模板 | 可以提交模板 |
| `backend/svn_check/configs/database.yaml` | 真实数据库配置 | 不提交 |
| `backend/svn_check/configs/svn.example.yaml` | SVN 访问模板 | 可以提交模板 |
| `backend/svn_check/configs/svn.yaml` | 真实 SVN 访问配置 | 不提交真实值 |
| `backend/data/app.db` | SQLite 平台运行库 | 不提交 |

## 已有模板检查

- 已有 `frontend/.env.example`。
- 已有 `backend/svn_check/configs/database.example.yaml`。
- 本轮新增 `backend/svn_check/configs/svn.example.yaml`，用于替代公开文档中的真实 SVN 示例。
- 当前未发现 `audit_datasource.example.yaml`；代码中也未发现同名强依赖配置。当前版本暂未内置该模板。

## 前端配置

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://127.0.0.1:5000/api
```

如前后端经 Nginx 同域部署，可设置：

```text
VITE_API_BASE_URL=/api
```

## 数据库配置

模板文件：`backend/svn_check/configs/database.example.yaml`

真实文件：`backend/svn_check/configs/database.yaml`

支持通过 YAML 或环境变量配置：

- `SVN_CHECK_DB_BACKEND=postgres|gaussdb`
- `SVN_CHECK_PG_HOST`
- `SVN_CHECK_PG_PORT`
- `SVN_CHECK_PG_DB`
- `SVN_CHECK_PG_USER`
- `SVN_CHECK_PG_PASSWORD`
- `SVN_CHECK_PG_SCHEMA`

Postgres 用于规则引擎的元数据表，不是 Flask 平台运行库。平台任务、报告和演示数据默认写入 SQLite。

## SVN 配置

模板文件：`backend/svn_check/configs/svn.example.yaml`

真实文件：`backend/svn_check/configs/svn.yaml`

真实配置中可以填写部署环境可访问的仓库地址、账号和认证方式。公开仓库中只能保留示例地址，如 `https://svn.example.com/repos/demo/trunk`。

## 哪些内容可以提交

- `.example`、`.sample`、`.template` 后缀的配置模板。
- 使用 `127.0.0.1`、`localhost`、`example.com`、`demo_user`、`demo_db`、`demo_table`、`demo_system` 的示例值。
- 不含内部名称和真实地址的部署说明。
- 可重复执行的 DDL、空数据结构和 mock 结构。

## 哪些内容不能提交

- 真实数据库连接串、JDBC URL、DSN。
- 生产 IP、内网 IP、真实域名。
- 数据库账号、密码、token、cookie、SSH key。
- 真实 SVN、FTP、Git 地址。
- 大段真实业务系统名称、真实表名、真实字段名。
- 带真实人员、机构、客户、交易或资产信息的截图、日志、Excel、CSV、SQLite 数据库。

## 敏感信息规范

- 使用环境变量或部署机私有配置承载真实值。
- 配置模板只展示字段名和安全示例值。
- 文档中的命令示例使用 `example.com`、`127.0.0.1`、`localhost`。
- mock 数据使用 `demo_*` 命名，不复刻真实业务系统。
- 公开发布前扫描 Markdown、源码、配置、截图、SQLite、压缩包和历史提交。

## 公开发布前建议扫描

```powershell
rg -n -i "password|passwd|token|secret|cookie|jdbc|dsn|ftp|svn://" .
rg -n "\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b" .
```

命中结果需要人工判断。不要把真实命中值复制到公开文档、issue 或 PR 描述中。
