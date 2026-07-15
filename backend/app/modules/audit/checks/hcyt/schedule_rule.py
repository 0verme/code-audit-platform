# -*- coding: utf-8 -*-
import time

import pandas as pd

from app.modules.metadata.services.public_data import (
    all_job_dependencies,
    all_job_outfile,
    all_plan,
    all_planjob,
    all_planseq,
    all_real_seq,
    all_recv_mapping_plans,
    all_seq,
    all_seqjob,
    get_job2,
)
from app.modules.audit.checks.re_service import extract_values, ifmiaoshu
from app.modules.audit.checks.dependency import build_dependency_graph, find_cycles

REAL_JOB_PLAN_NAMES = {
    'PLAN_CBS_CBSRUN_REAL_DWS_DAY',
    'PLAN_DWS_CBS_CBSRUN_DH_XQDATA_REAL',
    'PLAN_REAL_CBS_CBSRUN_LDXJC_HOUR',
    'PLAN_REAL_CBS_CBSRUN_LDXJC_REAL',
    'PLAN_REAL_DWS_DWD_IJEP_REAL',
    'PLAN_REAL_KUANYE_KUANYENEW_REAL',
    'PLAN_REAL_TA_LCXSQK_HALF_HOUR',
}


def _normalize_job_value(value):
    if value is None or pd.isna(value):
        return ''
    return str(value).strip().upper()


def _normalize_dependency_value(value):
    if value is None or pd.isna(value):
        return ''
    return str(value).strip().upper()


def _collect_online_job_dependencies(df):
    online_jobs = {}
    for _, row in df.iterrows():
        job_name = _normalize_job_value(row.iloc[2])
        if not job_name:
            continue
        online_jobs[job_name] = _normalize_dependency_value(row.iloc[27])
    return online_jobs


def _find_online_job_dependency_cycles(df, job_rows=None):
    online_jobs = _collect_online_job_dependencies(df)
    if not online_jobs:
        return []

    merged_jobs = {}
    if job_rows is None:
        for row in all_job_dependencies():
            job_name = _normalize_job_value(row[0])
            if not job_name:
                continue
            dependencies = '' if len(row) < 2 else _normalize_dependency_value(row[1])
            merged_jobs[job_name] = dependencies
    else:
        for row in job_rows:
            job_name = _normalize_job_value(row[2]) if len(row) > 2 else ''
            if not job_name:
                continue
            dependencies = '' if len(row) <= 27 else _normalize_dependency_value(row[27])
            merged_jobs[job_name] = dependencies

    merged_jobs.update(online_jobs)
    graph = build_dependency_graph(merged_jobs.items())
    return find_cycles(graph, only_nodes=set(online_jobs), max_cycles=20)


def rule_excle_plan(df):
    print('===================================rule_excle_plan=================================')
    result_text = ''
    warn_result_text = ''
    cnt = 0
    planname_lists = []
    recv_mapping_plan_lists = []
    for i in all_plan():
        planname_lists.append(i[0])
    for i in all_recv_mapping_plans():
        if i and i[0]:
            recv_mapping_plan_lists.append(str(i[0]).strip())
    recv_mapping_plan_set = set(recv_mapping_plan_lists)
    rr_plan = []
    for _, row in df.iterrows():
        plan_name = '' if pd.isna(row.iloc[0]) else str(row.iloc[0]).strip()
        plan_depand = '' if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        if not plan_name:
            continue
        if plan_name == 'PLAN_PROV_LOCAL_SEND_DAY':
            result_text += f'计划名: {plan_name} 计划名有误\n'
            cnt += 1

        if 'DWD' in plan_name and plan_name not in ('PLAN_PROV_DWD_LOCAL_DAY', 'PLAN_DWS_DWD_DAY'):
            result_text += f'计划名: {plan_name} 计划名有误\n'
            cnt += 1

        if 'DWP' in plan_name and plan_name not in ('PLAN_PROV_DWP_LOCAL_DAY', 'PLAN_DWS_DWP_DAY'):
            result_text += f'计划名: {plan_name} 计划名有误\n'
            cnt += 1

        if 'DWM' in plan_name and plan_name not in (
                'PLAN_DWS_DWM_DWS_DWM_DAY',
                'PLAN_DWS_DWM_MODEL',
                'PLAN_PROV_DWM_LOCAL_DAY'
        ):
            result_text += f'计划名: {plan_name} 计划名有误\n'
            cnt += 1

        if plan_depand:
            result_text += f'计划名: {plan_name} 存在前置依赖 {plan_depand}，请检查\n'
            cnt += 1

        if plan_name.startswith('PLAN_SA_RECV_') and plan_name not in recv_mapping_plan_set:
            warn_result_text += f'计划名 {plan_name} 未在 dwp.p_recv_ops_mapping 表的 recv_plan 字段配置，请联系王婷添加\n'

        if plan_name not in planname_lists:
            if plan_name.startswith('PLAN_DWS_') and plan_name.endswith('_DWS_DWUPRR_DAY'):
                warn_result_text += f'计划名: {plan_name} 未在生产调度（自动触发-一审检查是否是新增系统加工！！！！！！）\n'
            elif plan_name.startswith('PLAN_PROV_') and plan_name.endswith('_SEND_DAY'):
                warn_result_text += f'计划名: {plan_name} 未在生产调度（自动触发-一审检查是否是新增系统推数！！！！！！）\n'
            else:
                result_text += f'计划名: {plan_name} 未在生产调度，请检查\n'
                cnt += 1

        rr_plan.append(plan_name)

    r_plan = list(set(rr_plan + planname_lists))

    return result_text, warn_result_text, cnt, r_plan


def rule_excle_seq(df):
    print('===================================rule_excle_seq=================================')
    real_seq = []
    for j in all_real_seq():
        real_seq.append(j)
    result_text = ''
    warn_result_text = ''
    cnt = 0
    for _, row in df.iterrows():
        seq_name = '' if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        if seq_name in real_seq:
            result_text += f'作业流名：{seq_name}  作业流是循环作业,会覆盖生产的循环调度,需要删除不用上线\n'
            cnt += 1
    return result_text, warn_result_text, cnt


def rule_excle_job(df, r_plan=None, timing_log=None, job_rows=None):
    print('===================================rule_excle_job=================================')
    result_text = ''
    warn_result_text = ''
    cnt = 0

    def log_timing(message):
        if timing_log:
            timing_log(message)

    stage_start = time.time()
    r_job_outfile = {}
    for i in all_job_outfile():
        r_job_outfile[i[0]] = i[1]
    log_timing(f"JOB规则 all_job_outfile 查询/整理完成：{len(r_job_outfile)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    r_planseq = {}
    if job_rows is None:
        planseq_rows = all_planseq()
        for i in planseq_rows:
            plan_name = i[0]
            seq_name = i[1]
            r_planseq[seq_name] = plan_name
    else:
        for i in job_rows:
            if len(i) > 1:
                r_planseq[i[1]] = i[0]
    log_timing(f"JOB规则 all_planseq 查询/整理完成：{len(r_planseq)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    r_seqjob = {}
    if job_rows is None:
        seqjob_rows = all_seqjob()
        for i in seqjob_rows:
            seq_name = i[0]
            job_name = i[1]
            r_seqjob[job_name] = seq_name
    else:
        for i in job_rows:
            if len(i) > 2:
                r_seqjob[i[2]] = i[1]
    log_timing(f"JOB规则 all_seqjob 查询/整理完成：{len(r_seqjob)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    r_planjob = {}
    if job_rows is None:
        planjob_rows = all_planjob()
        for i in planjob_rows:
            plan_name = i[0]
            job_name = i[1]
            r_planjob[job_name] = plan_name
    else:
        for i in job_rows:
            if len(i) > 2:
                r_planjob[i[2]] = i[0]
    log_timing(f"JOB规则 all_planjob 查询/整理完成：{len(r_planjob)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    if job_rows is None:
        r_seq = [i[0] for i in all_seq()]
    else:
        r_seq = list({i[1] for i in job_rows if len(i) > 1 and not pd.isna(i[1])})
    log_timing(f"JOB规则 all_seq 查询/整理完成：{len(r_seq)} 行，{time.time() - stage_start:.2f}s")

    if r_plan is None:
        stage_start = time.time()
        r_plan = []
        for i in all_plan():
            r_plan.append(i[0])
        log_timing(f"JOB规则 all_plan 查询/整理完成：{len(r_plan)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    if job_rows is None:
        real_seq = [j[0] for j in all_real_seq()]
    else:
        real_seq = list({
            j[1]
            for j in job_rows
            if len(j) > 1 and j[0] in REAL_JOB_PLAN_NAMES and not pd.isna(j[1])
        })
    log_timing(f"JOB规则 all_real_seq 查询/整理完成：{len(real_seq)} 行，{time.time() - stage_start:.2f}s")

    stage_start = time.time()
    r_job = []
    r_job_status = {}
    if job_rows is None:
        status_rows = get_job2()
        for i in status_rows:
            job_name = '' if pd.isna(i[0]) else str(i[0]).strip()
            job_status = '' if len(i) < 2 or pd.isna(i[1]) else str(i[1]).strip()
            if job_name:
                r_job.append(job_name)
                r_job_status[job_name] = job_status
    else:
        for i in job_rows:
            job_name = '' if len(i) <= 2 or pd.isna(i[2]) else str(i[2]).strip()
            job_status_value = '' if len(i) <= 23 or pd.isna(i[23]) else str(i[23]).strip()
            job_status = '禁用' if job_status_value in ('9', '9.0') else '启用' if job_status_value in ('1', '1.0') else job_status_value
            if job_name:
                r_job.append(job_name)
                r_job_status[job_name] = job_status
    log_timing(f"JOB规则 get_job2 查询/整理完成：{len(r_job)} 行，{time.time() - stage_start:.2f}s")

    job_list = []
    yilai_job = []
    for _, row in df.iterrows():
        job_name = '' if pd.isna(row.iloc[2]) else str(row.iloc[2]).strip()
        if job_name:
            yilai_job.append(job_name)
    yilai_job = list(set(yilai_job + r_job))

    stage_start = time.time()
    dependency_cycles = _find_online_job_dependency_cycles(df, job_rows)
    log_timing(f"JOB规则 依赖环检查完成：{len(dependency_cycles)} 个环，{time.time() - stage_start:.2f}s")
    for cycle in dependency_cycles:
        result_text += f'作业依赖成环，请检查: {" -> ".join(cycle)}\n'
        cnt += 1

    for _, row in df.iterrows():
        plan_name = '' if pd.isna(row.iloc[0]) else str(row.iloc[0]).strip()
        seq_name = '' if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        job_name = '' if pd.isna(row.iloc[2]) else str(row.iloc[2]).strip()
        miaoshu = '' if pd.isna(row.iloc[3]) else str(row.iloc[3]).strip()
        program = '' if pd.isna(row.iloc[4]) else str(row.iloc[4]).strip()
        domain = '' if pd.isna(row.iloc[5]) else str(row.iloc[5]).strip()
        level = '' if pd.isna(row.iloc[6]) else str(row.iloc[6]).strip()
        cale = '' if pd.isna(row.iloc[9]) else str(row.iloc[9]).strip()
        didp_evt = '' if pd.isna(row.iloc[25]) else str(row.iloc[25]).strip()
        depand = '' if pd.isna(row.iloc[27]) else str(row.iloc[27]).strip()
        if job_name.upper() != job_name:
            result_text += f'作业名: {job_name} 不应该存在小写 请规范\n'
            cnt += 1
        if plan_name.upper() != plan_name:
            result_text += f'计划名:{plan_name} 不应该存在小写 请规范\n'
            cnt += 1
        if seq_name.upper() != seq_name:
            result_text += f' 作业流名:{seq_name} 不应该存在小写 请规范\n'
            cnt += 1
        if r_job_status.get(job_name) == '禁用':
            result_text += f'作业名：{job_name} 生产上是禁用状态，本次上线会重新启用，请确认是否符合预期\n'
            cnt += 1
        if seq_name == '':
            result_text += f' 作业流名:{seq_name} 不应该为空 要么是0 请确认\n'
            cnt += 1
        if seq_name in real_seq and str(level) not in ('99', '99.0'):
            result_text += f'{job_name} 实时作业的优先级需要设置 99\n'
            cnt += 1
        if 'REAL' in seq_name and str(level) not in ('99', '99.0'):
            result_text += f'{job_name} 实时作业的优先级需要设置 99\n'
            cnt += 1
        if ifmiaoshu(miaoshu, job_name):
            result_text += f'{job_name} 第四列作业描述必须要明确加工作用 参考： https://example.com/docs/schedule-description\n'
            cnt += 1
        if plan_name in ('PLAN_DWS_DWM_MODEL', 'PLAN_DWS_DWM_DWS_DWM_DAY') and cale != 'SYS_EVERYDAY_CALENDAR':
            result_text += f'{job_name} 的执行日历 {cale} 不对  实际应该是每日跑批 SYS_EVERYDAY_CALENDAR\n'
            cnt += 1
        if 'PLAN_SA_RECV' in plan_name and domain == 'EDWS_DOMAIN':
            result_text += f'{job_name} 执行域有误 不应为EDWS_DOMAIN\n'
            cnt += 1
        if 'PLAN_SA_MIDD' in plan_name and domain == 'EDWS_DOMAIN':
            result_text += f'{job_name} 执行域有误 不应为EDWS_DOMAIN\n'
            cnt += 1
        if 'PLAN_DWS_RDS' in plan_name and domain == 'EDWS_DOMAIN':
            result_text += f'{job_name} 执行域有误 不应为EDWS_DOMAIN\n'
            cnt += 1
        if domain not in ('EDWS_DOMAIN', 'CMS_DOMAIN', 'NOVA_DOMAIN', 'CBSRUN_DOMAIN', 'IS_DOMAIN', 'EXPORT_DOMAIN'):
            result_text += f'{job_name} 执行域有误不应为 ' + domain + '\n'
            cnt += 1
        if 'DWD' in plan_name and seq_name not in ('SEQ_DWS_DWD_DAY', 'SEQ_PROV_DWD_LOCAL_DAY', '0.0'):
            result_text += f'{seq_name} 计划流名称有误\n'
            cnt += 1
        if 'DWP' in plan_name and seq_name not in ('SEQ_DWS_DWP_DAY', 'SEQ_PROV_DWP_LOCAL_DAY', '0.0'):
            result_text += f'{seq_name} 计划流名称有误\n'
            cnt += 1
        if 'DWM' in plan_name and seq_name not in (
                'SEQ_DWS_DWM_DWS_DWM_DAY', 'SEQ_PROV_DWM_LOCAL_DAY', 'SEQ_DWS_DWM_MODEL_LON', 'SEQ_DWS_DWM_MODEL_GLA',
                'SEQ_DWS_DWM_MODEL_COM', '0.0'):
            result_text += f'{seq_name} 计划流名称有误\n'
            cnt += 1
        job_list.append([plan_name, seq_name, job_name, domain, didp_evt, depand])
        if 'JOB_DWS_DWS_DWF' in job_name and depand == '':
            result_text += f'{job_name} DWF层为什么没有前置依赖\n'
            cnt += 1
        elif 'JOB_SA_RECV' in job_name:
            pass
        elif 'JOB_DWS_DWS_DWO' in job_name and depand == '':
            result_text += f'{job_name} DWO层为什么没有前置依赖\n'
            cnt += 1
        elif 'JOB_PROV_DWS_' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'DWUPRR' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'DWM' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'DWA' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'DWP' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'SEND' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        elif 'LOCAL' in job_name and depand == '':
            result_text += f'{job_name} 为什么没有前置依赖\n'
            cnt += 1
        if '：' in depand:
            result_text += f'{job_name} 依赖列存在中文的冒号 ： 请修改\n'
            cnt += 1
        job_depand = depand.split('|')
        for i in job_depand:
            if i == '':
                job_real = ''
            else:
                parts = i.split(':')
                job_real = parts[1] if len(parts) > 1 else ''
            depend_plan_name = r_planjob.get(job_real, '')
            if domain == 'EDWS_DOMAIN' and 'JOB_PROV_' in job_real:
                result_text += f'{job_name} 加工作业的前置依赖不应该有卸数作业{job_real} \n'
                cnt += 1
            if job_real not in yilai_job and job_real != '':
                result_text += f'{job_name} 的前置作业 {job_real} 在生产不存在\n'
                cnt += 1
            if job_real in (job_name, plan_name):
                result_text += f'{job_name} 不要依赖自身 {job_real} \n'
                cnt += 1
            if plan_name.endswith('REAL') and job_real and depend_plan_name and not depend_plan_name.endswith('REAL'):
                result_text += f'作业名：{job_name} 所属计划 {plan_name} 为REAL计划，依赖的作业 {job_real} 属于普通计划 {depend_plan_name}，请检查\n'
                cnt += 1
            if plan_name not in (
                    'PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY', 'PLAN_REAL_CBS_CBSRUN_LDXJC_DAY') and depend_plan_name in (
                    'PLAN_DWS_WLD_DWS_DWF_DAY', 'PLAN_DWS_CA_DWS_DWF_DAY', 'PLAN_DWS_BICA_DWS_DWF_DAY',
                    'PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY', 'PLAN_REAL_CBS_CBSRUN_LDXJC_DAY',
                    'PLAN_DWS_KDW_PAM_DWS_DWF_DAY'):
                warn_result_text += f'作业名：{job_name} 依赖的 {job_real} 是 {depend_plan_name} 计划 该计划执行时间很晚 请确认出数时间是否符合要求\n'
            if plan_name != 'PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY' and depend_plan_name == 'PLAN_JZZF_MBP_NTCP_REAL_DWS_DAY':
                result_text += f'{job_name} 不允许依赖实时作业的表 {job_real}\n'
                cnt += 1
            if depend_plan_name == 'PLAN_DWS_KDW_PAM_DWS_DWF_DAY':
                result_text += f'{job_name} 不允许老绩效作业的表 {job_real}\n'
                cnt += 1
        if plan_name not in r_plan:
            result_text += f'{plan_name} 未在生产存在\n'
        if domain == 'EDWS_DOMAIN' and ' ' in didp_evt:
            result_text += f'作业名：{job_name} 作业参数有空格，检查JOB的Z列\n'
            cnt += 1
        if '	' in didp_evt:
            result_text += f'作业名：{job_name} 作业参数有TAB键，检查JOB的Z列\n'
            cnt += 1
        if 'PLAN_SA_RECV' in plan_name and 'outfile=' in didp_evt:
            out = extract_values(didp_evt)
            lls = r_job_outfile.get(out)
            if lls is not None and lls != job_name:
                result_text += f'作业名：{job_name}  不对劲 卸数路径' + out + ' 已经存在于 ' + lls + ' 可能是长短作业 保留短作业 上线后联系一审二审人员删除长作业\n'
                cnt += 1
        if 'PLAN_SA_RECV' in plan_name and 'selflg=N' in didp_evt:
            result_text += f'作业名：{job_name} 卸数请选【否】全字段和【否】获取源数据\n'
            cnt += 1
        if 'PLAN_SA_RECV' in plan_name and 'metaflg=Y' in didp_evt:
            result_text += f'作业名：{job_name} 卸数请选【否】全字段和【否】获取源数据\n'
            cnt += 1
        if 'DIDP_DATA_PROVISION.1.0' in program and 'srcfile' not in didp_evt and '-filt' not in didp_evt:
            result_text += f'作业名：{job_name} 卸数是全量卸数，请确认卸数结果表的数据量\n'
            cnt += 1
        if r_planjob.get(job_name) != plan_name and job_name in r_job and seq_name != '0':
            result_text += f'作业名： {job_name} 在生产上属于 {r_planjob.get(job_name)} 计划了需要删除该作业 重新上线后置作业\n'
            cnt += 1
        if r_seqjob.get(job_name) != seq_name and job_name in r_job and seq_name != '0':
            result_text += f'作业名：{job_name} 在生产上属于 {r_seqjob.get(job_name)} 作业流了需要修改,或先删除生产上的作业\n'
            cnt += 1
        if r_planseq.get(seq_name) != plan_name and seq_name in r_seq and seq_name != '0':
            result_text += f'作业名：{job_name}  作业流名：{seq_name} 在生产上属于 {r_planseq.get(seq_name)} 计划了需要修改该作业流\n'
            cnt += 1
        if job_name == 'JOB_DWS_DWS_DWUPRR_GJYW_ACCT_OPEN_INFO_R_00_DAY':
            result_text += f'{job_name} 请确认前置需要 有这四个job JOB_DWS_DWS_DWF_F_AGT_SAVB_BASICINFO_R_ACC_DAY、JOB_DWS_DWS_DWF_F_AGT_SAVB_ACCTINFO_R_ACC_DAY、JOB_DWS_DWS_DWF_F_EVT_SAVR_OPENBOOK_R_00_DAY、JOB_DWS_DWS_DWF_F_PTY_TABLE_R_00_DAY\n'
            cnt += 1
    return result_text, warn_result_text, cnt
