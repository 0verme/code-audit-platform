# Regression Commands

本文档固化当前新平台推荐回归命令。命令从仓库根目录 `E:/AI生成代码/代码审查平台` 执行，除前端构建外不要切换目录。

## Python Environment

当前推荐使用：

```powershell
D:\miniconda3\python.exe
```

已知情况：

- 系统 `python` 不在 PATH。
- Codex bundled Python 缺少部分项目依赖。
- `requests` dependency warning 是既有 warning，不作为本轮阻断项。
- `backend/dev_selfcheck.py` 中 DB catalog 降级输出是既有降级，不作为本轮阻断项。

## Backend Tests

```powershell
D:\miniconda3\python.exe backend\scripts\run_backend_tests.py
D:\miniconda3\python.exe backend\dev_selfcheck.py
```

## Single Tests

```powershell
D:\miniconda3\python.exe -m unittest tests.test_asset_issue
D:\miniconda3\python.exe -m unittest tests.test_portal_link_builder
D:\miniconda3\python.exe -m unittest tests.test_workspace_service
D:\miniconda3\python.exe -m unittest tests.test_local_audit_task
D:\miniconda3\python.exe -m unittest tests.test_audit_metadata_service
D:\miniconda3\python.exe -m unittest tests.test_re_service_lineage
D:\miniconda3\python.exe -m unittest tests.test_engine_lineage_summary
```

## Frontend Build

必须进入 `frontend` 目录后执行：

```powershell
cd frontend
npm run build
```

注意：

- 在仓库根目录直接运行 `npm run build` 会因为根目录没有 `package.json` 失败。
- 正确位置是 `frontend`。
- 不要因为根目录构建失败误判为前端构建失败。

## Git Checks

```powershell
git status --short
git diff --stat
git diff --name-only
```

## Sensitive Information Scan Suggestions

以下只作为建议扫描方向。扫描结果中如果出现真实值，不要复制到公开文档或提交说明中。

建议关键词：

- `password`
- `passwd`
- `token`
- `secret`
- `jdbc`
- `dsn`
- `host`
- `ip`
- 内网地址模式
- 数据库连接串模式

建议命令示例：

```powershell
rg -n -i "password|passwd|token|secret|jdbc|dsn|host|ip" .
rg -n "\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b" .
```

执行扫描时只判断是否存在风险，不在公开文档中记录真实连接串、真实账号、真实 token、真实内网 IP 或真实业务值。
