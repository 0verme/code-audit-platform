# 任务完成原子性设计（A5 基线）

本文件记录 A5 的真实 SQLite 故障注入证据和后续 A6 的设计目标；它不是对当前实现的正确性背书。本阶段没有修改生产持久化逻辑。

## 当前完成链路

```text
TaskRun.run()
  -> run_workflow()：HCYT / NUPS / FineReport
     -> context.save_category_rows() -> replace_audit_results() [连接 C3]
  -> finalize_run_result()
  -> TaskRun.finish()
     -> AuditRunState.mark_finished()（内存终态先发布）
     -> persist_task_run_completion()
        -> finalize_task() [连接 C1，提交]
        -> upsert_task_report() [连接 C2，delete + insert 后提交]
```

因此实际正常顺序为：兼容 `audit_results` 先写入，随后 task 和 canonical `task_reports` 写入。A5-05 也刻意验证了调用者若在 report 已提交后再写兼容明细，仍可产生 report 新、results 旧的可见状态。`fine_report_items` 是独立的 FineReport 读取投影，当前 runner 不通过 `TaskRun.finish()` 写入它；其种子/其他写入路径也不在 task completion transaction 中。

HCYT 使用 `sync_hcyt_legacy_results(... save_category_rows ...)`，NUPS 直接调用 `save_category_rows(build_legacy_nups_audit_result_rows(...))`，FineReport 直接调用 `save_category_rows(build_legacy_fine_audit_result_rows(...))`。三条调用合同分别已有 `tests/test_hcyt_runner_contract.py`、`tests/test_nups_runner_contract.py`、`tests/test_fine_runner_contract.py` 覆盖。

## 当前事务边界

| 写入对象 | 函数 | connection | transaction | 当前提交顺序 |
| --- | --- | --- | --- | --- |
| `audit_tasks` 终态 | `finalize_task()` | C1 `get_connection()` | context manager | 先提交 |
| `task_reports` | `upsert_task_report()` | C2 `get_connection()` | delete + insert 同一局部事务 | C1 后提交 |
| `audit_results` | `replace_audit_results()` | C3 `get_connection()` | delete + 全部逐行 insert 同一局部事务 | workflow 中先于 C1/C2；也可被其他调用者后写 |
| FineReport 投影 | `fine_report_items` 读路径 | 非 completion helper | 未纳入本链路 | 独立 |

SQLite 基线证明 C2/C3 内部的 delete/insert 会一起 rollback，但无法回滚已经由 C1 提交的数据。每个 `with get_connection()` 在无异常时 commit、有异常时 rollback，异常由 helper 向上传播；`TaskRun.run()` 的外层 `except` 会尝试写失败 completion，但若 `finish()` 本身持久化失败，该异常会继续离开该调用。

## 故障矩阵（来自 `tests/test_task_completion_atomicity_baseline.py`）

| 故障点 | task | report | results | 内存状态 | 用户可能看到的结果 |
| --- | --- | --- | --- | --- | --- |
| 无故障 | `pass` | 新版本 | 新版本 | 不涉及 | 三者一致 |
| task 提交后 report insert 失败 | `pass` 已提交 | 旧版本仍在 | 旧版本 | 不涉及 | 终态 task 缺少新 report |
| report delete 后、insert 前失败 | 不变 | 旧 report 被局部 rollback 恢复 | 不变 | 不涉及 | C2 自身无缺失 report |
| results 第二行 insert 失败 | 不变 | 不变 | 旧 rows 被局部 rollback 恢复 | 不涉及 | C3 自身没有部分 rows |
| report 成功后 results 失败 | `pass` | 新版本 | 旧版本 | 不涉及 | canonical 与 legacy 不一致 |
| 重复不同 payload completion | 最后一次时间 | 最后一次 | 最后一次 | 不涉及 | 没有重复行，但无显式幂等/CAS 语义 |
| `TaskRun.finish()` 持久化失败 | 未由该测试写库 | 未由该测试写库 | 未由该测试写库 | 已为 `success` | 内存状态可先于 DB 完成发布 |

## A6 目标不变量

1. 终态 task 不能在 report 缺失时对外表示完成。
2. canonical report 与兼容明细必须来自同一 completion version。
3. 同一 completion 的重复提交必须幂等。
4. 旧 worker/旧版本完成不得覆盖更新版本。
5. 只有 DB commit 成功后才能发布内存终态。
6. 失败时必须全部回滚，或保持可安全重放的 pending 状态。
7. API 不能同时暴露互相矛盾的 canonical 与 legacy 结果。

## 推荐最小实现（仅设计）

优先在同一 runtime DB 中提供一个原子 completion repository API：单 connection、单 transaction 内以条件更新（或 completion version）更新 task，真正 upsert report，批量替换 `audit_results`，随后 commit，再发布内存终态。FineReport 专属明细要么纳入同一事务，要么明确为带 completion version 的可重放投影。只有确认写入跨不同数据库时，才把 outbox/可重放投影列为后续备选，不在本阶段引入分布式事务、消息队列或两阶段提交。

## 数据库适用范围

SQLite 的局部事务回滚和三连接提交窗口已由 A5 真实临时数据库测试证明。PostgreSQL 可依据 psycopg 默认 `autocommit=False` 与本项目 `CompatConnection` context-manager 行为合理推断相同的单连接 commit/rollback 结构，但尚未做集成故障验证。DWS 仍需要真实环境验证隔离级别、驱动和批量写入行为；不得把 SQLite 结果称为 DWS 生产证明。

## 后续实施拆分

| 阶段 | 范围 | 回滚点 |
| --- | --- | --- |
| A6-1 | 增加原子 completion repository API | 保留旧 helper，feature-scoped 回退 |
| A6-2 | 迁移通用 task/report 写入 | 回退到旧 completion 调用点 |
| A6-3 | 迁移 `audit_results` 批量投影 | 回退 legacy 投影适配层 |
| A6-4 | 迁移 FineReport 专属明细 | 回退独立投影路径 |
| A6-5 | 改为 commit 后发布内存终态 | 回退 run-state 发布位置 |
| A6-6 | PG/DWS 集成故障验证 | 不改变 SQLite 已验证基线 |
