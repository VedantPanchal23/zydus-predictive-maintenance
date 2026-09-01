"""
Cryptographic Audit Trail Hash Chaining (US FDA 21 CFR Part 11)
================================================================
Provides SHA-256 hash chaining to ensure mathematical immutability and
tamper-evident audit logs across the predictive maintenance lifecycle.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, List, Tuple, Dict, Optional


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def _canonical_json(obj: Any) -> str:
    """Produces a deterministic, whitespace-normalized JSON string for hashing."""
    if obj is None:
        return "null"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _normalize_timestamp(ts: Any) -> str:
    if not ts:
        return ""
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def compute_record_hash(
    previous_hash: Optional[str],
    user_id: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Any = None,
    after_state: Any = None,
    reason_for_change: Optional[str] = None,
    timestamp_iso: Any = "",
) -> str:
    """
    Computes a deterministic SHA-256 hash over all record fields chained to the previous record hash:
    H = SHA256(previous_hash || user_id || user_role || action || entity_type || entity_id || before_state || after_state || reason || timestamp)
    """
    prev = previous_hash if previous_hash else GENESIS_HASH
    ts_norm = _normalize_timestamp(timestamp_iso)
    payload = (
        f"{prev}|"
        f"{user_id}|"
        f"{user_role}|"
        f"{action}|"
        f"{entity_type}|"
        f"{entity_id}|"
        f"{_canonical_json(before_state)}|"
        f"{_canonical_json(after_state)}|"
        f"{reason_for_change or ''}|"
        f"{ts_norm}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_audit_chain_integrity(records: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Verifies that every record in the provided sequential audit trail correctly matches
    its cryptographic SHA-256 hash and properly references the preceding record hash.
    
    Returns:
        (is_valid, list_of_tampered_records)
    """
    tampered: List[Dict[str, Any]] = []
    expected_prev = GENESIS_HASH

    for idx, rec in enumerate(records):
        rec_prev = rec.get("previous_hash") or GENESIS_HASH
        rec_hash = rec.get("record_hash")
        
        # Check link to previous
        if idx == 0:
            if rec_prev not in (GENESIS_HASH, None, ""):
                expected_prev = rec_prev  # Allow chain verification from sub-window if initial hash matches
        else:
            if rec_prev != expected_prev:
                tampered.append({
                    "record_id": rec.get("id"),
                    "error": f"Broken chain link: expected previous_hash '{expected_prev}', got '{rec_prev}'",
                    "record": rec,
                })

        # Recompute hash
        ts = rec.get("timestamp_utc") or rec.get("timestamp") or ""
        calc_hash = compute_record_hash(
            previous_hash=rec_prev,
            user_id=str(rec.get("user_id", "")),
            user_role=str(rec.get("user_role", "")),
            action=str(rec.get("action", "")),
            entity_type=str(rec.get("entity_type", "")),
            entity_id=str(rec.get("entity_id", "")),
            before_state=rec.get("before_state"),
            after_state=rec.get("after_state"),
            reason_for_change=rec.get("reason_for_change"),
            timestamp_iso=ts,
        )

        if rec_hash != calc_hash:
            tampered.append({
                "record_id": rec.get("id"),
                "error": f"Invalid record hash: stored '{rec_hash}', computed '{calc_hash}'",
                "record": rec,
            })

        expected_prev = rec_hash or calc_hash

    is_valid = len(tampered) == 0
    return is_valid, tampered
