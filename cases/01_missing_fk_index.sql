-- One customer's orders. orders.customer_id has a foreign key but no index:
-- Postgres does not index foreign keys automatically, so this scans 2M rows.
-- slow
SELECT order_id, status, created_at, total
FROM orders
WHERE customer_id = 4242
-- fix
CREATE INDEX IF NOT EXISTS orders_customer_id_idx ON orders (customer_id)
-- fast
SELECT order_id, status, created_at, total
FROM orders
WHERE customer_id = 4242
-- undo
DROP INDEX IF EXISTS orders_customer_id_idx
