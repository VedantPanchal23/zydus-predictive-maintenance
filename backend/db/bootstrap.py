"""
Idempotent Database Bootstrap & Seeder
======================================
Ensures schema, default users, equipment records, and initial telemetry baselines
are present on system startup without requiring external one-off containers.
"""

from __future__ import annotations

import logging
from pathlib import Path
import psycopg2

from common.db_pool import get_db_conn, get_db_cursor
from db.demo_bootstrap import (
    seed_sensor_history,
    seed_predictions_and_cache,
    seed_alerts_and_work_orders,
    connect_redis,
    fetch_equipment,
    recent_sensor_row_count,
)

logger = logging.getLogger("bootstrap")


def bootstrap_database_if_needed() -> None:
    """Check database state and seed baseline data only if fresh."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        return

    try:
        # 1. Apply schema and seed master tables
        sql = schema_path.read_text(encoding="utf-8")
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            logger.info("Database schema and master tables verified.")

            # 2. Check if sensor readings exist
            equipment = fetch_equipment(conn)
            if not equipment:
                logger.warning("No equipment rows found.")
                return

            sensor_rows = recent_sensor_row_count(conn)
            if sensor_rows < 100:
                logger.info("Fresh database detected (only %s sensor rows). Seeding baseline telemetry...", sensor_rows)
                redis_client = connect_redis()
                seed_sensor_history(conn, equipment)
                seed_predictions_and_cache(conn, redis_client, equipment)
                seed_alerts_and_work_orders(conn, equipment)
                logger.info("Baseline telemetry and initial alerts seeded successfully.")
            else:
                logger.info("Database already populated (%s recent sensor rows). Skipping bootstrap seeding.", sensor_rows)
    except Exception as exc:
        logger.warning("Database bootstrap non-fatal warning: %s", exc)
