-- =============================================================================
-- CERBERUS ANALYTICS
-- Migration: 005_create_dim_severity.sql
-- Description:
--   Dimensión de severidades utilizada para el análisis de findings.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_severity (
    severity_key    SMALLSERIAL PRIMARY KEY,

    severity_name   VARCHAR(10) NOT NULL UNIQUE
                    CHECK (severity_name IN ('critical', 'high', 'medium', 'low', 'info')),

    priority        SMALLINT NOT NULL UNIQUE
                    CHECK (priority BETWEEN 1 AND 5),

    color           VARCHAR(20) NOT NULL,

    sla_days        INTEGER,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE analytics.dim_severity IS
'Dimensión de severidad utilizada para análisis y visualización de findings.';

COMMENT ON COLUMN analytics.dim_severity.severity_key IS
'Clave sustituta de la severidad.';

COMMENT ON COLUMN analytics.dim_severity.severity_name IS
'Nombre de la severidad.';

COMMENT ON COLUMN analytics.dim_severity.priority IS
'Prioridad utilizada para ordenar visualizaciones y reportes.';

COMMENT ON COLUMN analytics.dim_severity.color IS
'Color sugerido para dashboards.';

COMMENT ON COLUMN analytics.dim_severity.sla_days IS
'SLA sugerido para la corrección de findings según su severidad.';