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
    all_upstream_system_ids,
    all_seq,
    all_seqjob,
    get_job2,
)
from ....shared.file_analysis import extract_values
from ....shared.dependency import build_dependency_graph, find_cycles
from .description_rule import has_meaningful_job_description
from app.config.audit_rules import get_audit_rules
from ....shared.findings import CheckResult

def _schedule_rules():
    return get_audit_rules()["hcyt"]["schedule"]

def _normalize_job_value(value):
    if value is None or pd.isna(value):
        return ''
    return str(value).strip().upper()


def _normalize_dependency_value(value):
    if value is None or pd.isna(value):
        return ''
    return str(value).strip().upper()


def _job_description_error_message(job_name, description_rules):
    message = f'{job_name} 第四列作业描述必须要明确加工作用'
    reference_url = str(description_rules.get("reference_url", "") or "").strip()
    if reference_url:
        message = f'{message} 参考：{reference_url}'
    return message


def _collect_online_job_dependencies(job_records):
    online_jobs = {}
    for row in job_records:
        job_name = _normalize_job_value(row[2])
        if not job_name:
            continue
        online_jobs[job_name] = _normalize_dependency_value(row[27])
    return online_jobs


def _find_online_job_dependency_cycles(job_records, job_rows=None, job_dependencies=None):
    online_jobs = _collect_online_job_dependencies(job_records)
    if not online_jobs:
        return []

    merged_jobs = {}
    if job_dependencies is not None:
        merged_jobs.update(job_dependencies)
    elif job_rows is None:
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
    result = CheckResult()
    planname_lists = []
    upstream_system_ids = []
    for i in all_plan():
        planname_lists.append(i[0])
    for i in all_upstream_system_ids():
        if i and i[0]:
            upstream_system_ids.append(str(i[0]).strip().upper())
    upstream_system_id_set = set(upstream_system_ids)
    rr_plan = []
    rules = _schedule_rules()
    for _, row in df.iterrows():
        plan_name = '' if pd.isna(row.iloc[0]) else str(row.iloc[0]).strip()
        plan_depand = '' if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        if not plan_name:
            continue
        if plan_name in rules["invalid_plan_names"]:
            result.add('hcyt.schedule.plan.invalid_name', '计划名规范', 'err', f'计划名: {plan_name} 计划名有误')

        for keyword, allowed_names in rules["plan_name_rules"].items():
            if keyword in plan_name and plan_name not in allowed_names:
                result.add(
                    f'hcyt.schedule.plan.{keyword.lower()}_name',
                    f'{keyword} 计划名',
                    'err',
                    f'计划名: {plan_name} 计划名有误',
                )

        if plan_depand:
            result.add('hcyt.schedule.plan.predecessor', '计划前置依赖', 'err', f'计划名: {plan_name} 存在前置依赖 {plan_depand}，请检查')

        if plan_name.startswith(rules["recv_mapping_plan_prefix"]) and plan_name.upper() not in upstream_system_id_set:
            result.add('hcyt.schedule.plan.upstream_registration', '上游系统登记', 'warn', f'计划名 {plan_name} 未在数据资产系统维护上游系统')

        if plan_name not in planname_lists:
            if plan_name.startswith(rules["missing_plan_warning_patterns"][0]["prefix"]) and plan_name.endswith(rules["missing_plan_warning_patterns"][0]["suffix"]):
                result.add('hcyt.schedule.plan.missing_dws_plan', '生产计划登记', 'warn', f'计划名: {plan_name} 未在生产调度（自动触发-一审检查是否是新增系统加工！！！！！！）')
            elif plan_name.startswith(rules["missing_plan_warning_patterns"][1]["prefix"]) and plan_name.endswith(rules["missing_plan_warning_patterns"][1]["suffix"]):
                result.add('hcyt.schedule.plan.missing_send_plan', '生产计划登记', 'warn', f'计划名: {plan_name} 未在生产调度（自动触发-一审检查是否是新增系统推数！！！！！！）')
            else:
                result.add('hcyt.schedule.plan.missing_production_plan', '生产计划登记', 'err', f'计划名: {plan_name} 未在生产调度，请检查')

        rr_plan.append(plan_name)

    r_plan = list(set(rr_plan + planname_lists))

    result.artifacts['plans'] = r_plan
    return result


def rule_excle_seq(df):
    print('===================================rule_excle_seq=================================')
    real_seq = {
        str(row[0]).strip()
        for row in all_real_seq()
        if row and not pd.isna(row[0])
    }
    result = CheckResult()
    for _, row in df.iterrows():
        seq_name = '' if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
        if seq_name in real_seq:
            result.add('hcyt.schedule.seq.realtime_override', '循环作业流覆盖', 'err', f'作业流名：{seq_name}  作业流是循环作业,会覆盖生产的循环调度,需要删除不用上线')
    return result


def rule_excle_job(df, r_plan=None, timing_log=None, job_rows=None):
    print('===================================rule_excle_job=================================')
    result = CheckResult()
    rules = _schedule_rules()

    def log_timing(message):
        if timing_log:
            timing_log(message)

    stage_start = time.perf_counter()
    r_job_outfile = {}
    for i in all_job_outfile():
        r_job_outfile[i[0]] = i[1]
    log_timing(f"JOB规则 all_job_outfile 查询/整理完成：{len(r_job_outfile)} 行，{time.perf_counter() - stage_start:.2f}s")

    r_planseq = {}
    r_seqjob = {}
    r_planjob = {}
    r_seq = set()
    real_seq = set()
    r_job = set()
    r_job_status = {}
    job_dependencies = None
    if job_rows is not None:
        stage_start = time.perf_counter()
        job_dependencies = {}
        for row in job_rows:
            if len(row) > 1:
                r_planseq[row[1]] = row[0]
                if not pd.isna(row[1]):
                    r_seq.add(row[1])
                    if row[0] in rules["real_job_plan_names"]:
                        real_seq.add(row[1])
            if len(row) > 2:
                r_seqjob[row[2]] = row[1]
                r_planjob[row[2]] = row[0]
                normalized_job_name = _normalize_job_value(row[2])
                if normalized_job_name:
                    dependency = '' if len(row) <= 27 else _normalize_dependency_value(row[27])
                    job_dependencies[normalized_job_name] = dependency
                job_name = '' if pd.isna(row[2]) else str(row[2]).strip()
                if job_name:
                    job_status_value = '' if len(row) <= 23 or pd.isna(row[23]) else str(row[23]).strip()
                    job_status = '禁用' if job_status_value in rules["disabled_status_values"] else '启用' if job_status_value in rules["enabled_status_values"] else job_status_value
                    r_job.add(job_name)
                    r_job_status[job_name] = job_status
        log_timing(
            f"JOB规则生产元数据单次整理完成：{len(job_rows)} 行，"
            f"{time.perf_counter() - stage_start:.2f}s"
        )
    else:
        stage_start = time.perf_counter()
        planseq_rows = all_planseq()
        for i in planseq_rows:
            plan_name = i[0]
            seq_name = i[1]
            r_planseq[seq_name] = plan_name
        log_timing(f"JOB规则 all_planseq 查询/整理完成：{len(r_planseq)} 行，{time.perf_counter() - stage_start:.2f}s")

        stage_start = time.perf_counter()
        seqjob_rows = all_seqjob()
        for i in seqjob_rows:
            seq_name = i[0]
            job_name = i[1]
            r_seqjob[job_name] = seq_name
        log_timing(f"JOB规则 all_seqjob 查询/整理完成：{len(r_seqjob)} 行，{time.perf_counter() - stage_start:.2f}s")

        stage_start = time.perf_counter()
        planjob_rows = all_planjob()
        for i in planjob_rows:
            plan_name = i[0]
            job_name = i[1]
            r_planjob[job_name] = plan_name
        log_timing(f"JOB规则 all_planjob 查询/整理完成：{len(r_planjob)} 行，{time.perf_counter() - stage_start:.2f}s")

        stage_start = time.perf_counter()
        r_seq = {i[0] for i in all_seq()}
        log_timing(f"JOB规则 all_seq 查询/整理完成：{len(r_seq)} 行，{time.perf_counter() - stage_start:.2f}s")

    if r_plan is None:
        stage_start = time.perf_counter()
        r_plan = []
        for i in all_plan():
            r_plan.append(i[0])
        log_timing(f"JOB规则 all_plan 查询/整理完成：{len(r_plan)} 行，{time.perf_counter() - stage_start:.2f}s")

    if job_rows is None:
        stage_start = time.perf_counter()
        real_seq = {j[0] for j in all_real_seq()}
        log_timing(f"JOB规则 all_real_seq 查询/整理完成：{len(real_seq)} 行，{time.perf_counter() - stage_start:.2f}s")

        stage_start = time.perf_counter()
        status_rows = get_job2()
        for i in status_rows:
            job_name = '' if pd.isna(i[0]) else str(i[0]).strip()
            job_status = '' if len(i) < 2 or pd.isna(i[1]) else str(i[1]).strip()
            if job_name:
                r_job.add(job_name)
                r_job_status[job_name] = job_status
        log_timing(f"JOB规则 get_job2 查询/整理完成：{len(r_job)} 行，{time.perf_counter() - stage_start:.2f}s")

    stage_start = time.perf_counter()
    job_records = list(df.itertuples(index=False, name=None))
    log_timing(f"JOB规则 JOB Excel 转换完成：{len(job_records)} 行，{time.perf_counter() - stage_start:.2f}s")

    job_list = []
    yilai_job = set(r_job)
    for row in job_records:
        job_name = '' if pd.isna(row[2]) else str(row[2]).strip()
        if job_name:
            yilai_job.add(job_name)

    stage_start = time.perf_counter()
    dependency_cycles = _find_online_job_dependency_cycles(
        job_records,
        job_rows,
        job_dependencies=job_dependencies,
    )
    log_timing(f"JOB规则 依赖环检查完成：{len(dependency_cycles)} 个环，{time.perf_counter() - stage_start:.2f}s")
    for cycle in dependency_cycles:
        result.add('hcyt.schedule.job.dependency_cycle', '作业依赖成环', 'err', f'作业依赖成环，请检查: {" -> ".join(cycle)}', evidence={'cycle': cycle})

    stage_start = time.perf_counter()
    for row in job_records:
        plan_name = '' if pd.isna(row[0]) else str(row[0]).strip()
        seq_name = '' if pd.isna(row[1]) else str(row[1]).strip()
        job_name = '' if pd.isna(row[2]) else str(row[2]).strip()
        miaoshu = '' if pd.isna(row[3]) else str(row[3]).strip()
        program = '' if pd.isna(row[4]) else str(row[4]).strip()
        domain = '' if pd.isna(row[5]) else str(row[5]).strip()
        level = '' if pd.isna(row[6]) else str(row[6]).strip()
        cale = '' if pd.isna(row[9]) else str(row[9]).strip()
        didp_evt = '' if pd.isna(row[25]) else str(row[25]).strip()
        depand = '' if pd.isna(row[27]) else str(row[27]).strip()
        if job_name.upper() != job_name:
            result.add('hcyt.schedule.job.lowercase_job', '作业名大小写', 'err', f'作业名: {job_name} 不应该存在小写 请规范')
        if plan_name.upper() != plan_name:
            result.add('hcyt.schedule.job.lowercase_plan', '计划名大小写', 'err', f'计划名:{plan_name} 不应该存在小写 请规范')
        if seq_name.upper() != seq_name:
            result.add('hcyt.schedule.job.lowercase_sequence', '作业流名大小写', 'err', f' 作业流名:{seq_name} 不应该存在小写 请规范')
        if r_job_status.get(job_name) == '禁用':
            result.add('hcyt.schedule.job.disabled_reenable', '禁用作业重新启用', 'err', f'作业名：{job_name} 生产上是禁用状态，本次上线会重新启用，请确认是否符合预期')
        if seq_name == '':
            result.add('hcyt.schedule.job.empty_sequence', '作业流名为空', 'err', f' 作业流名:{seq_name} 不应该为空 要么是0 请确认')
        if seq_name in real_seq and str(level) not in rules["realtime_priority_values"]:
            result.add('hcyt.schedule.job.realtime_priority', '实时作业优先级', 'err', f'{job_name} 实时作业的优先级需要设置 99')
        if rules["realtime_sequence_keyword"] in seq_name and str(level) not in rules["realtime_priority_values"]:
            result.add('hcyt.schedule.job.realtime_priority', '实时作业优先级', 'err', f'{job_name} 实时作业的优先级需要设置 99')
        if not has_meaningful_job_description(
            miaoshu,
            job_name,
            rules["description_validation"],
        ):
            result.add(
                'hcyt.schedule.job.description',
                '作业描述',
                'err',
                _job_description_error_message(job_name, rules["description_validation"]),
            )
        if plan_name in rules["realtime_calendar_plans"] and cale != rules["realtime_calendar_value"]:
            result.add('hcyt.schedule.job.realtime_calendar', '实时作业日历', 'err', f'{job_name} 的执行日历 {cale} 不对  实际应该是每日跑批 SYS_EVERYDAY_CALENDAR')
        if rules["forbidden_domain_plan_keywords"][0] in plan_name and domain == rules["forbidden_domain"]:
            result.add('hcyt.schedule.job.execution_domain', '作业执行域', 'err', f'{job_name} 执行域有误 不应为EDWS_DOMAIN')
        if rules["forbidden_domain_plan_keywords"][1] in plan_name and domain == rules["forbidden_domain"]:
            result.add('hcyt.schedule.job.execution_domain', '作业执行域', 'err', f'{job_name} 执行域有误 不应为EDWS_DOMAIN')
        if rules["forbidden_domain_plan_keywords"][2] in plan_name and domain == rules["forbidden_domain"]:
            result.add('hcyt.schedule.job.execution_domain', '作业执行域', 'err', f'{job_name} 执行域有误 不应为EDWS_DOMAIN')
        if domain not in rules["allowed_domains"]:
            result.add('hcyt.schedule.job.invalid_domain', '作业执行域', 'err', f'{job_name} 执行域有误不应为 ' + domain)
        for keyword, allowed_names in rules["sequence_name_rules"].items():
            if keyword in plan_name and seq_name not in allowed_names:
                result.add(
                    f'hcyt.schedule.job.{keyword.lower()}_sequence',
                    f'{keyword} 作业流名称',
                    'err',
                    f'{seq_name} 计划流名称有误',
                )
        job_list.append([plan_name, seq_name, job_name, domain, didp_evt, depand])
        if rules["dependency_required_job_keywords"][0] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dwf_dependency', 'DWF 前置依赖', 'err', f'{job_name} DWF层为什么没有前置依赖')
        elif any(keyword in job_name for keyword in rules["dependency_exceptions"]):
            pass
        elif rules["dependency_required_job_keywords"][1] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dwo_dependency', 'DWO 前置依赖', 'err', f'{job_name} DWO层为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][2] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][3] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][4] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][5] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][6] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][7] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        elif rules["dependency_required_job_keywords"][8] in job_name and depand == '':
            result.add('hcyt.schedule.job.missing_dependency', '作业前置依赖', 'err', f'{job_name} 为什么没有前置依赖')
        if '：' in depand:
            result.add('hcyt.schedule.job.chinese_dependency_colon', '依赖列中文冒号', 'err', f'{job_name} 依赖列存在中文的冒号 ： 请修改')
        job_depand = depand.split('|')
        for i in job_depand:
            if i == '':
                job_real = ''
            else:
                parts = i.split(':')
                job_real = parts[1] if len(parts) > 1 else ''
            depend_plan_name = r_planjob.get(job_real, '')
            if domain == rules["forbidden_domain"] and rules["provision_job_keyword"] in job_real:
                result.add('hcyt.schedule.job.provision_dependency', '加工依赖卸数作业', 'err', f'{job_name} 加工作业的前置依赖不应该有卸数作业{job_real} ')
            if job_real not in yilai_job and job_real != '':
                result.add('hcyt.schedule.job.missing_production_dependency', '生产前置作业', 'err', f'{job_name} 的前置作业 {job_real} 在生产不存在')
            if job_real in (job_name, plan_name):
                result.add('hcyt.schedule.job.self_dependency', '作业自依赖', 'err', f'{job_name} 不要依赖自身 {job_real} ')
            if plan_name.endswith(rules["realtime_plan_suffix"]) and job_real and depend_plan_name and not depend_plan_name.endswith(rules["realtime_plan_suffix"]):
                result.add('hcyt.schedule.job.realtime_plan_dependency', '实时计划依赖', 'err', f'作业名：{job_name} 所属计划 {plan_name} 为REAL计划，依赖的作业 {job_real} 属于普通计划 {depend_plan_name}，请检查')
            if plan_name not in rules["late_plan_exceptions"] and depend_plan_name in rules["late_plan_names"]:
                result.add('hcyt.schedule.job.late_plan_dependency', '晚执行计划依赖', 'warn', f'作业名：{job_name} 依赖的 {job_real} 是 {depend_plan_name} 计划 该计划执行时间很晚 请确认出数时间是否符合要求')
            if plan_name != rules["realtime_dependency_exception"] and depend_plan_name == rules["forbidden_dependency_plans"][0]:
                result.add('hcyt.schedule.job.forbidden_realtime_dependency', '禁止实时作业依赖', 'err', f'{job_name} 不允许依赖实时作业的表 {job_real}')
            if depend_plan_name == rules["forbidden_dependency_plans"][1]:
                result.add('hcyt.schedule.job.forbidden_legacy_dependency', '禁止老绩效依赖', 'err', f'{job_name} 不允许老绩效作业的表 {job_real}')
        if plan_name not in r_plan:
            result.add('hcyt.schedule.job.missing_production_plan', '生产计划登记', 'err', f'{plan_name} 未在生产存在')
        if domain == rules["forbidden_domain"] and ' ' in didp_evt:
            result.add('hcyt.schedule.job.parameter_space', '作业参数空格', 'err', f'作业名：{job_name} 作业参数有空格，检查JOB的Z列')
        if '	' in didp_evt:
            result.add('hcyt.schedule.job.parameter_tab', '作业参数 TAB', 'err', f'作业名：{job_name} 作业参数有TAB键，检查JOB的Z列')
        if rules["recv_plan_keyword"] in plan_name and 'outfile=' in didp_evt:
            out = extract_values(didp_evt)
            lls = r_job_outfile.get(out)
            if lls is not None and lls != job_name:
                result.add('hcyt.schedule.job.duplicate_export_path', '卸数路径重复', 'err', f'作业名：{job_name}  不对劲 卸数路径' + out + ' 已经存在于 ' + lls + ' 可能是长短作业 保留短作业 上线后联系一审二审人员删除长作业')
        if rules["recv_plan_keyword"] in plan_name and 'selflg=N' in didp_evt:
            result.add('hcyt.schedule.job.export_flags', '卸数字段选项', 'err', f'作业名：{job_name} 卸数请选【否】全字段和【否】获取源数据')
        if rules["recv_plan_keyword"] in plan_name and 'metaflg=Y' in didp_evt:
            result.add('hcyt.schedule.job.export_flags', '卸数字段选项', 'err', f'作业名：{job_name} 卸数请选【否】全字段和【否】获取源数据')
        if 'DIDP_DATA_PROVISION.1.0' in program and 'srcfile' not in didp_evt and '-filt' not in didp_evt:
            result.add('hcyt.schedule.job.full_export', '全量卸数', 'err', f'作业名：{job_name} 卸数是全量卸数，请确认卸数结果表的数据量')
        if r_planjob.get(job_name) != plan_name and job_name in r_job and seq_name != '0':
            result.add('hcyt.schedule.job.production_plan_mismatch', '生产计划归属', 'err', f'作业名： {job_name} 在生产上属于 {r_planjob.get(job_name)} 计划了需要删除该作业 重新上线后置作业')
        if r_seqjob.get(job_name) != seq_name and job_name in r_job and seq_name != '0':
            result.add('hcyt.schedule.job.production_sequence_mismatch', '生产作业流归属', 'err', f'作业名：{job_name} 在生产上属于 {r_seqjob.get(job_name)} 作业流了需要修改,或先删除生产上的作业')
        if r_planseq.get(seq_name) != plan_name and seq_name in r_seq and seq_name != '0':
            result.add('hcyt.schedule.job.sequence_plan_mismatch', '作业流计划归属', 'err', f'作业名：{job_name}  作业流名：{seq_name} 在生产上属于 {r_planseq.get(seq_name)} 计划了需要修改该作业流')
        if job_name in rules["required_predecessors"]:
            result.add('hcyt.schedule.job.required_predecessors', '指定前置作业', 'err', f'{job_name} 请确认前置需要 有这四个job JOB_DWS_DWS_DWF_F_AGT_SAVB_BASICINFO_R_ACC_DAY、JOB_DWS_DWS_DWF_F_AGT_SAVB_ACCTINFO_R_ACC_DAY、JOB_DWS_DWS_DWF_F_EVT_SAVR_OPENBOOK_R_00_DAY、JOB_DWS_DWS_DWF_F_PTY_TABLE_R_00_DAY')
    log_timing(f"JOB规则主循环完成：{len(job_records)} 行，{time.perf_counter() - stage_start:.2f}s")
    return result
