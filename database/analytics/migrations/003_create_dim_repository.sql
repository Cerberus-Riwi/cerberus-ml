CREATE TABLE IF NOT EXISTS analytics.dim_repository (
    repository_key     BIGSERIAL PRIMARY KEY,

    repository_url     TEXT NOT NULL UNIQUE,

    organization       VARCHAR(255) NOT NULL,

    repository_name    VARCHAR(255) NOT NULL,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE analytics.dim_repository IS
'Dimensión de repositorios provenientes de los escaneos.';

COMMENT ON COLUMN analytics.dim_repository.repository_key IS
'Clave sustituta del repositorio.';

COMMENT ON COLUMN analytics.dim_repository.repository_url IS
'URL completa del repositorio Git analizado.';

COMMENT ON COLUMN analytics.dim_repository.organization IS
'Organización u owner del repositorio extraído desde repository_url.';

COMMENT ON COLUMN analytics.dim_repository.repository_name IS
'Nombre del repositorio extraído desde repository_url.';