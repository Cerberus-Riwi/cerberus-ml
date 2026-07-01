CREATE TABLE IF NOT EXISTS cerberus.users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'user'
                  CHECK (role IN ('user', 'admin')),
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

COMMENT ON TABLE cerberus.users IS
    'Usuarios internos de Cerberus (auth propia). role: user | admin.';

-- ---------------------------------------------------------------------
-- Tabla user_repositories — repositorios favoritos de cada usuario
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cerberus.user_repositories (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES cerberus.users(id) ON DELETE CASCADE,
    github_url     VARCHAR(512) NOT NULL
                   CHECK (github_url ~ '^https://github\.com/.+/.+$'),
    default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, github_url)
);

COMMENT ON TABLE cerberus.user_repositories IS
    'Repositorios de GitHub marcados como favoritos por cada usuario.';

CREATE INDEX IF NOT EXISTS idx_user_repositories_user_id
    ON cerberus.user_repositories(user_id);

-- ---------------------------------------------------------------------
-- scan_requests — vínculo con el usuario que originó (o sigue) el escaneo
-- ---------------------------------------------------------------------
ALTER TABLE cerberus.scan_requests
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES cerberus.users(id);

CREATE INDEX IF NOT EXISTS idx_scan_requests_user_id
    ON cerberus.scan_requests(user_id);

-- ---------------------------------------------------------------------
-- Tabla audit_log — trazabilidad de acciones (panel de admin)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cerberus.audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES cerberus.users(id) ON DELETE SET NULL,
    action     VARCHAR(100) NOT NULL,   -- 'scan_created', 'login', 'user_suspended'...
    payload    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE cerberus.audit_log IS
    'Registro de auditoría de acciones de usuarios/admin. user_id se conserva '
    'como NULL si el usuario es eliminado, para no perder el historial.';

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON cerberus.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON cerberus.audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON cerberus.audit_log(created_at);