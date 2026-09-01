import pytest
from core.crypto_chain import compute_record_hash, verify_audit_chain_integrity, GENESIS_HASH

def test_hash_chain_generation():
    """Verify deterministic hash computation and sequential linking."""
    h1 = compute_record_hash(
        previous_hash=GENESIS_HASH,
        user_id="admin",
        user_role="admin",
        action="LOGIN_SUCCESS",
        entity_type="AUTH",
        entity_id="admin",
        timestamp_iso="2026-08-31T12:00:00Z",
    )
    assert len(h1) == 64
    assert h1 != GENESIS_HASH

    h2 = compute_record_hash(
        previous_hash=h1,
        user_id="engineer1",
        user_role="engineer",
        action="ACKNOWLEDGE_ALERT",
        entity_type="ALERT",
        entity_id="12",
        reason_for_change="Investigating bearing noise",
        timestamp_iso="2026-08-31T12:05:00Z",
    )
    assert len(h2) == 64
    assert h2 != h1

def test_chain_verification_valid_sequence():
    """Verify that an intact chain passes verification."""
    records = []
    prev = GENESIS_HASH
    for i in range(5):
        ts = f"2026-08-31T12:0{i}:00Z"
        rec_hash = compute_record_hash(
            previous_hash=prev,
            user_id=f"user_{i}",
            user_role="engineer",
            action="TEST_ACTION",
            entity_type="TEST_ENTITY",
            entity_id=str(i),
            timestamp_iso=ts,
        )
        records.append({
            "id": i + 1,
            "user_id": f"user_{i}",
            "user_role": "engineer",
            "action": "TEST_ACTION",
            "entity_type": "TEST_ENTITY",
            "entity_id": str(i),
            "previous_hash": prev,
            "record_hash": rec_hash,
            "timestamp_utc": ts,
        })
        prev = rec_hash

    is_valid, tampered = verify_audit_chain_integrity(records)
    assert is_valid is True
    assert len(tampered) == 0

def test_chain_verification_detects_tampering():
    """Verify that any modification to a historical record breaks chain validity."""
    records = []
    prev = GENESIS_HASH
    for i in range(5):
        ts = f"2026-08-31T12:0{i}:00Z"
        rec_hash = compute_record_hash(
            previous_hash=prev,
            user_id=f"user_{i}",
            user_role="engineer",
            action="TEST_ACTION",
            entity_type="TEST_ENTITY",
            entity_id=str(i),
            timestamp_iso=ts,
        )
        records.append({
            "id": i + 1,
            "user_id": f"user_{i}",
            "user_role": "engineer",
            "action": "TEST_ACTION",
            "entity_type": "TEST_ENTITY",
            "entity_id": str(i),
            "previous_hash": prev,
            "record_hash": rec_hash,
            "timestamp_utc": ts,
        })
        prev = rec_hash

    # Malicious actor tampers with record #2 user_id
    records[2]["user_id"] = "MALICIOUS_ACTOR"

    is_valid, tampered = verify_audit_chain_integrity(records)
    assert is_valid is False
    assert len(tampered) > 0
    assert tampered[0]["record_id"] == 3
