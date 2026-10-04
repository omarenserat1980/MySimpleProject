CREATE TABLE IF NOT EXISTS cinema_entitlements (
  order_id TEXT PRIMARY KEY,
  film_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL DEFAULT 'PENDING',
  granted_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cinema_entitlements_film ON cinema_entitlements(film_id);
