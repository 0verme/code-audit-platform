# Development Guide

## Runtime security defaults (A4)

The backend keeps local workspace audits and Flask debug **disabled by default**.
The UI variable `VITE_ENABLE_LOCAL_SOURCE` only controls whether the local option
is shown; it never grants backend access. Enable both sides explicitly for local
development, and do not enable local workspace auditing in production.

When started through `backend/app.py` or either `backend/scripts/start_backend.*`,
the backend automatically loads `backend/.env` if it exists. Copy
`backend/.env.example` to `backend/.env` as a starting point. Values already
provided by the operating system take precedence over values in that file.
The file is local-only and must not be committed.

```powershell
# Optional: use the checked-in template for file-based configuration.
Copy-Item backend\.env.example backend\.env

# Windows: use a JSON array for roots so drive-letter colons are unambiguous.
$env:AUDIT_LOCAL_SOURCE_ENABLED = "true"
$env:AUDIT_LOCAL_SOURCE_ROOTS = '["E:\\workspace\\audit-samples", "E:\\workspace\\other-samples"]'
$env:AUDIT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
$env:AUDIT_HOST = "127.0.0.1"
$env:AUDIT_PORT = "5088"
$env:AUDIT_DEBUG = "false"
```

```bash
# Linux: roots may use a JSON array (recommended) or colon-separated paths.
export AUDIT_LOCAL_SOURCE_ENABLED=true
export AUDIT_LOCAL_SOURCE_ROOTS='["/opt/audit/workspaces", "/srv/audit/samples"]'
export AUDIT_CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173'
export AUDIT_HOST=127.0.0.1
export AUDIT_PORT=5088
export AUDIT_DEBUG=false
```

`AUDIT_LOCAL_SOURCE_ROOTS` must contain at least one existing directory when
local source is enabled. The submitted directory and every file read must resolve
under an allowed root; UNC paths and symlinks/junctions that leave a root are
rejected or skipped. CORS has no wildcard default, and `*` is invalid. Boolean
settings accept `1/true/yes/on` and `0/false/no/off`.

## Lineage mapping resources

Lineage imports use `backend/data/lineage/mapping.xlsx`; the rebuildable SQLite cache is `backend/data/lineage/mapping_lineage.db`. Neither production resource is stored in Git. Deployment must provide the Excel file, then rebuild the cache through the existing importer, or set `LINEAGE_MAPPING_EXCEL_PATH` and `LINEAGE_MAPPING_DB_PATH`. Empty overrides use the defaults; relative overrides are resolved from `backend`, not the process working directory. A missing Excel or cache is reported as `unavailable` with its path and is never treated as a successful empty lineage result. These resources no longer use `backend/svn_check`.

## 本地开发环境准备

建议版本：

- Python 3.10+，建议 3.11。
- Node.js 18+。
- npm 9+。
- 可选：Postgres 12+，用于规则元数据表。
- 可选：SVN 命令行客户端，用于 SVN 工作区审计。

克隆仓库后先准备配置模板：

```powershell
copy frontend\.env.example frontend\.env
copy backend\svn_check\configs\database.example.yaml backend\svn_check\configs\database.yaml
copy backend\svn_check\configs\svn.example.yaml backend\svn_check\configs\svn.yaml
```

真实配置只放在本地，不提交。

## 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

后端默认监听 `http://127.0.0.1:5000`。首次启动会创建 `backend/data/app.db` 并写入演示数据。

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

`frontend/src/config/api.js` 会读取 `VITE_AUDIT_DATA_MODE` 和 `VITE_API_BASE_URL`。`VITE_AUDIT_DATA_MODE` 默认值是 `mock`，`VITE_API_BASE_URL` 默认值是 `http://127.0.0.1:5000/api`。

## mock 模式/API 模式

mock/API 是前端启动或构建时的部署配置，不是页面运行时开关。页面不提供后端执行模式切换开关。

- `VITE_AUDIT_DATA_MODE=mock`：提交审查直接使用 `frontend/src/mock/data.js` 中的演示数据，不依赖后端任务接口。
- `VITE_AUDIT_DATA_MODE=api`：提交审查调用后端 `POST /api/audit-tasks` 创建真实任务，并轮询任务和报告接口。
- API 模式下接口失败会显示明确错误，不会自动降级展示 mock 结果。
- 创建真实任务时，后端 `POST /api/audit-tasks` 支持 `sourceType=svn` 或 `sourceType=local`；本地目录模式是否可用取决于启用配置，且当前只支持 `hcyt` 工作流键。Git 仓库当前不支持：Git URL 会被识别并明确拒绝，不会回退到 SVN loader。

## 常用测试命令

```powershell
python -m unittest discover -s tests
python backend\dev_selfcheck.py
```

单测示例：

```powershell
python -m unittest tests.test_asset_issue
python -m unittest tests.test_workspace_service
python -m unittest tests.test_engine_lineage_summary
```

前端构建：

```powershell
cd frontend
npm run build
```

## 代码风格检查

当前项目未内置 Ruff、Black、ESLint 或 Prettier 命令。新增代码时建议先保持现有风格，并在后续 Roadmap 中补充统一 lint 配置。

可执行的基础检查：

```powershell
git diff --check
python -m unittest discover -s tests
cd frontend
npm run build
```

## Git 提交建议

- 提交前执行 `git status --short`，确认只包含本次相关文件。
- 文档、配置模板、业务代码分开提交。
- commit message 建议使用简洁的 Conventional Commit，例如 `docs: add public deployment and release documentation`。

## 新增功能时同步更新

- API 变更：更新 README、`docs/deployment.md`、`docs/development.md`。
- 新配置：更新 `docs/configuration.md` 和对应 `.example` 文件。
- 新规则输出：更新 `docs/architecture.md`、前端 mock 数据和相关单测。
- 新部署方式：更新 `docs/deployment.md` 和 `docs/public_release_checklist.md`。
- 外部系统适配：明确是可选集成还是强依赖，并补充失败降级说明。

## 避免引入内部敏感信息

- 不复制真实 SVN URL、数据库地址、账号、token 到源码或文档。
- 不把生产日志、真实 Excel、真实 SQLite 数据库放入仓库。
- mock 数据统一使用 `demo_*`、`example.com`、`127.0.0.1`。
- 截图发布前检查浏览器地址栏、任务日志、表名、人员名、系统名。
- 提交前执行敏感关键词扫描，并对命中结果逐项确认。
