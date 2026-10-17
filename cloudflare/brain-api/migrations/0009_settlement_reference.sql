ALTER TABLE revenue_ledger ADD COLUMN settlement_reference TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_settlement_reference_unique ON revenue_ledger(settlement_reference) WHERE settlement_reference IS NOT NULL;
