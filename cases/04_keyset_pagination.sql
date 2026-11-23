-- Exporting orders page by page. OFFSET makes Postgres walk and throw away every
-- earlier row, so deep pages get slower and slower. Keyset pagination remembers the
-- last id seen and seeks straight to it with the primary key. No new index needed.
-- slow
SELECT order_id, customer_id, total
FROM orders
ORDER BY order_id
LIMIT 50 OFFSET 1500000
-- fix
-- fast
SELECT order_id, customer_id, total
FROM orders
WHERE order_id > 1530930   -- last order_id on the previous page, sent back by the client
ORDER BY order_id
LIMIT 50
-- undo
