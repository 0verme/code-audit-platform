# -*- coding: utf-8 -*-
from dataclasses import replace

from core.asset_issue import create_audit_asset_issue
from core.hcyt._sql_parser import detect_created_functions, detect_created_views, detect_used_functions
from core.hcyt._sql_parser import split_schema_table
from core.hcyt.ddl_rule import extract_create_table_objects, load_metadata_name_set, run_dws_ddl_rules
from core.public_data import all_function_names, all_view_names
from services.portal_link_builder import build_portal_link
from services.re_service import find_dot_strings, read_data_from_file


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
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_views = sorted({item for item in find_dot_strings(data.upper()) if item.upper() in view_names})
    used_functions = detect_used_functions(data, function_names)
    warn_result_text += f'存在dws.sql\n'
    if created_views:
        reslut_text += f'检测到创建视图，请重点审核: {",".join(created_views)}\n'
        cnt += 1
    if created_functions:
        reslut_text += f'检测到创建函数，请重点审核: {",".join(created_functions)}\n'
        cnt += 1
    if used_views:
        reslut_text += f'检测到使用视图，请重点审核: {",".join(used_views)}\n'
        cnt += 1
    if used_functions:
        reslut_text += f'检测到使用函数，请重点审核: {",".join(used_functions)}\n'
        cnt += 1
    if len(data.split('\n')) > 20000:
        reslut_text += f'行数过多,大批量sql请上线人员操作\n'
        cnt += 1
    if 'alter'.upper() in data.upper():
        reslut_text += f'存在alter命令,请审核重点检查\n'
        cnt += 1
    if 'dwm.'.upper() in data.upper():
        reslut_text += f'存在对dwm模型层的操作,请审核重点检查\n'
        cnt += 1
    if 'TO GROUP GROUP_VERSION1'.upper() in data.upper():
        reslut_text += f'建表脚本不允许带 TO GROUP GROUP_VERSION1\n'
        cnt += 1
    if 'WLQ'.upper() in data.upper():
        reslut_text += f'建表脚本带WLQ,请确认是不是取数单的表名没改\n'
        cnt += 1
    if 'LZY'.upper() in data.upper() and 'RLZY' not in data.upper():
        reslut_text += f'建表脚本带LZY,请确认是不是取数单的表名没改\n'
        cnt += 1
    if 'BSC'.upper() in data.upper():
        reslut_text += f'建表脚本带BSC,请确认是不是取数单的表名没改\n'
        cnt += 1
    if 'YGW'.upper() in data.upper():
        reslut_text += f'建表脚本带YGW,请确认是不是取数单的表名没改\n'
        cnt += 1
    if 'TMPQS'.upper() in data.upper():
        reslut_text += f'建表脚本带TMPQS,请确认是不是取数单的表名没改\n'
        cnt += 1
    if 'DWM.M_PUB_CODE_MAP_NEW' in data.upper():
        reslut_text += f'存在码值表M_PUB_CODE_MAP_NEW修改,请审核重点检查\n'
        cnt += 1
    if 'DWM.M_PUB_CODE_INFO_NEW' in data.upper():
        reslut_text += f'存在码值表M_PUB_CODE_INFO_NEW修改,请审核重点检查\n'
        cnt += 1
    if 'DWM.M_PUB_CODE_USE_NEW' in data.upper():
        reslut_text += f'存在码值表M_PUB_CODE_USE_NEW修改,请审核重点检查\n'
        cnt += 1

    ddl_rule_messages = []
    for message in run_dws_ddl_rules(data):
        if message not in ddl_rule_messages:
            ddl_rule_messages.append(message)
    if ddl_rule_messages:
        if reslut_text and not reslut_text.endswith('\n'):
            reslut_text += '\n'
        reslut_text += '\n'.join(ddl_rule_messages) + '\n'
        cnt += len(ddl_rule_messages)
    return reslut_text, warn_result_text, cnt


def rule_hive(hive_url):
    data = read_data_from_file(hive_url)
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    warn_result_text += f'存在hive.sql\n'
    if len(data.split('\n')) > 20000:
        reslut_text += f'行数过多,大批量sql请上线人员操作\n'
        cnt += 1
    if 'varchar2'.upper() in data.upper():
        reslut_text += f'湖脚本不允许VARCHAR2类型的字段\n'
        cnt += 1
    if 'alter'.upper() in data.upper():
        reslut_text += f'存在alter命令,请审核重点检查\n'
        cnt += 1
    return reslut_text, warn_result_text, cnt
