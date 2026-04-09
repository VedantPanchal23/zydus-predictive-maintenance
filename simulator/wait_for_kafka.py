"""Wait for Kafka broker readiness before starting the sensor simulator."""

from __future__ import annotations

import os
import sys
import time

from kafka import KafkaAdminClient


def main() -> int:
    broker = os.environ.get("KAFKA_BROKER", "localhost:9092")
    timeout_seconds = int(os.environ.get("WAIT_FOR_KAFKA_TIMEOUT", "180"))
    interval_seconds = float(os.environ.get("WAIT_FOR_KAFKA_INTERVAL", "2"))

    deadline = time.time() + timeout_seconds
    while True:
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=broker,
                request_timeout_ms=4000,
                api_version_auto_timeout_ms=4000,
            )
            try:
                admin.list_topics()
            finally:
                admin.close()
            print(f"[wait] kafka ready at {broker}")
            return 0
        except Exception as exc:  # pragma: no cover - exercised in container startup
            if time.time() >= deadline:
                print(
                    f"[wait] kafka not ready within {timeout_seconds}s: {exc}",
                    file=sys.stderr,
                )
                return 1
            print(f"[wait] kafka not ready ({exc}); retrying in {interval_seconds:.1f}s")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
