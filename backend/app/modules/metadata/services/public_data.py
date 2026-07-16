import re

from .audit_metadata_service import (
    list_function_names,
    list_job_outfiles,
    list_para_table_names,
    list_result_table_sys_names,
    list_term_roots,
    list_upstream_system_ids,
    list_view_names,
)
from .db_service import select_sql
from .metadata_model import column_name, table_name


def _table(key):
    return table_name(key)


def _column(table, key):
    return column_name(table, key)


def all_real_seq():
    sql = f"""select DISTINCT {_column('jobs', 'sequence_name')} from {_table('jobs')}
WHERE a IN ('PLAN_CBS_CBSRUN_REAL_DWS_DAY','PLAN_DWS_CBS_CBSRUN_DH_XQDATA_REAL',
                         'PLAN_REAL_CBS_CBSRUN_LDXJC_HOUR','PLAN_REAL_CBS_CBSRUN_LDXJC_REAL',
                         'PLAN_REAL_DWS_DWD_IJEP_REAL','PLAN_REAL_KUANYE_KUANYENEW_REAL',
                         'PLAN_REAL_TA_LCXSQK_HALF_HOUR')"""
    plan_lists = select_sql(sql)
    return plan_lists

def all_plan():
    sql = f"""select a,b,c,d,e,f from {_table('plans')}"""
    plan_lists = select_sql(sql)
    return plan_lists


def get_job2():
    sql = f"""select {_column('jobs', 'job_name')},DECODE({_column('jobs', 'status')},1,'启用',9,'禁用') as x from {_table('jobs')}"""
    job_lists = select_sql(sql)
    return job_lists

def all_job_dependencies():
    sql = f"""select {_column('jobs', 'job_name')}, {_column('jobs', 'dependencies')} from {_table('jobs')}"""
    job_lists = select_sql(sql)
    return job_lists

def all_job():
    sql = f"""select * from {_table('jobs')}"""
    job_lists = select_sql(sql)
    return job_lists

def all_program():
    sql = f"""select a,b,c,d,e,f,g,h,i,j from {_table('programs')}"""
    program_lists = select_sql(sql)
    return program_lists

def all_seq():
    sql = f"""select distinct {_column('jobs', 'sequence_name')} from {_table('jobs')}"""
    seq_lists = select_sql(sql)
    return seq_lists

def all_role():
    sql = f"""select * from {_table('roles')}"""
    role_lists = select_sql(sql)
    role_lists_r=[]
    for i in role_lists:
        role_lists_r.append(i[0])
    return role_lists_r

def all_fine():
    sql = f"""select * from {_table('fine')}"""
    fine_lists = select_sql(sql)
    fine_lists_r=[]
    for i in fine_lists:
        fine_lists_r.append(i[0])
    return fine_lists_r

def all_seqjob():
    sql = f"""select DISTINCT {_column('jobs', 'sequence_name')},{_column('jobs', 'job_name')} from {_table('jobs')}"""
    seqjob_lists = select_sql(sql)
    return seqjob_lists

def all_planjob():
    sql = f"""select DISTINCT {_column('jobs', 'plan_name')},{_column('jobs', 'job_name')} from {_table('jobs')}"""
    planjob_lists = select_sql(sql)
    return planjob_lists

def all_planseq():
    sql = f"""select DISTINCT {_column('jobs', 'plan_name')},{_column('jobs', 'sequence_name')} from {_table('jobs')}"""
    planseq_lists = select_sql(sql)
    return planseq_lists

def all_job_outfile():
    return list_job_outfiles()

def all_sstb():
    sql = f"""select a from {_table('job_outfiles')}"""
    sstb_lists = select_sql(sql)
    return sstb_lists


def all_para_table_lists():
    return list_para_table_names()


def all_disabled_result_tables():
    sql = """
select substr(p.k,5) as table_name
from {jobs} j
inner join {programs} p
on j.e = p.b
where substr(p.k,5) is not null
  and j.x in (9, '9')
""".format(jobs=_table('jobs'), programs=_table('programs'))
    result_tables = select_sql(sql)
    return result_tables


def all_result_table_sys_names():
    return list_result_table_sys_names()


def all_upstream_system_ids():
    return list_upstream_system_ids()


def all_view_names():
    return list_view_names()


def all_function_names():
    return list_function_names()


def all_term_roots():
    return list_term_roots()

def all_tab_partitions(tb_name):
    schema_name, table_name = tb_name.upper().split('.', 1)
    sql = f"""SELECT count(*)
FROM dba_tab_partitions t
WHERE SCHEMA IN ('{schema_name}', '{schema_name.lower()}')
AND TABLE_NAME IN ('{table_name}', '{table_name.lower()}')"""
    partitions_lists = select_sql(sql)
    # partitions_lists_r=[]
    # for i in partitions_lists:
    #     partitions_lists_r.append(i[0])
    return partitions_lists


def all_tab_partition_counts(tb_names):
    normalized_names = []
    for tb_name in tb_names or []:
        try:
            schema_name, table_name = str(tb_name).strip().upper().split('.', 1)
        except ValueError:
            continue
        if re.fullmatch(r'[A-Z][A-Z0-9_$#]*', schema_name) and re.fullmatch(r'[A-Z][A-Z0-9_$#]*', table_name):
            normalized_names.append((schema_name, table_name))
    normalized_names = list(dict.fromkeys(normalized_names))
    if not normalized_names:
        return {}

    tables_by_schema = {}
    for schema_name, table_name in normalized_names:
        tables_by_schema.setdefault(schema_name, []).append(table_name)
    conditions = ' OR '.join(
        f"(SCHEMA IN ('{schema_name}', '{schema_name.lower()}') AND TABLE_NAME IN ("
        f"{', '.join(repr(name) for name in table_names + [name.lower() for name in table_names])}))"
        for schema_name, table_names in tables_by_schema.items()
    )
    sql = f"""
SELECT upper(SCHEMA), upper(TABLE_NAME), count(*)
FROM dba_tab_partitions
WHERE {conditions}
GROUP BY upper(SCHEMA), upper(TABLE_NAME)
"""
    counts = {f'{schema_name}.{table_name}': 0 for schema_name, table_name in normalized_names}
    for row in select_sql(sql) or []:
        if len(row) >= 3 and row[0] and row[1]:
            counts[f'{str(row[0]).upper()}.{str(row[1]).upper()}'] = int(row[2] or 0)
    return counts
