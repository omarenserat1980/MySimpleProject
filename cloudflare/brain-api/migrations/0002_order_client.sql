ALTER TABLE orders ADD COLUMN client_email TEXT;
CREATE INDEX IF NOT EXISTS idx_orders_client_email ON orders(client_email);
