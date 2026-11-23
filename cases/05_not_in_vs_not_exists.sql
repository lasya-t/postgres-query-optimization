-- Customers who never ordered (for a win-back campaign). NOT IN against a 2M-row
-- subquery can't become an anti-join (NOT IN behaves differently with NULLs), so
-- Postgres builds a huge hashed subplan. NOT EXISTS lets the planner use an anti-join.
-- slow
SELECT c.customer_id, c.email
FROM customers c
WHERE c.customer_id NOT IN (SELECT o.customer_id FROM orders o)
-- fix
-- fast
SELECT c.customer_id, c.email
FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)
-- undo
-- check
SELECT c.customer_id, c.email
FROM customers c
LEFT JOIN (SELECT DISTINCT customer_id FROM orders) o USING (customer_id)
WHERE o.customer_id IS NULL
