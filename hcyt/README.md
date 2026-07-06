# demo_test

This folder contains local workspace samples for the API-linked frontend.

Use this path in the UI for local HCYT testing:

`E:\AI生成代码\code-audit-platform\demo_test\local-hcyt-workspace`

What is inside:

- `dws.sql`: contains `ALTER`, `TO GROUP GROUP_VERSION1`, and `DWM.` references
- `hive.sql`: contains `VARCHAR2` and `ALTER`
- `DIDP_PROJECT_WORKSPACE/DWUPRR/...py`: contains `FOR I IN`, hard-coded date, `DISTINCT`, nested `NVL`
- `Didp/sbin/CZCB/post_demo.sh`: DOS line endings for shell format checks
- `SCHEMA_CONFIG/*.json`: config file for config checks
- `DW_PROJECT.1.0.config.json`: recv config for recv checks

Expected outcome:

- The local task should be accepted by the backend as `sourceType=local`
- The report should produce multiple warnings/errors in HCYT sections
- Schedule tables may be empty because this sample does not include legacy `.xls` scheduling files
