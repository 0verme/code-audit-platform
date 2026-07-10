# P0/P1 证据复核与实施优先级校准

> 复核日期：2026-07-11。范围仅限当前工作树代码、测试、受跟踪配置和部署文档；未连接生产环境或读取生产日志。

## 1. 复核方法

- 静态追踪 Flask 路由到 `TaskRun.run()`、来源解析、workspace loader、任务完成持久化与 metadata 降级。
- 核对 README、`docs/deployment.md`、YAML、启动入口与测试。仓库未提供 Docker/Compose、systemd、Nginx 或 Gunicorn/Waitress 启动命令，相关部署事实不能由仓库确认。
- “已有测试”仅说明已有合同覆盖，不等同于真实 Flask、网络、多进程或事务故障覆盖。

## 2. 当前部署与运行假设

| 项目 | 可由代码/文档确认 | 仍需人工确认 |
|---|---|---|
| Flask | `backend/app.py` 直接执行时为 `0.0.0.0`、`debug=True`；模块导入会执行启动清理。 | 实际 WSGI 命令、debug/reloader、worker 数。 |
| 部署 | `docs/deployment.md` 仅示例 `python app.py`；README 泛称 Gunicorn/Waitress + Nginx，未给 worker 数。 | 反向代理、TLS、网络暴露、ACL。 |
| 数据库 | 部署文档要求 PostgreSQL/DWS 共用 profile；SQLite 仍是测试/兼容分支。README 还含旧 SQLite/`svn_check` 描述。 | 实际 profile、隔离级别、连接池和 DWS 限制。 |
| local 开关 | 前端 `VITE_ENABLE_LOCAL_SOURCE` 仅控制 UI；后端不读取该变量。 | 仓库外是否有鉴权/授权。 |

## 3. 重点复核结论

### local source 与无认证 API

`app.py` 的 `/api/*` 无认证，`CORS(... origins="*")`；创建任务接受多个本地路径别名，直接 API 能绕过 UI 开关。`workspace_service.py` 仅验证目录存在，`resolve()` 后递归 `os.walk()`；没有后端开关、allowlist、文件数/大小限制，也未显式拒绝 UNC、junction 或 symlink 越界。`resolve()` 不是授权边界。

| 场景 | 复核后严重度 | 判断 |
|---|---|---|
| 可信内网、单用户、loopback/受控账号 | P1 | 仍可读取服务账号可访问目录，主要为误操作/资源耗尽。 |
| 多用户内网 | P0 | 任一 API 访问者可触发服务账号目录扫描。 |
| 外网部署 | P0（条件成立时） | 无认证、任意 CORS 与 debug 可能暴露是高风险；仓库不能证明已外网暴露。 |

最小修复：后端默认拒绝 local，仅显式本地开发模式允许；对解析后路径做 allowlist 和逐文件边界校验，拒绝 UNC/链接越界并限额；生产 `debug=False`、明确 CORS origin。多用户/外网仍需认证授权。

### `fail_orphan_tasks()` 与多 worker

`app.py` 顶层无条件调用 `fail_orphan_tasks()`，其 SQL 将所有 `running/queued` 标为 fail。每次导入各执行一次：Waitress 单进程通常一次；Gunicorn 每个 worker 一次；多实例各一次；Flask reloader 也可能多次导入。`engine.start_task()` 是每任务 daemon thread，registry 只在本进程；后启动进程不会杀线程，但会改数据库行，原线程随后可 `finish()` 覆盖终态。

| 模式 | 风险/复核后严重度 |
|---|---|
| 单进程连续运行 | P1：无互杀，仍有无界线程。 |
| 单进程重启 | P1：线程已丢失，启动时保守标失败。 |
| 单机多 worker | P0：后 worker 失败化先 worker 活任务，后者可回写。 |
| 多实例/滚动发布 | P0：共享运行库上同样发生。 |

仓库没有真实多 worker 配置，不能称其为当前必发。若当前只支持单进程，最小修复就是：明确并校验单 worker 约束、移除 import-time 全量修改、改为显式恢复步骤；暂不引入 lease/heartbeat。owner/lease/heartbeat/CAS 留给多实例阶段。

### Git、lineage、SVN、事务与 metadata

- **Git：** 前端输入和 `auditSources.js` 展示/提交 Git；`resolve_workspace()` 仅分 `local`，其余均进 SVN loader，`normalize_source_payload()` 强制 `svn`。Git URL 确定进入 SVN CLI 并误标来源。结论：近期前后端一致禁用/明确拒绝 Git；不要保留前端可选、后端不可用。
- **lineage：** `mapping_compat.py`、`traversal.py` 默认路径均指向已删除的 `backend/svn_check`；`HEADER_ALIASES` 中文乱码，不能匹配正常中文 Excel。生产 HCYT 是否总走默认 SQLite 未获证明；默认调用必失败。测试多传临时路径，并从该常量自身构造表头。最小边界是修默认资源位置/配置、UTF-8 alias、真实中文 xlsx 与 default-path smoke；不重构 traversal。
- **SVN 日志：** `run_svn_text()` 在 start/end/exception/slow 都传完整 command；command 含 `--username`/`--password`。成功、异常和超时都会泄漏；内部 URL 也出现于结构化日志/print。受跟踪 `backend/audit/configs/svn.yaml` 密码为空但含内部 URL，未发现真实 secret；真实配置不应继续 Git 跟踪。最小修复是日志脱敏视图和四路径测试，不重写 service。
- **任务完成：** `persist_task_run_completion()` 先用一个连接提交 task，再用第二连接 delete/insert report；`replace_audit_results()` 第三个连接 delete 后逐行 insert，FineReport 明细另有独立路径。因此可有 success 无 report、report 新而 results 旧、删后插入失败；无 completion version，重试幂等性不明确。PostgreSQL/DWS/SQLite 尚未做三方真实故障注入，但多连接窗口三者都有。最小协议：同一 repository transaction 内 CAS/version 更新 task、upsert versioned report、批量替换明细；提交后才发布内存终态；跨库投影用可重放 completion version/outbox。
- **metadata：** `TaskRun.safe()` 可把异常变为 `[]/{}/None`；`re_service._safe_metadata_rows()` 异常后 warning + `[]`。runner 通常不能分辨真实空数据与失败，最终报告无统一覆盖面。最小状态为 `executed`、`skipped`、`degraded`、`failed` 与原因；task execution status 必须与 audit verdict 分离。

## 4. P0/P1 证据矩阵

| 原编号 | 原/复核后 | 关键代码证据 | 当前可复现/触发 | 当前影响 | 最小修复 | DB 迁移 | 前端 | 阶段 |
|---|---|---|---|---|---|---|---|---|
| P0-01 | P0/P0 条件化 | `app.py`、`workspace_service.py` | 是；API + local。跨用户取决于部署。 | 服务账号目录扫描/耗尽。 | 默认拒绝 local、allowlist、debug/CORS 默认。 | 否 | 是 | A |
| P0-02 | P0/P0 多 worker；P1 单进程 | `app.py`、`runtime_store.py`、`engine.py` | 是；第二导入/实例共享 DB。 | 活任务错误失败/回写。 | 单 worker 约束、移除 import-time 更新。 | 否 | 否 | B |
| P1-01 | P1/P0 功能阻断 | `auditSources.js`、`source_resolver.py` | 是；Git URL。 | Git 进 SVN/误标。 | 前后端拒绝 Git。 | 否 | 是 | A |
| P1-02 | P1/P1 | `mapping_compat.py`、`traversal.py` | 是；默认路径或中文 xlsx。 | 血缘资源不可用。 | 修路径/alias/smoke。 | 否 | 否 | A |
| P1-03 | P1/P1 | `svn_service.py`、`svn.yaml` | 是；有凭据运行 SVN。 | 命令日志泄密。 | 脱敏四路径。 | 否 | 否 | A |
| P1-04 | P1/P2 | `executor.py` 未接生产 | 仅未来启用 executor。 | 架构分叉。 | 冻结/注明实验路径。 | 否 | 否 | D |
| P1-05 | P1/P1 | `engine.py`、前端轮询 | 是；重复提交/慢依赖。 | 无取消/超时/背压。 | 状态机、deadline、上限/退避。 | 可能 | 是 | C |
| P1-06 | P1/P1 | `runtime_store.py`、`engine.py` | 是；任一写点失败。 | 终态/报告/明细不一致。 | 单事务+CAS，先故障基线。 | 可能 | 否 | A/C |
| P1-07 | P1/P2 | schemas、无分页查询 | 数据量/非法写入时。 | 性能/质量退化。 | 热点索引、约束、分页。 | 是 | 是 | D |
| P1-08 | P1/P1 | `metadata/services/public_data.py` | 是；异常标识符到 metadata。 | 查询失败/注入边界。 | identifier allowlist。 | 否 | 否 | B |
| P1-09 | P1/P1 | `app.py`、`run.py`、`useAuditRun.js` | 是；多别名 fallback。 | 契约漂移。 | 边界 DTO/schema。 | 否 | 是 | C |
| P1-10 | P1/P1 | tests 大量 mock | 是；未覆盖部署边界。 | 全绿仍集成失败。 | Flask+临时 DB+fixture。 | 否 | 可能 | A/C |
| P1-11 | P1/P1 | README/部署文档冲突 | 是；按 README 操作。 | 错误运维指引。 | 当前文档索引/路径检查。 | 否 | 否 | A |
| P1-12 | P1/P2 | `TaskRun`/37 项 context | 当前可见，扩展时放大。 | 扩展成本。 | 契约稳定后按端口拆。 | 否 | 否 | D |
| P1-13 | P1/P1 | `TaskRun.safe()`、`re_service.py` | 是；metadata 异常。 | 空结果误解为通过。 | coverage 状态/verdict 分离。 | 可能 | 是 | C |

## 5. 治理阶段、第一批、暂缓项与顺序

| 阶段 | 合并目标 | 包含 | 不包含 |
|---|---|---|---|
| A 安全默认值与明显契约 | 单机可修的输入、资源、泄密与基线。 | P0-01 最小默认值、P1-01/02/03、P1-06 设计/故障注入、P1-10 基线、P1-11。 | 鉴权选型、多实例、队列、traversal 重构。 |
| B 单进程边界 | 明确当前支持模型。 | P0-02 单 worker/显式恢复、P1-08。 | lease/heartbeat、分布式接管。 |
| C 可信完成与可解释审计 | 执行、结论、覆盖面与 API 收口。 | P1-05/06 实现/09/13/10 扩展。 | 全仓 DTO/TS、三工作流合并。 |
| D 扩展与性能 | 有真实需求后再做。 | P1-04/07/12、lease/heartbeat。 | Celery/Redis/Kafka，除非需求明确。 |

第一批应限制为：Git 前后端一致拒绝；lineage 默认资源和乱码 alias；SVN 日志脱敏；debug/CORS/local source 最小安全默认值；任务完成事务设计和故障注入测试基线。不要实施 Celery、Redis、Kafka、全量 DTO/Pydantic、全面 TypeScript、三工作流合并、`TaskRun` 大拆、schema 大重构或全仓格式化/改名。

暂不实施：Git loader、lease/heartbeat、executor 接入、完整取消重试状态机、全量索引/约束、`TaskRun` 重构和外部队列。

仍需人工确认：实际 WSGI 命令/worker 数；debug/reloader；反向代理和公网可达性；已有 SSO/ACL；服务账号目录权限与可审计根；生产日志/历史泄漏；实际 DB profile/隔离级别；第二实例/滚动发布是否存在。

最终建议顺序：先完成 A 的五项与测试基线；确认部署事实后完成 B；再做 C；只有确认多实例或容量需求时进入 D。
