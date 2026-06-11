# 代码审查平台

当前仓库已将静态原型拆成可运行的 `React + Vite` 前端和 `Flask + SQLite` 后端，保留了原型的页面结构、卡片、表格、导航和交互，同时增加了 REST API、mock 回退、构建和离线部署说明。

## 真实审查引擎（已内置，脱离 pytools_new 独立运行）

真实项目 `pytools_new/apps/svn_check` 的规则引擎源码已**物理拷贝**进
`backend/svn_check/`（core 规则、SVN/正则/AI 服务、shared 的 db/lineage/graph、
configs），与 pytools_new 完全脱钩，可独立部署。拷贝时仅做最小改动：

- `services/diag_service.py` 改为纯 logging 实现（剥离 Streamlit）；
- `shared/db/gaussdb.py` 容忍 jaydebeapi/JVM 缺失（import 不再致命）；
- `services/db_service.py` 在 DB 访问入口加降级层：行内 GaussDB 连不上时返回
  空集并记日志，规则逻辑零改动；
- `services/svn_service.py` 配置路径改为随包定位（`svn_check/configs/`）。

`backend/engine.py` 是编排层（不含规则逻辑），提交审查时在后台线程执行完整流水线，
并把结果整理成「与 Streamlit 版展示内容对齐」的结构化报告：

- 工作流路由与 Streamlit 版一致：URL 含 `/hcyt/` 走湖仓审查、`/NUPS/`、`/nups/`
  走 NUPS、`/fine-report/` 走帆软报表审查；
- HCYT：SVN 分支差异拉取 → dws/hive SQL 规则 → sbin/SCHEMA_CONFIG/recv 检查 →
  PLAN/SEQ/CALE/JOB 调度 Excel 清单与规则 → dwo/dwf/加工程序检查 → 结果表与调度
  依赖比对（含禁用/源系统标注）→（可选）AI 分析；
- FineReport：目录(menu)/权限(authority) 表格与规则 → 帆软模板（数据源、引擎、
  sheet、数据集 SQL、敏感字段、引用表）→ 预览/下载链接；
- NUPS：NUPS SQL 检查 + 加工程序检查 + SQL 引用表；
- 行内 GaussDB / 血缘库连不上时自动降级：依赖数据库的展示信息弱化、纯静态规则照常输出；
- 任务进度/步骤/日志实时落库，前端 2 秒轮询 `GET /api/audit-tasks/:id`，完成后拉取
  `GET /api/audit-tasks/:id/report` 渲染真实报告；
- 运行 `python backend/dev_selfcheck.py` 可在无 SVN/数据库环境离线自检三条流水线。

> 行内库需要 GaussDB JDBC 驱动时，安装 `jaydebeapi` 并放置
> `backend/svn_check/resources/jars/gaussdb200.jar`（缺失则自动降级为纯静态检查）。

### 数据库后端：Postgres / GaussDB 可切换

规则引擎查询的元数据库支持两种后端，通过统一路由 `svn_check/shared/db/router.py` 分发：

- 选择方式：`svn_check/configs/database.yaml` 的 `backend: postgres|gaussdb`，或环境变量
  `SVN_CHECK_DB_BACKEND` 覆盖（优先级更高）；
- **Postgres（测试环境，当前默认）**：连接参数在 `database.yaml` 的 `postgres` 段，
  也可用 `SVN_CHECK_PG_HOST/PORT/DB/USER/PASSWORD/SCHEMA` 覆盖。驱动用 `psycopg`；
- **GaussDB（行内生产）**：经 JDBC 桥（jaydebeapi），配置见 `profiles` 段。

建表（把规则引擎所需的 `dwp.p_*` 元数据表建进 Postgres，幂等可重复执行）：

```bash
cd backend
python init_pg.py          # DDL 见 svn_check/migrate/postgres_schema.sql
```

已创建的表（schema `dwp`，表名 `p_` 开头）：`p_job_hjj`、`p_program_hjj`、`p_plan_hjj`、
`p_role_hjj`、`p_fine_hjj`、`p_job_outfile`、`p_para_table_lists`、`p_recv_dwf`、
`p_recv_ops_mapping`、`p_term_root`。`p_job_hjj` 用 `select *` 按列序取值，故保留 28 列
（`a..ab`，其中 `e`=程序KEY、`x`=状态、`ab`=前置依赖串）。

> 方言说明：`all_tab_partitions` 查询 Oracle 数据字典 `dba_tab_partitions`，
> Postgres 无对应表，该查询会走降级（分区步骤校验不触发），其余查询均已在 PG 验证可用。

## 目录结构

```text
code-review-platform/
├─ 静态原型代码/
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ config/
│  │  ├─ hooks/
│  │  ├─ mock/
│  │  ├─ pages/
│  │  ├─ services/
│  │  └─ styles/
│  ├─ package.json
│  ├─ vite.config.js
│  └─ .env.example
├─ backend/
│  ├─ app.py
│  ├─ database.py
│  ├─ requirements.txt
│  └─ data/
└─ README.md
```

## 第一阶段：前端工程化

前端位于 [frontend](E:/AI生成代码/代码审查平台/frontend)。

安装依赖：

```bash
cd frontend
npm install
```

开发启动：

```bash
npm run dev
```

生产构建：

```bash
npm run build
```

说明：

- 原型中的 React/Babel CDN 已移除，改为 Vite 本地构建。
- CSS 已迁移到 `src/styles`，并继续沿用原有视觉风格。
- mock 数据位于 `src/mock/data.js`，后端不可用时自动回退。
- 前端 API 地址通过 `VITE_API_BASE_URL` 配置，示例见 [frontend/.env.example](E:/AI生成代码/代码审查平台/frontend/.env.example)。

## 第二阶段：后端 Flask

后端位于 [backend](E:/AI生成代码/代码审查平台/backend)。

创建虚拟环境并安装依赖：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

开发启动：

```bash
python app.py
```

已提供接口：

- `GET /api/health`
- `GET /api/projects`
- `GET /api/audit-tasks`
- `GET /api/audit-tasks/:id` —— 任务状态 / 进度 / 步骤 / 实时日志
- `GET /api/audit-tasks/:id/report` —— 真实审查报告（前端页面数据结构）
- `GET /api/audit-results?task_id=` —— 按任务过滤的规则命中明细
- `POST /api/audit-tasks` —— 创建任务并后台执行真实审查
- `GET /api/fine-report/items`

说明：

- SQLite 数据库文件默认生成在 `backend/data/app.db`。
- 首次启动会自动初始化表结构和示例数据。
- 已启用 CORS，方便前端本地联调。

## 第三阶段：前后端联调

联调要点：

- `frontend/src/services/apiClient.js` 统一管理请求。
- `frontend/src/config/api.js` 统一管理 API 路径和基础地址。
- 首页项目列表、任务列表、结果列表、帆软报表列表优先请求后端。
- 当后端不可用时，页面会显示友好提示并回退到 `mock` 数据。
- 已处理 `loading / empty / error` 三类状态。

前后端一起启动时建议：

```bash
cd backend
python app.py
```

```bash
cd frontend
copy .env.example .env
npm run dev
```

默认前端会请求：

```text
http://127.0.0.1:5000/api
```

## 第四阶段：Linux 离线部署

### 前端离线部署

在有依赖缓存或内网 npm 源的环境完成构建：

```bash
cd frontend
npm install
npm run build
```

构建产物位于：

```text
frontend/dist
```

`dist` 可独立部署到 Nginx 静态目录，不依赖 `unpkg`、`cdn.jsdelivr` 或任何公网 CDN。

### 后端离线部署

建议先在内网制品库准备 Python wheel 包，再安装：

```bash
cd backend
pip install -r requirements.txt
```

Linux 启动方式：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

如果环境更适合 Windows 服务或纯 Python 方式，可用：

```bash
waitress-serve --host 0.0.0.0 --port 5000 app:app
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name _;

    root /opt/code-review-platform/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 后续可扩展点

- 将 SQLite 数据访问替换为 SQLAlchemy 或仓储层，方便后续切 Oracle/PostgreSQL。
- 增加 `GET /api/audit-results/:taskId` 之类的明细接口，进一步替换结果页 mock 数据。
- 将“提交审查”真正接入 SVN/Git 扫描与规则引擎。
