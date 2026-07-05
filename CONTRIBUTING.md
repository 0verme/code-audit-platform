# Contributing

感谢参与 SQL Review Platform。当前项目处于公开发布准备阶段，贡献时请优先保证可迁移、可脱敏和可回归。

## 开发流程

1. 从最新主干创建功能分支。
2. 本地准备 `.env`、`database.yaml`、`svn.yaml`，不要提交真实配置。
3. 修改代码时同步补充测试和文档。
4. 提交前执行基础检查。

## 基础检查

```powershell
git diff --check
python -m unittest discover -s tests
cd frontend
npm run build
```

如只修改 Markdown，可不执行完整前后端测试，但至少执行 `git diff --check` 和敏感信息扫描。

## 提交信息

建议使用 Conventional Commit：

```text
docs: add deployment guide
fix: handle missing metadata gracefully
test: cover local audit task flow
```

## 文档同步要求

- 新增配置：更新 `docs/configuration.md` 和 `.example` 模板。
- 新增部署方式：更新 `docs/deployment.md`。
- 新增 API 或报告结构：更新 README、`docs/architecture.md` 和前端 mock 数据。
- 新增规则：补充测试，并说明缺少元数据时的降级行为。

## 敏感信息要求

不要提交真实账号、密码、token、cookie、生产 IP、真实 SVN 地址、真实数据库连接串、真实业务系统名称或大段真实表字段信息。示例统一使用 `example.com`、`127.0.0.1`、`localhost`、`demo_user`、`demo_db`、`demo_table`。
