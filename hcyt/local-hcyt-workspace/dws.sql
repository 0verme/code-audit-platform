create table dwuprr.ijep_demo_asset (
    cust_no varchar2(32),
    bal_amt numeric(18,2)
) TO GROUP GROUP_VERSION1;

alter table dwuprr.ijep_demo_asset add column dt varchar(8);

insert into dwm.m_demo_target
select distinct cust_no, bal_amt
from dwuprr.ijep_demo_asset;
