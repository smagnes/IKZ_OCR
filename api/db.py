import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None

PLAN_LIMITS = {
    "starter": 200,
    "pro": 1000,
    "enterprise": 5000,
    "demo": 9999,
}


async def init_pool(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    logger.info("Połączenie z bazą danych OK")


async def close_pool():
    if _pool:
        await _pool.close()


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Pula połączeń nie jest zainicjalizowana")
    return _pool


# ── API KEYS ──────────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_api_key_record(raw_key: str) -> Optional[dict]:
    row = await get_pool().fetchrow(
        """
        SELECT id, key_prefix, name, facility_name, plan, scans_limit, is_active, webhook_url,
               (SELECT COUNT(*) FROM scans
                WHERE api_key_id = api_keys.id::text
                  AND created_at >= date_trunc('month', NOW())) AS scans_this_month
        FROM api_keys
        WHERE key_hash = $1 AND is_active = true
        """,
        _hash_key(raw_key),
    )
    return dict(row) if row else None


async def create_api_key(name: str, facility_name: str, plan: str = "starter") -> dict:
    raw = "mk_" + secrets.token_urlsafe(20)
    key_hash = _hash_key(raw)
    key_prefix = raw[:16]
    limit = PLAN_LIMITS.get(plan, 200)

    row = await get_pool().fetchrow(
        """
        INSERT INTO api_keys (key_hash, key_prefix, name, facility_name, plan, scans_limit)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, key_prefix, name, facility_name, plan, scans_limit, created_at
        """,
        key_hash, key_prefix, name, facility_name, plan, limit,
    )
    return {**dict(row), "raw_key": raw}


async def set_webhook_url(key_id: str, webhook_url: Optional[str]) -> None:
    await get_pool().execute(
        "UPDATE api_keys SET webhook_url = $1 WHERE id = $2",
        webhook_url, key_id,
    )


async def list_api_keys() -> list[dict]:
    rows = await get_pool().fetch(
        """
        SELECT id, key_prefix, name, facility_name, plan, scans_limit, is_active, webhook_url, created_at,
               (SELECT COUNT(*) FROM scans
                WHERE api_key_id = api_keys.id::text
                  AND created_at >= date_trunc('month', NOW())) AS scans_this_month
        FROM api_keys
        ORDER BY created_at DESC
        """
    )
    return [dict(r) for r in rows]


# ── SCANS ─────────────────────────────────────────────────────────────────────

async def save_scan(
    *,
    scan_id: str,
    api_key_id: str,
    doc_type: str,
    doc_type_label: str,
    patient: Optional[str],
    pesel_masked: Optional[str],
    doctor: Optional[str],
    facility: Optional[str],
    exam_date: Optional[str],
    fields: dict,
    alerts: list[str],
    raw_text: str,
    confidence_overall: float,
    processing_time_ms: int,
    ikz_silos_id: Optional[str],
    ikz_examination_id: Optional[int],
    source: str = "api",
) -> None:
    import json
    await get_pool().execute(
        """
        INSERT INTO scans (
            id, api_key_id, doc_type, doc_type_label,
            patient, pesel_masked, doctor, facility, exam_date,
            fields, alerts, raw_text,
            confidence_overall, processing_time_ms,
            ikz_silos_id, ikz_examination_id, source
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,
            $10::jsonb,$11,$12,$13,$14,$15,$16,$17
        )
        """,
        scan_id, api_key_id, doc_type, doc_type_label,
        patient, pesel_masked, doctor, facility, exam_date,
        json.dumps(fields), alerts, raw_text[:4000],
        confidence_overall, processing_time_ms,
        ikz_silos_id, ikz_examination_id, source,
    )


async def get_scans(
    api_key_id: str,
    page: int = 1,
    limit: int = 20,
    doc_type: Optional[str] = None,
) -> tuple[list[dict], int]:
    offset = (page - 1) * limit
    where = "WHERE api_key_id = $1"
    params: list = [api_key_id]

    if doc_type:
        params.append(doc_type)
        where += f" AND doc_type = ${len(params)}"

    total = await get_pool().fetchval(
        f"SELECT COUNT(*) FROM scans {where}", *params
    )
    rows = await get_pool().fetch(
        f"""
        SELECT id, doc_type, doc_type_label, patient, facility, exam_date,
               source, alerts, confidence_overall, created_at
        FROM scans {where}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
        """,
        *params,
    )
    return [dict(r) for r in rows], total


async def get_scan_by_id(scan_id: str, api_key_id: str) -> Optional[dict]:
    row = await get_pool().fetchrow(
        "SELECT * FROM scans WHERE id = $1 AND api_key_id = $2",
        scan_id, api_key_id,
    )
    return dict(row) if row else None


async def delete_scan(scan_id: str, api_key_id: str) -> bool:
    result = await get_pool().execute(
        "DELETE FROM scans WHERE id = $1 AND api_key_id = $2",
        scan_id, api_key_id,
    )
    return result == "DELETE 1"


async def get_stats(api_key_id: str) -> dict:
    row = await get_pool().fetchrow(
        """
        SELECT
            COUNT(*)                                                      AS total_scans,
            COUNT(*) FILTER (WHERE created_at >= date_trunc('month', NOW())) AS scans_this_month,
            AVG(processing_time_ms)::int                                  AS avg_processing_ms,
            AVG(confidence_overall)                                       AS avg_confidence
        FROM scans WHERE api_key_id = $1
        """,
        api_key_id,
    )
    by_type = await get_pool().fetch(
        "SELECT doc_type, COUNT(*) AS cnt FROM scans WHERE api_key_id = $1 GROUP BY doc_type",
        api_key_id,
    )
    by_source = await get_pool().fetch(
        "SELECT source, COUNT(*) AS cnt FROM scans WHERE api_key_id = $1 GROUP BY source",
        api_key_id,
    )
    return {
        "total_scans": row["total_scans"] or 0,
        "scans_this_month": row["scans_this_month"] or 0,
        "avg_processing_ms": row["avg_processing_ms"] or 0,
        "accuracy": round((row["avg_confidence"] or 0) * 100, 1),
        "by_type": {r["doc_type"]: r["cnt"] for r in by_type},
        "by_source": {r["source"]: r["cnt"] for r in by_source},
    }


async def ensure_schema():
    pool = get_pool()
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await pool.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    await pool.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id)")
    await pool.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS webhook_url TEXT")


async def create_user(name: str, email: str, password_hash: str) -> dict:
    row = await get_pool().fetchrow(
        """
        INSERT INTO users (name, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id, name, email, created_at
        """,
        name, email, password_hash,
    )
    return dict(row)


async def get_user_by_email(email: str) -> Optional[dict]:
    row = await get_pool().fetchrow(
        "SELECT id, name, email, password_hash, created_at FROM users WHERE email = $1",
        email,
    )
    return dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    row = await get_pool().fetchrow(
        "SELECT id, name, email, created_at FROM users WHERE id = $1",
        user_id,
    )
    return dict(row) if row else None


async def get_user_api_key(user_id: str) -> Optional[dict]:
    row = await get_pool().fetchrow(
        """
        SELECT id, key_prefix, name, facility_name, plan, scans_limit, is_active,
               (SELECT COUNT(*) FROM scans
                WHERE api_key_id = api_keys.id::text
                  AND created_at >= date_trunc('month', NOW())) AS scans_this_month
        FROM api_keys WHERE user_id = $1 AND is_active = true
        ORDER BY created_at ASC LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None


async def create_user_api_key(name: str, facility_name: str, plan: str, user_id: str) -> dict:
    raw = "mk_" + secrets.token_urlsafe(20)
    key_hash = _hash_key(raw)
    key_prefix = raw[:16]
    limit = PLAN_LIMITS.get(plan, 200)
    row = await get_pool().fetchrow(
        """
        INSERT INTO api_keys (key_hash, key_prefix, name, facility_name, plan, scans_limit, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, key_prefix, name, facility_name, plan, scans_limit, created_at
        """,
        key_hash, key_prefix, name, facility_name, plan, limit, user_id,
    )
    return {**dict(row), "raw_key": raw}


async def seed_demo_keys():
    existing = await get_pool().fetchval("SELECT COUNT(*) FROM api_keys")
    if existing > 0:
        return

    demo_keys = [
        ("mk_prod_demo123", "mk_prod_demo", "Produkcja Demo", "Centrum Medyk Kraków", "pro"),
        ("mk_test_dev456", "mk_test_dev4", "Development", "Wewnętrzny IKZ", "demo"),
    ]
    for raw, prefix, name, facility, plan in demo_keys:
        await get_pool().execute(
            """
            INSERT INTO api_keys (key_hash, key_prefix, name, facility_name, plan, scans_limit)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            _hash_key(raw), prefix, name, facility, plan, PLAN_LIMITS[plan],
        )
    logger.info("Demo klucze API dodane do bazy")
