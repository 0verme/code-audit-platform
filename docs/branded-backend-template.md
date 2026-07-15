# 统一品牌化后端模板规范

## 模块边界

所有品牌后端使用 `create_app()` 和唯一 `run.py` 入口。HTTP 路径按资源放入 `app/routes`；路由只读取参数、做轻量校验、调用 service 并转换响应。业务编排进入 `app/services`，且不得依赖 `request`、`jsonify`、`g` 或 `session`。稳定的规则、工作流、报告和领域算法进入 `app/modules/<domain>`，数据库连接与持久化进入 `app/db`。

## 新增能力

1. 新增领域能力时，先在 `app/modules/<domain>` 建立纯领域 API。
2. 在 `app/services/<resource>_service.py` 编排领域与持久化边界，并定义明确的失败语义。
3. 在 `app/routes/<resource>.py` 创建 Blueprint，保持 URL、字段、状态码兼容，并在 `routes/__init__.py` 注册。
4. 高风险创建、执行、导出接口使用 `require_permission()`；接入身份系统时只替换统一认证实现。
5. 为 service 写单元测试，为 API/数据库链路写集成测试。

## 配置、安全与日志

环境配置统一由 `app/settings.py` 解析。环境文件不得覆盖进程变量；CORS 不得使用通配符。本地路径必须经过启用开关、允许根目录、规范化路径、路径遍历和符号链接边界校验。响应携带请求 ID，日志记录方法、路径、状态与耗时，不记录凭据、连接串或源码内容。

## 迁移

每次 schema 变更都添加递增版本 SQL，并同时提供 `sqlite`、`postgresql`、`dws` 文件，在 `migrations/manifest.json` 登记。禁止修改已发布迁移；runner 通过 SHA-256 检测漂移。迁移必须显式执行、可重复、失败回滚，不得随应用启动执行破坏性升级。

## 测试与交付

变更至少覆盖 App Factory/Blueprint、API 契约、service 失败语义、安全边界和从空库到最新版本的迁移。生产依赖放入 `requirements.txt`，pytest、coverage、ruff 等仅放入 `requirements-dev.txt`。提交前运行相关测试、静态检查、`git diff` 审阅及敏感信息检查。
