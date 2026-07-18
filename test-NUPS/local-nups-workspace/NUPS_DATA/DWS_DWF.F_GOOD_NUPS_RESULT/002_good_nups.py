"""NUPS 合规加工程序，用于验证空问题列表。"""

SQL = """
insert into DWF.F_GOOD_NUPS_RESULT
select SOURCE_ID, REPORT_VALUE
from DWF.F_NUPS_SOURCE;
"""

LOG_MESSAGE = "影响条数"
