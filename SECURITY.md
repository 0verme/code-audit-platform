# Security Policy

## Supported Versions

当前项目尚未发布正式版本。公开发布前，项目维护者应明确受支持版本范围和安全修复策略。

## Reporting a Vulnerability

请通过项目维护者指定的私有渠道报告安全问题。不要在公开 issue 中粘贴真实账号、token、连接串、内网地址、生产日志或业务数据。

报告建议包含：

- 受影响版本或提交。
- 复现步骤。
- 影响范围。
- 已确认不包含敏感值的日志或截图。

## Sensitive Information Rules

- 不提交真实数据库连接串、账号、密码、token、cookie。
- 不提交生产 IP、真实 SVN/FTP/Git 地址。
- 不提交真实业务数据、客户数据、生产日志或数据库文件。
- 配置模板只使用 `example.com`、`127.0.0.1`、`localhost` 和 `demo_*` 示例值。

公开发布前请执行 `docs/public_release_checklist.md`。
