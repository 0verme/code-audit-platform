# Public Release Checklist

公开发布前按本清单检查。不要在检查报告中粘贴真实账号、真实连接串、真实内网地址或真实业务数据。

## 1. 文档检查

- README 已说明项目定位、场景、能力、架构、快速开始、部署、测试、安全注意、Roadmap 和 License 状态。
- `docs/deployment.md` 覆盖本地、单机、内网部署。
- `docs/configuration.md` 明确模板和真实配置边界。
- `docs/development.md` 覆盖本地开发、mock/API、测试和提交建议。
- `docs/architecture.md` 基于真实代码结构，没有编造强依赖。
- `docs/faq.md` 覆盖常见部署和公开发布问题。

## 2. 配置与密钥

- 不提交 `frontend/.env`。
- 不提交真实 `backend/svn_check/configs/database.yaml`。
- 不提交含真实账号的 `backend/svn_check/configs/svn.yaml`。
- 只提交 `.example` 模板。
- 模板中只使用 `example.com`、`127.0.0.1`、`localhost`、`demo_user`、`demo_db` 等示例值。

## 3. 数据与截图

- 不提交 `backend/data/app.db`。
- 不提交生产日志、Excel、CSV、压缩包、导出文件。
- 检查 `frontend/src/mock/data.js` 是否包含真实系统名、表名、字段名。
- 检查 `静态原型代码/screenshots` 是否包含真实地址、人员、系统、表名或任务信息。

## 4. 源码与注释

- 不在源码注释中保留真实生产地址、真实账号或真实系统说明。
- 外部系统能力只描述为可选适配，不写成强依赖。
- 对不确定能力使用“当前版本暂未内置”或“可按实际部署方式补充”。

## 5. 建议扫描命令

```powershell
git diff --check
rg -n -i "password|passwd|token|secret|cookie|jdbc|dsn|ftp|svn://" .
rg -n "\b10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}\b|\b192\.168\.[0-9]{1,3}\.[0-9]{1,3}\b" .
git status --short
```

命中结果需要人工判断；不能仅凭命中数量决定是否安全。

## 6. 历史提交

如果敏感信息曾经进入 Git 历史：

- 先确认是否必须公开原仓库历史。
- 必要时使用历史清理工具重写历史。
- 清理后轮换所有已暴露账号、密码、token。
- 参考 `docs/public_release_history_cleanup_plan.md`。

## 7. 发布前确认

- License 已由项目所有者确认。
- SECURITY 和 CONTRIBUTING 文档已存在。
- CHANGELOG 已记录公开版本状态。
- CI 或人工回归命令已执行。
- 发布包不包含 `node_modules`、`dist`、`.venv`、SQLite 数据库和真实配置。
