import pytest
import concurrent.futures
from common.db_pool import get_db_conn, get_db_cursor, get_pool

def test_pool_thread_safety_high_concurrency():
    """50 concurrent worker threads borrowing and returning connections simultaneously."""
    def worker(idx):
        with get_db_cursor() as cur:
            cur.execute("SELECT %s as num, NOW() as ts", (idx,))
            res = cur.fetchone()
            return res["num"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 50
    assert set(results) == set(range(50))

def test_cursor_auto_rollback_on_exception():
    """Verify that a failing transaction rolls back cleanly without breaking the connection pool."""
    with pytest.raises(Exception):
        with get_db_cursor() as cur:
            cur.execute("SELECT 1/0")  # Division by zero forces DB error

    # Subsequent query from pool must succeed immediately
    with get_db_cursor() as cur:
        cur.execute("SELECT 42 as value")
        assert cur.fetchone()["value"] == 42
