CREATE SCHEMA IF NOT EXISTS cerberus;

CREATE TABLE IF NOT EXISTS cerberus.scan_requests (
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

COMMENT ON TABLE cerberus.scan_requests IS
    'Solicitudes de escaneo publicadas por SecurityGate. Inicia el flujo completo.';

CREATE INDEX IF NOT EXISTS idx_scan_requests_repository_url ON cerberus.scan_requests(repository_url);
CREATE INDEX IF NOT EXISTS idx_scan_requests_requested_at ON cerberus.scan_requests(requested_at);
