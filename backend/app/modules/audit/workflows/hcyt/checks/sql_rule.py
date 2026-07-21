# -*- coding: utf-8 -*-
from dataclasses import replace

from app.modules.audit.rules.asset_issue import create_audit_asset_issue
from app.modules.audit.rules.portal_link_builder import build_portal_link
from app.modules.metadata.services.public_data import all_function_names, all_view_names
from app.modules.audit.shared.dws_sql_review import run_configured_dws_sql_reviews
from app.modules.audit.shared.file_analysis import find_dot_strings, read_data_from_file
from app.modules.audit.shared.findings import CheckResult

from ._sql_parser import detect_created_functions, detect_created_views, detect_used_functions
from ._sql_parser import split_schema_table
from .ddl_rule import (
    extract_create_table_objects,
    is_asset_review_required_table,
    load_metadata_name_set,
    run_dws_ddl_rules,
)
from .sensitive_sql import scan_sensitive_sql


def _build_asset_table_review_issue(full_table_name, source_module, source_file, issue_desc):
    schema_name, table_name = split_schema_table(full_table_name)
    issue = create_audit_asset_issue(
        issue_type='ASSET_TABLE_REVIEW',
        issue_title='资产表待核对',
        issue_desc=issue_desc,
        asset_type='table',
        source_module=source_module,
        source_file=source_file,
        severity='warning',
        suggestion='请到资产门户核对该表是否已登记，必要时补充资产表和字段信息',
        portal_module='data-warehouse',
        action_label='去核对资产表',
        schema_name=schema_name,
        table_name=table_name or full_table_name,
    )
    return replace(issue, portal_url=build_portal_link(issue))


def collect_created_table_review_issues(dws_url, source_module='hcyt', source_file=None):
    data = read_data_from_file(dws_url)
    source_file = source_file or dws_url
    issues = []
    for item in extract_create_table_objects(data):
        full_table_name = item['table_name']
        if not is_asset_review_required_table(full_table_name):
            continue
        issues.append(
            _build_asset_table_review_issue(
                full_table_name=full_table_name,
                source_module=source_module,
                source_file=source_file,
                issue_desc=f"建表语句涉及资产表待核对：{full_table_name}",
            )
        )
    return issues


def rule_dws(dws_url):
    print('===================================rule_dws=================================')
    data = read_data_from_file(dws_url)
    result = CheckResult()
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_views = sorted({item for item in find_dot_strings(data.upper()) if item.upper() in view_names})
    used_functions = detect_used_functions(data, function_names)
    result.add('hcyt.sql.file_present', 'DWS SQL 文件', 'info', '存在dws.sql')
    if created_views:
        result.add('hcyt.sql.create_view', '创建视图', 'err', f'检测到创建视图，请重点审核: {",".join(created_views)}')
    if created_functions:
        result.add('hcyt.sql.create_function', '创建函数', 'err', f'检测到创建函数，请重点审核: {",".join(created_functions)}')
    if used_views:
        result.add('hcyt.sql.use_view', '使用视图', 'err', f'检测到使用视图，请重点审核: {",".join(used_views)}')
    if used_functions:
        result.add('hcyt.sql.use_function', '使用函数', 'err', f'检测到使用函数，请重点审核: {",".join(used_functions)}')
    if len(data.split('\n')) > 20000:
        result.add('hcyt.sql.too_many_lines', 'SQL 行数过多', 'err', '行数过多,大批量sql请上线人员操作')
    result.findings.extend(scan_sensitive_sql(data, namespace='hcyt.sql'))
    if 'dwm.'.upper() in data.upper():
        result.add('hcyt.sql.dwm_operation', 'DWM 模型层操作', 'warn', '存在对dwm模型层的操作,请审核重点检查')
    if 'TO GROUP GROUP_VERSION1'.upper() in data.upper():
        result.add('hcyt.sql.legacy_group_clause', '旧版 GROUP 子句', 'err', '建表脚本不允许带 TO GROUP GROUP_VERSION1')
    result.findings.extend(run_configured_dws_sql_reviews(data, message_style="hcyt"))

    seen = {(item.rule_code, item.msg) for item in result.findings}
    for finding in run_dws_ddl_rules(data):
        key = (finding.rule_code, finding.msg)
        if key not in seen:
            result.findings.append(finding)
            seen.add(key)
    return result


def rule_hive(hive_url):
    data = read_data_from_file(hive_url)
    result = CheckResult()
    result.add('hcyt.hive.file_present', 'Hive SQL 文件', 'info', '存在hive.sql')
    if len(data.split('\n')) > 20000:
        result.add('hcyt.hive.too_many_lines', 'SQL 行数过多', 'err', '行数过多,大批量sql请上线人员操作')
    if 'varchar2'.upper() in data.upper():
        result.add('hcyt.hive.varchar2_type', 'VARCHAR2 字段类型', 'err', '湖脚本不允许VARCHAR2类型的字段')
    result.findings.extend(scan_sensitive_sql(data, namespace='hcyt.hive'))
    return result
