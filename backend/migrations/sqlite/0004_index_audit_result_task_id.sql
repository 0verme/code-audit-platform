CREATE INDEX IF NOT EXISTS ix_p_audit_run_issue_task_id
ON {{table:audit_results}} (task_id);
