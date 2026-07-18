"""NUPS 加工程序违规样例。

下面的填充区用于越过规则对前 1000 个字符的模板过滤。文件只参与静态审计，不执行。
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

RISK_SQL = """
create table DWM.BAD_PROGRAM_TABLE (
    CUSTOMER_ID character varying(20),
    CERT_NO varchar2(32)
) TO GROUP GROUP_VERSION1;

create view DWM.V_NUPS_PROGRAM as
select * from DWM.BAD_PROGRAM_TABLE;

create function DWM.F_NUPS_PROGRAM()
returns integer as 'select 1';

insert into DWM.BAD_NUPS_RESULT
select distinct
    nvl(nvl(T.BALANCE, 0), 0),
    coalesce(coalesce(T.BALANCE, 0), 0)
from DWM.M_NUPS_SOURCE T
join SOURCE_WITHOUT_SCHEMA S on T.CUSTOMER_ID = S.CUSTOMER_ID
where T.CUSTOMER_ID = S.CUSTOMER_ID(+)
  and T.CUSTOMER_ID=(select max(X.CUSTOMER_ID) from DWM.M_NUPS_X X)
  and T.CUSTOMER_ID in(select Y.CUSTOMER_ID from DWM.M_NUPS_Y Y)
  and T.END_DT>='20240101'
  and T.D_DATE=TO_DATE('20240102', 'YYYYMMDD')
  and T.D_DATE=DATE'2024-01-03'
  and DATE(D_DATE)=DATE'2024-01-04'
  and TO_DATE(D_DATE, 'YYYYMMDD')>=DATE'2024-01-05'
  and T.D_DATE<'20241231'
  and T.D_DATE>'20240101';
"""

for i in range(2):
    print(i)
