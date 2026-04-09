"""Wait for external dependencies before starting application processes."""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from urllib import error, request

import psycopg2
import redis


def _wait_for(name: str, probe, timeout: int, interval: float) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            probe()
            print(f"[wait] {name}: ready")
            return
        except Exception as exc:  # pragma: no cover - exercised in container startup
            if time.time() >= deadline:
                raise RuntimeError(f"{name} was not ready within {timeout}s: {exc}") from exc
            print(f"[wait] {name}: not ready ({exc}); retrying in {interval:.1f}s")
            time.sleep(interval)


def _probe_postgres() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    conn = psycopg2.connect(db_url, connect_timeout=3)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
    finally:
        conn.close()


def _probe_redis() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set")

    client = redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
    client.ping()


def _probe_kafka() -> None:
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is not set")

    last_error = None
    for server in [item.strip() for item in bootstrap_servers.split(",") if item.strip()]:
        if ":" not in server:
            raise RuntimeError(f"Invalid Kafka bootstrap server entry: {server}")
        host, port = server.rsplit(":", 1)
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                return
        except OSError as exc:
            last_error = exc

    raise RuntimeError(f"Cannot connect to any Kafka bootstrap server: {last_error}")


def _probe_mlflow() -> None:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is not set")

    health_url = f"{tracking_uri.rstrip('/')}/health"
    try:
        with request.urlopen(health_url, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
    except error.URLError as exc:
        raise RuntimeError(f"MLflow health probe failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for dependent services")
    parser.add_argument("--postgres", action="store_true", help="Wait for PostgreSQL")
    parser.add_argument("--redis", action="store_true", help="Wait for Redis")
    parser.add_argument("--kafka", action="store_true", help="Wait for Kafka")
    parser.add_argument("--mlflow", action="store_true", help="Wait for MLflow")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout per dependency in seconds")
    parser.add_argument("--interval", type=float, default=2.0, help="Retry interval in seconds")
    args = parser.parse_args()

    selected = []
    if args.postgres:
        selected.append(("postgres", _probe_postgres))
    if args.redis:
        selected.append(("redis", _probe_redis))
    if args.kafka:
        selected.append(("kafka", _probe_kafka))
    if args.mlflow:
        selected.append(("mlflow", _probe_mlflow))

    if not selected:
        parser.error("Select at least one dependency flag")

    try:
        for name, probe in selected:
            _wait_for(name, probe, timeout=args.timeout, interval=args.interval)
    except Exception as exc:
        print(f"[wait] dependency check failed: {exc}", file=sys.stderr)
        return 1

    print("[wait] all selected dependencies are ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
