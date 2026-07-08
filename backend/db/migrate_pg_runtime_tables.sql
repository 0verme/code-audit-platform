CREATE SCHEMA IF NOT EXISTS dwp;

ALTER TABLE IF EXISTS public.projects SET SCHEMA dwp;
ALTER TABLE IF EXISTS dwp.projects RENAME TO p_audit_project_config;

ALTER TABLE IF EXISTS public.audit_tasks SET SCHEMA dwp;
ALTER TABLE IF EXISTS dwp.audit_tasks RENAME TO p_audit_run;

ALTER TABLE IF EXISTS public.task_reports SET SCHEMA dwp;
ALTER TABLE IF EXISTS dwp.task_reports RENAME TO p_audit_run_report;

ALTER TABLE IF EXISTS public.audit_results SET SCHEMA dwp;
ALTER TABLE IF EXISTS dwp.audit_results RENAME TO p_audit_run_issue;
