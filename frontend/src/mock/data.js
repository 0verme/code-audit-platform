export { AUDIT_WORKFLOWS as WORKFLOWS, detectWorkflow } from "../config/auditWorkflows";

export const DEFAULT_RECENT = [
  { repo: "svn+ssh://svn.example.com/example/repo/branches/demo/hcyt", wf: "hcyt", rev: "r48217", status: "fail", when: "10 分钟前", who: "zhanglei" },
  { repo: "svn+ssh://svn.example.com/example/repo/branches/demo/hcyt", wf: "hcyt", rev: "r48231", status: "pass", when: "32 分钟前", who: "wangmin" },
  { repo: "https://git.example.com/report/fine-report.git", wf: "fine-report", rev: "8f1c2ad", status: "fail", when: "1 小时前", who: "liyang" },
  { repo: "svn+ssh://svn.example.com/example/repo/trunk/nups", wf: "nups", rev: "r9021", status: "warn", when: "2 小时前", who: "chenhao" },
];

// ===========================================================================
// HCYT 湖仓审查 mock（对齐真实报告结构：svn / sqlChecks / configFiles /
// schedule.tables / pyScripts 结果表标注 / 下载链接）
// ===========================================================================

const HCYT_FAIL = {
  task: {
    status: "fail",
    repo: "svn+ssh://svn.example.com/example/repo/branches/demo/hcyt",
    module: "hcyt",
    workflow: "HCYT 湖仓审查",
    revision: "r48217",
    author: "zhanglei",
    startedAt: "2026-06-07 14:22:08",
    duration: "1分47秒",
    changedFiles: 12,
    checks: 11,
    errors: 7,
    warnings: 14,
    conflicts: 2,
    sqlFiles: 12,
  },
  svn: {
    branchChanged: [
      "hcyt/dws/sql/dws_cust_asset_d.sql",
      "hcyt/dws/sql/dws_loan_balance_sum.sql",
      "hcyt/hive/sql/ods_trans_detail.hql",
      "hcyt/script/load_loan_daily.py",
      "hcyt/sbin/post_dws_cust_asset.sh",
      "hcyt/schema/dws_loan_balance_sum.json",
    ],
    trunkConflict: [
      "hcyt/dws/sql/dws_cust_asset_d.sql",
      "hcyt/schema/dws_loan_balance_sum.json",
    ],
  },
  changes: [
    { type: "M", path: "hcyt/dws/sql/dws_cust_asset_d.sql", add: 64, del: 12, cat: "DWS SQL", downloadUrl: "#" },
    { type: "A", path: "hcyt/dws/sql/dws_loan_balance_sum.sql", add: 132, del: 0, cat: "DWS SQL", downloadUrl: "#" },
    { type: "M", path: "hcyt/hive/sql/ods_trans_detail.hql", add: 21, del: 4, cat: "Hive SQL", downloadUrl: "#" },
    { type: "A", path: "hcyt/script/load_loan_daily.py", add: 156, del: 0, cat: "Python", downloadUrl: "#" },
    { type: "M", path: "hcyt/sbin/post_dws_cust_asset.sh", add: 8, del: 2, cat: "后置脚本", downloadUrl: "#" },
    { type: "A", path: "hcyt/schema/dws_loan_balance_sum.json", add: 41, del: 0, cat: "配置文件", downloadUrl: "#" },
  ],
  conflicts: [
    { path: "hcyt/dws/sql/dws_cust_asset_d.sql", trunkRev: "r48190", mineRev: "r48217", note: "trunk 在同一文件存在重叠修改，需要人工合并。" },
    { path: "hcyt/schema/dws_loan_balance_sum.json", trunkRev: "r48205", mineRev: "r48217", note: "Schema 字段定义与主干版本冲突。" },
  ],
  dws: [
    { file: "dws_cust_asset_d.sql", line: 18, rule: "禁止视图创建", level: "err", msg: "DWS 层不允许 CREATE VIEW，应改为物理表落地。" },
    { file: "dws_cust_asset_d.sql", line: 42, rule: "禁止 ALTER 语句", level: "err", msg: "检测到 ALTER TABLE，结构变更需走独立流程。" },
    { file: "dws_loan_balance_sum.sql", line: 96, rule: "超长代码行", level: "warn", msg: "单行 312 字符，超过 200 字符上限。" },
  ],
  hive: [
    { file: "dwd_acct_event_i.hql", line: 12, rule: "分区字段缺失", level: "err", msg: "增量表未声明 dt 分区字段。" },
    { file: "ods_cust_info.hql", line: 19, rule: "中文别名", level: "warn", msg: "字段别名包含中文字符，建议统一英文命名。" },
  ],
  sqlChecks: {
    dws: { script: "dws_cust_asset_d.sql", downloadUrl: "#" },
    hive: { script: "ods_trans_detail.hql", downloadUrl: "#" },
  },
  python: [
    { file: "load_loan_daily.py", line: 88, rule: "硬编码连接串", level: "err", msg: "数据库连接串明文硬编码，应迁移至配置中心。" },
    { file: "etl_cust_profile.py", line: 61, rule: "硬编码字段长度", level: "warn", msg: "varchar(32) 建议改为配置化参数。" },
  ],
  sbin: [
    { file: "post_dws_cust_asset.sh", line: 5, rule: "缺少 set -e", level: "warn", msg: "脚本异常不会中断执行。" },
  ],
  config: [
    { file: "dws_loan_balance_sum.json", line: 9, rule: "字段类型缺失", level: "err", msg: "字段 loan_amt 缺少 type 定义。" },
  ],
  configFiles: [
    {
      name: "dws_loan_balance_sum.json",
      columns: ["字段", "值"],
      rows: [
        ["schema", "dws_loan"],
        ["source_db", "dev_oracle_192"],
        ["charset", "UTF-8"],
        ["incremental", "true"],
      ],
    },
  ],
  recv: [
    { file: "cust_asset_recv.json", line: 3, rule: "编码格式未声明", level: "warn", msg: "未指定 charset，存在乱码风险。" },
  ],
  assetIssues: [
    {
      issueType: "ROOT_MISSING",
      issueTitle: "词根待维护",
      issueDesc: "字段 DWM.M_CUST_ASSET_D.CUST_RISK_TAG 存在未维护词根：RISK",
      objectName: "DWM.M_CUST_ASSET_D.CUST_RISK_TAG",
      rootWord: "RISK",
      sourceRule: "root-management",
      severity: "warning",
      actionLabel: "去维护词根",
      issueKey: "ROOT_MISSING|HCYT|dws_cust_asset_d.sql|DWM|M_CUST_ASSET_D|CUST_RISK_TAG|RISK",
      hashKey: "mock-root-01",
      portalUrl: "",
    },
    {
      issueType: "ASSET_TABLE_REVIEW",
      issueTitle: "资产表待核对",
      issueDesc: "SQL中识别到资产表待核对：DWM.M_LOAN_ACCT_INFO",
      objectName: "DWM.M_LOAN_ACCT_INFO",
      schemaName: "DWM",
      tableName: "M_LOAN_ACCT_INFO",
      sourceRule: "data-warehouse",
      severity: "warning",
      actionLabel: "去核对资产表",
      issueKey: "ASSET_TABLE_REVIEW|HCYT|load_loan_daily.py|DWM|M_LOAN_ACCT_INFO||",
      hashKey: "mock-table-01",
      portalUrl: "",
    },
  ],
  lineageSummary: {
    resultTables: [
      { tableName: "dwp.demo_result_table" },
      "dwp.demo_result_table_daily",
    ],
    jobs: [
      { jobName: "JOB_DEMO_001" },
      "JOB_DEMO_002",
    ],
    recvPlans: [
      { planName: "PLAN_DEMO_RECV" },
    ],
    sysNames: [
      { sysName: "DEMO_SYS" },
    ],
    outfiles: [
      { outfile: "demo_outfile.dat" },
    ],
    warnings: [
      "DEMO lineage metadata incomplete; using placeholder fallback.",
    ],
    stats: {
      resultTableCount: 2,
      jobCount: 2,
      recvPlanCount: 1,
      outfileCount: 1,
    },
  },
  schedule: {
    summary: { plan: 1, seq: 3, job: 12, cycles: 1, missing: 2 },
    tables: {
      plan: {
        title: "PLAN 计划清单",
        columns: ["计划名", "前置依赖"],
        rows: [["PLAN_DWS_DWM_DAY", ""]],
      },
      seq: {
        title: "SEQ 作业流清单",
        columns: ["计划名", "作业流名", "作业流描述"],
        rows: [
          ["PLAN_DWS_DWM_DAY", "SEQ_DWS_CUST_ASSET", "客户资产日加工"],
          ["PLAN_DWS_DWM_DAY", "SEQ_DWS_LOAN_BAL", "贷款余额汇总"],
        ],
      },
      cale: {
        title: "CALE 日历清单",
        columns: ["日历名", "类型"],
        rows: [["SYS_EVERYDAY_CALENDAR", "每日"]],
      },
      job: {
        title: "JOB 作业清单（绿=新增 / 红=禁用再上线）",
        columns: ["计划名", "作业流名", "作业名", "作业描述"],
        rows: [
          ["PLAN_DWS_DWM_DAY", "SEQ_DWS_CUST_ASSET", "JOB_DWS_CUST_ASSET_00_DAY", "客户资产加工（新增）"],
          ["PLAN_DWS_DWM_DAY", "SEQ_DWS_LOAN_BAL", "JOB_DWS_LOAN_BAL_00_DAY", "贷款余额加工"],
          ["PLAN_DWS_DWM_DAY", "SEQ_DWS_RISK", "JOB_DWS_RISK_TAG_00_DAY", "风险标签（线上禁用再上线）"],
        ],
        rowStates: ["new", "", "disabled"],
      },
    },
    rows: [
      { table: "SEQ", item: "SEQ_DWS_CUST_ASSET", rule: "SEQ-JOB 映射", level: "err", msg: "关联的 JOB_DWS_RISK_TAG 在 JOB 表中不存在。" },
      { table: "JOB", item: "JOB_DWS_LOAN_BAL -> JOB_DWS_RISK", rule: "循环依赖检测", level: "err", msg: "作业依赖成环，请检查: JOB_DWS_LOAN_BAL -> JOB_DWS_RISK -> JOB_DWS_LOAN_BAL" },
      { table: "JOB", item: "JOB_DWD_ACCT_EVENT", rule: "重试次数", level: "warn", msg: "retry=0，建议设置不小于 2。" },
    ],
  },
  pyScripts: [
    {
      script: "005_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_1_00.py",
      downloadUrl: "#",
      table: "DWUPRR.IJEP_FLINK_XGXQY_COUNTRY",
      job: "JOB_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_00_DAY",
      jobDisabled: false,
      freq: "每日",
      focus: "重点检查 SQL 结果表依赖与调度依赖是否一致，并确认 distinct 是否缺失。",
      lint: [
        { line: 47, rule: "去重缺失风险", level: "warn", msg: "LEFT JOIN 后未显式 distinct，可能产出重复数据。" },
        { line: 88, rule: "硬编码字段长度", level: "warn", msg: "varchar(32) 建议改为配置引用。" },
      ],
      result: [
        { sql: "DWF.F_DATA_RESULT_ACTIVITY", dep: "DWF.F_DATA_RESULT_ACTIVITY", state: "same", name: "DWF.F_DATA_RESULT_ACTIVITY", disabled: false, sysNames: ["二代评分卡"], highlight: true },
        { sql: "DWM.M_LOAN_ACCT_INFO", dep: null, state: "missing", name: "DWM.M_LOAN_ACCT_INFO", disabled: false, sysNames: [], highlight: false },
        { sql: null, dep: "DWM.M_DEPRECATED_OLD", state: "extra", name: "DWM.M_DEPRECATED_OLD", disabled: false, sysNames: [], highlight: false },
      ],
      codeval: ["DWUPRR.CODE_CURRENCY", "DWUPRR.CODE_LOAN_TYPE"],
      temp: ["DWUPRR.TMP_IJEP_FLINK_XGXQY_COUNTRY"],
    },
    {
      script: "012_DWS_DWUPRR_LOAN_BAL_SUM_00.py",
      downloadUrl: "#",
      table: "DWUPRR.LOAN_BAL_SUM",
      job: "JOB_DWS_DWUPRR_LOAN_BAL_SUM_00_DAY",
      jobDisabled: true,
      freq: "每日",
      focus: "重点核对结果表依赖是否完整，并确认异常捕获与连接串是否合规。",
      lint: [
        { line: 22, rule: "深层循环", level: "warn", msg: "存在 4 层 for 循环嵌套，可能有性能风险。" },
        { line: 88, rule: "硬编码连接串", level: "err", msg: "数据库连接串明文硬编码。" },
      ],
      result: [
        { sql: "DWF.F_LOAN_BALANCE_SUM", dep: "DWF.F_LOAN_BALANCE_SUM", state: "same", name: "DWF.F_LOAN_BALANCE_SUM", disabled: true, sysNames: [], highlight: true },
        { sql: "DWM.M_CUST_RATING_D", dep: "DWM.M_CUST_RATING_D", state: "same", name: "DWM.M_CUST_RATING_D", disabled: false, sysNames: ["统一授信"], highlight: true },
      ],
      codeval: [],
      temp: ["DWUPRR.TMP_LOAN_BAL_CALC", "DWUPRR.TMP_LOAN_AGG"],
    },
  ],
  refTables: [
    { name: "DWF.F_DATA_RESULT_ACTIVITY", type: "result" },
    { name: "DWF.F_LOAN_BALANCE_SUM", type: "result" },
    { name: "DWM.M_LOAN_ACCT_INFO", type: "mid" },
    { name: "DWUPRR.CODE_CURRENCY", type: "src" },
    { name: "DWUPRR.TMP_LOAN_AGG", type: "mid" },
  ],
  deps: [
    { lane: "上游 / 调度依赖表", nodes: [{ name: "DWM.M_CUST_RATING_D", q: "" }, { name: "DWF.F_LOAN_BALANCE_SUM", q: "" }] },
    { lane: "本次作业", nodes: [{ name: "JOB_DWS_CUST_ASSET_00_DAY", q: "", focus: true }, { name: "JOB_DWS_LOAN_BAL_00_DAY", q: "", focus: true }] },
  ],
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "warn",
    summary: "本次提交在 DWS 层存在视图创建和 ALTER 结构变更，Python 脚本中存在明文连接串，调度表存在循环依赖，建议优先修复后再合并。",
    findings: [
      { sev: "err", title: "高风险：明文连接串", body: "load_loan_daily.py:88 存在数据库口令明文硬编码，应迁移至配置中心或密钥管理服务。" },
      { sev: "err", title: "调度死锁风险", body: "JOB_DWS_LOAN_BAL 与 JOB_DWS_RISK 形成循环依赖，上线后会导致任务卡死。" },
      { sev: "warn", title: "分层规范偏离", body: "DWS 层不应出现视图与 ALTER，建议改为物理表重建。" },
    ],
  },
};

const HCYT_PASS = {
  ...HCYT_FAIL,
  task: {
    ...HCYT_FAIL.task,
    status: "pass",
    revision: "r48231",
    author: "wangmin",
    startedAt: "2026-06-07 16:40:12",
    duration: "58秒",
    changedFiles: 6,
    errors: 0,
    warnings: 1,
    conflicts: 0,
  },
  svn: { branchChanged: ["hcyt/dws/sql/dws_cust_asset_d.sql"], trunkConflict: [] },
  conflicts: [],
  dws: [{ file: "dws_cust_asset_d.sql", line: 7, rule: "缺少 SET 参数", level: "warn", msg: "未设置 mapreduce.job.queuename，将使用默认队列。" }],
  hive: [],
  python: [],
  sbin: [],
  config: [],
  configFiles: [],
  recv: [],
  assetIssues: [],
  lineageSummary: {
    resultTables: ["dwp.demo_result_table"],
    jobs: ["JOB_DEMO_001"],
    recvPlans: [],
    sysNames: ["DEMO_SYS"],
    outfiles: ["demo_outfile.dat"],
    warnings: [],
    stats: {
      resultTableCount: 1,
      jobCount: 1,
      recvPlanCount: 0,
      outfileCount: 1,
    },
  },
  schedule: {
    summary: { plan: 1, seq: 3, job: 9, cycles: 0, missing: 0 },
    tables: {
      plan: { title: "PLAN 计划清单", columns: ["计划名", "前置依赖"], rows: [["PLAN_DWS_DWM_DAY", ""]] },
      job: {
        title: "JOB 作业清单（绿=新增 / 红=禁用再上线）",
        columns: ["计划名", "作业流名", "作业名", "作业描述"],
        rows: [["PLAN_DWS_DWM_DAY", "SEQ_DWS_CUST_ASSET", "JOB_DWS_CUST_ASSET_00_DAY", "客户资产加工"]],
        rowStates: [""],
      },
    },
    rows: [],
  },
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "ok",
    summary: "本次提交整体符合湖仓分层与编码规范，仅存在一处低风险提示，可合并。",
    findings: [
      { sev: "ok", title: "规范符合", body: "DWS/Hive SQL 均符合分层规范，无结构性阻断问题。" },
      { sev: "info", title: "次要建议", body: "建议为 dws_cust_asset_d 显式声明计算队列。" },
    ],
  },
};

// ===========================================================================
// FineReport 报表审查 mock（目录/权限表格、引擎/sheet、预览链接、结果表标注）
// ===========================================================================

const HCYT_EDGE = {
  ...HCYT_PASS,
  task: {
    ...HCYT_PASS.task,
    status: "warn",
    repo: "svn+ssh://svn.example.com/example/repo/branches/demo-hcyt/edge",
    revision: "r-demo-edge",
    author: "demo_user",
    startedAt: "2026-06-07 18:00:00",
    duration: "12秒",
    changedFiles: 1,
    checks: 1,
    errors: 0,
    warnings: 2,
    conflicts: 0,
  },
  svn: { branchChanged: ["hcyt/demo/sql/demo_lineage_edge.sql"], trunkConflict: [] },
  changes: [
    { type: "M", path: "hcyt/demo/sql/demo_lineage_edge.sql", add: 8, del: 1, cat: "DWS SQL", downloadUrl: "#" },
  ],
  conflicts: [],
  dws: [],
  hive: [],
  python: [],
  sbin: [],
  config: [],
  configFiles: [],
  recv: [],
  assetIssues: [],
  lineageSummaryEmptyReplay: {},
  lineageSummary: {
    resultTables: [
      "demo.result_table_alpha",
      { tableName: "demo.result_table_beta" },
      null,
      "demo.result_table_with_extra_long_suffix_for_frontend_wrapping_check_demo_demo_demo_demo_demo_demo_demo_demo_demo_demo_demo",
    ],
    jobs: [
      "JOB_DEMO_EDGE_001",
      { jobName: "JOB_DEMO_EDGE_002" },
      { name: "JOB_DEMO_EDGE_003", token: "***" },
    ],
    recvPlans: [
      "PLAN_DEMO_RECV_EDGE",
      { planName: "PLAN_DEMO_RECV_OBJECT" },
    ],
    sysNames: [
      "DEMO_SOURCE_SYSTEM",
      { sysName: "DEMO_OBJECT_SOURCE" },
      { label: "demo source with ip 192.0.2.10" },
    ],
    outfiles: [
      "demo_outfile_edge.dat",
      { outfile: "demo_outfile_object.dat" },
      { note: "jdbc:demo://*** password=*** token=***" },
    ],
    warnings: [
      "DEMO lineage warning: placeholder metadata was incomplete.",
      { message: "DEMO masked text check password=*** token=*** jdbc:demo://*** 192.0.2.10" },
    ],
  },
  schedule: {
    summary: { plan: 0, seq: 0, job: 0, cycles: 0, missing: 0 },
    tables: {},
    rows: [],
  },
  pyScripts: [],
  refTables: [],
  deps: [],
  ai: {
    model: "mock",
    verdict: "warn",
    summary: "DEMO lineageSummary edge replay.",
    findings: [],
  },
};

const FR_FAIL = {
  task: {
    status: "fail",
    repo: "https://git.example.com/report/fine-report.git",
    module: "fine-report",
    workflow: "FineReport 报表审查",
    revision: "8f1c2ad",
    author: "liyang",
    startedAt: "2026-06-07 15:10:24",
    duration: "1分12秒",
    reports: 3,
    checks: 7,
    errors: 4,
    warnings: 8,
  },
  svn: { branchChanged: ["fine-report/risk/RPT_RISK_MONITOR_D.cpt"], trunkConflict: [] },
  menu: {
    columns: ["后台目录", "前台目录", "预览方式"],
    rows: [
      ["数据仓库/风险管理部/[R001]风险监控日报.cpt", "风险管理部/风险监控日报", "PC"],
      ["数据仓库/会计结算部/[R002]信贷余额汇总.cpt", "会计结算部/信贷余额汇总", "PC"],
    ],
    messages: [
      { level: "err", msg: "数据仓库/会计结算部/[R002]信贷余额汇总.cpt 第二段路径不对 会计结算部/会计部报表 改为 运营管理部" },
    ],
  },
  authority: {
    columns: ["前台目录", "赋予权限"],
    rows: [
      ["风险监控日报", "风险管理岗,数据分析岗"],
      ["信贷余额汇总", "信贷管理岗"],
    ],
    messages: [
      { level: "err", msg: "数据分析岗 生产没有该角色" },
    ],
  },
  reports: [
    {
      title: "[R001]风险监控日报",
      file: "fine-report/risk/RPT_RISK_MONITOR_D.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      engine: "未开分页引擎",
      sheets: ["明细", "汇总"],
      previewUrl: "#",
      downloadUrl: "#",
      focus: "重点检查 SELECT *、权限绑定和笛卡尔积风险。",
      datasets: [
        { name: "数据集 SQL", sql: "SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE t1.cust_no = t2.cust_no", rows: "约 5k" },
      ],
      issues: [
        { cat: "perf", loc: "ds_main", rule: "笛卡尔积风险", level: "err", msg: "两表逗号连接且关联条件不足，存在放大风险。" },
        { cat: "perm", loc: "数据权限", rule: "越权访问", level: "err", msg: "未绑定 org_no 数据权限。" },
        { cat: "dataset", loc: "ds_main", rule: "SELECT *", level: "warn", msg: "应显式列出报表实际使用字段。" },
      ],
      refTables: [
        { name: "DWS.RISK_TAG_D", type: "result", disabled: false, sysNames: ["二代评分卡"], highlight: true },
        { name: "DWM.M_CUST_INFO", type: "mid", disabled: false, sysNames: [], highlight: false },
      ],
    },
    {
      title: "[R002]信贷余额汇总表",
      file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
      type: "cpt",
      change: "M",
      conn: "dev_oracle_192",
      engine: "行式引擎",
      sheets: ["余额汇总"],
      previewUrl: "#",
      downloadUrl: "#",
      focus: "重点核对数据连接是否指向生产库，是否按账期过滤。",
      datasets: [
        { name: "数据集 SQL", sql: "SELECT loan_type, SUM(bal_amt) FROM dev_dw.DWS_LOAN_BAL_SUM GROUP BY loan_type", rows: "约 2k" },
      ],
      issues: [
        { cat: "conn", loc: "数据连接", rule: "连接指向非生产库", level: "err", msg: "当前连接指向开发库，上线后无法取到生产数据。" },
        { cat: "conn", loc: "ds_bal", rule: "库名硬编码", level: "err", msg: "SQL 中写死 dev_dw，跨环境不可迁移。" },
        { cat: "perf", loc: "ds_bal", rule: "缺少分区过滤", level: "warn", msg: "未限制 dt 分区，存在全表扫描。" },
      ],
      refTables: [{ name: "DWS.DWS_LOAN_BAL_SUM", type: "result", disabled: true, sysNames: [], highlight: true }],
    },
    {
      title: "客户资产 360 看板",
      file: "fine-report/cust/DEC_CUST_ASSET_360.frm",
      type: "frm",
      change: "A",
      conn: "FRDS_oracle_dw",
      engine: "新计算引擎",
      sheets: ["大屏"],
      previewUrl: "#",
      downloadUrl: "#",
      focus: "检查大屏是否存在大数据量直查、参数默认值缺失等问题。",
      datasets: [
        { name: "数据集 SQL", sql: "SELECT * FROM DWS.CUST_ASSET_D WHERE 1=1", rows: "约 1.2M" },
      ],
      issues: [
        { cat: "perf", loc: "ds_asset", rule: "大数据量无分页", level: "err", msg: "结果集过大，前端首屏将超时。" },
        { cat: "param", loc: "p_stat_date", rule: "必填参数无默认值", level: "warn", msg: "首屏加载可能直接报缺少参数。" },
      ],
      refTables: [{ name: "DWS.CUST_ASSET_D", type: "result", disabled: false, sysNames: ["押品系统"], highlight: true }],
    },
  ],
  refTables: [
    { name: "DWS.RISK_TAG_D", type: "result", disabled: false, sysNames: ["二代评分卡"], highlight: true },
    { name: "DWM.M_CUST_INFO", type: "mid", disabled: false, sysNames: [], highlight: false },
    { name: "DWS.DWS_LOAN_BAL_SUM", type: "result", disabled: true, sysNames: [], highlight: true },
    { name: "DWS.CUST_ASSET_D", type: "result", disabled: false, sysNames: ["押品系统"], highlight: true },
  ],
  assetIssues: [],
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "warn",
    summary: "本批报表存在连接指向开发库、数据权限未绑定和大屏大数据量直查等问题，建议先完成整改。",
    findings: [
      { sev: "err", title: "高危：连接指向开发库", body: "RPT_LOAN_BAL_SUM.cpt 当前连接 dev_oracle_192 指向开发环境，发布后将直接失败。" },
      { sev: "err", title: "数据权限越权", body: "RPT_RISK_MONITOR_D.cpt 未绑定机构数据权限，所有角色都可见全量风险明细。" },
      { sev: "warn", title: "大屏性能风险", body: "DEC_CUST_ASSET_360 数据集返回百万级记录，建议改为库内预聚合。" },
    ],
  },
};

const FR_PASS = {
  ...FR_FAIL,
  task: {
    ...FR_FAIL.task,
    status: "pass",
    revision: "3c90e7b",
    author: "wangmin",
    startedAt: "2026-06-07 16:48:30",
    duration: "41秒",
    reports: 2,
    errors: 0,
    warnings: 1,
  },
  svn: { branchChanged: ["fine-report/cust/RPT_CUST_ASSET_D.cpt"], trunkConflict: [] },
  menu: { columns: ["后台目录", "前台目录", "预览方式"], rows: [["数据仓库/运营管理部/[R010]客户资产日报.cpt", "运营管理部/客户资产日报", "PC"]], messages: [] },
  authority: { columns: ["前台目录", "赋予权限"], rows: [["客户资产日报", "运营管理岗"]], messages: [] },
  reports: [
    {
      title: "[R010]客户资产日报",
      file: "fine-report/cust/RPT_CUST_ASSET_D.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      engine: "新计算引擎",
      sheets: ["日报"],
      previewUrl: "#",
      downloadUrl: "#",
      focus: "检查数据集字段显式化与账期过滤。",
      datasets: [{ name: "数据集 SQL", sql: "SELECT cust_no, asset_amt, org_no FROM DWS.CUST_ASSET_D WHERE dt = ${p_stat_date}", rows: "约 10k" }],
      issues: [{ cat: "tpl", loc: "单元格 C3", rule: "格式建议", level: "warn", msg: "占比单元格建议使用百分比格式统一展示。" }],
      refTables: [{ name: "DWS.CUST_ASSET_D", type: "result", disabled: false, sysNames: [], highlight: false }],
    },
    {
      title: "[R002]贷款余额汇总表",
      file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      engine: "行式引擎",
      sheets: ["余额汇总"],
      previewUrl: "#",
      downloadUrl: "#",
      focus: "确认生产库连接和分区过滤已经修复。",
      datasets: [{ name: "数据集 SQL", sql: "SELECT loan_type, SUM(bal_amt) bal FROM DWS.LOAN_BAL_SUM WHERE dt = ${p_dt} GROUP BY loan_type", rows: "约 2k" }],
      issues: [],
      refTables: [{ name: "DWS.LOAN_BAL_SUM", type: "result", disabled: false, sysNames: [], highlight: false }],
    },
  ],
  refTables: [
    { name: "DWS.CUST_ASSET_D", type: "result", disabled: false, sysNames: [], highlight: false },
    { name: "DWS.LOAN_BAL_SUM", type: "result", disabled: false, sysNames: [], highlight: false },
  ],
  assetIssues: [],
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "ok",
    summary: "本批报表符合数据集、连接与权限规范，仅保留一处低风险格式建议，可发布。",
    findings: [
      { sev: "ok", title: "规范符合", body: "连接已指向生产库，数据集显式列字段并已限制账期分区。" },
      { sev: "info", title: "次要建议", body: "建议将占比字段统一为百分比格式。" },
    ],
  },
};

// ===========================================================================
// NUPS 统一报送平台审查 mock（新增：SQL 检查 + 加工程序 + SQL 引用表）
// ===========================================================================

const NUPS_FAIL = {
  task: {
    status: "fail",
    repo: "svn+ssh://svn.example.com/example/repo/trunk/nups",
    module: "nups",
    workflow: "NUPS 统一报送平台审查",
    revision: "r9021",
    author: "chenhao",
    startedAt: "2026-06-07 13:05:40",
    duration: "44秒",
    changedFiles: 4,
    checks: 4,
    errors: 5,
    warnings: 0,
    conflicts: 1,
  },
  svn: {
    branchChanged: ["NUPS_DATA/pboc.sql", "NUPS_DATA/east.sql", "NUPS_DATA/001_load_pboc.py", "NUPS_DATA/002_load_east.py"],
    trunkConflict: ["NUPS_DATA/pboc.sql"],
  },
  changes: [
    { type: "M", path: "NUPS_DATA/pboc.sql", cat: "SQL", downloadUrl: "#" },
    { type: "A", path: "NUPS_DATA/east.sql", cat: "SQL", downloadUrl: "#" },
    { type: "A", path: "NUPS_DATA/001_load_pboc.py", cat: "Python", downloadUrl: "#" },
    { type: "M", path: "NUPS_DATA/002_load_east.py", cat: "Python", downloadUrl: "#" },
  ],
  conflicts: [
    { path: "NUPS_DATA/pboc.sql", trunkRev: "trunk@HEAD", mineRev: "r9021", note: "分支与最新 trunk 都改了该文件，合并前请人工核对。" },
  ],
  sqlChecks: [
    {
      script: "pboc.sql",
      downloadUrl: "#",
      messages: [
        { level: "err", msg: "存在 alter 命令，请审核重点检查" },
        { level: "err", msg: "建表脚本不允许带 TO GROUP GROUP_VERSION1" },
      ],
    },
    {
      script: "east.sql",
      downloadUrl: "#",
      messages: [
        { level: "err", msg: "存在对 dwm 模型层的操作，请审核重点检查" },
      ],
    },
  ],
  pyScripts: [
    {
      script: "001_load_pboc.py",
      downloadUrl: "#",
      path: "NUPS_DATA/001_load_pboc.py",
      table: "NUPS_DATA.T_PBOC_RESULT",
      messages: [
        { level: "err", msg: "存在 for 循环 for i in，脚本不允许出现循环，如特殊情况需说明" },
        { level: "err", msg: "模板太旧，请增加影响条数 LOG.info('影响条数:' + str(rownum))" },
      ],
      sqlRefs: ["NUPS_DATA.SRC_PBOC", "NUPS_DATA.CODE_BANK"],
    },
    {
      script: "002_load_east.py",
      downloadUrl: "#",
      path: "NUPS_DATA/002_load_east.py",
      table: "NUPS_DATA.T_EAST_RESULT",
      messages: [
        { level: "err", msg: "检测到写死日期，请确认是否业务需求（如果是注释日期，去掉两头引号）: '20240101'" },
      ],
      sqlRefs: ["NUPS_DATA.SRC_EAST"],
    },
  ],
  assetIssues: [],
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "err",
    summary: "NUPS 加工程序存在循环、写死日期与旧模板问题，SQL 中含 alter 与模型层操作，建议修复后再上线。",
    findings: [
      { sev: "err", title: "脚本含循环", body: "001_load_pboc.py 存在 for 循环，NUPS 加工不允许循环，请改写为集合操作。" },
      { sev: "err", title: "写死日期", body: "002_load_east.py 出现硬编码日期 '20240101'，请确认是否业务需求。" },
    ],
  },
};

const NUPS_PASS = {
  ...NUPS_FAIL,
  task: {
    ...NUPS_FAIL.task,
    status: "pass",
    revision: "r9033",
    author: "wangmin",
    startedAt: "2026-06-07 17:02:10",
    duration: "29秒",
    changedFiles: 2,
    errors: 0,
    warnings: 0,
    conflicts: 0,
  },
  svn: { branchChanged: ["NUPS_DATA/cbrc.sql", "NUPS_DATA/003_load_cbrc.py"], trunkConflict: [] },
  changes: [
    { type: "M", path: "NUPS_DATA/cbrc.sql", cat: "SQL", downloadUrl: "#" },
    { type: "A", path: "NUPS_DATA/003_load_cbrc.py", cat: "Python", downloadUrl: "#" },
  ],
  conflicts: [],
  sqlChecks: [{ script: "cbrc.sql", downloadUrl: "#", messages: [] }],
  pyScripts: [
    {
      script: "003_load_cbrc.py",
      downloadUrl: "#",
      path: "NUPS_DATA/003_load_cbrc.py",
      table: "NUPS_DATA.T_CBRC_RESULT",
      messages: [],
      sqlRefs: ["NUPS_DATA.SRC_CBRC", "NUPS_DATA.CODE_ORG"],
    },
  ],
  assetIssues: [],
  ai: {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "ok",
    summary: "NUPS 本次提交符合规范，SQL 与加工程序均无阻断问题，可上线。",
    findings: [
      { sev: "ok", title: "规范符合", body: "SQL 无 alter/模型层操作，加工程序无循环与写死日期。" },
    ],
  },
};

export const HCYT_DATA = { FAIL: HCYT_FAIL, PASS: HCYT_PASS, EDGE: HCYT_EDGE };
export const FINEREPORT_DATA = { FAIL: FR_FAIL, PASS: FR_PASS };
export const NUPS_DATA = { FAIL: NUPS_FAIL, PASS: NUPS_PASS };
