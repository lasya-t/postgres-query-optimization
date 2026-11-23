"""Needs the lab database (LAB_DSN). The parsing tests always run."""
import os
from pathlib import Path

import psycopg
import pytest

from lab import CASES, parse_case, run_case

CASE_FILES = sorted(CASES.glob("*.sql"))


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda p: p.stem)
def test_case_files_parse(path):
    c = parse_case(path)
    assert c["slow"] and c["fast"]


needs_db = pytest.mark.skipif(not os.getenv("LAB_DSN"), reason="LAB_DSN not set")


@needs_db
@pytest.mark.parametrize("path", CASE_FILES, ids=lambda p: p.stem)
def test_fix_is_faster_and_returns_same_rows(path):
    with psycopg.connect(os.environ["LAB_DSN"], autocommit=True) as conn:
        r = run_case(conn, path, runs=2, timeout_ms=10_000)
    assert r.same_rows
    assert r.fast.ms < r.slow.ms
    assert r.fast.buffers <= r.slow.buffers or r.slow.timed_out
