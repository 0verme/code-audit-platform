# 后端目录结构审计

## 1. 审计范围

本次审计覆盖 `backend/`、`backend/audit/`、数据库配置加载入口、测试、启动脚本、Git 忽略规则和当前部署文档。审计基于仓库文件、导入关系与路径搜索；未读取本地 `database.yaml` 的内容。

审计计数：P0 0 项，P1 1 项（已修复），P2 2 项，P3 0 项。

## 2. 当前目录概览

`backend/` 包含应用入口 `app.py`、运行时数据库层 `db/`、审计领域包 `audit/`、元数据模块 `metadata/`、运维脚本 `scripts/`、运行级配置目录 `configs/`、运行数据目录 `data/` 与日志目录 `logs/`。`audit/` 内的 `checks/`、`rules/`、`prompts/` 是领域资源；外部连接配置不属于业务包资源。

## 3. 数据库配置迁移结果

- 本地运行配置：`backend/configs/database.yaml`（保留在本地，未纳入 Git）。
- 配置模板：`backend/configs/database.example.yaml` 和 `backend/configs/svn.example.yaml`（已纳入 Git）。
- 加载入口：`backend/db/profiles.py`。
- 默认路径：由集中路径定义模块计算的 `backend/configs/database.yaml`，不依赖当前工作目录。
- 覆盖方式：`AUDIT_DATABASE_CONFIG` 优先；保留 `CODE_AUDIT_DB_CONFIG_PATH` 作为旧环境变量兼容入口。

## 4. 已完成调整

- 将数据库配置移出业务子包，并用精确 `.gitignore` 规则保护真实文件。
- 集中默认路径和环境变量解析，补全缺文件、YAML 解析和必填字段错误信息。
- 更新当前 README、部署、开发、FAQ 和数据库配置文档。
- 增加默认路径、工作目录无关性、环境变量覆盖和非法 YAML 的单元测试。

## 5. 发现的问题

| 优先级 | 当前路径 | 问题 | 建议路径或方案 | 风险 | 是否建议立即处理 |
|---|---|---|---|---|---|
| P1 | `backend/.venv/` | 本地虚拟环境位于源码目录，根级 `.venv/` 规则不覆盖该嵌套位置。 | 已增加 `/backend/.venv/` 忽略规则；后续可移至仓库外。 | 误提交大量依赖与构建产物。 | 已处理 |
| P2 | `docs/*migration*`、`docs/*retirement*` | 多份历史迁移记录仍描述已退役的 `svn_check` 路径。 | 标注为历史快照，或在后续文档整理中归档。 | 读者可能误用旧命令。 | 否 |
| P2 | `backend/scripts/` 与 `tests/` | 多个脚本和测试通过 `sys.path.insert` 运行。 | 后续建立可安装包或统一测试入口后再收敛。 | 导入边界不够清晰。 | 否 |

## 6. 推荐目标目录结构

```text
backend/
├── app.py
├── configs/
│   ├── database.yaml          # 本地、忽略
│   ├── database.example.yaml  # 脱敏模板
│   └── svn.example.yaml       # SVN 连接模板
├── audit/
│   ├── checks/
│   ├── prompts/
│   └── rules/
├── db/
├── metadata/
├── scripts/
├── data/                      # 运行数据，忽略相应数据库文件
└── logs/                      # 运行日志
```

## 7. 暂不处理的问题及原因

未拆分 `audit`、未重构数据库访问层、未调整路由或 API、未删除历史脚本。这些调整影响面较大，且不属于本次配置迁移的低风险范围。

## 8. 后续重构顺序

1. 归档或标注历史 `svn_check` 迁移文档。
2. 在独立任务中评估 Python 包安装与脚本导入路径收敛。

## 9. 配置与敏感信息风险

真实 `backend/configs/database.yaml` 已保留为本地忽略文件；模板文件使用占位值。审计未输出真实配置内容。Git 历史中曾出现配置类路径的风险需要在公开发布前按现有历史清理计划复核，本次未重写历史。

## 10. 启动入口审计

当前应用入口是 `backend/app.py`；`backend/scripts/start_backend.ps1` 定位自身后启动该入口。两者的数据库配置解析均通过 `db.profiles`，不会以当前工作目录推断默认配置路径。应用启动仍需要可用的数据库配置与可达数据库；本次未连接任何实际数据库。

## 11. 运行时目录审计

`backend/data/` 的数据库扩展名与 `backend/logs/*.log` 已被忽略，且仅保留 `backend/logs/.gitkeep`。未发现已跟踪的数据库、日志、覆盖率或 Python 缓存产物。`backend/.venv/` 是需要补齐忽略规则的例外。

## 12. 测试和脚本目录审计

测试位于顶级 `tests/`，未与生产包混放。数据库初始化、迁移和自检脚本集中在 `backend/scripts/`。SVN 配置虽然由 `audit.checks.svn_service` 读取，但它包含部署人员维护的外部连接、认证和工作区参数，因此与数据库配置一起归入 `backend/configs/`。
