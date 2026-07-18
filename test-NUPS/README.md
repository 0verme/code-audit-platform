# NUPS 本地审查全规则样例

在前端选择“NUPS 统一报送平台审查”和“本地目录”，使用：

`E:\AI生成代码\code-audit-platform\test-NUPS\local-nups-workspace`

样例只用于触发审计规则，不能作为生产 SQL 或加工模板使用。

## 样例分布

- `NUPS_DATA/pboc.sql`：覆盖 NUPS SQL、DDL、遗留标记和保护码表规则。
- `NUPS_DATA/cbrc.sql`：合规 SQL，用于验证空问题列表。
- `NUPS_DATA/DWS_DWM.BAD_NUPS_RESULT/001_bad_nups.py`：覆盖加工程序与结果表命名规则。
- `NUPS_DATA/DWS_DWF.F_GOOD_NUPS_RESULT/002_good_nups.py`：合规程序，用于验证无问题状态及结果表名解析。

## 预期 SQL 规则

- `nups.sql.create_view`
- `nups.sql.create_function`
- `nups.sql.alter_statement`
- `nups.sql.dwm_operation`
- `nups.sql.legacy_group_clause`
- `nups.sql.legacy_marker`
- `nups.sql.protected_code_table`
- `nups.ddl.table_name`
- `nups.ddl.temp_table_name`
- `nups.ddl.column_comment`

## 预期加工程序规则

- `nups.program.create_view`
- `nups.program.create_function`
- `nups.program.for_loop`
- `nups.program.character_varying_length`
- `nups.program.varchar2_length`
- `nups.program.nested_nvl`
- `nups.program.nested_coalesce`
- `nups.program.distinct_review`
- `nups.program.legacy_outer_join`
- `nups.program.affected_rows_log`
- `nups.program.legacy_group_clause`
- `nups.program.hardcoded_date`
- `nups.program.missing_schema`
- `nups.program.scalar_subquery`
- `nups.program.in_subquery`
- `nups.program.end_dt_range`
- `nups.program.d_date_to_date`
- `nups.program.d_date_literal`
- `nups.program.d_date_function`
- `nups.program.to_date_d_date`
- `nups.program.d_date_less_than`
- `nups.program.d_date_greater_than`

加工程序还会复用 DDL 规则，并通过目录 `DWS_DWM.BAD_NUPS_RESULT` 触发结果表命名错误。

## 环境相关或刻意跳过

使用生产视图/函数、错误表、分区回滚依赖当前生产元数据，不作为必现项。超过 20000 行规则也未造大文件。

## 验收方式

1. 页面应识别 2 个 SQL 和 2 个 Python 文件，不应出现 HCYT 的 Hive、调度、配置或后置脚本。
2. `pboc.sql` 和 `001_bad_nups.py` 应展示上述错误。
3. `cbrc.sql` 与 `002_good_nups.py` 应保留为空问题列表。
4. 两个 Python 条目的结果表应分别解析为 `DWM.BAD_NUPS_RESULT` 与 `DWF.F_GOOD_NUPS_RESULT`。
