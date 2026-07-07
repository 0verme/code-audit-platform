/* Sample HCYT review data — exported to window.HCYT_DATA.
   Two states: "fail" (violations present) and "pass" (clean). */
(function () {
  const FAIL = {
    task: {
      status: "fail",
      repo: "svn+ssh://svn.example.com/example/repo/branches/demo",
      module: "hcyt",
      workflow: "HCYT 湖仓审查",
      revision: "r48217",
      author: "zhanglei",
      startedAt: "2026-06-07 14:22:08",
      duration: "1分 47秒",
      changedFiles: 23,
      checks: 11,
      errors: 7,
      warnings: 14,
      conflicts: 2,
    },
    changes: [
      { type: "M", path: "hcyt/dws/sql/dws_cust_asset_d.sql", add: 64, del: 12, cat: "DWS SQL" },
      { type: "A", path: "hcyt/dws/sql/dws_loan_balance_sum.sql", add: 132, del: 0, cat: "DWS SQL" },
      { type: "M", path: "hcyt/hive/sql/ods_trans_detail.hql", add: 21, del: 4, cat: "Hive SQL" },
      { type: "A", path: "hcyt/hive/sql/dwd_acct_event_i.hql", add: 88, del: 0, cat: "Hive SQL" },
      { type: "M", path: "hcyt/script/etl_cust_profile.py", add: 47, del: 9, cat: "Python" },
      { type: "A", path: "hcyt/script/load_loan_daily.py", add: 156, del: 0, cat: "Python" },
      { type: "M", path: "hcyt/sbin/post_dws_cust_asset.sh", add: 8, del: 2, cat: "后置脚本" },
      { type: "A", path: "hcyt/schema/dws_loan_balance_sum.json", add: 41, del: 0, cat: "配置文件" },
      { type: "M", path: "hcyt/recv/recv_json/cust_asset_recv.json", add: 6, del: 1, cat: "收卸配置" },
      { type: "M", path: "hcyt/plan/HCYT_DAILY_PLAN.xlsx", add: 0, del: 0, cat: "调度表" },
      { type: "A", path: "hcyt/dws/sql/dws_risk_tag_d.sql", add: 73, del: 0, cat: "DWS SQL" },
      { type: "M", path: "hcyt/hive/sql/ods_cust_info.hql", add: 14, del: 3, cat: "Hive SQL" },
    ],
    conflicts: [
      { path: "hcyt/dws/sql/dws_cust_asset_d.sql", trunkRev: "r48190", mineRev: "r48217", note: "trunk 已于 r48190 修改同一文件，存在内容重叠" },
      { path: "hcyt/schema/dws_loan_balance_sum.json", trunkRev: "r48205", mineRev: "r48217", note: "主干同名 Schema 已存在，字段定义冲突" },
    ],
    dws: [
      { file: "dws_cust_asset_d.sql", line: 18, rule: "禁止视图创建", level: "err", msg: "DWS 层不允许 CREATE VIEW，应改为物理表落地" },
      { file: "dws_cust_asset_d.sql", line: 42, rule: "禁止 ALTER 语句", level: "err", msg: "检测到 ALTER TABLE，结构变更需走 DDL 变更流程" },
      { file: "dws_loan_balance_sum.sql", line: 7, rule: "缺少 SET 参数", level: "warn", msg: "未设置 mapreduce.job.queuename，将使用默认队列" },
      { file: "dws_loan_balance_sum.sql", line: 96, rule: "超长代码行", level: "warn", msg: "单行 312 字符，超过 200 字符上限" },
      { file: "dws_risk_tag_d.sql", line: 33, rule: "笛卡尔积风险", level: "err", msg: "JOIN 未指定关联条件，存在笛卡尔积风险" },
      { file: "dws_risk_tag_d.sql", line: 51, rule: "SELECT *", level: "warn", msg: "禁止使用 SELECT *，需显式列出字段" },
    ],
    hive: [
      { file: "dwd_acct_event_i.hql", line: 12, rule: "分区字段缺失", level: "err", msg: "增量表未声明 dt 分区字段" },
      { file: "dwd_acct_event_i.hql", line: 55, rule: "动态分区上限", level: "warn", msg: "未设置 hive.exec.max.dynamic.partitions" },
      { file: "ods_trans_detail.hql", line: 8, rule: "超长代码行", level: "warn", msg: "单行 248 字符，超过 200 字符上限" },
      { file: "ods_cust_info.hql", line: 19, rule: "中文别名", level: "warn", msg: "字段别名包含中文字符，建议使用英文" },
    ],
    python: [
      { file: "etl_cust_profile.py", line: 34, rule: "嵌套函数", level: "warn", msg: "检测到 3 层嵌套函数定义，建议拆分" },
      { file: "etl_cust_profile.py", line: 61, rule: "硬编码字段长度", level: "warn", msg: "字段长度硬编码 varchar(32)，应引用配置" },
      { file: "load_loan_daily.py", line: 22, rule: "深层循环", level: "warn", msg: "存在 4 层 for 循环嵌套，可能存在性能问题" },
      { file: "load_loan_daily.py", line: 88, rule: "硬编码连接串", level: "err", msg: "数据库连接串明文硬编码，需迁移至配置中心" },
      { file: "load_loan_daily.py", line: 140, rule: "裸异常捕获", level: "warn", msg: "使用 except: 裸捕获，应指定异常类型" },
    ],
    sbin: [
      { file: "post_dws_cust_asset.sh", line: 5, rule: "缺少 set -e", level: "warn", msg: "脚本未启用 set -e，异常不会中断执行" },
      { file: "post_dws_cust_asset.sh", line: 11, rule: "硬编码路径", level: "warn", msg: "存在绝对路径 /home/etl/data，应使用变量" },
    ],
    config: [
      { file: "dws_loan_balance_sum.json", line: 9, rule: "字段类型缺失", level: "err", msg: "字段 loan_amt 缺少 type 定义" },
      { file: "dws_loan_balance_sum.json", line: 24, rule: "主键未声明", level: "warn", msg: "未声明 primaryKey，下游去重可能异常" },
    ],
    recv: [
      { file: "cust_asset_recv.json", line: 3, rule: "编码格式", level: "warn", msg: "未指定 charset，默认 GBK 可能乱码" },
    ],
    schedule: {
      summary: { plan: 1, seq: 3, job: 12, cycles: 1, missing: 2 },
      rows: [
        { table: "PLAN", item: "HCYT_DAILY_PLAN", rule: "调度周期声明", level: "ok", msg: "周期 D 配置正确" },
        { table: "SEQ", item: "SEQ_DWS_CUST_ASSET", rule: "SEQ-JOB 映射", level: "err", msg: "引用 JOB_DWS_RISK_TAG 在 JOB 表中不存在" },
        { table: "JOB", item: "JOB_DWS_CUST_ASSET", rule: "前置依赖", level: "warn", msg: "前置作业 JOB_ODS_CUST_INFO 未在本次提交" },
        { table: "JOB", item: "JOB_DWS_LOAN_BAL → JOB_DWS_RISK", rule: "循环依赖检测", level: "err", msg: "检测到循环依赖：A→B→A" },
        { table: "JOB", item: "JOB_DWD_ACCT_EVENT", rule: "重试次数", level: "warn", msg: "retry=0，建议设置 ≥2" },
      ],
    },
    pyScripts: [
      {
        script: "005_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_1_00.py",
        table: "DWUPRR.IJEP_FLINK_XGXQY_COUNTRY",
        job: "JOB_DWS_DWS_DWUPRR_IJEP_FLINK_XGXQY_COUNTRY_00_DAY",
        freq: "每日",
        focus: "重点检查脚本中的 distinct 是否必须添加，关联是否会产出重复数据。",
        lint: [
          { line: 47, rule: "去重缺失风险", level: "warn", msg: "LEFT JOIN 后未显式 distinct，存在关联出重复数据风险，需结合审核重点确认" },
          { line: 88, rule: "硬编码字段长度", level: "warn", msg: "字段长度硬编码 varchar(32)，建议引用配置中心" },
        ],
        result: [
          { sql: "DWF.F_DATA_RESULT_ACTIVITY", note: "反欺诈", dep: "DWF.F_DATA_RESULT_ACTIVITY", state: "same" },
          { sql: "DWM.M_PTY_CORP_INFO_ECIF", dep: "DWM.M_PTY_CORP_INFO_ECIF", state: "same" },
          { sql: "DWM.M_PTY_PERS_INFO_ECIF", dep: "DWM.M_PTY_PERS_INFO_ECIF", state: "same" },
        ],
        codeval: [],
        temp: ["DWUPRR.TMP_IJEP_FLINK_XGXQY_COUNTRY"],
      },
      {
        script: "012_DWS_DWUPRR_LOAN_BAL_SUM_00.py",
        table: "DWUPRR.LOAN_BAL_SUM",
        job: "JOB_DWS_DWUPRR_LOAN_BAL_SUM_00_DAY",
        freq: "每日",
        focus: "重点核对结果表依赖：SQL 引用与调度依赖是否完全一致，避免漏配或冗余依赖导致跑批顺序错误。",
        lint: [
          { line: 22, rule: "深层循环", level: "warn", msg: "存在 4 层 for 循环嵌套，可能存在性能问题" },
          { line: 88, rule: "硬编码连接串", level: "err", msg: "数据库连接串明文硬编码，需迁移至配置中心" },
          { line: 140, rule: "裸异常捕获", level: "warn", msg: "使用 except: 裸捕获，应指定异常类型" },
        ],
        result: [
          { sql: "DWF.F_LOAN_BALANCE_SUM", dep: "DWF.F_LOAN_BALANCE_SUM", state: "same" },
          { sql: "DWM.M_LOAN_ACCT_INFO", dep: null, state: "missing" },
          { sql: "DWM.M_CUST_RATING_D", dep: "DWM.M_CUST_RATING_D", state: "same" },
          { sql: null, dep: "DWM.M_DEPRECATED_OLD", state: "extra" },
        ],
        codeval: ["DWUPRR.CODE_CURRENCY", "DWUPRR.CODE_LOAN_TYPE"],
        temp: ["DWUPRR.TMP_LOAN_BAL_CALC", "DWUPRR.TMP_LOAN_AGG"],
      },
    ],
    refTables: [
      { name: "dws_cust_asset_d", type: "result" },
      { name: "dws_loan_balance_sum", type: "result" },
      { name: "dws_risk_tag_d", type: "result" },
      { name: "dwd_acct_event_i", type: "mid" },
      { name: "dwd_trans_clean", type: "mid" },
      { name: "ods_trans_detail", type: "src" },
      { name: "ods_cust_info", type: "src" },
      { name: "ods_loan_acct", type: "src" },
      { name: "tmp_cust_asset_calc", type: "temp" },
      { name: "tmp_loan_agg", type: "temp" },
      { name: "dim_branch", type: "src" },
      { name: "dim_product", type: "src" },
    ],
    deps: [
      { lane: "上游 / 源表", nodes: [
        { name: "ods_cust_info", q: "12" }, { name: "ods_loan_acct", q: "8" }, { name: "ods_trans_detail", q: "20" },
      ] },
      { lane: "本次作业", nodes: [
        { name: "JOB_DWS_CUST_ASSET", q: "6m", focus: true }, { name: "JOB_DWS_LOAN_BAL", q: "9m", focus: true }, { name: "JOB_DWS_RISK_TAG", q: "4m", focus: true },
      ] },
      { lane: "下游 / 影响", nodes: [
        { name: "ads_cust_360", q: "" }, { name: "ads_risk_board", q: "" }, { name: "rpt_loan_daily", q: "" },
      ] },
    ],
    ai: {
      model: "Qwen2.5-Coder-32B (本地)",
      verdict: "warn",
      summary: "本次提交在 DWS 层存在视图创建与 ALTER 结构变更，违反湖仓分层规范；Python 脚本中检测到硬编码连接串属高风险项，建议优先修复。调度表存在一处循环依赖，会导致调度死锁。",
      findings: [
        { sev: "err", title: "高风险：明文连接串", body: "load_loan_daily.py:88 数据库口令明文硬编码，存在凭据泄露风险，建议迁移至配置中心或密钥管理服务。" },
        { sev: "err", title: "调度死锁风险", body: "JOB_DWS_LOAN_BAL 与 JOB_DWS_RISK 形成 A→B→A 循环依赖，上线后调度将无法收敛。" },
        { sev: "warn", title: "分层规范偏离", body: "DWS 层不应出现视图与 ALTER，建议将 dws_cust_asset_d 改为物理表全量重建。" },
        { sev: "info", title: "可读性建议", body: "etl_cust_profile.py 嵌套函数层级偏深，建议提取为模块级函数以便单测。" },
      ],
    },
  };

  // legacy flat python lint list (used by 问题优先 / 看板 aggregate views) — derived from pyScripts
  FAIL.python = FAIL.pyScripts.flatMap(s => s.lint.map(l => ({ file: s.script, ...l })));

  const PASS = JSON.parse(JSON.stringify(FAIL));
  PASS.task = {
    ...FAIL.task,
    status: "pass",
    revision: "r48231",
    author: "wangmin",
    startedAt: "2026-06-07 16:40:12",
    duration: "58秒",
    changedFiles: 9,
    errors: 0,
    warnings: 1,
    conflicts: 0,
  };
  PASS.changes = FAIL.changes.slice(0, 9);
  PASS.conflicts = [];
  PASS.dws = [
    { file: "dws_cust_asset_d.sql", line: 7, rule: "缺少 SET 参数", level: "warn", msg: "未设置 mapreduce.job.queuename，将使用默认队列" },
  ];
  PASS.hive = [];
  PASS.python = [];
  PASS.sbin = [];
  PASS.config = [];
  PASS.recv = [];
  PASS.pyScripts = [PASS.pyScripts[0]];
  PASS.python = PASS.pyScripts.flatMap(s => s.lint.map(l => ({ file: s.script, ...l })));
  PASS.schedule = {
    summary: { plan: 1, seq: 3, job: 9, cycles: 0, missing: 0 },
    rows: [
      { table: "PLAN", item: "HCYT_DAILY_PLAN", rule: "调度周期声明", level: "ok", msg: "周期 D 配置正确" },
      { table: "SEQ", item: "SEQ_DWS_CUST_ASSET", rule: "SEQ-JOB 映射", level: "ok", msg: "映射完整" },
      { table: "JOB", item: "全部作业", rule: "循环依赖检测", level: "ok", msg: "未检测到循环依赖" },
    ],
  };
  PASS.ai = {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "ok",
    summary: "本次提交整体符合湖仓分层与编码规范，仅存在一处队列参数缺省的低风险提示，可合并。",
    findings: [
      { sev: "ok", title: "规范符合", body: "DWS/Hive SQL 均符合分层规范，无视图创建或结构变更。" },
      { sev: "info", title: "次要建议", body: "建议为 dws_cust_asset_d 显式声明计算队列，避免占用默认队列资源。" },
    ],
  };

  window.HCYT_DATA = { FAIL, PASS };
})();

/* ---- FineReport 报表审查 sample data — 按报表列表检查 ---- */
(function () {
  const FAIL = {
    task: {
      status: "fail",
      repo: "https://git.example.com/report/fine-report.git",
      module: "fine-report",
      workflow: "FineReport 报表审查",
      revision: "8f1c2ad",
      author: "liyang",
      startedAt: "2026-06-07 15:10:24",
      duration: "1分 12秒",
      reports: 6,
      checks: 7,
      errors: 6,
      warnings: 12,
    },
    reports: [
      {
        title: "风险监控日报",
        file: "fine-report/risk/RPT_RISK_MONITOR_D.cpt",
        type: "cpt",
        change: "M",
        conn: "FRDS_oracle_dw",
        focus: "重点检查主数据集是否存在 SELECT * 与隐式笛卡尔积；数据权限是否按机构维度（org_no）绑定，避免角色跨机构越权查看明细。",
        datasets: [
          { name: "ds_main", sql: "SELECT * FROM DWS.RISK_TAG_D t1, DWM.M_CUST_INFO t2 WHERE t1.cust_no = t2.cust_no", rows: "≈85k" },
          { name: "ds_org", sql: "SELECT org_no, org_name FROM DIM.ORG_INFO", rows: "320" },
        ],
        issues: [
          { cat: "perf", loc: "ds_main", rule: "笛卡尔积风险", level: "err", msg: "两表以逗号连接、仅 1 个关联条件，t2 对 t1 一对多，结果行数存在放大风险" },
          { cat: "perm", loc: "数据权限", rule: "越权访问", level: "err", msg: "报表未绑定机构数据权限（org_no），所有角色可见全机构明细，存在越权" },
          { cat: "dataset", loc: "ds_main", rule: "SELECT *", level: "warn", msg: "数据集使用 SELECT *，应显式列出报表实际引用字段以减少回表与传输" },
          { cat: "tpl", loc: "单元格 B2", rule: "格式硬编码", level: "warn", msg: "金额单元格未套用千分位格式，建议引用统一数字格式" },
        ],
        refTables: [
          { name: "DWS.RISK_TAG_D", type: "result" },
          { name: "DWM.M_CUST_INFO", type: "mid" },
          { name: "DIM.ORG_INFO", type: "src" },
        ],
      },
      {
        title: "信贷余额汇总表",
        file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
        type: "cpt",
        change: "M",
        conn: "dev_oracle_192",
        focus: "重点核对数据连接是否指向生产库；汇总数据集是否限定账期分区，避免全表扫描历史数据。",
        datasets: [
          { name: "ds_bal", sql: "SELECT loan_type, SUM(bal_amt) FROM dev_dw.DWS_LOAN_BAL_SUM GROUP BY loan_type", rows: "≈12k" },
        ],
        issues: [
          { cat: "conn", loc: "数据连接", rule: "连接指向非生产库", level: "err", msg: "数据连接 dev_oracle_192 指向开发库，上线后将取不到生产数据" },
          { cat: "conn", loc: "ds_bal", rule: "库名硬编码", level: "err", msg: "SQL 中硬编码库名 dev_dw，跨环境不可迁移，应使用连接默认 schema" },
          { cat: "perf", loc: "ds_bal", rule: "缺少分区过滤", level: "warn", msg: "未限定 dt 账期分区，将全表扫描历史数据" },
        ],
        refTables: [
          { name: "DWS.DWS_LOAN_BAL_SUM", type: "result" },
        ],
      },
      {
        title: "客户资产 360 看板",
        file: "fine-report/cust/DEC_CUST_ASSET_360.frm",
        type: "frm",
        change: "A",
        conn: "FRDS_oracle_dw",
        focus: "决策大屏：重点检查大数据量数据集是否分页或库内预聚合；必填参数是否设默认值，避免首屏空查报错。",
        datasets: [
          { name: "ds_asset", sql: "SELECT * FROM DWS.CUST_ASSET_D WHERE 1=1", rows: "≈1.2M" },
          { name: "ds_trend", sql: "SELECT dt, asset_amt FROM DWM.M_ASSET_TREND", rows: "≈36k" },
        ],
        issues: [
          { cat: "perf", loc: "ds_asset", rule: "大数据量无分页", level: "err", msg: "结果约 120 万行直接载入前端，无分页/无聚合，首屏渲染将超时" },
          { cat: "dataset", loc: "ds_asset", rule: "SELECT *", level: "warn", msg: "看板仅使用 6 个字段，却 SELECT * 拉取全表字段" },
          { cat: "param", loc: "p_stat_date", rule: "必填参数无默认值", level: "warn", msg: "必填参数 p_stat_date 未设默认值，首屏加载将报参数缺失" },
        ],
        refTables: [
          { name: "DWS.CUST_ASSET_D", type: "result" },
          { name: "DWM.M_ASSET_TREND", type: "mid" },
        ],
      },
      {
        title: "反欺诈活动结果明细",
        file: "fine-report/risk/RPT_ANTIFRAUD_DETAIL.cpt",
        type: "cpt",
        change: "A",
        conn: "FRDS_oracle_dw",
        focus: "重点检查跨库 JOIN 是否必要；明细数据集是否带 where 限制活动时间范围，避免全量返回。",
        datasets: [
          { name: "ds_act", sql: "SELECT * FROM DWF.F_DATA_RESULT_ACTIVITY a LEFT JOIN DWM2.M_PTY_CORP b ON a.pty_id = b.pty_id", rows: "≈48k" },
        ],
        issues: [
          { cat: "dataset", loc: "ds_act", rule: "跨库引用", level: "warn", msg: "JOIN 跨 DWF 与 DWM2 两个库，存在跨库查询性能与权限风险" },
          { cat: "perf", loc: "ds_act", rule: "无 where 条件", level: "warn", msg: "明细数据集无 where，未限制活动时间范围，全量返回" },
          { cat: "tpl", loc: "Sheet2", rule: "空 sheet", level: "warn", msg: "模板包含空白 Sheet2，导出时会多出空白页，建议删除" },
        ],
        refTables: [
          { name: "DWF.F_DATA_RESULT_ACTIVITY", type: "result" },
          { name: "DWM2.M_PTY_CORP", type: "mid" },
        ],
      },
      {
        title: "监管报送-贷款月报",
        file: "fine-report/regp/loan_monthly_report.cpt",
        type: "cpt",
        change: "M",
        conn: "FRDS_oracle_dw",
        focus: "监管报送报表：重点检查文件命名规范与冗余参数清理；金额口径需与监管模板一致。",
        datasets: [
          { name: "ds_m", sql: "SELECT branch_no, SUM(bal_amt) bal FROM DWS.LOAN_MONTH GROUP BY branch_no", rows: "≈5k" },
        ],
        issues: [
          { cat: "tpl", loc: "文件命名", rule: "命名不规范", level: "warn", msg: "文件名未采用 RPT_/DEC_ 大写前缀规范，建议改为 RPT_LOAN_MONTHLY" },
          { cat: "param", loc: "p_old_flag", rule: "未使用参数", level: "warn", msg: "定义了参数 p_old_flag 但模板与数据集均未引用，建议删除" },
        ],
        refTables: [
          { name: "DWS.LOAN_MONTH", type: "result" },
        ],
      },
      {
        title: "经营分析决策大屏",
        file: "fine-report/ops/DEC_OPS_ANALYSIS.frm",
        type: "frm",
        change: "A",
        conn: "FRDS_oracle_dw",
        focus: "经营大屏：重点检查 KPI 数据集行数与刷新频率，建议库内预聚合；机构排名是否受菜单/数据权限约束。",
        datasets: [
          { name: "ds_kpi", sql: "SELECT * FROM DWS.OPS_KPI_D", rows: "≈260k" },
          { name: "ds_rank", sql: "SELECT org_no, amt FROM DWM.M_ORG_RANK ORDER BY amt DESC", rows: "1.2k" },
        ],
        issues: [
          { cat: "perf", loc: "ds_kpi", rule: "查询行数过大", level: "err", msg: "ds_kpi 返回约 26 万行用于卡片汇总，应在库内预聚合为日粒度后再供数" },
          { cat: "dataset", loc: "ds_kpi", rule: "SELECT *", level: "warn", msg: "建议显式列出大屏实际引用的 KPI 字段" },
          { cat: "perm", loc: "菜单权限", rule: "菜单未授权", level: "warn", msg: "大屏挂载在公共目录，未配置菜单角色，存在未授权访问" },
        ],
        refTables: [
          { name: "DWS.OPS_KPI_D", type: "result" },
          { name: "DWM.M_ORG_RANK", type: "mid" },
        ],
      },
    ],
    ai: {
      model: "Qwen2.5-Coder-32B (本地)",
      verdict: "warn",
      summary: "本批 6 张报表中 4 张存在阻断性问题：信贷余额汇总表数据连接指向开发库且库名硬编码，属高危；风险监控日报存在笛卡尔积与数据权限越权；两张决策大屏均为大数据量无分页/无预聚合，前端渲染将超时。建议优先修复连接与权限问题。",
      findings: [
        { sev: "err", title: "高危：连接指向开发库", body: "RPT_LOAN_BAL_SUM.cpt 数据连接 dev_oracle_192 指向开发环境且 SQL 硬编码库名 dev_dw，上线后取数失败。" },
        { sev: "err", title: "数据权限越权", body: "RPT_RISK_MONITOR_D.cpt 未绑定机构数据权限，所有角色可见全机构客户风险明细。" },
        { sev: "warn", title: "大屏性能", body: "DEC_CUST_ASSET_360 与 DEC_OPS_ANALYSIS 数据集均为数十万至百万行直查，建议库内预聚合或分页。" },
        { sev: "info", title: "命名与冗余", body: "loan_monthly_report.cpt 命名未遵循前缀规范，并存在未引用参数 p_old_flag，建议清理。" },
      ],
    },
  };

  // aggregate dedup reference tables across all reports
  function aggRefs(reports) {
    const seen = new Map();
    for (const r of reports) for (const t of (r.refTables || [])) if (!seen.has(t.name)) seen.set(t.name, t);
    return [...seen.values()];
  }
  FAIL.refTables = aggRefs(FAIL.reports);

  const PASS = JSON.parse(JSON.stringify(FAIL));
  PASS.task = {
    ...FAIL.task,
    status: "pass",
    revision: "3c90e7b",
    author: "wangmin",
    startedAt: "2026-06-07 16:48:30",
    duration: "41秒",
    reports: 2,
    errors: 0,
    warnings: 1,
  };
  PASS.reports = [
    {
      title: "客户资产日报",
      file: "fine-report/cust/RPT_CUST_ASSET_D.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      focus: "重点检查数据集字段显式化与账期分区过滤；数据权限已按机构绑定，复核口径即可。",
      datasets: [
        { name: "ds_main", sql: "SELECT cust_no, asset_amt, org_no FROM DWS.CUST_ASSET_D WHERE dt = ${p_stat_date}", rows: "≈40k" },
      ],
      issues: [
        { cat: "tpl", loc: "单元格 C3", rule: "格式建议", level: "warn", msg: "占比单元格建议套用百分比格式，当前为通用格式" },
      ],
      refTables: [
        { name: "DWS.CUST_ASSET_D", type: "result" },
        { name: "DIM.ORG_INFO", type: "src" },
      ],
    },
    {
      title: "贷款余额汇总表",
      file: "fine-report/credit/RPT_LOAN_BAL_SUM.cpt",
      type: "cpt",
      change: "M",
      conn: "FRDS_oracle_dw",
      focus: "数据连接已指向生产库、数据集显式列字段并限定分区，复核汇总口径即可。",
      datasets: [
        { name: "ds_bal", sql: "SELECT loan_type, SUM(bal_amt) bal FROM DWS.LOAN_BAL_SUM WHERE dt = ${p_dt} GROUP BY loan_type", rows: "≈12k" },
      ],
      issues: [],
      refTables: [
        { name: "DWS.LOAN_BAL_SUM", type: "result" },
      ],
    },
  ];
  PASS.refTables = aggRefs(PASS.reports);
  PASS.ai = {
    model: "Qwen2.5-Coder-32B (本地)",
    verdict: "ok",
    summary: "本批 2 张报表均符合数据集、连接与权限规范，仅存在一处单元格格式建议，可发布。",
    findings: [
      { sev: "ok", title: "规范符合", body: "数据连接指向生产库，数据集显式列字段并限定账期分区，数据权限按机构绑定。" },
      { sev: "info", title: "次要建议", body: "RPT_CUST_ASSET_D 占比单元格建议套用百分比格式以统一展示。" },
    ],
  };

  window.FINEREPORT_DATA = { FAIL, PASS };
})();
