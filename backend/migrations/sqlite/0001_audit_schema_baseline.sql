CREATE TABLE IF NOT EXISTS {{table:projects}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    project_key TEXT NOT NULL,
    repo_path TEXT NOT NULL,
    workflow TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS {{table:audit_tasks}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    workflow TEXT NOT NULL,
    status TEXT NOT NULL,
    revision TEXT NOT NULL,
    author TEXT NOT NULL,
    operator_user TEXT NOT NULL DEFAULT '',
    client_ip TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    duration TEXT NOT NULL,
    ai_enabled INTEGER NOT NULL DEFAULT 0,
    debug_enabled INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    step TEXT NOT NULL DEFAULT '',
    finished_at TEXT,
    error TEXT,
    logs_json TEXT NOT NULL DEFAULT '[]',
    source_type TEXT NOT NULL DEFAULT 'svn'
);

CREATE TABLE IF NOT EXISTS {{table:task_reports}} (
    task_id INTEGER PRIMARY KEY,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES {{table:audit_tasks}}(id)
);

CREATE TABLE IF NOT EXISTS {{table:audit_results}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    file_name TEXT NOT NULL,
    line_no INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES {{table:audit_tasks}}(id)
);

CREATE TABLE IF NOT EXISTS {{table:fine_report_items}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
