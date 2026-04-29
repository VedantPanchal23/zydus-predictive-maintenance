"""Equipment registry utilities used by scheduler and WebSocket feeds."""

from __future__ import annotations

import logging
import os

import psycopg2

from common.reliability import retry_call

logger = logging.getLogger("equipment-registry")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db",
)
DB_RETRIES = int(os.environ.get("ML_DB_RETRIES", "3"))

FALLBACK_EQUIPMENT_IDS = [
    "GRAN-LINE-01",
    "TABLET-PRESS-01",
    "BLISTER-PACK-01",
    "CAPSULE-FILL-01",
    "COATING-DRUM-01",
    "VIAL-WASHER-01",
    "ASEPTIC-FILL-01",
    "CIP-SKID-01",
    "ULT-FREEZER-01",
    "COLD-ROOM-01",
    "CHILLER-LOOP-01",
    "STABILITY-CHAMBER-01",
    "HPLC-STACK-01",
    "LCMS-01",
    "DISSOLUTION-01",
    "TOC-ANALYZER-01",
    "INFUSION-PUMP-01",
    "SYRINGE-PUMP-01",
    "LINAC-01",
    "CT-SCANNER-01",
]


def list_active_equipment_ids() -> list[str]:
    conn = None
    try:
        conn = retry_call(
            lambda: psycopg2.connect(DB_URL),
            retries=DB_RETRIES,
            initial_delay=1.0,
            retry_exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError),
            logger=logger,
            operation_name="equipment registry connection",
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name
                FROM equipment
                WHERE status = 'active'
                ORDER BY id
                """
            )
            names = [row[0] for row in cur.fetchall()]

        if names:
            return names
        logger.warning("Equipment registry returned no active rows; using fallback list")
    except psycopg2.Error as exc:
        logger.warning("Failed to load equipment registry, using fallback list: %s", exc)
    finally:
        if conn is not None:
            conn.close()

    return FALLBACK_EQUIPMENT_IDS.copy()
