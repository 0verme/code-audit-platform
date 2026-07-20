# -*- coding: utf-8 -*-
# !/bin/python
from pathlib import Path
import xml.etree.ElementTree as ET

from app.modules.metadata.services.public_data import all_role, all_fine
from app.modules.audit.checks.re_service import read_data_from_file, find_hardcoded_dates, extract_tables, find_dot_strings
from app.config.audit_rules import get_audit_rules
from app.modules.audit.findings import CheckResult

gjz_lists = ['DATETIME', 'DUAL', 'AGE','LAST_DAY']

SENSITIVE_FIELD_ERROR_RULES = {
    '身份证': ['身份证', '身份证号', '证件号码', 'ID_CARD', 'IDCARD', 'ID_NO', 'CERT_NO','SFZ','ZJH','CERT_ID'],
    '地址': ['地址', '开户地址', '家庭地址', '住址', 'ADDRESS', 'ADDR'],
    '手机号': ['手机号', '手机号码', '联系电话', '移动电话', 'MOBILE', 'PHONE_NO', 'TEL_NO', 'PHONE'],
    '座机': ['座机', '座机号', '座机号码', '固定电话', '固话', '办公电话', '公司电话', '家庭电话', '住宅电话', 'LANDLINE', 'FIXED_PHONE', 'FIXED_TEL', 'OFFICE_TEL', 'OFFICE_PHONE', 'HOME_TEL', 'HOME_PHONE', 'TELEPHONE'],
}

SENSITIVE_FIELD_WARNING_RULES = {
    '证件类型': ['证件类型', 'CERT_TYPE', 'ID_TYPE'],
    '卡号': ['卡号', '银行卡号', '借记卡号', '贷记卡号', '信用卡号', '卡片号码', '卡号码', 'CARD_NO', 'CARDNO', 'CARD_NUM', 'CARD_NUMBER', 'BANK_CARD_NO', 'BANKCARD_NO', 'CARD_ID', 'PAN'],
    '账号': ['账号', '帐号', '账户', '帐户', '账户号', '帐户号', '银行账号', '银行帐号', '客户账号', '客户帐号', '结算账号', '结算帐号', 'ACCT_NO', 'ACCTNO', 'ACCOUNT_NO', 'ACCOUNTNO', 'ACC_NO', 'ACCNO', 'ACCOUNT', 'ACCT', 'BANK_ACCT_NO', 'BANK_ACCOUNT_NO', 'CUST_ACCT_NO'],
    '邮箱': ['邮箱', '电子邮箱', '电子邮件', '邮件地址', '邮箱地址', 'E_MAIL', 'EMAIL', 'MAIL', 'EMAIL_ADDR', 'EMAIL_ADDRESS', 'MAIL_ADDR', 'MAIL_ADDRESS'],
}

SENSITIVE_FIELD_ERROR_NAMES = frozenset(SENSITIVE_FIELD_ERROR_RULES)




def get_cpt_sql(fine_name):
    import xml.etree.ElementTree as ET
    # 解析XML文件
    tree = ET.parse(fine_name)
    root = tree.getroot()
    # 使用findall方法查找所有Query元素
    query_elements = root.findall('.//Query')
    reslut = ''
    # 提取并打印每个Query元素的文本内容
    for query_element in query_elements:
        reslut += query_element.text
    return reslut


def _find_sensitive_fields(text, rules):
    upper_text = text.upper()
    hit_fields = []
    for field_name, keywords in rules.items():
        matched_keywords = []
        for keyword in keywords:
            if keyword.upper() in upper_text and keyword not in matched_keywords:
                matched_keywords.append(keyword)
        if matched_keywords:
            hit_fields.append(f"{field_name}(命中关键字: {', '.join(matched_keywords)})")
    return hit_fields


def find_sensitive_fields(text):
    configured_rules = get_audit_rules()["fine_report"]["sensitive_field_rules"]
    if configured_rules:
        error_rules = {
            field_name: keywords
            for field_name, keywords in configured_rules.items()
            if field_name in SENSITIVE_FIELD_ERROR_NAMES
        }
        warning_rules = {
            field_name: keywords
            for field_name, keywords in configured_rules.items()
            if field_name not in SENSITIVE_FIELD_ERROR_NAMES
        }
    else:
        error_rules = SENSITIVE_FIELD_ERROR_RULES
        warning_rules = SENSITIVE_FIELD_WARNING_RULES
    return (
        _find_sensitive_fields(text, error_rules),
        _find_sensitive_fields(text, warning_rules),
    )



def extract_sub_path(file_path, anchor="数据仓库"):
    p = Path(file_path)
    parts = p.parts  # 自动处理 / 和 \

    if anchor in parts:
        idx = parts.index(anchor)
        return Path(*parts[idx:])  # 拼回路径
    else:
        return None

def find_report(xml_file_path):
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    reports = []
    # 查找所有<Report>标签
    for report in root.findall('.//Report'):
        # 检查class和name属性是否匹配
        if report.get('class') == 'com.fr.report.worksheet.WorkSheet':
            reports.append(report.get('name'))
    return reports


def find_column_name(xml_file_path):
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    column_names = []
    # 查找所有<Attributes>标签
    for attributes in root.findall('.//Attributes'):
        # 检查dsName属性是否为'表头'
        if attributes.get('dsName') == '表头':
            # 获取columnName属性值
            column_name = attributes.get('columnName')
            column_names.append(column_name)
    return column_names


def find_clientPaging(xml_file_path):
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    flag = '未开分页引擎'
    # 查找所有<Report>标签
    for report in root.findall('.//LayerReportAttr'):
        # 检查class和name属性是否匹配
        if report.get('clientPaging') == 'true':
            flag = '新计算引擎'
        if report.get('clientPaging') == 'true' and report.get('engineState') == '1':
            flag = '行式引擎'
    return flag


def get_cpt_yuan(fine_name):
    import xml.etree.ElementTree as ET
    # 解析XML文件
    tree = ET.parse(fine_name)
    root = tree.getroot()
    # 使用findall方法查找所有Query元素
    query_elements = root.findall('.//DatabaseName')
    reslut = []
    # 提取并打印每个Query元素的文本内容
    for query_element in query_elements:
        reslut.append(query_element.text.replace('\n', ''))
    reslut = list(set(reslut))
    return ",".join(reslut)


def rule_menu(authority_name):
    print('===========rule_menu==========')
    result = CheckResult()
    try:
        menu_rules = get_audit_rules()["fine_report"]["menu_normalization"]
        required_root_prefix = menu_rules["required_root_prefix"]
        backend_replacement_sources = {
            source for rule in menu_rules["replacements"] if "backend" in rule.get("locations", [])
            for source in rule.get("sources", [])
        }
        menu_replacement_sources = {
            source for rule in menu_rules["replacements"] if "menu" in rule.get("locations", [])
            for source in rule.get("sources", [])
        }
        data = read_data_from_file(authority_name)
        relsut = []
        for i in data.split('\n'):
            i = i.replace('，', ',').replace('\r', '').strip()
            if not i:
                continue
            finememu = i.split(',')[1]
            cpturl = i.split(',')[0]
            if required_root_prefix not in cpturl:
                result.add('fine.menu.root_prefix', '后台目录根路径', 'err', f'{cpturl} 第一段路径不对 需要在开头加上 数据仓库/ ')
            if '.cpt' not in cpturl and '.frm' not in cpturl:
                result.add('fine.menu.backend_extension', '后台目录模板扩展名', 'err', f'{cpturl} 第一段路径不对 目录里应有.cpt或.frm')
            if '(村镇银行发展部)' in cpturl:
                result.add('fine.menu.backend_department_brackets', '后台目录部门括号', 'err', f'{cpturl} 第一段路径不对 (村镇银行发展部) 改为 中文括号（村镇银行发展部） ')
            if any(source in cpturl for source in backend_replacement_sources):
                result.add('fine.menu.backend_department', '后台目录部门名称', 'err', f'{cpturl} 第一段路径不对 会计结算部/会计部报表 改为 运营管理部')
            if ' ' in cpturl:
                result.add('fine.menu.backend_space', '后台目录空格', 'err', f'{cpturl} 里面有空格')
            if required_root_prefix in finememu:
                result.add('fine.menu.frontend_root_prefix', '前台目录根路径', 'err', f'{finememu} 第二段路径不对 数据仓库/ 不需要写')
            if any(source in finememu for source in menu_replacement_sources):
                result.add('fine.menu.frontend_department', '前台目录部门名称', 'err', f'{finememu} 第二段路径不对 会计结算部/会计部报表 改为 运营管理部')
            if '互联网金融部' in menu_replacement_sources and '互联网金融部' in finememu:
                result.add('fine.menu.frontend_finance_department', '前台目录部门名称', 'err', f'{finememu} 第二段路径不对 互联网金融部 改为 互联网金融')
            if '（村镇银行发展部）' in finememu:
                result.add('fine.menu.frontend_department_brackets', '前台目录部门括号', 'err', f'{finememu} 第二段路径不对 （村镇银行发展部） 改为 英文括号 (村镇银行发展部)')
            if '.cpt' in finememu:
                result.add('fine.menu.frontend_extension', '前台目录模板扩展名', 'err', f'{finememu} 第二段路径不对 目录里不应有.cpt')
            if ' ' in finememu:
                result.add('fine.menu.frontend_space', '前台目录空格', 'err', f'{finememu} 里面有空格')
            relsut.append(finememu.split('/')[-1])
        result.artifacts['menu_entries'] = relsut
        return result
    except Exception as e:
        result.add('fine.menu.execution_error', '目录规则执行异常', 'err', str(e.args))
        result.artifacts['menu_entries'] = []
        return result

def normalize_fine_entry_name(value):
    if value is None:
        return ''
    text = str(value).replace('\ufeff', '').replace('\r', '').replace('\n', '').strip()
    text = text.replace('，', ',')
    if '/' in text:
        text = text.split('/')[-1]
    if text.endswith('.cpt') or text.endswith('.frm'):
        text = text.rsplit('.', 1)[0]
    return text.strip()


def rule_authority(authority_name,memu_url):
    print('===========rule_authority==========')
    role_lists, fine_lists = all_role(), all_fine()

    result = CheckResult()
    try:
        data = read_data_from_file(authority_name)
        authority_lists = [['报表名称', '权限']]
        valid_report_names = {
            normalize_fine_entry_name(name)
            for name in fine_lists + memu_url
            if normalize_fine_entry_name(name)
        }
        for i in data.split('\n'):
            line = i.replace('，', ',').replace('\r\n', '').strip()
            if not line:
                continue
            repot_name = normalize_fine_entry_name(line.split(',')[0])
            r_lists = [item.replace('\n', '').strip() for item in line.split(',')[1:] if item.strip()]
            authority_lists.append([repot_name, r_lists])
            for j in r_lists:
                if j not in role_lists:
                    print(j)
                    result.add('fine.authority.missing_role', '生产角色登记', 'err', f'{j} 生产没有该角色 ')
            if repot_name and repot_name not in valid_report_names:
                result.add('fine.authority.missing_menu', '报表目录登记', 'err', f'{repot_name} 未有该目录 ')
        return result
    except Exception as e:
        result.add('fine.authority.execution_error', '权限规则执行异常', 'err', str(e.args))
        return result

def rule_fine(fine_name):
    print('===========rule_fine==========')
    sstb_name = []
    viewlet_url = str(extract_sub_path(fine_name))
    print(fine_name)
    result = CheckResult()
    data = read_data_from_file(fine_name)
    f_name = fine_name.split('/')[-1]
    if '[' not in f_name or ']' not in f_name:
        result.add('fine.report.missing_number', '报表编号', 'err', '该帆软没有报表编号')
    if ' ' in fine_name:
        result.add('fine.report.name_space', '报表名称空格', 'err', '名称有带空值')
    if 'DISTINCT' in data.upper():
        result.add('fine.report.distinct_review', 'DISTINCT 审查', 'err', '请审核重点检查脚本中的distinct是否必须添加 有无关联出重复数据')
    if '<ATTR DIVIDEMODE="1"/>' in data:
        result.add('fine.report.group_only', '报表列表展示', 'err', '该报表没有列表展示 全是分组，请确认是否需要分组')
    if "权限机构树" in data and "SELECT MIN(T.NBJGH)  FROM DWP.P_SYS_USER_INFO T WHERE T.GH ='${FINE_USERNAME}" not in data.upper():
        result.add('fine.report.org_tree_default', '机构树默认值', 'err', '机构树默认值不对')
    for i in sstb_name:
        if i.upper() in data.upper():
            result.add('fine.report.forbidden_table', '错误表引用', 'err', f' {viewlet_url} 用错表 {i}')
    try:
        yuan = get_cpt_yuan(fine_name).upper()
        sheets = find_report(fine_name)
        reslut = get_cpt_sql(fine_name).upper()
        yq = find_clientPaging(fine_name)
        sensitive_error_fields, sensitive_warning_fields = find_sensitive_fields(reslut)
        if sensitive_error_fields:
            result.add('fine.report.sensitive_fields', '敏感信息字段', 'err', f"检测到敏感信息字段: {','.join(sensitive_error_fields)}，请重点确认是否涉及证件或个人隐私信息展示")
        if sensitive_warning_fields:
            result.add('fine.report.sensitive_fields', '敏感信息字段', 'warn', f"检测到敏感信息字段: {','.join(sensitive_warning_fields)}，请重点确认是否涉及证件或个人隐私信息展示")
        datekk = find_hardcoded_dates(reslut)
        datekk = ["'" + item + "'" for item in datekk]
        datekk = list(set(datekk))
        if len(datekk) > 0:
            result.add('fine.report.hardcoded_date', '写死日期', 'err', "检测到的写死日期 请甄别是否业务需求 (如果是注释日期去掉两头引号): " + " ".join(datekk))

        if '=(SELECT' in reslut:
            result.add('fine.report.scalar_subquery', '标量子查询', 'err', '存在 = ( select 子查询 注意跑批效率 和 万一数据多条导致程序报错')
        reslut = reslut.replace('JOIN(SELECT', '')
        if 'IN(SELECT' in reslut:
            result.add('fine.report.in_subquery', 'IN 子查询', 'err', '存在 in ( select 子查询 注意跑批效率')
        if '.END_DT>=' in reslut:
            result.add('fine.report.end_dt_range', '拉链结束日期范围', 'err', '检测到 END_DT>= 注意拉链数据重复')
        if "D_DATE=TO_DATE('" in data:
            result.add('fine.report.d_date_to_date', '主题表日期写法', 'err', "存在关键字 D_DATE=TO_DATE(' 使用主题表请改为 d_date ='YYYYMMDD' ")
        if "D_DATE=DATE'" in data:
            result.add('fine.report.d_date_literal', '主题表日期写法', 'err', "存在关键 D_DATE = DATE' 使用主题表请改为 d_date ='YYYYMMDD' ")

        tables = extract_tables(reslut)
        tables2 = find_dot_strings(reslut)
        tables_total = tables + tables2
        sql_table = list(set(tables_total))
        for i in sql_table:
            if i.upper() in gjz_lists:
                pass
            elif '.' not in i.upper():
                result.add('fine.report.missing_schema', '表名缺少 SCHEMA', 'err', f'表名 {i} 没有带SCHAME请注意加上 如果是用with表注意效率')
        sql_table = sorted(sql_table)

        result.artifacts.update({
            'viewlet': viewlet_url,
            'connection': yuan,
            'engine': yq,
            'sheets': sheets,
            'sql_tables': sql_table,
        })
        return result

    except Exception as e:
        result.add('fine.report.execution_error', '规则执行异常', 'warn', str(e.args))
        return result
