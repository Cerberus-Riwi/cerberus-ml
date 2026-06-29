-- =============================================================================
-- CERBERUS ANALYTICS
-- Migration: 004_create_dim_rule.sql
-- Description:
--   Dimensión de reglas detectadas durante los escaneos.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_rule (
    rule_key            BIGSERIAL PRIMARY KEY,

    rule_id             VARCHAR(100) NOT NULL UNIQUE,

    title               VARCHAR(200) NOT NULL,

    description         TEXT,

    recommendation      TEXT,

    category            VARCHAR(100),

    cwe                 VARCHAR(50),

    owasp               VARCHAR(50),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE analytics.dim_rule IS
'Dimensión de reglas de seguridad y calidad detectadas por los motores de análisis.';

COMMENT ON COLUMN analytics.dim_rule.rule_key IS
'Clave sustituta de la regla.';

COMMENT ON COLUMN analytics.dim_rule.rule_id IS
'Identificador único de la regla proveniente del motor de análisis.';

COMMENT ON COLUMN analytics.dim_rule.title IS
'Título corto de la regla.';

COMMENT ON COLUMN analytics.dim_rule.description IS
'Descripción de la regla.';

COMMENT ON COLUMN analytics.dim_rule.recommendation IS
'Recomendación para corregir el hallazgo.';

COMMENT ON COLUMN analytics.dim_rule.category IS
'Categoría funcional de la regla (opcional).';

COMMENT ON COLUMN analytics.dim_rule.cwe IS
'Identificador CWE asociado a la regla (opcional).';

COMMENT ON COLUMN analytics.dim_rule.owasp IS
'Categoría OWASP asociada a la regla (opcional).';