-- NUPS SQL 违规样例：只用于本地审计展示。
create table DWM.BAD_NUPS_TABLE (
    CUSTOMER_ID varchar2(32),
    BALANCE numeric(18, 2)
) TO GROUP GROUP_VERSION1;

create temporary table TMP.BAD_TEMP_TABLE (
    ID bigint
);

alter table DWM.BAD_NUPS_TABLE
    add column NEW_FIELD varchar(20);

create view DWM.V_NUPS_AUDIT as
select CUSTOMER_ID from DWM.BAD_NUPS_TABLE;

create function DWM.F_NUPS_AUDIT()
returns integer
as $$
begin
    return 1;
end;
$$ language plpgsql;

update DWM.M_PUB_CODE_MAP_NEW
set CODE_NAME = 'WLQ'
where CODE_ID = '001';
