# -*- coding: utf-8 -*-
import re
import time
from dataclasses import replace
from pathlib import Path

from app.modules.audit.rules.asset_issue import create_audit_asset_issue
from ._sql_parser import detect_created_functions, detect_created_views, detect_used_functions
from ._sql_parser import normalize_sql_table_name, split_schema_table
from .ddl_rule import (
    check_table_name_rule,
    is_asset_review_required_table,
    run_dws_ddl_rules,
)
from app.modules.metadata.services.public_data import all_function_names, all_sstb, all_tab_partitions, all_view_names
from app.modules.audit.rules.portal_link_builder import build_portal_link
from ....shared.findings import CheckResult
from ....shared.file_analysis import (
    detect_file_format,
    extract_tables,
    find_dot_strings,
    find_hardcoded_dates,
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


def _timed(label, fn, log_timing=None, result_fields=None, **fields):
    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, 'start', **fields)
    result = None
    try:
        result = fn()
        return result
    finally:
        if log_timing is not None:
            end_fields = dict(fields)
            if result_fields is not None and result is not None:
                end_fields.update(result_fields(result))
            end_fields['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 1)
            log_timing(label, 'end', **end_fields)


def _load_cached_metadata(cache, key, label, loader, log_timing=None, result_fields=None, **fields):
    cache_hit = key in cache

    def load():
        if cache_hit:
            return cache[key]
        value = loader()
        cache[key] = value
        return value

    return _timed(
        label,
        load,
        log_timing,
        result_fields=result_fields,
        cache_hit=cache_hit,
        **fields,
    )


def build_asset_table_review_issues(table_names, source_module, source_file, issue_desc_prefix='SQL中识别到资产表待核对'):
    issues = []
    seen = set()
    for table_name in table_names or []:
        normalized_table_name = normalize_sql_table_name(table_name)
        if not normalized_table_name or normalized_table_name in seen:
            continue
        seen.add(normalized_table_name)
        if not is_asset_review_required_table(normalized_table_name):
            continue
        schema_name, simple_table_name = split_schema_table(normalized_table_name)
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
    result = CheckResult()
    for i in sbin_url:
        data = read_data_from_file(i)
        if i.endswith('.py') and '\t' in data:
            result.add('hcyt.sbin.tab_character', '脚本 TAB 字符', 'err', f'{i}脚本含有TAB键，请替换成空格', file=i)
        if detect_file_format(i) == 'DOS':
            result.add('hcyt.sbin.dos_format', '脚本文件格式', 'err', f'{i}编码是DOS不是UNIX请修改', file=i)
    return result


def rule_config(config_names):
    print('===================================rule_config=================================')
    result = CheckResult()
    for i in config_names:
        yuan = i.split('/')[-1]
        result.add(
            'hcyt.config.production_source',
            '上下游生产配置',
            'warn',
            f'新增修改上下游源配置: {yuan} 请确认svn配置是否改成生产信息',
            file=i,
        )
    return result


def rule_recv_json(recv_lists):
    print('===================================rule_recv_json=================================')
    result = CheckResult()
    for recv_url in recv_lists:
        data = read_data_from_file(recv_url)
        recv_url = safe_remove_prefix(recv_url)
        if '003.DLK_DLO.' in recv_url or '010.DWS_DWF.' in recv_url or 'LOCAL_' in recv_url:
            pass
        elif '"sql" : ""'.upper() not in data.upper():
            result.add(
                'hcyt.recv.custom_export',
                '自定义卸数配置',
                'err',
                f' {recv_url}  是自定义卸数，请重点检查SCHAME是否是生产',
                file=recv_url,
            )
    return result


def rule_dwf(dwf_url):
    print('===================================rule_dwf_py=================================')
    result = CheckResult()
    data = read_data_from_file(dwf_url)
    if "SRC_TBL_ENG_NM = ''".upper() in data.upper() or "SRC_CD_FLD_ENG_NM = ''".upper() in data.upper():
        result.add('hcyt.dwf.empty_code_mapping', 'DWF 码值映射', 'err', f' {dwf_url}  DWF的码值映射为空', file=dwf_url)
    return result


def rule_dwo(dwo_url):
    print('===================================rule_dwo_py=================================')
    result = CheckResult()
    data = read_data_from_file(dwo_url)
    if "版 本 号: v 1.0".upper() in data.upper() and "功能描述: 湖仓联通加工算法".upper() in data.upper():
        result.add('hcyt.dwo.legacy_version', 'DWO 模板版本', 'err', f' {dwo_url}  湖仓联通DWO不允许使用1.0版本', file=dwo_url)
    return result


def rule_dws_py(dws_url, *, log_timing=None, file_name=None, metadata_cache=None):
    print('===================================rule_dws_py=================================')
    timing_fields = {'file': file_name} if file_name else {}
    metadata_cache = metadata_cache if metadata_cache is not None else {}
    kk = _load_cached_metadata(
        metadata_cache,
        'sstb_rows',
        'programs.file.rule.load_sstb',
        all_sstb,
        log_timing,
        result_fields=lambda rows: {'rows': len(rows or [])},
        **timing_fields,
    )
    result = CheckResult()
    data = _timed(
        'programs.file.rule.read_source',
        lambda: read_data_from_file(dws_url),
        log_timing,
        result_fields=lambda text: {'chars': len(text or '')},
        **timing_fields,
    )
    rule_evaluation_started = time.perf_counter()
    if log_timing is not None:
        log_timing('programs.file.rule.evaluate', 'start', **timing_fields)
    view_names = _load_cached_metadata(
        metadata_cache,
        'view_names',
        'programs.file.rule.load_view_names',
        lambda: {str(r[0]).strip().upper() for r in all_view_names() if r and r[0]},
        log_timing,
        result_fields=lambda names: {'rows': len(names)},
        **timing_fields,
    )
    function_names = _load_cached_metadata(
        metadata_cache,
        'function_names',
        'programs.file.rule.load_function_names',
        lambda: {str(r[0]).strip().upper() for r in all_function_names() if r and r[0]},
        log_timing,
        result_fields=lambda names: {'rows': len(names)},
        **timing_fields,
    )
    raw_dws_url = dws_url
    result_table_name = get_program_table_name(raw_dws_url)
    dws_url = safe_remove_prefix(dws_url)
    result_table_name_message = check_table_name_rule(result_table_name)
    if result_table_name_message:
        result.findings.append(result_table_name_message)
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_functions = detect_used_functions(data, function_names)
    if created_views:
        result.add('hcyt.program.create_view', '创建视图', 'err', f'检测到创建视图，请重点审核: {",".join(created_views)}')
    if created_functions:
        result.add('hcyt.program.create_function', '创建函数', 'err', f'检测到创建函数，请重点审核: {",".join(created_functions)}')
    if 'RECURSIVE' in data.upper():
        result.add('hcyt.program.recursive_query', '递归查询', 'err', '检测到使用 recursive 递归语法，请重点确认是否必须使用递归')
    if 'FOR I IN' in data.upper():
        result.add('hcyt.program.for_loop', 'FOR 循环', 'err', '存在for循环 for i in 脚本不允许出现循环 如特殊情况需说明')
    if 'CHARACTER VARYING(' in data.upper():
        result.add('hcyt.program.character_varying_length', '字段长度写死', 'err', '在程序里建表不要写死字段长度 CHARACTER VARYING( ')
    if 'VARCHAR2(' in data.upper():
        result.add('hcyt.program.varchar2_length', '字段长度写死', 'err', '在程序里建表不要写死字段长度 VARCHAR2(')
    if 'NVL(NVL(' in data.upper():
        result.add('hcyt.program.nested_nvl', '嵌套 NVL', 'err', '多个NVL(NVL(的写法请用一个COALESCE函数代替')
    if 'COALESCE(COALESCE(' in data.upper():
        result.add('hcyt.program.nested_coalesce', '嵌套 COALESCE', 'err', 'COALESCE(COALESCE( 别直接替换卡bug')
    if 'DISTINCT' in data.upper():
        result.add('hcyt.program.distinct_review', 'DISTINCT 审查', 'warn', '请审核重点检查脚本中的distinct是否必须添加 有无关联出重复数据')
    if '(+)' in data.upper():
        result.add('hcyt.program.legacy_outer_join', '旧式外连接', 'err', '脚本中存在 (+) 这种写法维护性较差 请修改')
    if "影响条数" not in data.upper():
        result.add('hcyt.program.affected_rows_log', '影响条数日志', 'err', "模版太旧 请增加影响条数 LOG.info('影响条数:' + str(rownum))")
    if "TO GROUP GROUP_VERSION1" in data.upper():
        result.add('hcyt.program.legacy_group_clause', '旧版 GROUP 子句', 'err', '建表脚本中不允许出现 TO GROUP GROUP_VERSION1 请删除')
    seen_ddl = set()
    for finding in run_dws_ddl_rules(data):
        key = (finding.rule_code, finding.msg)
        if key not in seen_ddl:
            result.findings.append(finding)
            seen_ddl.add(key)
    content = data[1000:]
    datekk = find_hardcoded_dates(content)
    datekk = ["'" + item + "'" for item in datekk]
    datekk = list(set(datekk))
    if len(datekk) > 0:
        result.add(
            'hcyt.program.hardcoded_date',
            '写死日期',
            'err',
            f"检测到的写死日期 请甄别是否业务需求 (如果是注释日期去掉两头引号): {' '.join(datekk)} ",
            evidence={'dates': datekk},
        )

    tables = extract_tables(content)
    tables2 = find_dot_strings(content)
    tables_total = tables + tables2
    sql_table = [
        item for item in set(tables_total)
        if item.upper() not in {value.upper() for value in gjz_lists}
    ]
    used_views = sorted({item for item in sql_table if item.upper() in view_names})
    if used_views:
        result.add('hcyt.program.use_view', '使用视图', 'err', f'检测到使用视图，请重点审核: {",".join(used_views)}')
    if used_functions:
        result.add('hcyt.program.use_function', '使用函数', 'err', f'检测到使用函数，请重点审核: {",".join(used_functions)}')
    sql_table = [
        item for item in sql_table
        if item.upper() != result_table_name.upper() and item.upper() not in function_names
    ]

    fq_flag = has_partition_rollback_step(data)
    fq_flag2 = False
    schame, table_name = result_table_name.split('.')
    partition_table = f'{schame}.{table_name}'.upper()
    partition_counts = metadata_cache.get('partition_counts')
    if partition_counts is not None:
        partition_count = partition_counts.get(partition_table)
        r = _timed(
            'programs.file.rule.load_partitions',
            lambda: [] if partition_count is None else [(partition_count,)],
            log_timing,
            result_fields=lambda rows: {'rows': len(rows or [])},
            table=partition_table,
            cache_hit=True,
            **timing_fields,
        )
    else:
        r = _load_cached_metadata(
            metadata_cache,
            f'partitions:{partition_table}',
            'programs.file.rule.load_partitions',
            lambda: all_tab_partitions(partition_table),
            log_timing,
            result_fields=lambda rows: {'rows': len(rows or [])},
            table=partition_table,
            **timing_fields,
        )
    partition_metadata_known = bool(r and r[0] and r[0][0] is not None)
    if partition_metadata_known and r[0][0] > 0:
        fq_flag2 = True
    if partition_metadata_known and fq_flag2 != fq_flag:
        result.add(
            'hcyt.program.partition_rollback',
            '分区回滚步骤',
            'err',
            f'{schame}.{table_name} 分区表应该增加分区步骤 rollback_deal 或者 结果表不是分区表不要加分区步骤',
            evidence={'table': f'{schame}.{table_name}'},
        )
    for i in sql_table:
        if i.upper() in gjz_lists:
            pass
        elif '.' not in i.upper():
            result.add('hcyt.program.missing_schema', '表名缺少 SCHEMA', 'err', f'表名 {i} 没有带 SCHAME请注意加上 如果是用with表注意效率', evidence={'table': i})

    for i in kk:
        i = i[0]
        if i == '':
            continue
        if i.upper() in data.upper():
            result.add('hcyt.program.forbidden_table', '错误表引用', 'err', f'用错表 {i}', evidence={'table': i})
    data = data.replace(' ', '').replace('\t', '').upper()
    if '=(SELECT' in data:
        result.add('hcyt.program.scalar_subquery', '标量子查询', 'err', '存在 = ( select 子查询 注意跑批效率 和 万一数据多条导致程序报错')
    data = data.replace('JOIN(SELECT', '')
    if 'IN(SELECT' in data:
        result.add('hcyt.program.in_subquery', 'IN 子查询', 'warn', '存在 in ( select 子查询 注意跑批效率')
    if '.END_DT>=' in data:
        result.add('hcyt.program.end_dt_range', '拉链结束日期范围', 'err', '检测到 END_DT>= 注意拉链数据重复')
    if "D_DATE=TO_DATE('" in data:
        result.add('hcyt.program.d_date_to_date', '主题表日期写法', 'err', "存在关键字 D_DATE=TO_DATE(' 使用主题表请改为 d_date ='YYYYMMDD' ")
    if "D_DATE=DATE'" in data:
        result.add('hcyt.program.d_date_literal', '主题表日期写法', 'err', "存在关键 D_DATE = DATE' 使用主题表请改为 d_date ='YYYYMMDD' ")
    if "DATE(D_DATE)" in data:
        result.add('hcyt.program.d_date_function', '主题表日期写法', 'err', "存在关键 DATE(D_DATE) 使用主题表请改为 d_date ='YYYYMMDD' ")
    if "TO_DATE(D_DATE," in data:
        result.add('hcyt.program.to_date_d_date', '主题表日期写法', 'err', "存在关键 TO_DATE(D_DATE, 使用主题表请改为 d_date ='YYYYMMDD' ")
    data = data.replace('END_DATE', '').upper()
    if "D_DATE<" in data:
        result.add('hcyt.program.d_date_less_than', '主题表日期区间', 'err', '存在关键字 D_DATE< 请检查，如果使用全量主题表 不允许使用区间')
    if "D_DATE>" in data:
        result.add('hcyt.program.d_date_greater_than', '主题表日期区间', 'err', '存在关键字 D_DATE> 请检查，如果使用全量主题表 不允许使用区间')
    if log_timing is not None:
        log_timing(
            'programs.file.rule.evaluate',
            'end',
            elapsed_ms=round((time.perf_counter() - rule_evaluation_started) * 1000, 1),
            findings=result.count,
            sql_tables=len(sql_table),
            **timing_fields,
        )
    result.artifacts['sql_tables'] = sql_table
    return result
