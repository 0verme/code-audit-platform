# -*- coding: utf-8 -*-
from pathlib import Path

from core.hcyt_rule import (
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
from core.public_data import all_function_names, all_sstb, all_tab_partitions, all_view_names
from services.re_service import (
    extract_tables,
    find_dot_strings,
    find_hardcoded_dates,
    match_path,
    read_data_from_file,
)


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


def get_program_table_name(py_url):
    folder = Path(py_url).parent.name
    if '.' not in folder:
        return ''
    schema, table_name = folder.split('.', 1)
    schema = schema.replace('DWS_', '')
    return f'{schema}.{table_name}'


def is_nups_py(file_path):
    return match_path(file_path, '**/NUPS_DATA/**/*.py') or file_path.lower().endswith('.py')


def get_nups_type(file_paths):
    dws_url = []
    py_lists = []

    for file_path in file_paths:
        file_name = Path(file_path).name.lower()
        if file_name in NUPS_SQL_NAMES:
            dws_url.append(file_path)
        elif is_nups_py(file_path):
            py_lists.append(file_path)

    return sorted(dws_url), sorted(py_lists)


def check_table_name_rule(full_table_name, is_temp=False):
    schema_name, table_name = split_schema_table(full_table_name)
    if is_temp or schema_name == 'TMP':
        if not any(table_name.startswith(prefix) for prefix in DWS_TEMP_TABLE_PREFIXES):
            return f'临时表 {full_table_name} 命名不符合规范，应以 {"/".join(DWS_TEMP_TABLE_PREFIXES)} 开头'
        return ''

    allowed_prefixes = DWS_TABLE_PREFIX_RULES.get(schema_name)
    if allowed_prefixes and not any(table_name.startswith(prefix) for prefix in allowed_prefixes):
        return f'表 {full_table_name} 命名不符合规范，{schema_name} 层表名应以 {"/".join(allowed_prefixes)} 开头'
    return ''


def check_column_comment_rule(column_item, comment_map):
    table_name = column_item['table_name']
    schema_name, _ = split_schema_table(table_name)
    if schema_name not in COLUMN_COMMENT_REQUIRED_SCHEMAS:
        return ''

    full_column_name = f"{table_name}.{column_item['column_name']}"
    comment_text = column_item['inline_comment'] or comment_map.get(full_column_name, '')
    if not comment_text:
        return f'字段 {full_column_name} 缺少注释，请在建表字段后补 COMMENT 或增加 COMMENT ON COLUMN'
    return ''


def run_dws_ddl_rules(sql_text):
    warnings = []
    created_tables = extract_create_table_objects(sql_text)
    altered_tables = extract_alter_table_targets(sql_text)
    comment_map = extract_comment_on_column_map(sql_text)
    column_items = extract_create_table_column_defs(sql_text) + extract_alter_table_add_columns(sql_text)

    for item in created_tables:
        message = check_table_name_rule(item['table_name'], is_temp=item['is_temp'])
        if message:
            warnings.append(message)

    for table_name in altered_tables:
        message = check_table_name_rule(table_name)
        if message:
            warnings.append(f'{message}（ALTER TABLE 对象）')

    for column_item in column_items:
        comment_message = check_column_comment_rule(column_item, comment_map)
        if comment_message:
            warnings.append(comment_message)

    return warnings


def _legacy_rule_dws(dws_url):
    print('===================================nups_rule_dws=================================')
    data = read_data_from_file(dws_url)
    result_text = ''
    cnt = 0
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    created_views = detect_created_views(data)
    created_functions = detect_created_functions(data)
    used_views = sorted({item for item in find_dot_strings(data.upper()) if item.upper() in view_names})
    used_functions = detect_used_functions(data, function_names)
    if created_views:
        result_text += f'检测到创建视图，请重点审核: {",".join(created_views)}\n'
        cnt += 1
    if created_functions:
        result_text += f'检测到创建函数，请重点审核: {",".join(created_functions)}\n'
        cnt += 1
    if used_views:
        result_text += f'检测到使用视图，请重点审核: {",".join(used_views)}\n'
        cnt += 1
    if used_functions:
        result_text += f'检测到使用函数，请重点审核: {",".join(used_functions)}\n'
        cnt += 1
    if len(data.split('\n')) > 20000:
        result_text += '行数过多，大批量 sql 请上线人员操作\n'
        cnt += 1
    if 'ALTER' in data.upper():
        result_text += '存在 alter 命令，请审核重点检查\n'
        cnt += 1
    if 'DWM.' in data.upper():
        result_text += '存在对 dwm 模型层的操作，请审核重点检查\n'
        cnt += 1
    if 'TO GROUP GROUP_VERSION1' in data.upper():
        result_text += '建表脚本不允许带 TO GROUP GROUP_VERSION1\n'
        cnt += 1
    for token in ('WLQ', 'BSC', 'YGW', 'TMPQS'):
        if token in data.upper():
            result_text += f'建表脚本带 {token}，请确认是不是取数单的表名没改\n'
            cnt += 1
    if 'LZY' in data.upper() and 'RLZY' not in data.upper():
        result_text += '建表脚本带 LZY，请确认是不是取数单的表名没改\n'
        cnt += 1
    for table_name in ('DWM.M_PUB_CODE_MAP_NEW', 'DWM.M_PUB_CODE_INFO_NEW', 'DWM.M_PUB_CODE_USE_NEW'):
        if table_name in data.upper():
            result_text += f'存在码值表 {table_name.split(".")[-1]} 修改，请审核重点检查\n'
            cnt += 1
    return result_text, cnt


def rule_dws(dws_url):
    result_text, cnt = _legacy_rule_dws(dws_url)
    data = read_data_from_file(dws_url)
    ddl_rule_messages = []
    for message in run_dws_ddl_rules(data):
        if message not in ddl_rule_messages:
            ddl_rule_messages.append(message)
    if ddl_rule_messages:
        if result_text and not result_text.endswith('\n'):
            result_text += '\n'
        result_text += '\n'.join(ddl_rule_messages) + '\n'
        cnt += len(ddl_rule_messages)
    return result_text, cnt


def rule_dws_py(dws_url):
    print('===================================nups_rule_dws_py=================================')
    kk = all_sstb()
    result_text = ''
    cnt = 0
    data = read_data_from_file(dws_url)
    view_names = load_metadata_name_set(all_view_names())
    function_names = load_metadata_name_set(all_function_names())
    result_table_name = get_program_table_name(dws_url)
    if result_table_name:
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
    if 'FOR I IN' in data.upper():
        result_text += '存在 for 循环 for i in，脚本不允许出现循环，如特殊情况需说明\n'
        cnt += 1
    if 'CHARACTER VARYING(' in data.upper():
        result_text += '在程序里建表不要写死字段长度 CHARACTER VARYING(\n'
        cnt += 1
    if 'VARCHAR2(' in data.upper():
        result_text += '在程序里建表不要写死字段长度 VARCHAR2(\n'
        cnt += 1
    if 'NVL(NVL(' in data.upper():
        result_text += '多个 NVL(NVL( 的写法请用一个 COALESCE 函数替代\n'
        cnt += 1
    if 'COALESCE(COALESCE(' in data.upper():
        result_text += 'COALESCE(COALESCE( 请直接替换，避免卡 bug\n'
        cnt += 1
    if 'DISTINCT' in data.upper():
        result_text += '请审核重点检查脚本中的 distinct 是否必须添加，有无关联出重复数据\n'
        cnt += 1
    if '(+)' in data.upper():
        result_text += '脚本中存在 (+)，这种写法维护性较差，请修改\n'
        cnt += 1
    if '影响条数' not in data:
        result_text += "模板太旧，请增加影响条数 LOG.info('影响条数:' + str(rownum))\n"
        cnt += 1
    if 'TO GROUP GROUP_VERSION1' in data.upper():
        result_text += '建表脚本中不允许出现 TO GROUP GROUP_VERSION1，请删除\n'
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
    if datekk:
        result_text += f"检测到写死日期，请确认是否业务需求（如果是注释日期，去掉两头引号）: {' '.join(datekk)} \n"
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
    if result_table_name:
        schema, table_name = result_table_name.split('.', 1)
        r = all_tab_partitions(f'{schema}.{table_name}')
        if r and r[0] and r[0][0] > 0:
            fq_flag2 = True
        if fq_flag2 != fq_flag:
            result_text += f'{schema}.{table_name} 分区表应该增加分区步骤 rollback_deal，或者结果表不是分区表则不要加分区步骤\n'
            cnt += 1

    for item in sql_table:
        if item.upper() in gjz_lists:
            pass
        elif '.' not in item.upper():
            result_text += f'表名 {item} 没有带 SCHEMA，请注意加上；如果是 with 表，请注意效率\n'
            cnt += 1

    for item in kk:
        item = item[0]
        if not item:
            continue
        if item.upper() in data.upper():
            result_text += f'用错表 {item}\n'
            cnt += 1

    normalized_data = data.replace(' ', '').replace('\t', '').upper()
    if '=(SELECT' in normalized_data:
        result_text += '存在 = ( select 子查询，请注意跑批效率，以及万一数据多条导致程序报错\n'
        cnt += 1
    normalized_data = normalized_data.replace('JOIN(SELECT', '')
    if 'IN(SELECT' in normalized_data:
        result_text += '存在 in ( select 子查询，请注意跑批效率\n'
        cnt += 1
    if '.END_DT>=' in normalized_data:
        result_text += '检测到 END_DT>=，注意拉链数据重复\n'
        cnt += 1
    if "D_DATE=TO_DATE('" in normalized_data:
        result_text += "存在关键字 D_DATE=TO_DATE('，使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if "D_DATE=DATE'" in normalized_data:
        result_text += "存在关键字 D_DATE = DATE'，使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if 'DATE(D_DATE)' in normalized_data:
        result_text += "存在关键字 DATE(D_DATE)，使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    if 'TO_DATE(D_DATE,' in normalized_data:
        result_text += "存在关键字 TO_DATE(D_DATE,，使用主题表请改为 d_date ='YYYYMMDD' \n"
        cnt += 1
    normalized_data = normalized_data.replace('END_DATE', '')
    if 'D_DATE<' in normalized_data:
        result_text += '存在关键字 D_DATE<，请检查；如果使用全量主题表，不允许使用区间\n'
        cnt += 1
    if 'D_DATE>' in normalized_data:
        result_text += '存在关键字 D_DATE>，请检查；如果使用全量主题表，不允许使用区间\n'
        cnt += 1
    return result_text, cnt, sql_table
