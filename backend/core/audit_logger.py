"""
GxP / US FDA 21 CFR Part 11 Immutable Audit Logger
===================================================
Captures all critical actions, logins, state changes, and automated triggers
with SHA-256 cryptographic hash chaining for tamper-evident compliance.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple

import psycopg2.extras
from core.db_pool import get_db_cursor
from core.crypto_chain import compute_record_hash, verify_audit_chain_integrity, GENESIS_HASH

logger = logging.getLogger("audit-logger")


def _get_latest_record_hash() -> str:
    """Fetches the latest hash from the audit_logs table to link the new record."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row and row.get("record_hash"):
                return row["record_hash"]
    except Exception as exc:
        logger.debug("Could not query latest record_hash (using genesis): %s", exc)
    return GENESIS_HASH


def log_audit_event(
    user_id: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Any = None,
    after_state: Any = None,
    reason_for_change: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[int]:
    """
    Inserts a cryptographically hash-chained audit trail record.
    """
    ts = datetime.now(timezone.utc).isoformat()
    prev_hash = _get_latest_record_hash()
    
    rec_hash = compute_record_hash(
        previous_hash=prev_hash,
        user_id=user_id,
        user_role=user_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_state=before_state,
        after_state=after_state,
        reason_for_change=reason_for_change,
        timestamp_iso=ts,
    )

    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs (
                    user_id, user_role, action, entity_type, entity_id,
                    before_state, after_state, reason_for_change,
                    ip_address, user_agent, previous_hash, record_hash, timestamp_utc
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s
                ) RETURNING id;
                """,
                (
                    user_id,
                    user_role,
                    action,
                    entity_type,
                    str(entity_id),
                    json.dumps(before_state, default=str) if before_state is not None else None,
                    json.dumps(after_state, default=str) if after_state is not None else None,
                    reason_for_change,
                    ip_address,
                    user_agent,
                    prev_hash,
                    rec_hash,
                    ts,
                ),
            )
            row = cur.fetchone()
            log_id = row["id"] if row else None
            logger.info(
                "GxP Audit [#%s] | %s (%s) performed %s on %s:%s | Hash: %s... | Reason: %s",
                log_id,
                user_id,
                user_role,
                action,
                entity_type,
                entity_id,
                rec_hash[:12],
                reason_for_change or "N/A",
            )
            return log_id
    except Exception as exc:
        logger.error("Failed to write GxP audit log entry: %s", exc)
        return None


def verify_database_audit_chain(limit: int = 1000) -> Tuple[bool, List[Dict[str, Any]], int]:
    """
    Queries historical audit log records and verifies cryptographic SHA-256 chain integrity.
    Returns:
        (is_valid, tampered_records_list, total_records_checked)
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, user_role, action, entity_type, entity_id,
                       before_state, after_state, reason_for_change, ip_address,
                       user_agent, previous_hash, record_hash, timestamp_utc
                FROM audit_logs
                ORDER BY id ASC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
            is_valid, tampered = verify_audit_chain_integrity(rows)
            return is_valid, tampered, len(rows)
    except Exception as exc:
        logger.error("Error during audit chain verification: %s", exc)
        return False, [{"error": str(exc)}], 0
