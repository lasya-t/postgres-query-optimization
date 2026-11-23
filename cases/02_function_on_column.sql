-- Case-insensitive login lookup. Emails are stored in mixed case, so the app calls lower().
-- A plain index on email can't be used once a function wraps the column.
-- slow
SELECT customer_id, state FROM customers WHERE lower(email) = 'user77@example.com'
-- fix
CREATE INDEX IF NOT EXISTS customers_email_idx ON customers (email);
CREATE INDEX IF NOT EXISTS customers_lower_email_idx ON customers (lower(email))
-- fast
SELECT customer_id, state FROM customers WHERE lower(email) = 'user77@example.com'
-- undo
DROP INDEX IF EXISTS customers_email_idx;
DROP INDEX IF EXISTS customers_lower_email_idx
