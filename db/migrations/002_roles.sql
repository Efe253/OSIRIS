-- OSIRIS — Migration 002: roller, API anahtarları, graf kalıcılığı
-- Faz 5 Paket 2+3 (RBAC + graf kenarları). Yalnızca yeni tablolar — geri alınabilir.
-- Bkz. doküman §10.3 (RBAC) ve §5.5 (graf motoru).

-- ============================================================
-- Roller (kullanıcı kimlikleri). Tekrar çalıştırılabilirlik için korumalı.
-- ============================================================
DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer');
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE 'type exists: %', 'user_role';
END
$$;

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT NOT NULL UNIQUE,
    role        user_role NOT NULL DEFAULT 'viewer',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- API anahtarları (yalnızca SHA-256 özeti saklanır, ham değer ASLA)
-- ============================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash    CHAR(64) NOT NULL UNIQUE,
    key_prefix  CHAR(8) NOT NULL,          -- tanımlama için ilk 8 karakter
    name        TEXT,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash);

-- ============================================================
-- Graf kenarları (bellek-içi grafın kalıcı karşılığı)
-- Düğümler isimle tutulur; entity UUID eşleşmesi uygulama katmanında.
-- ============================================================
CREATE TABLE IF NOT EXISTS graph_edges (
    source_name     TEXT NOT NULL,
    target_name     TEXT NOT NULL,
    relation_type   TEXT NOT NULL DEFAULT 'related',
    weight          FLOAT NOT NULL DEFAULT 1.0,
    evidence_count  INTEGER NOT NULL DEFAULT 1,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_name, target_name, relation_type),
    CHECK (source_name <> target_name),
    CHECK (char_length(source_name) BETWEEN 1 AND 500),
    CHECK (char_length(target_name) BETWEEN 1 AND 500)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges (source_name);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges (target_name);
