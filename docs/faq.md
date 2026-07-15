# FAQ

## 没有生产元数据能不能运行？

可以。前后端和 SQLite 平台运行库不依赖生产元数据。缺少元数据时，部分依赖、登记、禁用状态、源系统标注等检查会降级，报告中需要人工复核的内容会增多。

## 没有部署数据资产门户能不能运行？

可以。当前平台不强依赖数据资产门户。`assetIssues` 和 `unifiedAssetIssues` 是风险输出结构，主要用于展示和未来适配。

## 审计平台和资产门户是什么关系？

审计平台负责上线前检查和风险汇总；资产门户如果存在，可以作为后续风险承接、资产详情跳转或治理闭环系统。两者应通过适配层集成，而不是强绑定部署。

## 如何切换 mock/API 模式？

通过前端启动或构建环境变量切换：`VITE_AUDIT_DATA_MODE=mock` 使用 `frontend/src/mock/data.js` 演示数据；`VITE_AUDIT_DATA_MODE=api` 调用后端任务接口。页面上不提供 mock/API 运行时开关。API 模式下接口失败会显示错误，不会自动降级为 mock。

## 数据库连接失败怎么排查？

先区分两类数据库：

- SQLite：平台运行库，默认 `backend/data/app.db`，首次启动自动创建。
- Postgres/GaussDB：规则元数据库，用于增强元数据检查。

排查步骤：

1. 检查 `backend/database.yaml` 是否存在。
2. 检查 `AUDIT_DATABASE_CONFIG` 和 `CODE_AUDIT_DB_PROFILE` 环境变量是否覆盖了 YAML。
3. 用数据库客户端验证 host、port、库名、用户、schema。
4. 确认 Postgres 已执行 `python backend/init_pg.py`。
5. 如果只是元数据库不可用，平台仍可运行，但部分规则会降级。

## 前端访问后端跨域怎么处理？

开发模式下 `backend/app.py` 已对 `/api/*` 启用 CORS。生产环境建议通过 Nginx 同域代理 `/api/`，并将 `VITE_API_BASE_URL` 设置为 `/api`。

## 定时任务失败怎么看数据日期？

当前仓库没有内置定时同步任务。建议部署方在同步任务日志和元数据快照表中记录数据日期、快照日期、来源系统、行数和失败原因。审计报告使用元数据时，应能追溯到最近一次成功快照。

## 如何做公开发布前脱敏？

- 检查 README、docs、源码注释、mock 数据、截图和 SQLite 数据库。
- 扫描 `password`、`token`、`secret`、`jdbc`、`svn://`、内网 IP 等关键词。
- 将真实系统名、表名、字段名替换为 `demo_system`、`demo_table`、`demo_field`。
- 删除或重做含真实地址和真实任务信息的截图。
- 如果敏感信息进入历史提交，按历史清理流程处理，不只修改最新文件。

## Docker 怎么部署？

当前版本暂未内置 Dockerfile 或 docker-compose。可以按单机部署方式先完成前端 build、后端 WSGI 启动和 Nginx 代理，后续再补容器化。
