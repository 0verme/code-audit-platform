# -*- coding: utf-8 -*-
import re
from dataclasses import replace
from pathlib import Path

from audit.rules.asset_issue import create_audit_asset_issue
from audit.checks.hcyt._sql_parser import detect_created_functions, detect_created_views, detect_used_functions
from audit.checks.hcyt.ddl_rule import check_table_name_rule, run_dws_ddl_rules
from metadata.services.public_data import all_function_names, all_sstb, all_tab_partitions, all_view_names
from audit.rules.portal_link_builder import build_portal_link
from svn_check.services.re_service import (
    detect_file_format,
    extract_tables,
    find_dot_strings,
    find_hardcoded_dates,
    match_any,
    read_data_from_file,
    safe_remove_prefix,
)

gjz_lists = [
    'DATETIME',
    'DUAL',
    'AGE',
    'LAST_DAY',
    'UTILS.DIDP_GAUSSDB_TOOLS',
    'UTILS.DATEUTILS',
    'UTILS.DIDP_BASE_FRAME',
    'UTILS.DIDP_PROCESS_TOOLS',
]


def build_asset_table_review_issues(table_names, source_module, source_file, issue_desc_prefix='SQL中识别到资产表待核对'):
    issues = []
    seen = set()
    for table_name in table_names or []:
        normalized_table_name = str(table_name).strip().upper()
        if not normalized_table_name or normalized_table_name in seen:
            continue
        seen.add(normalized_table_name)
        if '.' in normalized_table_name:
            schema_name, simple_table_name = normalized_table_name.split('.', 1)
        else:
            schema_name, simple_table_name = '', normalized_table_name
        issue = create_audit_asset_issue(
            issue_type='ASSET_TABLE_REVIEW',
            issue_title='资产表待核对',
            issue_desc=f"{issue_desc_prefix}：{normalized_table_name}",
            asset_type='table',
            source_module=source_module,
            source_file=source_file,
            severity='warning',
            suggestion='请到资产门户核对该表是否已登记，必要时补充资产表和字段信息',
            portal_module='data-warehouse',
            action_label='去核对资产表',
            schema_name=schema_name,
            table_name=simple_table_name,
        )
        issues.append(replace(issue, portal_url=build_portal_link(issue)))
    return issues


def get_program_table_name(py_url):
    folder = Path(py_url).parent.name
    schame, table_name = folder.split('.')
    schame = schame.replace('DWS_', '')
    return f'{schame}.{table_name}'


def has_partition_rollback_step(text):
    upper_text = text.upper()
    has_rollback_func = re.search(r'\bDEF\s+ROLLBACK_DEAL\s*\(', upper_text) is not None
    has_partition_op = any(keyword in upper_text for keyword in (
        'TRUNCATE PARTITION',
        'ADD PARTITION',
        'DROP PARTITION',
        'SPLIT PARTITION',
    ))
    return has_rollback_func and has_partition_op


def rule_sbin(sbin_url):
    print('===================================sbin_name=================================')
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    for i in sbin_url:
        data = read_data_from_file(i)
        if i.endswith('.py') and '\t' in data:
            reslut_text += f'{i}脚本含有TAB键，请替换成空格\n'
            cnt += 1
        if detect_file_format(i) == 'DOS':
            reslut_text += f'{i}编码是DOS不是UNIX请修改\n'
            cnt += 1
    return reslut_text, warn_result_text, cnt


def rule_config(config_names):
    print('===================================rule_config=================================')
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    for i in config_names:
        yuan = i.split('/')[-1]
        reslut_text += f'新增修改上下游源配置: {yuan} 请确认svn配置是否改成生产信息\n'
        cnt += 1
    return reslut_text, warn_result_text, cnt


def rule_recv_json(recv_lists):
    print('===================================rule_recv_json=================================')
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    for recv_url in recv_lists:
        data = read_data_from_file(recv_url)
        recv_url = safe_remove_prefix(recv_url)
        if '003.DLK_DLO.' in recv_url or '010.DWS_DWF.' in recv_url or 'LOCAL_' in recv_url:
            pass
        elif '"sql" : ""'.upper() not in data.upper():
            reslut_text += f' {recv_url}  是自定义卸数，请重点检查SCHAME是否是生产\n'
            cnt += 1
    return reslut_text, warn_result_text, cnt


def rule_dwf(dwf_url):
    print('===================================rule_dwf_py=================================')
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    data = read_data_from_file(dwf_url)
    if "SRC_TBL_ENG_NM = ''".upper() in data.upper() or "SRC_CD_FLD_ENG_NM = ''".upper() in data.upper():
        reslut_text += f' {dwf_url}  DWF的码值映射为空\n'
    return reslut_text, warn_result_text, cnt


def rule_dwo(dwo_url):
    print('===================================rule_dwo_py=================================')
    reslut_text = ''
    warn_result_text = ''
    cnt = 0
    data = read_data_from_file(dwo_url)
    if "版 本 号: v 1.0".upper() in data.upper() and "功能描述: 湖仓联通加工算法".upper() in data.upper():
        reslut_text += f' {dwo_url}  湖仓联通DWO不允许使用1.0版本\n'
    return reslut_text, warn_result_text, cnt


def rule_dws_py(dws_url):
    print('===================================rule_dws_py=================================')
    kk = all_sstb()
    result_text = ''
    warn_result_text = ''
    cnt = 0
    data = read_data_from_file(dws_url)
    view_names = set(str(r[0]).strip().upper() for r in all_view_names() if r and r[0])
    function_names = set(str(r[0]).strip().upper() for r in all_function_names() if r and r[0])
    raw_dws_url = dws_url
    result_table_name = get_program_table_name(raw_dws_url)
    dws_url = safe_remove_prefix(dws_url)
    result_table_name_message = check_table_name_rule(result_table_name)
    if result_table_name_message:
        result_text += f'{result_table_name_message}\n'
        cnt += 1
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_functions = detect_used_functions(data, function_names)
    if created_views:
        result_text += f'检测到创建视图，请重点审核: {",".join(created_views)}\n'
        cnt += 1
    if created_functions:
        result_text += f'检测到创建函数，请重点审核: {",".join(created_functions)}\n'
        cnt += 1
    if 'RECURSIVE' in data.upper():
        result_text += '检测到使用 recursive 递归语法，请重点确认是否必须使用递归\n'
        cnt += 1
    if 'FOR I IN' in data.upper():
        result_text += f'存在for循环 for i in 脚本不允许出现循环 如特殊情况需说明\n'
        cnt += 1
    if 'CHARACTER VARYING(' in data.upper():
        result_text += f'在程序里建表不要写死字段长度 CHARACTER VARYING( \n'
        cnt += 1
    if 'VARCHAR2(' in data.upper():
        result_text += f'在程序里建表不要写死字段长度 VARCHAR2(\n'
        cnt += 1
    if 'NVL(NVL(' in data.upper():
        result_text += f'多个NVL(NVL(的写法请用一个COALESCE函数代替\n'
        cnt += 1
    if 'COALESCE(COALESCE(' in data.upper():
        result_text += f'COALESCE(COALESCE( 别直接替换卡bug\n'
        cnt += 1
    if 'DISTINCT' in data.upper():
        warn_result_text += f'请审核重点检查脚本中的distinct是否必须添加 有无关联出重复数据\n'
        cnt += 1
    if '(+)' in data.upper():
        result_text += f'脚本中存在 (+) 这种写法维护性较差 请修改\n'
        cnt += 1
    if "影响条数" not in data.upper():
        result_text += f"模版太旧 请增加影响条数 LOG.info('影响条数:' + str(rownum))\n"
        cnt += 1
    if "TO GROUP GROUP_VERSION1" in data.upper():
        result_text += f"建表脚本中不允许出现 TO GROUP GROUP_VERSION1 请删除\n"
        cnt += 1
    py_ddl_rule_messages = []
    for message in run_dws_ddl_rules(data):
        if message not in py_ddl_rule_messages:
            py_ddl_rule_messages.append(message)
    for message in py_ddl_rule_messages:
        result_text += f'{message}\n'
        cnt += 1
    content = data[1000:]
    datekk = find_hardcoded_dates(content)
    datekk = ["'" + item + "'" for item in datekk]
    datekk = list(set(datekk))
    if len(datekk) > 0:
        result_text += f"检测到的写死日期 请甄别是否业务需求 (如果是注释日期去掉两头引号): {' '.join(datekk)} \n"
        cnt += 1

    tables = extract_tables(content)
    tables2 = find_dot_strings(content)
    tables_total = tables + tables2
    sql_table = [
        item for item in set(tables_total)
        if item.upper() not in {value.upper() for value in gjz_lists}
    ]
    used_views = sorted({item for item in sql_table if item.upper() in view_names})
    if used_views:
        result_text += f'检测到使用视图，请重点审核: {",".join(used_views)}\n'
        cnt += 1
    if used_functions:
        result_text += f'检测到使用函数，请重点审核: {",".join(used_functions)}\n'
        cnt += 1
    sql_table = [
        item for item in sql_table
        if item.upper() != result_table_name.upper() and item.upper() not in function_names
    ]

    fq_flag = has_partition_rollback_step(data)
    fq_flag2 = False
    schame, table_name = result_table_name.split('.')
    r = all_tab_partitions(f'{schame}.{table_name}')
    if r and r[0] and r[0][0] > 0:
        fq_flag2 = True
    if fq_flag2 != fq_flag:
        result_text += (f'{schame}.{table_name} 分区表应该增加分区步骤 rollback_deal 或者 结果表不是分区表不要加分区步骤\n')
        cnt += 1
    for i in sql_table:
        if i.upper() in gjz_lists:
            pass
        elif '.' not in i.upper():
            result_text += (f"表名 {i} 没有带 SCHAME请注意加上 如果是用with表注意效率\n")
            cnt += 1

    for i in kk:
        i = i[0]
        if i == '':
            continue
        if i.upper() in data.upper():
            result_text += (f'用错表 {i}')
            cnt += 1
    data = data.replace(' ', '').replace('\t', '').upper()
    if '=(SELECT' in data:
        result_text += (f"存在 = ( select 子查询 注意跑批效率 和 万一数据多条导致程序报错\n")
        cnt += 1
    data = data.replace('JOIN(SELECT', '')
    if 'IN(SELECT' in data:
        warn_result_text += (f"存在 in ( select 子查询 注意跑批效率\n")
        cnt += 1
    if '.END_DT>=' in data:
        result_text += (f"检测到 END_DT>= 注意拉链数据重复\n")
        cnt += 1
    if "D_DATE=TO_DATE('" in data:
        result_text += f"存在关键字 D_DATE=TO_DATE(' 使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if "D_DATE=DATE'" in data:
        result_text += f"存在关键 D_DATE = DATE' 使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if "DATE(D_DATE)" in data:
        result_text += f"存在关键 DATE(D_DATE) 使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if "TO_DATE(D_DATE," in data:
        result_text += f"存在关键 TO_DATE(D_DATE, 使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    data = data.replace('END_DATE', '').upper()
    if "D_DATE<" in data:
        result_text += f"存在关键字 D_DATE< 请检查，如果使用全量主题表 不允许使用区间\n"
        cnt += 1
    if "D_DATE>" in data:
        result_text += f"存在关键字 D_DATE> 请检查，如果使用全量主题表 不允许使用区间\n"
        cnt += 1
    return result_text, warn_result_text, cnt, sql_table
