from services.db_service import select_sql


def all_real_seq():
    sql = f"""select DISTINCT b from dwp.p_job_hjj
WHERE a IN ('PLAN_CBS_CBSRUN_REAL_DWS_DAY','PLAN_DWS_CBS_CBSRUN_DH_XQDATA_REAL',
                         'PLAN_REAL_CBS_CBSRUN_LDXJC_HOUR','PLAN_REAL_CBS_CBSRUN_LDXJC_REAL',
                         'PLAN_REAL_DWS_DWD_IJEP_REAL','PLAN_REAL_KUANYE_KUANYENEW_REAL',
                         'PLAN_REAL_TA_LCXSQK_HALF_HOUR')"""
    plan_lists = select_sql(sql)
    return plan_lists

def all_plan():
    sql = f"""select a,b,c,d,e,f from dwp.p_plan_hjj"""
    plan_lists = select_sql(sql)
    return plan_lists


def get_job2():
    sql = f"""select c,DECODE(x,1,'启用',9,'禁用') as x from dwp.p_job_hjj"""
    job_lists = select_sql(sql)
    return job_lists

def all_job_dependencies():
    sql = """select c, ab from dwp.p_job_hjj"""
    job_lists = select_sql(sql)
    return job_lists

def all_job():
    sql = f"""select * from dwp.p_job_hjj"""
    job_lists = select_sql(sql)
    return job_lists

def all_program():
    sql = f"""select a,b,c,d,e,f,g,h,i,j from dwp.p_program_hjj"""
    program_lists = select_sql(sql)
    return program_lists

def all_seq():
    sql = f"""select distinct b from dwp.p_job_hjj"""
    seq_lists = select_sql(sql)
    return seq_lists

def all_role():
    sql = f"""select * from dwp.p_role_hjj"""
    role_lists = select_sql(sql)
    role_lists_r=[]
    for i in role_lists:
        role_lists_r.append(i[0])
    return role_lists_r

def all_fine():
    sql = f"""select * from dwp.p_fine_hjj"""
    fine_lists = select_sql(sql)
    fine_lists_r=[]
    for i in fine_lists:
        fine_lists_r.append(i[0])
    return fine_lists_r

def all_seqjob():
    sql = f"""select DISTINCT b,c from dwp.p_job_hjj"""
    seqjob_lists = select_sql(sql)
    return seqjob_lists

def all_planjob():
    sql = f"""select DISTINCT a,c from dwp.p_job_hjj"""
    planjob_lists = select_sql(sql)
    return planjob_lists

def all_planseq():
    sql = f"""select DISTINCT a,b from dwp.p_job_hjj"""
    planseq_lists = select_sql(sql)
    return planseq_lists

def all_job_outfile():
    sql = f"""select a,b from dwp.p_job_outfile"""
    job_outfile_lists = select_sql(sql)
    return job_outfile_lists

def all_sstb():
    sql = f"""select a from dwp.p_job_outfile"""
    sstb_lists = select_sql(sql)
    return sstb_lists


def all_para_table_lists():
    sql = """select para_table_name from dwp.p_para_table_lists"""
    para_table_lists = select_sql(sql)
    return para_table_lists


def all_disabled_result_tables():
    sql = """
select substr(p.k,5) as table_name
from dwp.p_job_hjj j
inner join dwp.p_program_hjj p
on j.e = p.b
where substr(p.k,5) is not null
  and j.x in (9, '9')
"""
    result_tables = select_sql(sql)
    return result_tables


def all_result_table_sys_names():
    sql = """
select d.table_name, m.sys_name
from dwp.p_recv_dwf d
inner join dwp.p_recv_ops_mapping m
on d.recv_plan = m.recv_plan
where d.table_name is not null
  and m.sys_name is not null
"""
    result_tables = select_sql(sql)
    return result_tables


def all_recv_mapping_plans():
    sql = """
select distinct recv_plan
from dwp.p_recv_ops_mapping
where recv_plan is not null
"""
    recv_plan_lists = select_sql(sql)
    return recv_plan_lists


def all_view_names():
    sql = """
SELECT upper(table_schema) || '.' || upper(table_name)
FROM information_schema.views
WHERE upper(table_schema) NOT IN ('PG_CATALOG', 'INFORMATION_SCHEMA')
"""
    return select_sql(sql)


def all_function_names():
    sql = """
SELECT upper(n.nspname) || '.' || upper(p.proname)
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE upper(n.nspname) NOT IN ('PG_CATALOG', 'INFORMATION_SCHEMA')
"""
    return select_sql(sql)


def all_term_roots():
    sql = """
SELECT DISTINCT upper(root_code)
FROM dwp.p_term_root
WHERE root_code IS NOT NULL
"""
    return select_sql(sql)

def all_tab_partitions(tb_name):
    schema_name, table_name = tb_name.upper().split('.', 1)
    sql = f"""SELECT count(*)
FROM dba_tab_partitions t
WHERE upper(SCHEMA)='{schema_name}'
AND upper(TABLE_NAME)='{table_name}'"""
    partitions_lists = select_sql(sql)
    # partitions_lists_r=[]
    # for i in partitions_lists:
    #     partitions_lists_r.append(i[0])
    return partitions_lists
