# P0 迁移清单

P0 目标是先建立可控迁移路径，不做盲目覆盖。除 Round P0-1 外，其余 round 允许在明确登记和验证后修改新平台业务代码；旧平台默认不改业务代码。

## Round P0-1：规则差异冻结快照

目标：函数级比对旧平台 `apps/svn_check` 与新平台 `backend/svn_check` 的差异，只输出报告，不改代码。

涉及旧平台文件：

- `core/asset_issue.py`
- `core/public_data.py`
- `core/hcyt/ddl_rule.py`
- `core/hcyt/sql_rule.py`
- `core/hcyt/python_rule.py`
- `core/hcyt/schedule_rule.py`
- `core/fine_rule.py`
- `core/nups_rule.py`
- `services/portal_link_builder.py`
- `services/workspace_service.py`
- `services/db_profile.py`
- `services/audit_metadata_service.py`
- `services/re_service.py`
- `services/svn_service.py`

涉及新平台文件：

- `backend/svn_check/**`
- `docs/function_diff_snapshot.md`

是否允许改业务代码：否。

预期产物：

- 函数级差异快照。
- 不能覆盖、逐函数迁移、以新版为准的文件分类。

验证方式：

- 复核 Git diff 只包含文档。
- 复核敏感配置未输出。

风险点：

- 编码乱码导致中文文案差异难以判断。
- 只做顶层函数比对，嵌套函数和常量差异需后续人工复核。

回滚方式：

- 删除或回退差异报告文档。

## Round P0-2：资产 issue / 词根缺失 / 门户链接迁移

目标：迁移旧平台新增的资产 issue 数据结构、去重逻辑、词根缺失结构化输出、资产门户链接生成能力。

涉及旧平台文件：

- `core/asset_issue.py`
- `core/hcyt/ddl_rule.py`
- `core/hcyt/sql_rule.py`
- `core/hcyt/python_rule.py`
- `services/portal_link_builder.py`
- `tests/apps/test_svn_check_asset_issue.py`

涉及新平台文件：

- `backend/svn_check/core/asset_issue.py`
- `backend/svn_check/core/hcyt/ddl_rule.py`
- `backend/svn_check/core/hcyt/sql_rule.py`
- `backend/svn_check/core/hcyt/python_rule.py`
- `backend/svn_check/services/portal_link_builder.py`
- `backend/engine.py`
- `frontend/src/pages/ResultsPage.jsx`
- `frontend/src/pages/FineReportPage.jsx`

是否允许改业务代码：允许改新平台，禁止改旧平台。

预期产物：

- 新平台具备资产 issue 数据结构。
- 报告 JSON 包含资产 issue 或等价字段。
- 前端可以展示资产待维护和门户链接。

验证方式：

- 单测覆盖 issue key/hash、去重、门户链接。
- 用 `backend/dev_selfcheck.py` 或新增最小测试验证报告字段。
- 前端使用 mock 或真实报告 JSON 验证不崩溃。

风险点：

- 门户 base URL 涉及敏感配置，必须使用环境变量和占位示例。
- 旧平台函数不能直接覆盖新平台同名文件。

回滚方式：

- 回退本 round 修改的新平台文件。
- 保留登记表状态为“暂缓”。

## Round P0-3：本地目录审计 API 化

目标：把旧平台 `workspace_service.py` 的本地目录审计能力接入新平台任务 API，而不是 Streamlit 页面。

涉及旧平台文件：

- `services/workspace_service.py`
- `app.py`
- `ui/hcyt_stream.py`

涉及新平台文件：

- `backend/app.py`
- `backend/engine.py`
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/services/reviewService.js`
- `frontend/src/config/api.js`

是否允许改业务代码：允许改新平台，禁止改旧平台。

预期产物：

- `POST /api/audit-tasks` 支持本地目录来源。
- 任务模型能区分 SVN 与 local。
- 报告 JSON 保留 source type 和 workspace root。

验证方式：

- 使用临时本地目录提交任务。
- 验证 `changes`、`task.sourceType`、错误提示。
- 验证非法目录不泄露本机敏感路径以外的信息。

风险点：

- 本地路径输入存在安全边界问题。
- 前端默认示例不能写入真实敏感路径。

回滚方式：

- 回退 API payload 和 engine workspace 相关改动。
- 前端隐藏本地目录入口。

## Round P0-4：DB Profile / DB Router 统一方案

目标：先设计兼容方案，不直接大改配置。明确旧平台 `db_profile.py` 和新平台 `shared/db/router.py` 如何统一。

涉及旧平台文件：

- `services/db_profile.py`
- `services/db_service.py`
- `services/audit_metadata_service.py`
- 上层 `configs/audit_datasource.yaml`

涉及新平台文件：

- `backend/svn_check/shared/db/router.py`
- `backend/svn_check/shared/db/postgres.py`
- `backend/svn_check/shared/db/gaussdb.py`
- `backend/svn_check/configs/database.yaml`
- `backend/svn_check/services/db_service.py`

是否允许改业务代码：本 round 只允许改文档；实现 round 另开。

预期产物：

- DB profile 兼容设计。
- 配置优先级说明。
- 敏感配置脱敏规范。

验证方式：

- 文档评审。
- 不读取或输出真实配置值。

风险点：

- 旧平台和新平台配置来源不同。
- 生产 GaussDB 与测试 Postgres 语义差异。

回滚方式：

- 回退设计文档。

## Round P0-5：audit metadata service 与宽表链路摘要迁移

目标：迁移 `audit_metadata_service.py`、`re_service.py` 中与元数据、outfile、宽表链路摘要相关的能力。

涉及旧平台文件：

- `services/audit_metadata_service.py`
- `services/re_service.py`
- `core/public_data.py`
- `ui/public_stream.py`
- `ui/hcyt_stream.py`

涉及新平台文件：

- `backend/svn_check/services/audit_metadata_service.py`
- `backend/svn_check/services/re_service.py`
- `backend/svn_check/core/public_data.py`
- `backend/engine.py`
- `frontend/src/pages/ResultsPage.jsx`
- `frontend/src/pages/ScriptAudit.jsx`

是否允许改业务代码：允许改新平台，禁止改旧平台。

预期产物：

- 新平台具备元数据查询适配服务。
- 新平台报告 JSON 包含宽表链路摘要。
- outfile、recv plan、来源系统可以在结果页展示。

验证方式：

- 使用 mock DB 或空 DB 验证降级路径。
- 使用最小报告 JSON 验证前端展示。
- 确认敏感配置未进入日志和报告。

风险点：

- 元数据表缺失时必须降级。
- `public_data.py` 两边同名函数实现差异较多。

回滚方式：

- 回退新增服务和 engine 字段。
- 前端隐藏链路摘要区块。

## Round P0-6：测试迁移

目标：把旧平台 `test_svn_check_asset_issue.py` 迁移到新平台正式 tests 目录，并补充最小可运行测试。

涉及旧平台文件：

- `tests/apps/test_svn_check_asset_issue.py`

涉及新平台文件：

- `tests/`
- `backend/svn_check/core/asset_issue.py`
- `backend/svn_check/services/portal_link_builder.py`
- `backend/requirements.txt` 或测试说明文档

是否允许改业务代码：允许补测试；业务代码只允许修复测试暴露的 P0 迁移问题。

预期产物：

- 新平台正式测试目录。
- 资产 issue / 门户链接单测可运行。
- 最小迁移回归脚本。

验证方式：

- 运行新平台测试命令。
- 运行 `backend/dev_selfcheck.py`，如环境不支持需记录原因。

风险点：

- 当前环境 `python` 命令异常，需要先确认可用 Python 运行时。
- 编码乱码可能影响中文断言，应优先断言结构字段。

回滚方式：

- 回退 tests 目录和相关测试配置。
