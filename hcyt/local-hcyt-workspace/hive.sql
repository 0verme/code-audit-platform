create table ods.demo_trans (
    acct_no varchar2(32)
);

alter table ods.demo_trans add columns (
    dt string
);
