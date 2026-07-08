CREATE SCHEMA IF NOT EXISTS dwp;

ALTER TABLE IF EXISTS public.projects SET SCHEMA dwp;
DO $$
BEGIN
    IF to_regclass('dwp.p_audit_project_config') IS NULL AND to_regclass('dwp.projects') IS NOT NULL THEN
        ALTER TABLE dwp.projects RENAME TO p_audit_project_config;
    END IF;
END $$;

ALTER TABLE IF EXISTS public.audit_tasks SET SCHEMA dwp;
DO $$
BEGIN
    IF to_regclass('dwp.p_audit_run') IS NULL AND to_regclass('dwp.audit_tasks') IS NOT NULL THEN
        ALTER TABLE dwp.audit_tasks RENAME TO p_audit_run;
    END IF;
END $$;

ALTER TABLE IF EXISTS public.task_reports SET SCHEMA dwp;
DO $$
BEGIN
    IF to_regclass('dwp.p_audit_run_report') IS NULL AND to_regclass('dwp.task_reports') IS NOT NULL THEN
        ALTER TABLE dwp.task_reports RENAME TO p_audit_run_report;
    END IF;
END $$;

ALTER TABLE IF EXISTS public.audit_results SET SCHEMA dwp;
DO $$
BEGIN
    IF to_regclass('dwp.p_audit_run_issue') IS NULL AND to_regclass('dwp.audit_results') IS NOT NULL THEN
        ALTER TABLE dwp.audit_results RENAME TO p_audit_run_issue;
    END IF;
END $$;
