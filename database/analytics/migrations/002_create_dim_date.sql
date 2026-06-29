-- =============================================================================
-- CERBERUS ANALYTICS
-- Migration: 002_create_dim_date.sql
-- Description:
--   Crea la dimensión de fechas utilizada por el Data Mart.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key        INTEGER PRIMARY KEY,
    full_date       DATE NOT NULL UNIQUE,

    day_number      SMALLINT NOT NULL CHECK (day_number BETWEEN 1 AND 31),
    day_name        VARCHAR(10) NOT NULL,

    week_number     SMALLINT NOT NULL CHECK (week_number BETWEEN 1 AND 53),

    month_number    SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    month_name      VARCHAR(15) NOT NULL,

    quarter_number  SMALLINT NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),

    year_number     INTEGER NOT NULL,

    is_weekend      BOOLEAN NOT NULL
);

COMMENT ON TABLE analytics.dim_date IS
'Dimensión de fechas para consultas analíticas y dashboards.';

COMMENT ON COLUMN analytics.dim_date.date_key IS
'Clave sustituta en formato YYYYMMDD.';