# Enterprise Security, Access Control & GxP Compliance Specification
## US FDA 21 CFR Part 11 & Cryptographic Audit Architecture (Zydus-PdM)

---

## 1. Regulatory Context & Compliance Mandates

Predictive maintenance systems operating in pharmaceutical manufacturing (sterile injectables, oncology APIs, tablet compression) and clinical oncology care are subject to strict regulatory frameworks:
- **US FDA 21 CFR Part 11**: Electronic Records; Electronic Signatures.
- **EU Annex 11**: Computerised Systems validation and audit trails.
- **WHO Good Manufacturing Practices (cGMP)**: Data integrity, tamper evidence, and authorized access control.

---

## 2. Authentication, Token Lifecycle & RBAC Matrix

### 2.1 Password Hashing & Secret Security
- **Bcrypt (Work Factor 12) / Argon2id**: Zero plain-text passwords stored anywhere.
- **JWT Token Lifecycle**: HMAC-SHA256 (`HS256`) signed with strong secret keys (`JWT_SECRET`). Expiration default: 24 hours.

### 2.2 4-Tier Role-Based Access Control (RBAC) Matrix

| Endpoint / Capability | `viewer` | `engineer` | `admin` | `auditor` |
| :--- | :---: | :---: | :---: | :---: |
| **GET /health & /metrics** | ? | ? | ? | ? |
| **GET /api/equipment (Directory)** | ? | ? | ? | ? |
| **GET /api/equipment/{id}/sensors** | ? | ? | ? | ? |
| **GET /api/equipment/{id}/prediction** | ? | ? | ? | ? |
| **GET /api/dashboard/summary** | ? | ? | ? | ? |
| **GET /api/alerts (View Alerts)** | ? | ? | ? | ? |
| **PATCH /api/alerts/{id}/acknowledge** | ? (401) | ? | ? | ? (401) |
| **GET /api/workorders (View Orders)** | ? | ? | ? | ? |
| **PATCH /api/workorders/{id}/complete** | ? (401) | ? | ? | ? (401) |
| **GET /api/audit-logs (GxP Audit Trail)** | ? (401) | ? (401) | ? | ? |
| **POST /api/auth/users (User Admin)** | ? (401) | ? (401) | ? | ? (401) |
| **WebSocket Stream (/ws/live)** | ? | ? | ? | ? |

---

## 3. Cryptographic Tamper-Evident Audit Trail (SHA-256 Chaining)

To meet the highest standard of **US FDA 21 CFR Part 11** electronic record integrity, the `audit_logs` table employs **SHA-256 Hash Chaining**:

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    reason_for_change TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    previous_hash VARCHAR(64),
    record_hash VARCHAR(64) NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.1 Hash Computation Formula
For each audit record $k$:
$$\text{RecordHash}_k = \text{SHA256}\left( \text{RecordHash}_{k-1} \,\|\, \text{user\_id} \,\|\, \text{action} \,\|\, \text{entity\_type} \,\|\, \text{entity\_id} \,\|\, \text{payload} \,\|\, \text{timestamp\_utc} \right)$$
If an unauthorized actor modifies any historical audit row, all subsequent hashes in the chain become mathematically invalid, instantly exposing the tampering during quality audits.

---

## 4. Electronic Signatures & Dual-Control Workflows

1. **Work Order Completion**:
   - Maintenance technician MUST supply electronic signature confirmation (`user_id`, password re-verification, and structured `reason_for_change` notes).
2. **Alert Acknowledgment**:
   - Requires valid engineer/admin session token and recorded acknowledgment timestamp + notes.
3. **Threshold & Configuration Changes**:
   - Restricted to `admin` role with full before/after JSON differential logging.

---

## 5. Network Security, Rate Limiting & Denial of Service Defense

- **Input Validation**: Strict Pydantic models validate all incoming payloads, rejecting unexpected fields and SQL injection vectors.
- **Brute-Force Defense**: Failed login attempts are logged in `audit_logs` and rate-limited.
- **Connection Isolation**: Internal data stores (TimescaleDB, Redis, Kafka) operate on an isolated Docker network (`zydus-network`), exposing only external endpoints on designated ports.
