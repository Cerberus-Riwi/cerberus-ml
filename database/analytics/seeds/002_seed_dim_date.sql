-- =============================================================================
-- CERBERUS ANALYTICS
-- Seed: 002_seed_dim_date.sql
-- Description:
--   Genera automáticamente la dimensión de fechas.
-- =============================================================================

INSERT INTO analytics.dim_date (
    date_key,
    full_date,
    day_number,
    day_name,
    week_number,
    month_number,
    month_name,
    quarter_number,
    year_number,
    is_weekend
)
SELECT
    TO_CHAR(d::date, 'YYYYMMDD')::INTEGER,
    d::date,
    EXTRACT(DAY FROM d)::SMALLINT,
    TO_CHAR(d::date, 'FMDay'),
    EXTRACT(WEEK FROM d)::SMALLINT,
    EXTRACT(MONTH FROM d)::SMALLINT,
    TO_CHAR(d::date, 'FMMonth'),
    EXTRACT(QUARTER FROM d)::SMALLINT,
    EXTRACT(YEAR FROM d)::INTEGER,
    CASE
        WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE
        ELSE FALSE
    END
FROM generate_series(
    DATE '2020-01-01',
    DATE '2035-12-31',
    INTERVAL '1 day'
) AS gs(d)
ON CONFLICT (full_date)
DO NOTHING;