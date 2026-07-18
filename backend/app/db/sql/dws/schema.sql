CREATE SCHEMA IF NOT EXISTS dwp;

CREATE TABLE IF NOT EXISTS dwp.p_audit_project_config (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    project_key TEXT NOT NULL,
    repo_path TEXT NOT NULL,
    workflow TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dwp.p_audit_run (
    id BIGSERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    workflow TEXT NOT NULL,
    status TEXT NOT NULL,
    revision TEXT NOT NULL,
    author TEXT NOT NULL,
    operator_user TEXT NOT NULL DEFAULT '',
    client_ip TEXT NOT NULL DEFAULT '',
    started_at TIMESTAMP NOT NULL,
    duration TEXT NOT NULL,
    ai_enabled INTEGER NOT NULL DEFAULT 0,
    debug_enabled INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    step TEXT NOT NULL DEFAULT '',
    finished_at TIMESTAMP,
    error TEXT,
    logs_json TEXT NOT NULL DEFAULT '[]',
    source_type TEXT NOT NULL DEFAULT 'svn',
    idempotency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dwp.p_audit_run_report (
    task_id BIGINT PRIMARY KEY,
    report_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS dwp.p_audit_run_issue (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    category TEXT NOT NULL,
    file_name TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_p_audit_run_issue_task_id ON dwp.p_audit_run_issue (task_id);

CREATE TABLE IF NOT EXISTS dwp.fine_report_items (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    report_type TEXT NOT NULL,
    change_type TEXT NOT NULL,
    connection_name TEXT NOT NULL,
    focus TEXT NOT NULL,
    dataset_sql TEXT NOT NULL,
    dataset_rows TEXT NOT NULL,
    issues_json TEXT NOT NULL,
    ref_tables_json TEXT NOT NULL
);
