ALTER TABLE revenue_ledger ADD COLUMN environment TEXT NOT NULL DEFAULT 'test';
CREATE INDEX IF NOT EXISTS idx_revenue_environment_state ON revenue_ledger(environment, state);
