-- =============================================================================
-- CERBERUS ANALYTICS
-- Migration: 001_create_schema.sql
-- Description:
--   Crea el esquema analítico que almacenará el Data Mart utilizado
--   por los procesos ELT y los dashboards de Power BI.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

COMMENT ON SCHEMA analytics IS
'Data Mart analítico de Cerberus utilizado para reporting, KPIs y Power BI.';