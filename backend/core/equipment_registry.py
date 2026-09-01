"""Equipment registry utilities used by scheduler, ingestion and WebSocket feeds."""

from __future__ import annotations

import logging
from typing import Optional
from common.db_pool import get_db_cursor

logger = logging.getLogger("equipment-registry")

FALLBACK_EQUIPMENT_IDS = [
    "GRAN-LINE-01", "FBD-DRYER-01", "TAB-PRESS-01", "COATER-01",
    "VIAL-FILL-01", "LYO-CHAMBER-01", "AUTOCLAVE-01", "WFI-STILL-01",
    "BIOREACTOR-01", "TFF-SKID-01", "CHROM-SKID-01", "CIP-SYSTEM-01",
    "HPLC-AUTO-01", "LCMS-CHAMBER-01", "SPECTRO-UV-01", "DISSOLUTION-01",
    "LINAC-01", "CYCLOTRON-01", "MRI-CRYO-01", "ULT-FREEZER-01",
]

_eq_map: dict[str, int] = {}


def list_active_equipment_ids() -> list[str]:
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT name FROM equipment ORDER BY id")
            rows = cur.fetchall()
            names = [row["name"] for row in rows]
        if names:
            return names
    except Exception as exc:
        logger.debug("Failed to load equipment registry: %s", exc)
    return FALLBACK_EQUIPMENT_IDS.copy()


def resolve_equipment_id(name_or_id: str | int) -> Optional[int]:
    """Resolves string equipment name/code to its primary key integer."""
    if isinstance(name_or_id, int):
        return name_or_id
    if str(name_or_id).isdigit():
        return int(name_or_id)
    if name_or_id in _eq_map:
        return _eq_map[name_or_id]
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, name FROM equipment;")
            rows = cur.fetchall()
            for r in rows:
                _eq_map[r["name"]] = r["id"]
                _eq_map[str(r["id"])] = r["id"]
        return _eq_map.get(str(name_or_id), None)
    except Exception:
        return None
