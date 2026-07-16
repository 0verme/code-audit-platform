ALTER TABLE {{table:audit_tasks}} ADD COLUMN idempotency_key TEXT;
CREATE UNIQUE INDEX ux_p_audit_run_idempotency_key ON {{table:audit_tasks}} (idempotency_key);
