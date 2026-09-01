"""
Database Connection Pool Manager
================================
Provides thread-safe, high-concurrency connection pooling for TimescaleDB / PostgreSQL.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("db-pool")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db",
)
MIN_CONNECTIONS = int(os.environ.get("DB_POOL_MIN", "2"))
MAX_CONNECTIONS = int(os.environ.get("DB_POOL_MAX", "30"))

_pool: pool.ThreadedConnectionPool | None = None


def _resolve_dsn() -> str:
    dsn = DB_URL
    # If postgres host is specified but unresolvable locally (e.g. running on Windows host outside Docker)
    if "@postgres:" in dsn:
        try:
            import socket
            socket.gethostbyname("postgres")
        except Exception:
            dsn = dsn.replace("@postgres:", "@localhost:")
    return dsn


def init_pool(min_conn: int = MIN_CONNECTIONS, max_conn: int = MAX_CONNECTIONS) -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool

    dsn = _resolve_dsn()
    retries = 5
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            _pool = pool.ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                dsn=dsn,
            )
            logger.info("Initialized database connection pool (min=%s, max=%s)", min_conn, max_conn)
            return _pool
        except psycopg2.Error as exc:
            # If postgres hostname failed, try localhost
            if "could not translate host name" in str(exc) and "@postgres:" in dsn:
                dsn = dsn.replace("@postgres:", "@localhost:")
                continue
            if attempt == retries:
                logger.error("Failed to initialize database pool after %s attempts: %s", attempt, exc)
                raise
            logger.warning("Database pool init failed (attempt %s/%s): %s. Retrying in %.1fs...", attempt, retries, exc, delay)
            time.sleep(delay)
    raise RuntimeError("Could not initialize database connection pool")


def get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = init_pool()
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        logger.info("Database connection pool closed")
        _pool = None


@contextmanager
def get_db_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager to check out a connection from the pool."""
    p = get_pool()
    conn = p.getconn()
    try:
        if conn.closed:
            conn = psycopg2.connect(_resolve_dsn())
        yield conn
    finally:
        try:
            if not conn.closed:
                p.putconn(conn)
        except Exception as exc:
            logger.debug("Error returning connection to pool: %s", exc)


@contextmanager
def get_db_cursor(cursor_factory=RealDictCursor) -> Generator[psycopg2.extensions.cursor, None, None]:
    """Context manager providing a cursor with auto-commit/rollback semantics."""
    with get_db_conn() as conn:
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
