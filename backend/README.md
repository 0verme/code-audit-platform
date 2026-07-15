# Code Audit Platform Backend

该后端采用统一品牌化 Flask 模板，同时保留现有审计业务、API 路径、请求/响应字段与数据库 profile 能力。

## 目录

- `app/__init__.py`：App Factory、Blueprint 注册、CORS、请求日志和统一错误处理。
- `app/routes/`：HTTP 参数读取、基础校验和响应转换。
- `app/services/`：任务、运行、结果、报告与源码下载的业务编排，不依赖 Flask request/session。
- `app/modules/audit/`：HCYT、NUPS、FineReport、AI、规则、工作流和报告领域代码。
- `app/modules/lineage/`、`app/modules/metadata/`：血缘与元数据领域代码。
- `app/db/`：SQLite、PostgreSQL、DWS/GaussDB profile、连接和运行期存储。
- `app/migrations/`、`migrations/`：迁移 runner 与三方言版本化 SQL。
- `scripts/`：运维及开发脚本；`tests/`：新架构单元和集成测试。

## 启动

在 `backend` 目录创建虚拟环境并安装依赖：

```powershell
python -m pip install -r requirements.txt
python run.py
```

生产环境可使用 WSGI 服务器加载 `run:app`：

```powershell
waitress-serve run:app
```

现有 `scripts/start_backend.ps1` 和 `scripts/start_backend.cmd` 均调用唯一入口 `run.py`。

## 环境变量

- `AUDIT_HOST`、`AUDIT_PORT`、`AUDIT_DEBUG`：监听地址、端口和调试开关。
- `AUDIT_CORS_ORIGINS`：逗号分隔的可信来源；禁止 `*`。
- `AUDIT_LOCAL_SOURCE_ENABLED`：是否允许本地源码审计，默认关闭。
- `AUDIT_LOCAL_SOURCE_ROOTS`：允许根目录列表，支持 JSON 数组或系统路径分隔符。
- `AUDIT_DATABASE_CONFIG`、`CODE_AUDIT_DB_PROFILE`：数据库配置路径与 profile。
- `AUDIT_LOG_LEVEL`：日志级别。

`backend/.env` 仅用于本地开发；加载使用 `setdefault` 语义，不覆盖进程已注入变量。不要提交 `.env`、密钥或真实连接串。

## 数据库迁移

迁移不会在应用启动时自动执行：

```powershell
python scripts/schema_migrate.py status
python scripts/schema_migrate.py apply
```

`0001` 是 SQLite、PostgreSQL、DWS 的现有 schema 基线。runner 记录版本、名称、校验和、时间和耗时；重复 `apply` 不会重复执行已登记版本。

## 验证

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check app tests
python -m compileall -q app tests
```
