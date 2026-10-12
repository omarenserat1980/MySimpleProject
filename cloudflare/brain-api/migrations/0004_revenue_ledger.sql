CREATE TABLE IF NOT EXISTS revenue_ledger (
  revenue_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL UNIQUE,
  tran_ref TEXT NOT NULL UNIQUE,
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  state TEXT NOT NULL,
  evidence TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_revenue_order ON revenue_ledger(order_id);
