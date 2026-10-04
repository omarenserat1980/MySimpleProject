CREATE TABLE IF NOT EXISTS deliveries (
  delivery_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL,
  artifact_url TEXT,
  evidence TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  delivered_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_deliveries_order ON deliveries(order_id);
