-- Builds the lab database: 200k customers, 2M orders, 6M order lines.
-- Only primary keys exist at the start, like a schema nobody has tuned yet.
DROP TABLE IF EXISTS order_lines, orders, customers CASCADE;

CREATE TABLE customers (
    customer_id  int PRIMARY KEY,
    email        text NOT NULL,
    state        char(2) NOT NULL,
    created_at   timestamptz NOT NULL
);

CREATE TABLE orders (
    order_id     bigint PRIMARY KEY,
    customer_id  int NOT NULL REFERENCES customers,
    status       text NOT NULL,
    created_at   timestamptz NOT NULL,
    total        numeric(10, 2) NOT NULL
);

CREATE TABLE order_lines (
    order_id     bigint NOT NULL REFERENCES orders,
    line_no      int NOT NULL,
    sku          text NOT NULL,
    qty          int NOT NULL,
    PRIMARY KEY (order_id, line_no)
);

SELECT setseed(0.42);

INSERT INTO customers
SELECT i,
       'User' || i || '@Example.com',
       (ARRAY['PA','NJ','NY','DE','MD','CA','TX','FL'])[1 + (random() * 7)::int],
       timestamptz '2022-01-01' + random() * interval '900 days'
FROM generate_series(1, 200000) i;

INSERT INTO orders
SELECT i,
       1 + (random() * 199999)::int,
       CASE WHEN random() < 0.90 THEN 'completed' WHEN random() < 0.7 THEN 'cancelled' ELSE 'pending' END,
       timestamptz '2024-01-01' + random() * interval '700 days',
       round((5 + random() * 1500)::numeric, 2)
FROM generate_series(1, 2000000) i;

INSERT INTO order_lines
SELECT o, l, 'SKU-' || (1 + (random() * 4999)::int), 1 + (random() * 3)::int
FROM generate_series(1, 2000000) o, generate_series(1, 3) l;

-- customers who never ordered, for the anti-join case
DELETE FROM order_lines WHERE order_id IN (SELECT order_id FROM orders WHERE customer_id % 50 = 0);
DELETE FROM orders WHERE customer_id % 50 = 0;

VACUUM ANALYZE;
