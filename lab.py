"""Run each optimization case: time the slow query, apply the fix, time the fast one, compare.

A case file in cases/ has four sections:

    -- slow   the original query
    -- fix    DDL that enables the faster plan (indexes); may be empty for pure rewrites
    -- fast   the improved query (often the same text as slow)
    -- undo   DDL that removes the fix, so the lab can be re-run from scratch
    -- check  (optional) a query whose rows must equal the fast query's, used when
              the slow query times out and can't be compared directly

Timings come from EXPLAIN (ANALYZE, BUFFERS): best of N runs, so the cache is warm for both.
Both versions must return the same rows (compared by a hash of the sorted result).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

CASES = Path(__file__).with_name("cases")
DSN = os.getenv("LAB_DSN", "postgresql://postgres@localhost:5432/lab")


@dataclass
class Measure:
    ms: float
    buffers: int
    nodes: list[str]
    timed_out: bool = False


@dataclass
class CaseResult:
    name: str
    slow: Measure
    fast: Measure
    same_rows: bool


def parse_case(path: Path) -> dict[str, str]:
    parts = re.split(r"^-- (slow|fix|fast|undo|check)\s*$", path.read_text(), flags=re.M)
    sections = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    missing = {"slow", "fix", "fast", "undo"} - sections.keys()  # check is optional
    if missing:
        raise ValueError(f"{path.name} missing sections: {missing}")
    return sections


def _nodes(plan: dict) -> list[str]:
    out = [plan["Node Type"] + (f" on {plan['Index Name']}" if "Index Name" in plan else "")]
    for child in plan.get("Plans", []):
        out += _nodes(child)
    return out


def measure(cur, sql: str, runs: int = 3, timeout_ms: int = 30_000) -> Measure:
    best = None
    cur.execute(f"SET statement_timeout = {timeout_ms}")
    for _ in range(runs):
        try:
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        except psycopg.errors.QueryCanceled:
            cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")  # plan only, no timing
            return Measure(float(timeout_ms), 0, _nodes(cur.fetchone()[0][0]["Plan"]), timed_out=True)
        plan = cur.fetchone()[0][0]
        top = plan["Plan"]
        m = Measure(plan["Execution Time"], top.get("Shared Hit Blocks", 0) + top.get("Shared Read Blocks", 0), _nodes(top))
        if best is None or m.ms < best.ms:
            best = m
    return best


def result_hash(cur, sql: str) -> str:
    cur.execute(sql)
    rows = sorted(map(repr, cur.fetchall()))
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def run_script(cur, script: str) -> None:
    # one statement at a time: several in one call run as a single transaction,
    # and some commands (VACUUM, CREATE INDEX CONCURRENTLY) refuse to run inside one
    for stmt in (s.strip() for s in script.split(";")):
        if stmt:
            cur.execute(stmt)


def run_case(conn, path: Path, runs: int = 3, timeout_ms: int = 30_000) -> CaseResult:
    c = parse_case(path)
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = 0")
        run_script(cur, c["undo"])
        slow = measure(cur, c["slow"], runs, timeout_ms)
        if slow.timed_out:
            if not c.get("check"):
                raise ValueError(f"{path.name}: slow query timed out and there is no -- check section")
            reference = result_hash(cur, c["check"])
        else:
            reference = result_hash(cur, c["slow"])
        cur.execute("SET statement_timeout = 0")
        run_script(cur, c["fix"])
        fast = measure(cur, c["fast"], runs, timeout_ms)
        same = result_hash(cur, c["fast"]) == reference
    return CaseResult(path.stem, slow, fast, same)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", help="run cases whose name contains this")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--timeout-ms", type=int, default=30_000)
    p.add_argument("--json", help="write results to this file")
    args = p.parse_args()

    results = []
    with psycopg.connect(DSN, autocommit=True) as conn:
        for path in sorted(CASES.glob("*.sql")):
            if args.only and args.only not in path.stem:
                continue
            r = run_case(conn, path, args.runs, args.timeout_ms)
            results.append(r)
            print(f"\n{r.name}")
            flag = ">" if r.slow.timed_out else " "
            print(f"  before{flag}{r.slow.ms:9.2f} ms  {r.slow.buffers:>8,} buffers  {' > '.join(r.slow.nodes[:3])}")
            print(f"  after  {r.fast.ms:9.2f} ms  {r.fast.buffers:>8,} buffers  {' > '.join(r.fast.nodes[:3])}")
            speed = f"{r.slow.ms / max(r.fast.ms, 0.001):,.0f}x"
            print(f"  {'more than ' if r.slow.timed_out else ''}{speed} faster, same rows: {r.same_rows}"
                  + (" (checked against reference query; slow one timed out)" if r.slow.timed_out else ""))
    if args.json:
        Path(args.json).write_text(json.dumps([r.__dict__ | {"slow": r.slow.__dict__, "fast": r.fast.__dict__} for r in results], indent=2))


if __name__ == "__main__":
    main()
