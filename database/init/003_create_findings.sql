CREATE TABLE IF NOT EXISTS cerberus.findings (
    id              UUID PRIMARY KEY,  -- viene del contrato, generado por el servicio analizador
    scan_result_id  UUID NOT NULL REFERENCES cerberus.scan_results(id) ON DELETE CASCADE,
    severity        VARCHAR(10) NOT NULL
                     CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title           VARCHAR(200) NOT NULL CHECK (length(title) >= 1),
    description     VARCHAR(2000),
    rule_id         VARCHAR(100) NOT NULL CHECK (length(rule_id) >= 1),

    -- file_path: obligatorio para findings SAST (Semgrep, Trivy, Gitleaks, Sonar)
    -- Nullable desde v1.1.0 del contrato para permitir findings DAST sin archivo
    file_path       TEXT,

    line_start      INTEGER CHECK (line_start >= 1),
    line_end        INTEGER CHECK (line_end >= 1),
    recommendation  VARCHAR(1000),

    -- location_url: usado por findings DAST (OWASP ZAP) en vez de file_path.
    -- Agregado en v1.1.0 del contrato (solicitado por Luis Miguel).
    location_url    TEXT,

    -- Regla del contrato: lineEnd >= lineStart (cuando ambos existen)
    CONSTRAINT chk_line_range CHECK (
        line_start IS NULL OR line_end IS NULL OR line_end >= line_start
    )

    -- PENDIENTE (en discusión con Luis Miguel / Ximena):
    -- CONSTRAINT chk_has_location CHECK (file_path IS NOT NULL OR location_url IS NOT NULL)
);

COMMENT ON TABLE cerberus.findings IS
    'Hallazgos individuales de seguridad/calidad detectados por los servicios analizadores.';

CREATE INDEX IF NOT EXISTS idx_findings_severity ON cerberus.findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_rule_id ON cerberus.findings(rule_id);
CREATE INDEX IF NOT EXISTS idx_findings_scan_result_id ON cerberus.findings(scan_result_id);
