-- supabase_schema.sql
-- Run this ONCE in your Supabase project → SQL Editor.
-- It creates all tables used by ICSS.
-- NOTE: The crowd_metrics table uses a "timestamp" column (NOT "created_at").

-- ═══════════════════════════════════════════════════════════
-- TABLE: crowd_metrics  (primary analytics store)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS crowd_metrics (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp       TIMESTAMPTZ  DEFAULT NOW(),
    people_count    INT          NOT NULL DEFAULT 0,
    density         FLOAT8       NOT NULL DEFAULT 0.0,
    flow_direction  TEXT         NOT NULL DEFAULT 'Unknown',
    risk_level      TEXT         NOT NULL DEFAULT 'Normal',
    crowd_level     TEXT                  DEFAULT 'Low',
    peak_count      INT                   DEFAULT 0,
    average_count   FLOAT8                DEFAULT 0.0
);

-- Index for fast time-ordered queries
CREATE INDEX IF NOT EXISTS idx_crowd_metrics_timestamp
    ON crowd_metrics (timestamp DESC);

-- Enable Row Level Security (safe default)
ALTER TABLE crowd_metrics ENABLE ROW LEVEL SECURITY;

-- Allow the anon key to read and insert rows
CREATE POLICY "anon_read"   ON crowd_metrics FOR SELECT USING (true);
CREATE POLICY "anon_insert" ON crowd_metrics FOR INSERT WITH CHECK (true);


-- ═══════════════════════════════════════════════════════════
-- TABLE: alerts  (crowd alert events)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS alerts (
    id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ  DEFAULT NOW(),
    message   TEXT         NOT NULL,
    status    TEXT         NOT NULL DEFAULT 'active',   -- 'active' | 'resolved'
    severity  TEXT         NOT NULL DEFAULT 'HIGH'      -- 'HIGH' | 'CRITICAL' | 'MEDIUM'
);

-- Index for fast time-ordered queries
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
    ON alerts (timestamp DESC);

-- Enable Row Level Security
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Allow the anon key to read and insert rows
CREATE POLICY "alerts_anon_read"   ON alerts FOR SELECT USING (true);
CREATE POLICY "alerts_anon_insert" ON alerts FOR INSERT WITH CHECK (true);
