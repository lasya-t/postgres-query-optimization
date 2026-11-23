-- Daily revenue by status for the last 30 days. A plain index on created_at finds the
-- rows but then has to visit the table for status and total. A covering index
-- (INCLUDE status, total) answers from the index alone: an index-only scan.
-- slow
SELECT status, count(*), sum(total)
FROM orders
WHERE created_at >= timestamptz '2025-11-01' AND created_at < timestamptz '2025-12-01'
GROUP BY status
-- fix
CREATE INDEX IF NOT EXISTS orders_created_cover_idx ON orders (created_at) INCLUDE (status, total);
VACUUM orders
-- fast
SELECT status, count(*), sum(total)
FROM orders
WHERE created_at >= timestamptz '2025-11-01' AND created_at < timestamptz '2025-12-01'
GROUP BY status
-- undo
DROP INDEX IF EXISTS orders_created_cover_idx
