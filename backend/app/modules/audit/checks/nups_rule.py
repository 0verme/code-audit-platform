# -*- coding: utf-8 -*-
from pathlib import Path

from app.modules.audit.checks.hcyt_rule import (
    COLUMN_COMMENT_REQUIRED_SCHEMAS,
    DWS_TABLE_PREFIX_RULES,
    DWS_TEMP_TABLE_PREFIXES,
    detect_created_functions,
    detect_created_views,
    detect_used_functions,
    extract_alter_table_add_columns,
    extract_alter_table_targets,
    extract_comment_on_column_map,
    extract_create_table_column_defs,
    extract_create_table_objects,
    gjz_lists,
    has_partition_rollback_step,
    load_metadata_name_set,
    split_schema_table,
)
from app.modules.metadata.services.public_data import all_function_names, all_sstb, all_tab_partitions, all_view_names
from app.modules.audit.checks.re_service import (
    extract_tables,
    find_dot_strings,
    find_hardcoded_dates,
    match_path,
    read_data_from_file,
)
from app.config.audit_rules import get_audit_rules
from app.modules.audit.checks.dws_sql_review import run_configured_dws_sql_reviews
from app.modules.audit.findings import CheckResult, Finding


NUPS_SQL_NAMES = {
    'cbrc.sql',
    'cot.sql',
    'cqcs.sql',
    'east.sql',
    'fbd.sql',
    'hnbb.sql',
    'irs.sql',
    'nups_data.sql',
    'pboc.sql',
    'pisa.sql',
    'sjbl.sql',
}


def _file_rules():
    return get_audit_rules()["nups"]["file_rules"]


def get_program_table_name(py_url):
    folder = Path(py_url).parent.name
    if '.' not in folder:
        return ''
    schema, table_name = folder.split('.', 1)
    schema = schema.replace(_file_rules()["program_table_name"]["directory_schema_prefix"], '')
    return f'{schema}.{table_name}'


def is_nups_py(file_path):
    return any(match_path(file_path, pattern) for pattern in _file_rules()["program_path_patterns"]) or file_path.lower().endswith('.py')


def get_nups_type(file_paths):
    dws_url = []
    py_lists = []

    for file_path in file_paths:
        file_name = Path(file_path).name.lower()
        sql_names = _file_rules()["sql_filenames"] or NUPS_SQL_NAMES
        if file_name in sql_names or (not _file_rules()["sql_filenames"] and file_name.endswith('.sql')):
            dws_url.append(file_path)
        elif is_nups_py(file_path):
            py_lists.append(file_path)

    return sorted(dws_url), sorted(py_lists)


def check_table_name_rule(full_table_name, is_temp=False):
    schema_name, table_name = split_schema_table(full_table_name)
    if is_temp or schema_name == 'TMP':
        if not any(table_name.startswith(prefix) for prefix in DWS_TEMP_TABLE_PREFIXES):
            return Finding('nups.ddl.temp_table_name', '临时表命名', 'err', f'临时表 {full_table_name} 命名不符合规范，应以 {"/".join(DWS_TEMP_TABLE_PREFIXES)} 开头')
        return None

    allowed_prefixes = DWS_TABLE_PREFIX_RULES.get(schema_name)
    if allowed_prefixes and not any(table_name.startswith(prefix) for prefix in allowed_prefixes):
        return Finding('nups.ddl.table_name', '分层表命名', 'err', f'表 {full_table_name} 命名不符合规范，{schema_name} 层表名应以 {"/".join(allowed_prefixes)} 开头')
    return None


def check_column_comment_rule(column_item, comment_map):
    table_name = column_item['table_name']
    schema_name, _ = split_schema_table(table_name)
    if schema_name not in COLUMN_COMMENT_REQUIRED_SCHEMAS:
        return None

    full_column_name = f"{table_name}.{column_item['column_name']}"
    comment_text = column_item['inline_comment'] or comment_map.get(full_column_name, '')
    if not comment_text:
        return Finding('nups.ddl.column_comment', '字段注释', 'err', f'字段 {full_column_name} 缺少注释，请在建表字段后补 COMMENT 或增加 COMMENT ON COLUMN')
    return None


def run_dws_ddl_rules(sql_text):
    findings = []
    created_tables = extract_create_table_objects(sql_text)
    altered_tables = extract_alter_table_targets(sql_text)
    comment_map = extract_comment_on_column_map(sql_text)
    column_items = extract_create_table_column_defs(sql_text) + extract_alter_table_add_columns(sql_text)

    for item in created_tables:
        message = check_table_name_rule(item['table_name'], is_temp=item['is_temp'])
        if message:
            findings.append(message)

    for table_name in altered_tables:
        message = check_table_name_rule(table_name)
        if message:
            findings.append(Finding(message.rule_code, message.rule, message.level, f'{message.msg}（ALTER TABLE 对象）'))

    for column_item in column_items:
        comment_message = check_column_comment_rule(column_item, comment_map)
        if comment_message:
            findings.append(comment_message)

    return findings


def _legacy_rule_dws(dws_url):
    print('===================================nups_rule_dws=================================')
    data = read_data_from_file(dws_url)
    result = CheckResult()
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_views = sorted({item for item in find_dot_strings(data.upper()) if item.upper() in view_names})
    used_functions = detect_used_functions(data, function_names)
    if created_views:
        result.add('nups.sql.create_view', '创建视图', 'err', f'检测到创建视图，请重点审核: {",".join(created_views)}')
    if created_functions:
        result.add('nups.sql.create_function', '创建函数', 'err', f'检测到创建函数，请重点审核: {",".join(created_functions)}')
    if used_views:
        result.add('nups.sql.use_view', '使用视图', 'err', f'检测到使用视图，请重点审核: {",".join(used_views)}')
    if used_functions:
        result.add('nups.sql.use_function', '使用函数', 'err', f'检测到使用函数，请重点审核: {",".join(used_functions)}')
    if len(data.split('\n')) > 20000:
        result.add('nups.sql.too_many_lines', 'SQL 行数过多', 'err', '行数过多，大批量 sql 请上线人员操作')
    if 'ALTER' in data.upper():
        result.add('nups.sql.alter_statement', 'ALTER 命令', 'err', '存在 alter 命令，请审核重点检查')
    if 'DWM.' in data.upper():
        result.add('nups.sql.dwm_operation', 'DWM 模型层操作', 'err', '存在对 dwm 模型层的操作，请审核重点检查')
    if 'TO GROUP GROUP_VERSION1' in data.upper():
        result.add('nups.sql.legacy_group_clause', '旧版 GROUP 子句', 'err', '建表脚本不允许带 TO GROUP GROUP_VERSION1')
    result.findings.extend(run_configured_dws_sql_reviews(data, message_style="nups"))
    return result


def rule_dws(dws_url):
    result = _legacy_rule_dws(dws_url)
    data = read_data_from_file(dws_url)
    seen = {(item.rule_code, item.msg) for item in result.findings}
    for finding in run_dws_ddl_rules(data):
        key = (finding.rule_code, finding.msg)
        if key not in seen:
            result.findings.append(finding)
            seen.add(key)
    return result


def rule_dws_py(dws_url):
    print('===================================nups_rule_dws_py=================================')
    kk = all_sstb()
    result = CheckResult()
    data = read_data_from_file(dws_url)
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    result_table_name = get_program_table_name(dws_url)
    if result_table_name:
        result_table_name_message = check_table_name_rule(result_table_name)
        if result_table_name_message:
            result.findings.append(result_table_name_message)

    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_functions = detect_used_functions(data, function_names)
    if created_views:
        result.add('nups.program.create_view', '创建视图', 'err', f'检测到创建视图，请重点审核: {",".join(created_views)}')
    if created_functions:
        result.add('nups.program.create_function', '创建函数', 'err', f'检测到创建函数，请重点审核: {",".join(created_functions)}')
    if 'FOR I IN' in data.upper():
        result.add('nups.program.for_loop', 'FOR 循环', 'err', '存在 for 循环 for i in，脚本不允许出现循环，如特殊情况需说明')
    if 'CHARACTER VARYING(' in data.upper():
        result.add('nups.program.character_varying_length', '字段长度写死', 'err', '在程序里建表不要写死字段长度 CHARACTER VARYING(')
    if 'VARCHAR2(' in data.upper():
        result.add('nups.program.varchar2_length', '字段长度写死', 'err', '在程序里建表不要写死字段长度 VARCHAR2(')
    if 'NVL(NVL(' in data.upper():
        result.add('nups.program.nested_nvl', '嵌套 NVL', 'err', '多个 NVL(NVL( 的写法请用一个 COALESCE 函数替代')
    if 'COALESCE(COALESCE(' in data.upper():
        result.add('nups.program.nested_coalesce', '嵌套 COALESCE', 'err', 'COALESCE(COALESCE( 请直接替换，避免卡 bug')
    if 'DISTINCT' in data.upper():
        result.add('nups.program.distinct_review', 'DISTINCT 审查', 'err', '请审核重点检查脚本中的 distinct 是否必须添加，有无关联出重复数据')
    if '(+)' in data.upper():
        result.add('nups.program.legacy_outer_join', '旧式外连接', 'err', '脚本中存在 (+)，这种写法维护性较差，请修改')
    if '影响条数' not in data:
        result.add('nups.program.affected_rows_log', '影响条数日志', 'err', "模板太旧，请增加影响条数 LOG.info('影响条数:' + str(rownum))")
    if 'TO GROUP GROUP_VERSION1' in data.upper():
        result.add('nups.program.legacy_group_clause', '旧版 GROUP 子句', 'err', '建表脚本中不允许出现 TO GROUP GROUP_VERSION1，请删除')

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
    if datekk:
        result.add('nups.program.hardcoded_date', '写死日期', 'err', f"检测到写死日期，请确认是否业务需求（如果是注释日期，去掉两头引号）: {' '.join(datekk)} ", evidence={'dates': datekk})

    tables = extract_tables(content)
    tables2 = find_dot_strings(content)
    tables_total = tables + tables2
    sql_table = [
        item for item in set(tables_total)
        if item.upper() not in {value.upper() for value in gjz_lists}
    ]
    used_views = sorted({item for item in sql_table if item.upper() in view_names})
    if used_views:
        result.add('nups.program.use_view', '使用视图', 'err', f'检测到使用视图，请重点审核: {",".join(used_views)}')
    if used_functions:
        result.add('nups.program.use_function', '使用函数', 'err', f'检测到使用函数，请重点审核: {",".join(used_functions)}')
    sql_table = [
        item for item in sql_table
        if item.upper() != result_table_name.upper() and item.upper() not in function_names
    ]

    fq_flag = has_partition_rollback_step(data)
    fq_flag2 = False
    if result_table_name:
        schema, table_name = result_table_name.split('.', 1)
        r = all_tab_partitions(f'{schema}.{table_name}')
        if r and r[0] and r[0][0] > 0:
            fq_flag2 = True
        if fq_flag2 != fq_flag:
            result.add('nups.program.partition_rollback', '分区回滚步骤', 'err', f'{schema}.{table_name} 分区表应该增加分区步骤 rollback_deal，或者结果表不是分区表则不要加分区步骤')

    for item in sql_table:
        if item.upper() in gjz_lists:
            pass
        elif '.' not in item.upper():
            result.add('nups.program.missing_schema', '表名缺少 SCHEMA', 'err', f'表名 {item} 没有带 SCHEMA，请注意加上；如果是 with 表，请注意效率')

    for item in kk:
        item = item[0]
        if not item:
            continue
        if item.upper() in data.upper():
            result.add('nups.program.forbidden_table', '错误表引用', 'err', f'用错表 {item}')

    normalized_data = data.replace(' ', '').replace('\t', '').upper()
    if '=(SELECT' in normalized_data:
        result.add('nups.program.scalar_subquery', '标量子查询', 'err', '存在 = ( select 子查询，请注意跑批效率，以及万一数据多条导致程序报错')
    normalized_data = normalized_data.replace('JOIN(SELECT', '')
    if 'IN(SELECT' in normalized_data:
        result.add('nups.program.in_subquery', 'IN 子查询', 'err', '存在 in ( select 子查询，请注意跑批效率')
    if '.END_DT>=' in normalized_data:
        result.add('nups.program.end_dt_range', '拉链结束日期范围', 'err', '检测到 END_DT>=，注意拉链数据重复')
    if "D_DATE=TO_DATE('" in normalized_data:
        result.add('nups.program.d_date_to_date', '主题表日期写法', 'err', "存在关键字 D_DATE=TO_DATE('，使用主题表请改为 d_date ='YYYYMMDD' ")
    if "D_DATE=DATE'" in normalized_data:
        result.add('nups.program.d_date_literal', '主题表日期写法', 'err', "存在关键字 D_DATE = DATE'，使用主题表请改为 d_date ='YYYYMMDD' ")
    if 'DATE(D_DATE)' in normalized_data:
        result.add('nups.program.d_date_function', '主题表日期写法', 'err', "存在关键字 DATE(D_DATE)，使用主题表请改为 d_date ='YYYYMMDD' ")
    if 'TO_DATE(D_DATE,' in normalized_data:
        result.add('nups.program.to_date_d_date', '主题表日期写法', 'err', "存在关键字 TO_DATE(D_DATE,，使用主题表请改为 d_date ='YYYYMMDD' ")
    normalized_data = normalized_data.replace('END_DATE', '')
    if 'D_DATE<' in normalized_data:
        result.add('nups.program.d_date_less_than', '主题表日期区间', 'err', '存在关键字 D_DATE<，请检查；如果使用全量主题表，不允许使用区间')
    if 'D_DATE>' in normalized_data:
        result.add('nups.program.d_date_greater_than', '主题表日期区间', 'err', '存在关键字 D_DATE>，请检查；如果使用全量主题表，不允许使用区间')
    result.artifacts['sql_tables'] = sql_table
    return result
