CREATE TABLE IF NOT EXISTS cerberus.scan_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id         UUID NOT NULL REFERENCES cerberus.scan_requests(scan_id),
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

COMMENT ON TABLE cerberus.scan_results IS
    'Resultado de un análisis por servicio (Vulnerability o CodeQuality) para un escaneo dado.';

CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON cerberus.scan_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_status ON cerberus.scan_results(status);
