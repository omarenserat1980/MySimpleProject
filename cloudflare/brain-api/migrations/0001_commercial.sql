CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  service TEXT NOT NULL,
  plan TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'NEW',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
  tran_ref TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  provider TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'PAYMENT_PENDING',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  verified_at TEXT,
  raw_evidence TEXT NOT NULL,
  UNIQUE(order_id, provider)
);

CREATE TABLE IF NOT EXISTS payment_events (
  event_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  tran_ref TEXT,
  event_type TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  evidence TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_events_order ON payment_events(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
