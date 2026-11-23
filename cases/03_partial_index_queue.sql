-- Ops dashboard: the 20 newest pending orders. Only ~4% of orders are pending,
-- but without an index Postgres reads all 2M rows and sorts the pending ones.
-- A partial index holds only pending orders, already sorted newest first.
-- slow
SELECT order_id, customer_id, created_at, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20
-- fix
CREATE INDEX IF NOT EXISTS orders_pending_recent_idx ON orders (created_at DESC) WHERE status = 'pending'
-- fast
SELECT order_id, customer_id, created_at, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20
-- undo
DROP INDEX IF EXISTS orders_pending_recent_idx
