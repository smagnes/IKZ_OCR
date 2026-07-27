CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id VARCHAR(50) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    doc_type_label VARCHAR(100),
    patient VARCHAR(200),
    pesel_masked VARCHAR(20),
    doctor VARCHAR(200),
    facility VARCHAR(200),
    exam_date VARCHAR(20),
    fields JSONB DEFAULT '{}',
    alerts TEXT[] DEFAULT '{}',
    raw_text TEXT,
    confidence_overall FLOAT,
    processing_time_ms INTEGER,
    ikz_silos_id VARCHAR(50),
    ikz_examination_id INTEGER,
    source VARCHAR(50) DEFAULT 'api',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_api_key    ON scans(api_key_id);
CREATE INDEX IF NOT EXISTS idx_scans_doc_type   ON scans(doc_type);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    facility_name VARCHAR(200) NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    scans_limit INTEGER DEFAULT 200,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    plan VARCHAR(50) DEFAULT 'starter',
    mrr INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'trial',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Demo keys are seeded by Python app on startup (db.seed_demo_keys)
-- so that the hash matches the Python hashlib.sha256 implementation.
