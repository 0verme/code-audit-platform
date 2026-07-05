# Public Release Safety Checklist

本文档用于公开版发布前的敏感信息清理复核。这里只记录文件路径、风险类型和建议处理方式，不记录任何真实账号、密码、token、内网地址、连接串、业务样例值或联系人信息。

## Scope

- 仅作为公开发布前清单，不执行清理动作。
- 当前工作区清理不等于 git 历史干净。
- 公开前必须做 git 历史扫描和二次人工复核。
- 本轮不执行 `git filter-repo`、BFG、递归删除或历史重写。

## Must Clean

| Path / pattern | Risk type | Recommended handling |
|---|---|---|
| `E:/AI生成代码/pytools_new/configs/audit_datasource.yaml` | 数据源、账号、连接配置 | 移出公开仓库，改为本地私有配置，并提供 `.example` 模板 |
| `E:/AI生成代码/pytools_new/configs/database.yaml` | 数据库连接、账号、环境标识 | 移出公开仓库，改为环境变量或私有配置，并提供脱敏模板 |
| `E:/AI生成代码/pytools_new/configs/svn.yaml` | SVN 地址、凭据、内部路径 | 移出公开仓库，改为环境变量或私有配置，并提供 `.example` |
| `E:/AI生成代码/pytools_new/configs/migrate/clusters.json` | 集群、内网地址、业务映射 | 删除或替换为 demo 数据；真实映射不建议公开 |
| `backend/svn_check/configs/database.yaml` | 数据库连接配置 | 不公开真实文件；仅保留脱敏模板 |
| `backend/svn_check/configs/svn.yaml` | SVN 凭据和仓库地址 | 不公开真实文件；仅保留脱敏模板 |
| `backend/data/app.db` | 私有 SQLite 数据 | 不公开；替换为可重建的 demo 数据或初始化脚本 |
| `**/.env`, `**/.env.local` | 密钥、token、API base URL、本地参数 | 不公开；加入忽略规则并提供 `.example` |
| `**/*.db`, `**/*.sqlite`, `**/*.sqlite3` | 私有缓存或业务数据 | 不公开；必要时提供空库生成说明 |
| `**/logs/**`, `**/*.log`, `**/cache/**` | 运行日志、请求参数、路径、人员信息 | 不公开；发布前清理工作区并扫描历史 |
| 文档中的真实内网地址、真实连接串、真实表名样例、联系人、客户或系统名 | 业务敏感信息 | 全部替换为占位符或 demo 名称 |

## Template Recommended

| Path / pattern | Risk type | Recommended handling |
|---|---|---|
| `database.yaml` | 环境相关数据库参数 | 改为 `database.yaml.example`，真实值通过环境变量或本地私有文件提供 |
| `audit_datasource.yaml` | 审计数据源参数 | 改为 `audit_datasource.yaml.example`，只保留字段结构和占位符 |
| `svn.yaml` | SVN 仓库和认证参数 | 改为 `svn.yaml.example`，真实凭据走环境变量 |
| `.env.local` | 本地开发参数 | 不提交真实文件；提供 `.env.example` |
| `configs/tools.yaml` | 工具路径、内部服务地址 | 替换为占位符或平台无关默认值 |
| `frontend/src/mock/*` | mock 数据和 API 样例 | 保留结构，替换为 demo 数据，避免真实业务字段和值 |
| API base URL 配置 | 内部域名、网关路径 | 改为环境变量，文档仅写变量名和占位符 |

## Keep With Desensitization Review

| Path / pattern | Risk type | Recommended handling |
|---|---|---|
| `docs/*` | 架构说明、历史迁移记录可能夹带真实系统名或表名 | 发布前全文扫描，替换为泛化名称或 demo 名称 |
| `README.md` | 快速开始、截图、配置示例可能夹带真实值 | 保留公开说明，真实配置全部替换为占位符 |
| demo SQL | 表名、字段、作业名可能暴露业务语义 | 使用 demo 命名空间和 synthetic 数据 |
| mock JSON | 真实业务样例数据 | 使用 synthetic 数据，避免真实客户、系统、人员、表名 |
| screenshots | 内部系统名称、URL、人员信息 | 裁剪或重制为 demo 截图 |
| 静态原型代码目录 | 页面文案、示例数据、内部链接 | 保留前做敏感词和路径扫描 |
| `backend/engine.py`, `backend/database.py` | 代码注释或默认值可能含内部示例 | 仅做人工复核；本轮不修改业务代码 |

## Not Recommended For Public Release

| Path / pattern | Risk type | Recommended handling |
|---|---|---|
| 内部审计报告 | 真实业务规则、问题样例、人员和系统信息 | 不公开；如需展示，重制 demo 报告 |
| 真实初始化 SQL | 真实表结构、业务映射、环境信息 | 不公开；新建 demo 初始化脚本 |
| 真实平台截图 | 内部 URL、菜单、账号、业务对象 | 不公开；使用 demo 环境重新截图 |
| 私有业务映射表 | 客户、系统、作业、表、字段映射 | 不公开；保留在私有仓库或私有配置中心 |
| 历史归档文档 | 老系统路径、问题记录、联系人、真实样例 | 不公开；公开版只保留脱敏摘要 |

## Git History Risk

- 工作区清理不代表 git 历史已经干净。
- 公开前需要扫描完整历史中的敏感关键词、内网地址模式、数据库连接串模式和私有文件路径。
- 如果历史里出现真实连接串、账号、凭据、私有数据文件或真实业务映射，需要评估重写历史或新建公开仓库。
- 本轮只形成清单，不执行历史重写、文件删除或真实内容清理。

## Release Gate

公开发布前建议至少完成以下 gate：

1. 当前工作区敏感关键词扫描无真实值输出。
2. git 历史敏感关键词扫描完成并人工复核。
3. 配置文件均为 `.example` 或环境变量说明，不包含真实值。
4. SQLite、日志、缓存、截图、报告和归档资料完成公开性判断。
5. README、docs、mock、demo SQL 完成二次人工脱敏复核。
6. 如无法确认历史干净，优先新建公开仓库并只迁移脱敏后的文件。
