# Postgres Query Optimization Lab

Six slow queries on a realistic 2-million-order Postgres database, each fixed and **measured** with `EXPLAIN (ANALYZE, BUFFERS)`. A small harness times each query before and after its fix and checks that the fixed version returns exactly the same rows.

## Dataset

`setup_data.sql` builds 200k customers, 1.96M orders and 5.9M order lines (775 MB) with a fixed random seed. It starts **untuned**, with primary keys only, like many real schemas.

## Results

| # | Problem | Fix | Before | After | Speedup |
|---|---|---|---|---|---|
| 1 | Foreign key `orders.customer_id` has no index (Postgres doesn't create one automatically) | B-tree index | 52.8 ms | 0.03 ms | ~1,900× |
| 2 | `WHERE lower(email) = ...` can't use an index on `email` | expression index on `lower(email)` | 36.6 ms | 0.03 ms | ~1,100× |
| 3 | "20 newest pending orders" scans 2M rows, then sorts | **partial** index `(created_at DESC) WHERE status='pending'` (1.3 MB, vs 17 MB for a full index) | 76.2 ms | 0.09 ms | ~890× |
| 4 | `OFFSET 1500000` reads and throws away 1.5M rows | **keyset pagination**: `WHERE order_id > last_seen` (no new index) | 330 ms | 0.02 ms | ~13,800× |
| 5 | `NOT IN (subquery over 2M rows)` | rewrite as `NOT EXISTS` → hash anti-join | **> 30 s** (timed out) | 478 ms | > 60× |
| 6 | 30-day revenue by status visits the table for every row | **covering** index `(created_at) INCLUDE (status, total)` → index-only scan | 78.4 ms | 20.3 ms | ~4× |

*Before/after = best of 3 runs on a warm cache. Buffers and plan shapes for each case are printed by `lab.py`.*

**Why case 5 is so slow:** `NOT IN` returns no rows at all if the subquery contains a NULL, so Postgres can't turn it into an anti-join. When the subquery is too big to hash in `work_mem`, it falls back to comparing every customer against the materialized list of orders, roughly 200k × 2M comparisons.

## Harness details

Each case is one `.sql` file with `-- slow`, `-- fix`, `-- fast` and `-- undo` sections, plus an optional `-- check`. For every case, `lab.py`:
1. **drops every non-primary-key index**, so each case starts from the same untuned schema
2. times the slow query (best of N, with a timeout)
3. applies the fix, one statement at a time
4. times the fast query
5. compares result hashes. When the slow query times out, it compares against the `-- check` reference query instead

Three harness problems turned up while building the lab and were fixed in separate commits:
- running `VACUUM` inside the transaction that wraps multiple statements fails
- an index left behind by one case made a later case look fast before its fix
- the slow `NOT IN` query needed a timeout

## How to run

```bash
pip install -r requirements.txt
createdb lab && psql -d lab -f setup_data.sql          # ~1 minute
export LAB_DSN=postgresql://postgres@localhost:5432/lab
python lab.py                  # all cases
python lab.py --only 04        # one case
pytest
```

## Next steps
- BRIN index on `created_at` for append-only time-series tables
- Index bloat and `fillfactor` after heavy updates
