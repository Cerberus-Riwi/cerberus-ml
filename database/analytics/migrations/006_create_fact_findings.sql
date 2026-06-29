-- =============================================================================
-- CERBERUS ANALYTICS
-- Migration: 006_create_fact_findings.sql
-- Description:
--   Tabla de hechos del Data Mart.
--   Cada registro representa un finding detectado durante un escaneo.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.fact_findings (

    -- Clave sustituta del Data Mart
    finding_key         BIGSERIAL PRIMARY KEY,

    -- Identificador del finding en el OLTP
    finding_id          UUID NOT NULL UNIQUE,

    -- Relaciones con dimensiones
    repository_key      BIGINT NOT NULL,
    rule_key            BIGINT NOT NULL,
    severity_key        SMALLINT NOT NULL,
    date_key            INTEGER NOT NULL,

    -- Información operacional
    scan_id             UUID NOT NULL,
    scan_result_id      UUID NOT NULL,

    verdict             VARCHAR(10) NOT NULL
                        CHECK (verdict IN ('pass', 'fail', 'warning')),

    service_id          VARCHAR(30) NOT NULL,

    title               VARCHAR(200) NOT NULL,

    file_path           TEXT,

    location_url        TEXT,

    line_start          INTEGER,

    line_end            INTEGER,

    recommendation      TEXT,

    issued_at           TIMESTAMPTZ NOT NULL,

    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_fact_repository
        FOREIGN KEY (repository_key)
        REFERENCES analytics.dim_repository(repository_key),

    CONSTRAINT fk_fact_rule
        FOREIGN KEY (rule_key)
        REFERENCES analytics.dim_rule(rule_key),

    CONSTRAINT fk_fact_severity
        FOREIGN KEY (severity_key)
        REFERENCES analytics.dim_severity(severity_key),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_key)
        REFERENCES analytics.dim_date(date_key)
);

COMMENT ON TABLE analytics.fact_findings IS
'Tabla de hechos del Data Mart. Cada fila representa un finding detectado durante un escaneo.';

CREATE INDEX idx_fact_repository
ON analytics.fact_findings(repository_key);

CREATE INDEX idx_fact_rule
ON analytics.fact_findings(rule_key);

CREATE INDEX idx_fact_severity
ON analytics.fact_findings(severity_key);

CREATE INDEX idx_fact_date
ON analytics.fact_findings(date_key);

CREATE INDEX idx_fact_scan
ON analytics.fact_findings(scan_id);

CREATE INDEX idx_fact_verdict
ON analytics.fact_findings(verdict);