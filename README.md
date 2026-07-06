# SQL Review Platform

面向数据开发和湖仓上线场景的 SQL 调度与代码审计平台，用于在发布前检查本次新增或变更内容中的 SQL、调度、依赖、字段映射、产出表和元数据一致性风险。

> 当前仓库仍包含历史迁移痕迹、演示数据和本地开发配置。公开发布或迁移部署前，请先执行 [公开发布前检查](docs/public_release_checklist.md)。

## 适用场景

- 数据仓库、湖仓、批处理链路上线前审查。
- SQL、Python、Shell、配置文件、调度清单等变更的集中检查。
- 产出表、上游依赖、调度依赖和元数据登记的一致性核对。
- 前端演示、离线规则回归、本地目录审计和 SVN 工作区审计。
- 将审计结果转换为统一风险输出，供后续对接资产门户或工单系统。

## 核心能力

- **SQL 审计**：规则引擎位于 `backend/svn_check/core`，覆盖 SQL、DDL、Hive/DWS 类脚本、报表数据集 SQL 等检查。
- **调度/作业检查**：结合调度 Excel、作业元数据和加工程序，核对作业、程序、依赖和禁用状态。
- **元数据辅助检查**：`backend/svn_check/services/audit_metadata_service.py` 和 `shared/db` 提供元数据访问边界；外部数据库不可用时部分检查会降级。
- **上游/下游依赖分析**：`shared/graph`、`shared/lineage` 和 `services/re_service.py` 负责依赖汇总、引用表识别和血缘摘要。
- **统一风险输出**：后端报告中包含 `assetIssues` 与 `unifiedAssetIssues`，用于描述资产问题和未来外部系统适配边界；当前平台运行不强依赖外部资产门户。
- **前端结果展示**：React/Vite 前端展示任务、进度、日志、风险分组和报表检查；mock/API 执行模式由构建环境配置决定。

## 架构概览

- **前端**：`frontend/`，React 18 + Vite，通过 `VITE_AUDIT_DATA_MODE=mock|api` 决定使用本地演示数据或后端任务 API，API 地址由 `VITE_API_BASE_URL` 配置。
- **后端**：`backend/`，Flask 提供 REST API，`backend/engine.py` 编排真实规则引擎并异步执行审计任务。
- **平台运行库**：默认使用 SQLite，文件位于 `backend/data/app.db`，首次启动由 `backend/database.py` 自动建表并写入演示数据。
- **规则元数据库**：规则引擎可连接 Postgres 或 GaussDB 类元数据库；Postgres 初始化脚本位于 `backend/svn_check/migrate/postgres_schema.sql`。
- **脚本/定时任务**：当前仓库没有独立 `jobs/` 或 crontab 目录；元数据同步可按部署环境另行补充，并将快照日期写入同步结果或日志。
- **可选元数据同步**：元数据是增强审计效果的数据准备层，不是前后端启动的强依赖。

## 目录结构

```text
.
├── backend/
│   ├── app.py                         # Flask API 入口
│   ├── database.py                    # SQLite 平台运行库初始化
│   ├── engine.py                      # 审计任务编排与报告生成
│   ├── init_pg.py                     # Postgres 元数据表初始化脚本
│   ├── requirements.txt               # 后端依赖
│   └── svn_check/
│       ├── configs/                   # 数据库、SVN 等配置模板/配置
│       ├── core/                      # SQL/调度/报表等规则
│       ├── migrate/postgres_schema.sql
│       ├── services/                  # SVN、元数据、AI、诊断等服务边界
│       └── shared/                    # DB、血缘、图依赖等共享能力
├── frontend/
│   ├── src/
│   │   ├── config/                    # API 地址配置
│   │   ├── mock/                      # 前端 mock 数据
│   │   ├── pages/                     # 页面
│   │   ├── services/                  # API client
│   │   └── styles/                    # 样式
│   ├── .env.example
│   └── package.json
├── tests/                             # unittest 回归用例
├── docs/                              # 设计、部署、开发和发布文档
└── 静态原型代码/                       # 历史静态原型资料
```

## 快速开始

### 环境要求

- Python 3.10+，建议 3.11。
- Node.js 18+，npm 9+。
- 本地开发默认不需要外部数据库；规则元数据检查需要 Postgres 12+ 或按实际环境配置 GaussDB/JDBC。
- 如使用 SVN 审计，需要本机安装 `svn` 命令行客户端并配置可访问的仓库地址。

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
copy backend\svn_check\configs\database.example.yaml backend\svn_check\configs\database.yaml
copy backend\svn_check\configs\svn.example.yaml backend\svn_check\configs\svn.yaml
copy frontend\.env.example frontend\.env
```

将示例值替换为本地或测试环境配置。不要把真实账号、密码、token、内网 IP、生产 SVN 地址提交到仓库。

### 初始化数据库

平台运行库 SQLite 会在后端首次启动时自动初始化。

如果需要初始化规则元数据 Postgres 表：

```powershell
cd backend
python init_pg.py
```

该命令读取 `backend/svn_check/configs/database.yaml` 或 `SVN_CHECK_*` 环境变量，并执行 `backend/svn_check/migrate/postgres_schema.sql`。

### 启动后端

```powershell
cd backend
python app.py
```

默认监听 `http://127.0.0.1:5000`，健康检查：

```text
GET http://127.0.0.1:5000/api/health
```

### 启动前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

`.env` 中 `VITE_AUDIT_DATA_MODE=mock` 时前端使用本地演示数据，可不启动后端；设置为 `api` 时，“提交审查”会调用 `VITE_API_BASE_URL` 指向的后端任务接口，接口失败会显示错误且不会自动降级为 mock。

默认访问 Vite 输出地址，通常是 `http://127.0.0.1:5173`。

## 常见部署方式

- **本地开发部署**：后端 `python app.py`，前端 `npm run dev`，SQLite 自动初始化，元数据服务可不配置。
- **单机部署**：前端 `npm run build` 后交给 Nginx 托管；后端用 `gunicorn` 或 `waitress` 常驻运行；Nginx 反向代理 `/api/` 到 Flask。
- **内网部署**：使用内网 Python/npm 镜像源，真实配置只放在部署机器或环境变量中，不进入 Git。
- **Docker/容器化**：当前版本暂未内置 Dockerfile 或 docker-compose，可按后续规划补充。

详细步骤见 [部署文档](docs/deployment.md)。

## 配置说明

主要配置入口：

- [配置说明](docs/configuration.md)
- `frontend/.env.example`
- `backend/svn_check/configs/database.example.yaml`
- `backend/svn_check/configs/svn.example.yaml`

真实配置文件应保留在部署环境，不应提交到仓库。

## 测试与回归

后端当前使用 `unittest`：

```powershell
python -m unittest discover -s tests
python backend\dev_selfcheck.py
```

前端构建检查：

```powershell
cd frontend
npm run build
```

更多命令见 [回归命令](docs/regression_commands.md)。

## 安全与公开发布注意事项

- 不提交真实数据库连接串、生产 IP、账号密码、token、cookie。
- 不提交真实 SVN/FTP 地址或内部 Git 地址。
- 不在 README、截图、mock 数据中大段暴露真实系统名、真实表名、真实字段名。
- 发布前检查 `backend/database.py` 中的演示数据、`frontend/src/mock/data.js`、`docs/` 历史文档和截图。
- 对历史提交中曾经出现的敏感信息，按 [历史清理计划](docs/public_release_history_cleanup_plan.md) 处理。
- 公开发布前按 [发布检查清单](docs/public_release_checklist.md) 执行。

## Roadmap

- 提供统一配置加载与多环境配置示例。
- 补齐容器化部署文件和生产级启动脚本。
- 将平台运行库从 SQLite 扩展到可选 PostgreSQL。
- 增强元数据同步任务的快照日期、失败重试和审计日志。
- 完善资产风险输出到外部门户、工单或消息系统的适配层。
- 补充 CI、代码风格检查和端到端测试。

## License

待补充。当前仓库尚未声明开源协议，公开发布前必须由项目所有者确认许可证文本。
