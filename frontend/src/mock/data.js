export const WORKFLOWS = [
  {
    key: "hcyt",
    kw: "/hcyt/",
    name: "HCYT 湖仓审查",
    desc: "DWS / Hive SQL / Python / 调度表 / 收卸配置",
    icon: "db",
    color: "var(--accent)",
  },
  {
    key: "fine-report",
    kw: "/fine-report/",
    name: "FineReport 报表审查",
    desc: "报表模板 / 数据集 / 参数与权限校验",
    icon: "grid",
    color: "var(--ok)",
  },
  {
    key: "nups",
    kw: "/nups/",
    name: "NUPS 统一支付审查",
    desc: "接口契约 / 配置文件 / 联调依赖检查",
    icon: "layers",
    color: "var(--warn)",
  },
];

export const DEFAULT_RECENT = [
  { repo: "svn://10.18.32.7/datawh/branches/2026Q2/hcyt", wf: "hcyt", rev: "r48217", status: "fail", when: "10 分钟前", who: "zhanglei" },
  { repo: "svn://10.18.32.7/datawh/branches/2026Q2/hcyt", wf: "hcyt", rev: "r48231", status: "pass", when: "32 分钟前", who: "wangmin" },
  { repo: "https://git.intra/report/fine-report.git", wf: "fine-report", rev: "8f1c2ad", status: "fail", when: "1 小时前", who: "liyang" },
  { repo: "svn://10.18.32.7/pay/nups/trunk", wf: "nups", rev: "r9021", status: "warn", when: "2 小时前", who: "chenhao" },
];

export function detectWorkflow(path) {
  const value = (path || "").toLowerCase();
  for (const workflow of WORKFLOWS) {
    if (value.includes(workflow.kw)) {
      return workflow.key;
    }
  }
  if (value.includes("hcyt")) return "hcyt";
  if (value.includes("report")) return "fine-report";
  if (value.includes("nups") || value.includes("pay")) return "nups";
  return null;
}

const HCYT_FAIL = {
  task: {
    status: "fail",
    repo: "svn://10.18.32.7/datawh/branches/2026Q2/hcyt",
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
  },
  changes: [
    { type: "M", path: "hcyt/dws/sql/dws_cust_asset_d.sql", add: 64, del: 12, cat: "DWS SQL" },
    { type: "A", path: "hcyt/dws/sql/dws_loan_balance_sum.sql", add: 132, del: 0, cat: "DWS SQL" },
    { type: "M", path: "hcyt/hive/sql/ods_trans_detail.hql", add: 21, del: 4, cat: "Hive SQL" },
    { type: "A", path: "hcyt/script/load_loan_daily.py", add: 156, del: 0, cat: "Python" },
    { type: "M", path: "hcyt/sbin/post_dws_cust_asset.sh", add: 8, del: 2, cat: "后置脚本" },
    { type: "A", path: "hcyt/schema/dws_loan_balance_sum.json", add: 41, del: 0, cat: "配置文件" },
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
  recv: [
    { file: "cust_asset_recv.json", line: 3, rule: "编码格式未声明", level: "warn", msg: "未指定 charset，存在乱码风险。" },
  ],
  schedule: {
    summary: { plan: 1, seq: 3, job: 12, cycles: 1, missing: 2 },
    rows: [
      { table: "PLAN", item: "HCYT_DAILY_PLAN", rule: "调度周期声明", level: "ok", msg: "周期 D 配置正确。" },
      { table: "SEQ", item: "SEQ_DWS_CUST_ASSET", rule: "SEQ-JOB 映射", level: "err", msg: "关联的 JOB_DWS_RISK_TAG 在 JOB 表中不存在。" },
      { table: "JOB", item: "JOB_DWS_LOAN_BAL -> JOB_DWS_RISK", rule: "循环依赖检测", level: "err", msg: "检测到 A -> B -> A 循环依赖。" },
      { table: "JOB", item: "JOB_DWD_ACCT_EVENT", rule: "重试次数", level: "warn", msg: "retry=0，建议设置不小于 2。" },
    ],
  },
  pyScripts: [
    {
      script: "005_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_1_00.py",
      table: "DWUPRR.IJEP_FLINK_XGXQY_COUNTRY",
      job: "JOB_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_00_DAY",
      freq: "每日",
      focus: "重点检查 SQL 结果表依赖与调度依赖是否一致，并确认 distinct 是否缺失。",
      lint: [
        { line: 47, rule: "去重缺失风险", level: "warn", msg: "LEFT JOIN 后未显式 distinct，可能产出重复数据。" },
        { line: 88, rule: "硬编码字段长度", level: "warn", msg: "varchar(32) 建议改为配置引用。" },
      ],
      result: [
        { sql: "DWF.F_DATA_RESULT_ACTIVITY", dep: "DWF.F_DATA_RESULT_ACTIVITY", state: "same" },
        { sql: "DWM.M_LOAN_ACCT_INFO", dep: null, state: "missing" },
        { sql: null, dep: "DWM.M_DEPRECATED_OLD", state: "extra" },
      ],
      codeval: ["DWUPRR.CODE_CURRENCY", "DWUPRR.CODE_LOAN_TYPE"],
      temp: ["DWUPRR.TMP_IJEP_FLINK_XGXQY_COUNTRY"],
    },
    {
      script: "012_DWS_DWUPRR_LOAN_BAL_SUM_00.py",
      table: "DWUPRR.LOAN_BAL_SUM",
      job: "JOB_DWS_DWUPRR_LOAN_BAL_SUM_00_DAY",
      freq: "每日",
      focus: "重点核对结果表依赖是否完整，并确认异常捕获与连接串是否合规。",
      lint: [
        { line: 22, rule: "深层循环", level: "warn", msg: "存在 4 层 for 循环嵌套，可能有性能风险。" },
        { line: 88, rule: "硬编码连接串", level: "err", msg: "数据库连接串明文硬编码。" },
      ],
      result: [
        { sql: "DWF.F_LOAN_BALANCE_SUM", dep: "DWF.F_LOAN_BALANCE_SUM", state: "same" },
        { sql: "DWM.M_CUST_RATING_D", dep: "DWM.M_CUST_RATING_D", state: "same" },
      ],
      codeval: [],
      temp: ["DWUPRR.TMP_LOAN_BAL_CALC", "DWUPRR.TMP_LOAN_AGG"],
    },
  ],
  refTables: [
    { name: "dws_cust_asset_d", type: "result" },
    { name: "dws_loan_balance_sum", type: "result" },
    { name: "dwd_acct_event_i", type: "mid" },
    { name: "ods_cust_info", type: "src" },
    { name: "tmp_loan_agg", type: "temp" },
  ],
  deps: [
    { lane: "上游 / 源表", nodes: [{ name: "ods_cust_info", q: "12" }, { name: "ods_loan_acct", q: "8" }] },
    { lane: "本次作业", nodes: [{ name: "JOB_DWS_CUST_ASSET", q: "6m", focus: true }, { name: "JOB_DWS_LOAN_BAL", q: "9m", focus: true }] },
    { lane: "下游 / 影响", nodes: [{ name: "ads_cust_360", q: "" }, { name: "rpt_loan_daily", q: "" }] },
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
  conflicts: [],
  dws: [{ file: "dws_cust_asset_d.sql", line: 7, rule: "缺少 SET 参数", level: "warn", msg: "未设置 mapreduce.job.queuename，将使用默认队列。" }],
  hive: [],
  python: [],
  sbin: [],
  config: [],
  recv: [],
  schedule: {
    summary: { plan: 1, seq: 3, job: 9, cycles: 0, missing: 0 },
    rows: [
      { table: "PLAN", item: "HCYT_DAILY_PLAN", rule: "调度周期声明", level: "ok", msg: "周期 D 配置正确。" },
      { table: "SEQ", item: "SEQ_DWS_CUST_ASSET", rule: "SEQ-JOB 映射", level: "ok", msg: "映射完整。" },
      { table: "JOB", item: "全部作业", rule: "循环依赖检测", level: "ok", msg: "未检测到循环依赖。" },
    ],
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

const FR_FAIL = {
  task: {
    status: "fail",
    repo: "https://git.intra/report/fine-report.git",
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
  reports: [
    {
      title: "风险监控日报",
      file: "fine-report/risk/RPT_RISK_MONITOR_D.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      focus: "重点检查 SELECT *、权限绑定和笛卡尔积风险。",
      datasets: [
        { name: "ds_main", sql: "SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE t1.cust_no = t2.cust_no", rows: "约 5k" },
      ],
      issues: [
        { cat: "perf", loc: "ds_main", rule: "笛卡尔积风险", level: "err", msg: "两表逗号连接且关联条件不足，存在放大风险。" },
        { cat: "perm", loc: "数据权限", rule: "越权访问", level: "err", msg: "未绑定 org_no 数据权限。" },
        { cat: "dataset", loc: "ds_main", rule: "SELECT *", level: "warn", msg: "应显式列出报表实际使用字段。" },
      ],
      refTables: [
        { name: "DWS.RISK_TAG_D", type: "result" },
        { name: "DWM.M_CUST_INFO", type: "mid" },
      ],
    },
    {
      title: "信贷余额汇总表",
      file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
      type: "cpt",
      change: "M",
      conn: "dev_oracle_192",
      focus: "重点核对数据连接是否指向生产库，是否按账期过滤。",
      datasets: [
        { name: "ds_bal", sql: "SELECT loan_type, SUM(bal_amt) FROM dev_dw.DWS_LOAN_BAL_SUM GROUP BY loan_type", rows: "约 2k" },
      ],
      issues: [
        { cat: "conn", loc: "数据连接", rule: "连接指向非生产库", level: "err", msg: "当前连接指向开发库，上线后无法取到生产数据。" },
        { cat: "conn", loc: "ds_bal", rule: "库名硬编码", level: "err", msg: "SQL 中写死 dev_dw，跨环境不可迁移。" },
        { cat: "perf", loc: "ds_bal", rule: "缺少分区过滤", level: "warn", msg: "未限制 dt 分区，存在全表扫描。" },
      ],
      refTables: [{ name: "DWS.DWS_LOAN_BAL_SUM", type: "result" }],
    },
    {
      title: "客户资产 360 看板",
      file: "fine-report/cust/DEC_CUST_ASSET_360.frm",
      type: "frm",
      change: "A",
      conn: "FRDS_oracle_dw",
      focus: "检查大屏是否存在大数据量直查、参数默认值缺失等问题。",
      datasets: [
        { name: "ds_asset", sql: "SELECT * FROM DWS.CUST_ASSET_D WHERE 1=1", rows: "约 1.2M" },
      ],
      issues: [
        { cat: "perf", loc: "ds_asset", rule: "大数据量无分页", level: "err", msg: "结果集过大，前端首屏将超时。" },
        { cat: "param", loc: "p_stat_date", rule: "必填参数无默认值", level: "warn", msg: "首屏加载可能直接报缺少参数。" },
      ],
      refTables: [{ name: "DWS.CUST_ASSET_D", type: "result" }],
    },
  ],
  refTables: [
    { name: "DWS.RISK_TAG_D", type: "result" },
    { name: "DWM.M_CUST_INFO", type: "mid" },
    { name: "DWS.DWS_LOAN_BAL_SUM", type: "result" },
    { name: "DWS.CUST_ASSET_D", type: "result" },
  ],
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
  reports: [
    {
      title: "客户资产日报",
      file: "fine-report/cust/RPT_CUST_ASSET_D.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      focus: "检查数据集字段显式化与账期过滤。",
      datasets: [{ name: "ds_main", sql: "SELECT cust_no, asset_amt, org_no FROM DWS.CUST_ASSET_D WHERE dt = ${p_stat_date}", rows: "约 10k" }],
      issues: [{ cat: "tpl", loc: "单元格 C3", rule: "格式建议", level: "warn", msg: "占比单元格建议使用百分比格式统一展示。" }],
      refTables: [{ name: "DWS.CUST_ASSET_D", type: "result" }],
    },
    {
      title: "贷款余额汇总表",
      file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      focus: "确认生产库连接和分区过滤已经修复。",
      datasets: [{ name: "ds_bal", sql: "SELECT loan_type, SUM(bal_amt) bal FROM DWS.LOAN_BAL_SUM WHERE dt = ${p_dt} GROUP BY loan_type", rows: "约 2k" }],
      issues: [],
      refTables: [{ name: "DWS.LOAN_BAL_SUM", type: "result" }],
    },
  ],
  refTables: [
    { name: "DWS.CUST_ASSET_D", type: "result" },
    { name: "DWS.LOAN_BAL_SUM", type: "result" },
  ],
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

export const HCYT_DATA = { FAIL: HCYT_FAIL, PASS: HCYT_PASS };
export const FINEREPORT_DATA = { FAIL: FR_FAIL, PASS: FR_PASS };
