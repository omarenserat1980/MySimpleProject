CREATE TABLE IF NOT EXISTS order_events (
  event_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  event_type TEXT NOT NULL,
  evidence TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_order_events_order ON order_events(order_id, created_at);
