# Runtime Table Naming Migration

PostgreSQL migration SQL:

- [backend/db/migrate_pg_runtime_tables.sql](/E:/AI生成代码/code-audit-platform/backend/db/migrate_pg_runtime_tables.sql)

Count validation SQL before migration:

```sql
SELECT 'projects' AS table_name, COUNT(*) FROM public.projects
UNION ALL
SELECT 'audit_tasks', COUNT(*) FROM public.audit_tasks
UNION ALL
SELECT 'task_reports', COUNT(*) FROM public.task_reports
UNION ALL
SELECT 'audit_results', COUNT(*) FROM public.audit_results;
```

Count validation SQL after migration:

```sql
SELECT 'p_audit_project_config' AS table_name, COUNT(*) FROM dwp.p_audit_project_config
UNION ALL
SELECT 'p_audit_run', COUNT(*) FROM dwp.p_audit_run
UNION ALL
SELECT 'p_audit_run_report', COUNT(*) FROM dwp.p_audit_run_report
UNION ALL
SELECT 'p_audit_run_issue', COUNT(*) FROM dwp.p_audit_run_issue;
```
