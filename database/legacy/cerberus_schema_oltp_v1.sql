-- =====================================================================
-- CERBERUS - Diseño inicial de base de datos OLTP
-- Basado en los contratos: scan-request, scan-result, scan-verdict (v1)
-- Motor: PostgreSQL
-- Autor: Miguel Ángel Rodríguez Cano (Data Analyst)
-- =====================================================================

-- Se recomienda crear un schema dedicado en vez de usar "public"
CREATE SCHEMA IF NOT EXISTS cerberus;
SET search_path TO cerberus;

-- =====================================================================
-- TABLA: scan_requests
-- Origen del contrato: scan-request.schema.json
-- Una fila = una solicitud de escaneo emitida por SecurityGate
-- =====================================================================
CREATE TABLE scan_requests (
    scan_id         UUID PRIMARY KEY,
    repository_url  TEXT NOT NULL
                    CHECK (repository_url ~ '^https://github\.com/.+/.+$'),
    branch          VARCHAR(255) NOT NULL CHECK (length(branch) >= 1),
    commit_hash     CHAR(40) NOT NULL
                    CHECK (commit_hash ~ '^[0-9a-f]{40}$'),
    requested_at    TIMESTAMPTZ NOT NULL,

    -- Campos de "metadata" del contrato (todos opcionales)
    pr_number       INTEGER CHECK (pr_number >= 1),
    triggered_by    VARCHAR(100),

    -- Auditoría interna (no viene del contrato, es de control propio)
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE scan_requests IS
    'Solicitudes de escaneo publicadas por SecurityGate. Inicia el flujo completo.';

-- =====================================================================
-- TABLA: scan_results
-- Origen del contrato: scan-result.schema.json
-- Una fila = el resultado de UN servicio analizador para UN escaneo.
-- Puede haber 1 o 2 filas por scan_id (vulnerability-service / codequality-service)
-- =====================================================================
CREATE TABLE scan_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id         UUID NOT NULL REFERENCES scan_requests(scan_id),
    service_id      VARCHAR(30) NOT NULL
                    CHECK (service_id IN ('vulnerability-service', 'codequality-service')),
    status          VARCHAR(10) NOT NULL
                    CHECK (status IN ('success', 'failed', 'timeout')),
    error_message   VARCHAR(500),
    completed_at    TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Regla del contrato: errorMessage obligatorio si status != success,
    -- y debe estar AUSENTE si status = success.
    CONSTRAINT chk_error_message_matches_status CHECK (
        (status = 'success' AND error_message IS NULL)
        OR
        (status IN ('failed', 'timeout') AND error_message IS NOT NULL)
    ),

    -- Protección anti-duplicado: un servicio no debe reportar
    -- dos veces el mismo escaneo (RabbitMQ puede reentregar mensajes)
    CONSTRAINT uq_scan_service UNIQUE (scan_id, service_id)
);

COMMENT ON TABLE scan_results IS
    'Resultado de un análisis por servicio (Vulnerability o CodeQuality) para un escaneo dado.';

-- =====================================================================
-- TABLA: findings
-- Origen del contrato: scan-result.schema.json -> findings[]
-- Una fila = un hallazgo individual dentro de un scan_result
-- =====================================================================
CREATE TABLE findings (
    id              UUID PRIMARY KEY,  -- viene del contrato, generado por el servicio analizador
    scan_result_id  UUID NOT NULL REFERENCES scan_results(id) ON DELETE CASCADE,
    severity        VARCHAR(10) NOT NULL
                    CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title           VARCHAR(200) NOT NULL CHECK (length(title) >= 1),
    description     VARCHAR(2000),
    rule_id         VARCHAR(100) NOT NULL CHECK (length(rule_id) >= 1),
    file_path       TEXT NOT NULL CHECK (length(file_path) >= 1),
    line_start      INTEGER CHECK (line_start >= 1),
    line_end        INTEGER CHECK (line_end >= 1),
    recommendation  VARCHAR(1000),

    -- Regla del contrato: lineEnd >= lineStart (cuando ambos existen)
    CONSTRAINT chk_line_range CHECK (
        line_start IS NULL OR line_end IS NULL OR line_end >= line_start
    )
);

COMMENT ON TABLE findings IS
    'Hallazgos individuales de seguridad/calidad detectados por los servicios analizadores.';

-- =====================================================================
-- TABLA: scan_verdicts
-- Origen del contrato: scan-verdict.schema.json
-- Una fila = el veredicto final consolidado de un escaneo.
-- NOTA: el campo "results" del contrato (que incluye los scan-result
-- completos) NO se duplica aquí; ya existen en scan_results/findings.
-- Esta tabla solo guarda lo que es propio del veredicto.
-- =====================================================================
CREATE TABLE scan_verdicts (
    scan_id             UUID PRIMARY KEY REFERENCES scan_requests(scan_id),
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

COMMENT ON TABLE scan_verdicts IS
    'Veredicto final consolidado por SecurityGate. Determina pass/warning/fail y el rollback.';

-- =====================================================================
-- ÍNDICES
-- Pensados para los patrones de consulta más probables:
-- buscar por severidad, por archivo, por rango de fechas, por repo.
-- =====================================================================

-- Findings: tus análisis (clustering, KPIs) van a filtrar mucho por severidad y regla
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_rule_id ON findings(rule_id);
CREATE INDEX idx_findings_scan_result_id ON findings(scan_result_id);

-- Scan results: para encontrar resultados de un escaneo rápido
CREATE INDEX idx_scan_results_scan_id ON scan_results(scan_id);

-- Scan requests: filtros típicos de dashboards (por repo, por fecha)
CREATE INDEX idx_scan_requests_repository_url ON scan_requests(repository_url);
CREATE INDEX idx_scan_requests_requested_at ON scan_requests(requested_at);

-- Scan verdicts: tendencias en el tiempo y por tipo de veredicto
CREATE INDEX idx_scan_verdicts_verdict ON scan_verdicts(verdict);
CREATE INDEX idx_scan_verdicts_issued_at ON scan_verdicts(issued_at);

-- =====================================================================
-- FIN DEL SCRIPT
-- =====================================================================
