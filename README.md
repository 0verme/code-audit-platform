# SQL Review Platform

面向数据开发和湖仓上线场景的 SQL 调度与代码审计平台，用于在发布前检查本次新增或变更内容中的 SQL、调度、依赖、字段映射、产出表和元数据一致性风险。

> 当前仓库仍包含历史迁移痕迹、演示数据和本地开发配置。公开发布或迁移部署前，请先执行 [公开发布前检查](docs/public_release_checklist.md)。

## 适用场景

- 数据仓库、湖仓、批处理链路上线前审查。
- SQL、Python、Shell、配置文件、调度清单等变更的集中检查。
- 产出表、上游依赖、调度依赖和元数据登记的一致性核对。
- 前端演示、离线规则回归、本地目录审计（需显式开启）和 SVN 工作区审计。
- 将审计结果转换为统一风险输出，供后续对接资产门户或工单系统。

## 核心能力

- **多工作流审计**：HCYT、NUPS、FineReport 三类工作流各自独立 runner，由统一 dispatcher 分发。
- **SQL / 调度 / 程序检查**：覆盖 SQL、DDL、Hive/DWS 类脚本、调度 Excel、加工程序、报表模板与数据集 SQL 等。
- **元数据辅助检查**：通过 `app/modules/metadata` 与数据库 profile 访问登记信息；外部库不可用时部分检查会降级。
- **依赖与血缘摘要**：`app/modules/lineage` 与规则层依赖分析，用于引用表识别和血缘子图展示。
- **统一风险输出**：报告中包含 `assetIssues` 与 `unifiedAssetIssues`，便于对接资产门户或工单；平台本身不强制依赖外部门户。
- **前端结果展示**：React/Vite 展示任务、进度、日志、风险分组和报表检查；`mock` / `api` 模式由构建环境配置决定。

## 架构概览

- **前端**：`frontend/`，React 18 + Vite。`VITE_AUDIT_DATA_MODE=mock|api` 决定使用本地演示数据或后端任务 API；API 地址由 `VITE_API_BASE_URL` 配置。
- **后端**：`backend/`，Flask App Factory（入口 `run.py` → `app.create_app`），提供 REST API 并异步执行审计任务。
- **平台运行库**：由 `backend/configs/database.yaml` 中的 **单一 DB profile** 驱动，类型为 `postgresql` 或 `dws`（GaussDB JDBC）。运行表与只读元数据默认共用同一 profile（可选只读元数据 profile）。
- **规则与工作流**：位于 `backend/app/modules/audit/`，按 `workflows/`（hcyt / nups / fine_report）、`core/`、`source/`、`shared/` 组织；部分顶层文件为兼容 re-export。
- **迁移**：版本化 SQL 在 `backend/migrations/`，通过 `python scripts/schema_migrate.py apply` 显式执行，**启动时不自动 migrate**。

更细的模块说明见 [架构文档](docs/architecture.md)。后端目录约定见 [backend/README.md](backend/README.md)。

## 目录结构

```text
.
├── backend/
│   ├── run.py                     # 唯一应用入口（开发与 WSGI 均加载此处）
│   ├── requirements.txt           # 后端运行依赖
│   ├── requirements-dev.txt       # pytest / ruff 等开发依赖
│   ├── configs/                   # database / svn / audit_rules 配置与 example 模板
│   ├── migrations/                # 三方言版本化 schema（sqlite 测试 / postgresql / dws）
│   ├── resources/jars/            # 可选 GaussDB JDBC 驱动
│   ├── scripts/                   # 启动、迁移、自检、种子数据等脚本
│   ├── tests/                     # 后端包内单元/集成测试
│   └── app/
│       ├── __init__.py            # create_app：Blueprint、CORS、请求日志（无任务状态副作用）
│       ├── settings.py            # 运行时安全与监听配置
│       ├── auth.py                # 权限扩展点（当前默认可放行，待接身份源）
│       ├── routes/                # HTTP 层
│       ├── services/              # 业务编排（不依赖 Flask request）
│       ├── db/                    # profile、连接、runtime store、方言 SQL
│       ├── config/                # 审计规则加载
│       └── modules/
│           ├── audit/             # 引擎、工作流、规则、来源解析、报告
│           ├── lineage/           # 血缘映射与遍历
│           └── metadata/          # 元数据服务与初始化 SQL
├── frontend/
│   ├── src/
│   │   ├── config/                # API、工作流、来源类型与展示配置
│   │   ├── hooks/                 # 任务轮询等
│   │   ├── pages/                 # 首页、结果页、血缘页等
│   │   ├── services/              # API client
│   │   ├── mock/                  # mock 演示数据
│   │   └── utils/                 # 展示与结果归一
│   ├── .env.example
│   └── package.json
├── tests/                         # 仓库根级回归用例（unittest）
├── docs/                          # 设计、部署、开发与发布文档
├── test-hcyt/ · test-NUPS/ · test-fine-report/   # 本地场景工作区样例
└── 静态原型代码/                   # 历史静态原型（非运行时）
```

## 快速开始

### 环境要求

- Python 3.10+，建议 3.11。
- Node.js 18+，npm 9+。
- 可访问的 **PostgreSQL** 或 **DWS/GaussDB**（按 profile 配置）；开发可用本机 Postgres。
- 如使用 SVN 审计，需本机安装 `svn` 命令行客户端并配置可访问的仓库。
- Git 来源**当前版本不支持**；前端与后端会明确拒绝。

### 安装后端依赖

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 准备配置文件

```powershell
copy backend\configs\database.example.yaml backend\configs\database.yaml
copy backend\configs\svn.example.yaml backend\configs\svn.yaml
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

将示例值替换为本地或测试环境配置。**不要**把真实账号、密码、token、内网 IP、生产 SVN 地址提交到仓库。

关键环境变量（详见 [配置说明](docs/configuration.md) 与 `backend/.env.example`）：

| 变量 | 说明 |
|------|------|
| `CODE_AUDIT_DB_PROFILE` | 运行库 profile 名 |
| `AUDIT_DATABASE_CONFIG` | 可选，覆盖 `database.yaml` 路径 |
| `AUDIT_CORS_ORIGINS` | 逗号分隔的前端 Origin，禁止 `*` |
| `AUDIT_LOCAL_SOURCE_ENABLED` | 是否允许本地目录审计，默认 `false` |
| `AUDIT_LOCAL_SOURCE_ROOTS` | 本地审计允许根目录（建议 JSON 数组） |
| `AUDIT_HOST` / `AUDIT_PORT` / `AUDIT_DEBUG` | 监听地址、端口（默认 `5088`）、调试开关 |

### 初始化数据库

迁移**不会**在应用启动时自动执行：

```powershell
cd backend
python scripts\schema_migrate.py status
python scripts\schema_migrate.py apply
```

如需初始化规则/元数据相关表（按当前活动 profile 执行 DDL），可参考：

```powershell
cd backend
python scripts\init_pg.py
# 或
python scripts\init_runtime_db.py
```

以脚本帮助信息与 [数据库迁移文档](docs/db_migration.md) 为准。

### 启动后端

推荐使用虚拟环境中的解释器（避免 WindowsApps 假 `python`）：

```powershell
cd backend
.\scripts\start_backend.ps1
```

或直接：

```powershell
cd backend
.\.venv\Scripts\python.exe run.py
```

生产可用 WSGI：

```powershell
cd backend
waitress-serve run:app
# 或 gunicorn -w 1 -b 127.0.0.1:5088 run:app
```

**重要：当前任务执行使用进程内线程 + 内存 registry。请保持单进程、单 worker。** 多 worker / 多实例没有 owner/lease 保证，可能重复执行或产生状态竞争。确认旧进程已停止后，使用 `python backend/scripts/recover_orphan_tasks.py` 做一次性孤儿任务恢复。详见 [架构文档 · 部署约束](docs/architecture.md#部署约束)。

默认监听 `http://127.0.0.1:5088`，健康检查：

```text
GET http://127.0.0.1:5088/api/health
```

`backend/.env` 仅用于本地开发；加载使用 `setdefault` 语义，不覆盖进程已注入变量。

### 启动前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

`.env` 中：

- `VITE_AUDIT_DATA_MODE=mock`：仅用本地演示数据，可不启动后端。
- `VITE_AUDIT_DATA_MODE=api`：提交审查走后端；接口失败会显示错误，**不会**静默降级为 mock。
- `VITE_API_BASE_URL`：开发期可设为 `http://127.0.0.1:5088/api`，同源反代生产可设为 `/api`。
- `VITE_ENABLE_LOCAL_SOURCE`：仅控制 UI 是否展示本地目录选项；真正放行需后端 `AUDIT_LOCAL_SOURCE_ENABLED` + `AUDIT_LOCAL_SOURCE_ROOTS`。

默认访问 Vite 地址，通常是 `http://127.0.0.1:5173`。

## 主要 API（摘要）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/projects` | 项目列表 |
| GET/POST | `/api/audit-tasks` | 任务列表 / 创建任务 |
| GET | `/api/audit-tasks/:id` | 任务详情 |
| GET | `/api/audit-tasks/:id/report` | 完整报告 JSON |
| GET | `/api/audit-tasks/:id/source-file` | 下载任务关联源文件 |
| GET | `/api/audit-tasks/:id/lineage/subgraph` | 任务血缘子图 |
| GET/POST | `/api/audit-runs` · `.../status` · `.../partial-result` | 运行创建与进度轮询 |
| GET | `/api/audit-results` | 审计明细 |
| GET | `/api/audit-configuration/workflows` 等 | 前端预检用配置（无密钥） |

创建任务支持 `Idempotency-Key` 请求头。权限装饰器已预留，**身份源接入前默认可放行**——仅适合可信内网。

## 常见部署方式

- **本地开发**：`backend` 下 `run.py` 或 `scripts/start_backend.ps1`；前端 `npm run dev`；配置 Postgres 或 DWS profile。
- **单机部署**：前端 `npm run build` 后由 Nginx 托管；后端 `waitress` / `gunicorn -w 1`；Nginx 将 `/api/` 反代到 Flask。
- **内网部署**：使用内网 Python/npm 镜像源；真实配置只放部署机或环境变量；本地目录审计默认关闭。
- **容器化**：当前版本未内置 Dockerfile / docker-compose，可按后续规划补充。

详细步骤见 [部署文档](docs/deployment.md)。

## 配置说明

- [配置说明](docs/configuration.md)
- `frontend/.env.example`
- `backend/.env.example`
- `backend/configs/database.example.yaml`
- `backend/configs/svn.example.yaml`
- `backend/configs/audit_rules.yaml`（随代码提交的完整非敏感审计规则）

数据库、SVN、`.env` 等包含环境信息的真实配置应保留在部署环境，不应提交到仓库；审计业务规则不含敏感信息，正式 YAML 直接纳入版本管理。

## 测试与回归

仓库根级用例（unittest）：

```powershell
python backend/scripts/run_backend_tests.py
```

后端包内测试与静态检查（在 `backend` 目录）：

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check app tests
python -m compileall -q app tests
```

前端：

```powershell
cd frontend
npm test
npm run build
```

运维自检脚本：`backend/scripts/dev_selfcheck.py`。更多命令见 [回归命令](docs/regression_commands.md)。

本地场景样例工作区见 `test-hcyt/`、`test-NUPS/`、`test-fine-report/` 下的 README。

## 安全与公开发布注意事项

- 不提交真实数据库连接串、生产 IP、账号密码、token、cookie。
- 不提交真实 SVN/FTP 地址或内部 Git 地址。
- 不在 README、截图、mock 数据中大段暴露真实系统名、真实表名、真实字段名。
- 生产保持 `AUDIT_LOCAL_SOURCE_ENABLED=false`、`AUDIT_DEBUG=false`，CORS 使用明确 Origin。
- 当前 API 默认无强认证，**不要**暴露到不可信网络。
- 公开发布前按 [发布检查清单](docs/public_release_checklist.md) 执行。

## Roadmap

- 统一配置加载与多环境配置示例（持续完善）。
- 补齐容器化部署文件和生产级启动脚本。
- 任务执行从进程内线程演进为租约/心跳或可靠队列，支持安全重启与单实例约束加固。
- 接入真实身份认证，使 `require_permission` 生效。
- 增强元数据同步任务的快照日期、失败重试和审计日志。
- 完善资产风险输出到外部门户、工单或消息系统的适配层。
- 收敛 audit 模块兼容 re-export，仅保留 `workflows` / `core` / `source` 主干路径。
- 补充 CI、端到端测试与安全扫描。

## 相关文档

| 文档 | 内容 |
|------|------|
| [docs/README.md](docs/README.md) | 文档索引 |
| [docs/architecture.md](docs/architecture.md) | 系统架构与数据流 |
| [docs/database_schema.md](docs/database_schema.md) | 当前数据库表结构 |
| [docs/deployment.md](docs/deployment.md) | 部署 |
| [docs/development.md](docs/development.md) | 开发环境与本地源配置 |
| [docs/configuration.md](docs/configuration.md) | 数据库 profile 等配置 |
| [docs/db_migration.md](docs/db_migration.md) | Schema 迁移 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献约定 |
| [SECURITY.md](SECURITY.md) | 安全策略 |

## License

本项目采用 [Apache License 2.0](LICENSE) 开源协议，完整协议文本见仓库根目录 [LICENSE](LICENSE) 文件。
