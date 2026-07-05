# 函数级差异快照

比对时间：2026-07-05。

比对范围：

- 旧平台：`E:\AI生成代码\pytools_new\apps\svn_check`
- 新平台：`E:\AI生成代码\代码审查平台\backend\svn_check`

说明：

- 本快照只做只读扫描。
- 未输出敏感配置值。
- 文件一致性使用 SHA256 判断。
- 函数差异使用顶层 `def` / `class` 名称和块级哈希判断。
- 该快照不能替代逐行代码评审，尤其不能直接作为覆盖依据。

## 总体结论

新平台缺失旧平台 P0 新增能力：

- `core/asset_issue.py`
- `services/portal_link_builder.py`
- `services/workspace_service.py`
- `services/db_profile.py`
- `services/audit_metadata_service.py`

同名但不可直接覆盖的文件：

- `core/public_data.py`
- `core/hcyt/ddl_rule.py`
- `core/hcyt/sql_rule.py`
- `core/hcyt/python_rule.py`
- `core/hcyt/schedule_rule.py`
- `services/re_service.py`
- `services/svn_service.py`

同名且当前完全一致的文件：

- `core/fine_rule.py`
- `core/nups_rule.py`

## 文件级差异表

| 文件 | 同名文件存在 | 文件完全一致 | 旧平台有、新平台没有 | 新平台有、旧平台没有 | 两边都有但实现不同 |
|---|---:|---:|---|---|---|
| `core/asset_issue.py` | 否 | 否 | `_clean_text`, `AuditAssetIssue`, `build_issue_hash_key`, `build_issue_key`, `create_audit_asset_issue`, `dedupe_issues` | 无 | 不适用 |
| `core/public_data.py` | 是 | 否 | `all_result_table_recv_details` | 无 | `all_fine`, `all_function_names`, `all_job_outfile`, `all_para_table_lists`, `all_recv_mapping_plans`, `all_result_table_sys_names`, `all_role`, `all_tab_partitions`, `all_term_roots`, `all_view_names`, `get_job2` |
| `core/hcyt/ddl_rule.py` | 是 | 否 | `_build_root_missing_issue`, `collect_root_missing_issues` | 无 | 未发现顶层同名函数块差异 |
| `core/hcyt/sql_rule.py` | 是 | 否 | `_build_asset_table_review_issue`, `collect_created_table_review_issues` | 无 | 未发现顶层同名函数块差异 |
| `core/hcyt/python_rule.py` | 是 | 否 | `build_asset_table_review_issues` | 无 | 未发现顶层同名函数块差异 |
| `core/hcyt/schedule_rule.py` | 是 | 否 | 无 | 无 | `_find_online_job_dependency_cycles` |
| `core/fine_rule.py` | 是 | 是 | 无 | 无 | 无 |
| `core/nups_rule.py` | 是 | 是 | 无 | 无 | 无 |
| `services/portal_link_builder.py` | 否 | 否 | `_build_url`, `build_data_warehouse_link`, `build_portal_link`, `build_root_management_link`, `get_portal_base_url` | 无 | 不适用 |
| `services/workspace_service.py` | 否 | 否 | `_build_workspace_info`, `load_local_workspace`, `load_svn_workspace`, `WorkspaceInfo` | 无 | 不适用 |
| `services/db_profile.py` | 否 | 否 | `get_active_audit_profile`, `get_active_audit_profile_name`, `get_active_backend`, `is_gauss_jdbc_profile`, `is_postgres_profile`, `load_audit_datasource_config` | 无 | 不适用 |
| `services/audit_metadata_service.py` | 否 | 否 | `_get_gauss_profile_name`, `_normalize_single_column_rows`, `list_function_names`, `list_job_outfiles`, `list_para_table_names`, `list_recv_mapping_plans`, `list_result_table_recv_details`, `list_result_table_sys_names`, `list_term_roots`, `list_view_names` | 无 | 不适用 |
| `services/re_service.py` | 是 | 否 | `build_job_outfile_lookup`, `build_wide_table_lineage_summary` | 无 | 未发现顶层同名函数块差异 |
| `services/svn_service.py` | 是 | 否 | 无 | 无 | 未发现顶层同名函数块差异 |

## 不能直接覆盖的文件

以下文件不能直接从旧平台覆盖到新平台：

- `core/public_data.py`：新平台已适配 `shared/db/router.py`，旧平台依赖 `db_profile.py` 和 `audit_metadata_service.py`。
- `core/hcyt/ddl_rule.py`：旧平台新增资产 issue / 词根缺失结构化输出，新平台已有旧版规则。
- `core/hcyt/sql_rule.py`：旧平台新增资产表待核对结构化 issue。
- `core/hcyt/python_rule.py`：旧平台新增资产表待核对结构化 issue。
- `core/hcyt/schedule_rule.py`：同名函数 `_find_online_job_dependency_cycles` 实现不同。
- `services/re_service.py`：旧平台新增 outfile lookup 和宽表链路摘要，新平台已有简化版。
- `services/svn_service.py`：同名函数一致但文件哈希不同，需逐行确认配置路径和部署适配差异。

## 适合逐函数迁移的文件

- `core/asset_issue.py`：新平台缺失，适合整体新增后接测试。
- `services/portal_link_builder.py`：新平台缺失，适合整体新增但必须脱敏配置。
- `services/workspace_service.py`：适合迁移 `load_local_workspace`，但 API 接入要重写。
- `services/db_profile.py`：不建议原样迁移，适合抽取 profile 语义并并入新平台 DB router 设计。
- `services/audit_metadata_service.py`：适合逐函数迁移到新平台服务层。
- `services/re_service.py`：适合迁移 `build_job_outfile_lookup`、`build_wide_table_lineage_summary`。
- `core/hcyt/ddl_rule.py`：适合迁移 `_build_root_missing_issue`、`collect_root_missing_issues`。
- `core/hcyt/sql_rule.py`：适合迁移 `_build_asset_table_review_issue`、`collect_created_table_review_issues`。
- `core/hcyt/python_rule.py`：适合迁移 `build_asset_table_review_issues`。

## 适合以新版为准的文件

- `backend/svn_check/shared/db/router.py`
- `backend/svn_check/shared/db/postgres.py`
- `backend/svn_check/shared/db/gaussdb.py`
- `backend/svn_check/shared/lineage/mapping_sqlite.py`
- `backend/svn_check/shared/graph/dependency.py`
- `backend/svn_check/migrate/postgres_schema.sql`
- `core/fine_rule.py`
- `core/nups_rule.py`

这些文件要么是新平台专有能力，要么当前与旧平台完全一致，不需要从旧平台覆盖。

## 后续建议

1. 先执行 P0-2，迁移资产 issue、词根缺失、门户链接。
2. 再执行 P0-3，把本地目录能力接入新平台 API。
3. P0-4 先做 DB profile 设计，不直接改真实配置。
4. P0-5 再迁移元数据服务和宽表链路摘要。
5. 每一轮只迁移明确函数，不做整文件覆盖。
