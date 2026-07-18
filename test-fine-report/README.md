# FineReport 本地审查全规则样例

在前端选择“FineReport 帆软报表审查”和“本地目录”，使用：

`E:\AI生成代码\code-audit-platform\test-fine-report\local-fine-report-workspace`

样例只用于触发审计规则，不能作为生产报表模板、目录或权限配置使用。

## 样例分布

- `menu.txt`：覆盖后台/前台根路径、扩展名、部门名称、括号及空格规则。
- `authority.txt`：覆盖目录未登记，并在生产元数据不存在演示角色时覆盖角色未登记。
- `数据仓库/报表管理/RPT_DEMO_SALES.cpt`：覆盖编号、日期、子查询、拉链日期和无 Schema 表规则。
- `数据仓库/报表管理/RPT_DEMO_CUSTOMER.frm`：覆盖敏感字段、全分组展示和机构树默认值规则。
- `数据仓库/报表管理/[FR002]空格 报表.frm`：单独覆盖报表路径空格规则。
- `数据仓库/报表管理/[FR001]合规报表.cpt`：覆盖合规模板、分页引擎、数据连接、工作表和引用表的正常展示。

## 预期目录规则

- `fine.menu.root_prefix`
- `fine.menu.backend_extension`
- `fine.menu.backend_department_brackets`
- `fine.menu.backend_department`
- `fine.menu.backend_space`
- `fine.menu.frontend_root_prefix`
- `fine.menu.frontend_department`
- `fine.menu.frontend_finance_department`
- `fine.menu.frontend_department_brackets`
- `fine.menu.frontend_extension`
- `fine.menu.frontend_space`

## 预期报表规则

- `fine.report.missing_number`
- `fine.report.name_space`
- `fine.report.distinct_review`
- `fine.report.group_only`
- `fine.report.org_tree_default`
- `fine.report.sensitive_fields`
- `fine.report.hardcoded_date`
- `fine.report.scalar_subquery`
- `fine.report.in_subquery`
- `fine.report.end_dt_range`
- `fine.report.d_date_to_date`
- `fine.report.d_date_literal`
- `fine.report.missing_schema`

`authority.txt` 中的唯一孤立名称应稳定触发 `fine.authority.missing_menu`；`fine.authority.missing_role` 依赖当前生产角色元数据。

## 验收方式

1. 页面应识别 4 个模板，同时展示目录表和权限表。
2. 两个违规模板应展示上述错误；`[FR001]合规报表.cpt` 应为空问题列表。
3. 合规模板应显示 `demo_reporting` 连接、`行式引擎`、工作表名称及 `DWF.F_FINE_SOURCE` 引用。
4. 页面总错误数应与模板、目录和权限问题数一致。
