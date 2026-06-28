-- =====================================================================
-- Migración 004 — Tabla scan_verdicts
-- Origen del contrato: scan-verdict.schema.json (v1.0.0)
-- Una fila = el veredicto final consolidado de un escaneo.
--
-- Orden de ejecución: 001 -> 002 -> 003 -> 004 -> (005 analytics, futuro)
-- Requiere que 001_create_scans.sql se haya ejecutado primero (FK a scan_requests)
--
-- NOTA: el campo "results" del contrato (que incluye los scan-result
-- completos) NO se duplica aquí; ya existen en scan_results/findings.
-- Esta tabla solo guarda lo que es propio del veredicto.
-- =====================================================================

CREATE TABLE IF NOT EXISTS cerberus.scan_verdicts (
    scan_id             UUID PRIMARY KEY REFERENCES cerberus.scan_requests(scan_id),
    verdict             VARCHAR(10) NOT NULL
                        CHECK (verdict IN ('pass', 'fail', 'warning')),

    -- Campos de "summary" aplanados como columnas (útiles para KPIs)
    critical_count      INTEGER NOT NULL CHECK (critical_count >= 0),
    high_count          INTEGER NOT NULL CHECK (high_count >= 0),
    medium_count        INTEGER NOT NULL CHECK (medium_count >= 0),
    low_count           INTEGER NOT NULL CHECK (low_count >= 0),
    info_count          INTEGER NOT NULL CHECK (info_count >= 0),

    rollback_triggered  BOOLEAN NOT NULL,
    issued_at           TIMESTAMPTZ NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Regla del contrato: verdict y los conteos deben ser consistentes
    CONSTRAINT chk_verdict_matches_counts CHECK (
        (verdict = 'fail' AND (critical_count > 0 OR high_count > 0))
        OR
        (verdict = 'warning' AND critical_count = 0 AND high_count = 0
            AND (medium_count > 0 OR low_count > 0))
        OR
        (verdict = 'pass' AND critical_count = 0 AND high_count = 0
            AND medium_count = 0 AND low_count = 0)
    ),

    -- Regla del contrato: rollback solo puede ser true si verdict = fail
    CONSTRAINT chk_rollback_only_on_fail CHECK (
        rollback_triggered = FALSE OR verdict = 'fail'
    )
);

COMMENT ON TABLE cerberus.scan_verdicts IS
    'Veredicto final consolidado por SecurityGate. Determina pass/warning/fail y el rollback.';

CREATE INDEX IF NOT EXISTS idx_scan_verdicts_verdict ON cerberus.scan_verdicts(verdict);
CREATE INDEX IF NOT EXISTS idx_scan_verdicts_issued_at ON cerberus.scan_verdicts(issued_at);
