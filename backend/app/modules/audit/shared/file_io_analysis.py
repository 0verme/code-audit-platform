from __future__ import annotations

import os
import re
import shutil
from collections import Counter
from datetime import datetime

import pandas as pd
import xlrd

from .path_export import tail_path

def get_result(merge_df, input_path, tail_levels=3, prog_path_col=None):
    input_tail = tail_path(input_path, tail_levels)

    if prog_path_col is None:
        raise ValueError("未传入程序路径列名 prog_path_col")
    if prog_path_col not in merge_df.columns:
        raise ValueError(f"程序路径列不存在: {prog_path_col}")

    df = merge_df.copy()
    df["_path_tail"] = df[prog_path_col].apply(lambda x: tail_path(x, tail_levels))
    result = df[df["_path_tail"] == input_tail].copy()

    if result.empty:
        raise ValueError(f"未找到匹配程序路径: {input_path}")

    selected_columns = [result.columns[2], result.columns[9], result.columns[27]]
    result = result[selected_columns]
    return result.iloc[0].tolist()


def load_txt_to_df2(file_path, columns):
    data = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            parts = line.split(',', 1)  # 只按第一个逗号切一次

            if len(parts) == 2:
                data.append(parts)
            else:
                data.append([parts[0], None])  # 没有逗号的情况

    return pd.DataFrame(data, columns=columns)

def load_xls_to_df(file_path):
    """
    读取无表头txt并转换为DataFrame
    参数：
    file_path: 文件路径
    columns: 列名列表
    sep: 分隔符（默认逗号，可改为\t、|等）
    encoding: 文件编码（默认utf-8）
    返回：
    pandas DataFrame
    """
    df = pd.read_excel(file_path,engine='xlrd')
    return df



def load_txt_to_df(file_path, columns, sep=",", encoding="utf-8"):
    """
    读取无表头txt并转换为DataFrame
    参数：
    file_path: 文件路径
    columns: 列名列表
    sep: 分隔符（默认逗号，可改为\t、|等）
    encoding: 文件编码（默认utf-8）
    返回：
    pandas DataFrame
    """
    df = pd.read_csv(
        file_path,
        sep=sep,
        header=None,     # 关键：无表头
        names=columns,   # 指定列名
        encoding=encoding
    )
    return df

"""判断字符是否是中文"""
def is_chinese(char):
    return '\u4e00' <= char <= '\u9fff'

def clear_folder(folder_path):
    shutil.rmtree(folder_path)
    os.makedirs(folder_path)

"""
读取所有带.的字符串
"""
def find_dot_strings(sql):
    # 使用正则表达式匹配带有"."的字符串
    pattern = r'\b\w+\.\w+\b'
    matches = re.findall(pattern, sql)
    reslut = []
    matches = [match for match in matches if not any(is_chinese(c) for c in match)]
    for i in matches:
        i = i.upper()
        if i.split('.')[0] in ('DM', 'DWA', 'DWD', 'DWUPRR', 'DWM', 'DWP', 'DWO', 'DWF'):
            reslut.append(i)
    return reslut

"""
读取from和join 后面的表名
"""
def extract_tables(sql_query):
    # 使用正则表达式匹配 FROM 和 LEFT JOIN 后面的表名
    pattern = r'\b(FROM|JOIN|USING)\s+([\w.]+)'
    matches = re.findall(pattern, sql_query, re.IGNORECASE)
    matches = [match for match in matches if not any(is_chinese(c) for c in match)]
    tables = set()
    for match in matches:
        table_name = match[1].strip()
        if table_name:
            tables.add(table_name.upper())
    return list(tables)


def find_hardcoded_dates(sql_content):
    # 定义日期的正则表达式模式
    date_pattern = r"'\b\d{4}[-]?\d{2}[-]?\d{2}\b'"
    # 查找所有匹配的日期
    matches = re.findall(date_pattern, sql_content)
    # 筛选出有效的日期
    valid_dates = []
    for match in matches:
        match = match.strip("'")
        try:
            if '-' in match:
                date_obj = datetime.strptime(match, '%Y-%m-%d')
            else:
                date_obj = datetime.strptime(match, '%Y%m%d')
            # 检查年份是否在1900到3000之间
            if 1900 <= date_obj.year <= 3000:
                valid_dates.append(match)
        except ValueError:
            # 如果转换失败，则认为这不是一个有效的日期
            continue
    return valid_dates

def find_unique_elements_with_count(a, b):
    counter_A = Counter(a)
    counter_B = Counter(b)
    c = []
    d = []
    for element in counter_A:
        if element not in counter_B:
            c.extend([element] * counter_A[element])
    for element in counter_B:
        if element not in counter_A:
            d.extend([element] * counter_B[element])
    return c, d

def read_excel_file(file_path):
    workbook = xlrd.open_workbook(file_path)
    worksheet = workbook.sheet_by_index(0)
    data = [worksheet.row_values(rownum) for rownum in range(1, worksheet.nrows)]
    return data


def extract_values(input_string):
    # 定义正则表达式模式来匹配 outfile= 和 proname= 的值
    outfile_pattern = r'-outfile:\d+:(outfile=[^:]+):0'
    # 查找所有匹配项
    outfile_matches = re.findall(outfile_pattern, input_string)
    # 提取值并去除前缀
    outfile_value = [match.replace('outfile=', '') for match in outfile_matches]
    if len(outfile_value) > 0:
        outfile_value = outfile_value[0]
    else:
        outfile_value = ''
    return outfile_value


_PRONAME_VALUE_RE = re.compile(
    r"""(?ix)
    (?<![A-Z0-9_])
    proname\s*=\s*
    ["']?
    ([^:\s()"'`;]+)
    """
)
_SEND_PRONAME_RE = re.compile(r"(?i)_SEND[0-9]*$")


def extract_pronames(input_string):
    """Extract normalized proname values from a JOB parameter string."""
    seen = set()
    values = []
    for match in _PRONAME_VALUE_RE.finditer(str(input_string or "")):
        value = match.group(1).strip().upper()
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return values


def is_send_proname(value):
    return bool(_SEND_PRONAME_RE.search(str(value or "").strip()))


def has_send_proname(input_string):
    return any(is_send_proname(value) for value in extract_pronames(input_string))

def detect_file_format(file_path):
    with open(file_path, 'rb') as file:
        first_line = file.readline()
        if b'\r\n' in first_line:
            return 'DOS'
        elif b'\n' in first_line:
            return 'Unix'
        else:
            return 'Unknown'

def read_data_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            raw_content = file.read()

        for encoding in ('utf-8', 'utf-8-sig', 'gb18030', 'gbk'):
            try:
                return raw_content.decode(encoding)
            except UnicodeDecodeError:
                pass

        return raw_content.decode('utf-8', errors='replace')
    else:
        return ''
