# Changelog del schema OLTP — cerberus.findings

Este archivo registra cambios puntuales al schema después del diseño inicial
(`cerberus_schema_oltp_v1.sql`), para mantener trazabilidad de por qué la
base de datos se desvía del contrato `scan-result.schema.json` v1.0.0 original.

---

## [2026-07-01] Autenticación interna, repositorios favoritos y auditoría

**Motivo:** Cerberus ML incorpora autenticación propia (login de usuarios) y
un panel de administración. Se necesita persistir usuarios, sus repositorios
favoritos, y un registro de auditoría de acciones administrativas.

**Contrato de referencia:** ninguno — a diferencia del resto del schema OLTP,
estas tablas no derivan de `scan-*.schema.json`; son funcionalidad propia de
Cerberus ML no relacionada con los contratos de SecurityGate.

### Cambios aplicados

```sql
-- Ver database/init/005_create_users_and_audit.sql para el detalle completo
CREATE TABLE cerberus.users (...);
CREATE TABLE cerberus.user_repositories (...);
ALTER TABLE cerberus.scan_requests ADD COLUMN user_id UUID REFERENCES cerberus.users(id);
CREATE TABLE cerberus.audit_log (...);
```

### Impacto en el modelo

| Tabla | Cambio |
|---|---|
| `cerberus.users` | Nueva. Usuarios internos (`role`: `user` \| `admin`, `is_active`). |
| `cerberus.user_repositories` | Nueva. Repositorios favoritos por usuario. |
| `cerberus.scan_requests` | Se agrega `user_id` (nullable, `FK → users.id`). |
| `cerberus.audit_log` | Nueva. Auditoría de acciones (`ON DELETE SET NULL` en `user_id`). |

### Nota de seguimiento

Este cambio se ejecutó primero directamente sobre la base de datos y luego
se formalizó como migración versionada. Al formalizarlo se agregaron además
(no estaban en la ejecución original):

* `CHECK (role IN ('user','admin'))` en `users.role`.
* `CHECK` de formato GitHub en `user_repositories.github_url`, igual al que
  ya existía en `scan_requests.repository_url`.
* Índices en las nuevas columnas/tablas con FK (`user_id` en `scan_requests`,
  `user_repositories` y `audit_log`).
* `ON DELETE SET NULL` explícito en `audit_log.user_id`.

> **Pendiente de seguimiento:** actualizar `docs/ARCHITECTURE.md` para
> reflejar que este servicio ahora también persiste autenticación, y
> regenerar el diagrama ER (`database/diagrams/cerberus_er_oltp_diagram.png`).
>
> **Pendiente de seguimiento:** `consumer/db_writer.py` todavía no popula
> `scan_requests.user_id` al insertar — ningún escaneo queda vinculado a un
> usuario hasta que se actualice ese flujo.

---

## [2026-06-XX] Soporte para findings de tipo DAST/ZAP sin filePath

**Solicitado por:** Luis Miguel (VulnerabilityService)
**Motivo:** Las herramientas de análisis dinámico (DAST), como OWASP ZAP,
no siempre pueden asociar un hallazgo a un archivo y línea específicos del
código fuente — en su lugar, identifican el problema por una URL de la
aplicación en ejecución (ej. un endpoint vulnerable a XSS).

**Contrato de referencia:** Este cambio está respaldado por la actualización
del contrato `scan-result.schema.json` a la versión **v1.1.0** (aprobada por
Ximena Jaramillo, líder técnica), donde `filePath` pasa a ser opcional para
findings de origen DAST.

> Ver el changelog/tag correspondiente en el repositorio `cerberus-contracts`
> para el detalle exacto del cambio en el contrato.

### Cambios aplicados a `cerberus.findings`

```sql
-- 1. Permitir que file_path sea NULL (para findings de ZAP)
ALTER TABLE cerberus.findings
ALTER COLUMN file_path DROP NOT NULL;

-- 2. Agregar la columna location_url (para findings de ZAP)
ALTER TABLE cerberus.findings
ADD COLUMN location_url TEXT NULL;
```

### Regla de negocio resultante

Cada finding debe tener **al menos uno** de los dos campos de ubicación:

- `file_path` — para findings de origen estático (SAST), ej. Semgrep, Trivy, Gitleaks, Sonar
- `location_url` — para findings de origen dinámico (DAST), ej. OWASP ZAP

> **Nota de seguimiento:** actualmente la base de datos no impone esta regla
> con un `CHECK` (ej. `CHECK (file_path IS NOT NULL OR location_url IS NOT NULL)`).
> Se recomienda agregarlo en una migración posterior para evitar findings sin
> ninguna ubicación, lo cual no tendría sentido funcional.

### Impacto en el modelo

| Campo | Antes (v1.0.0) | Ahora (v1.1.0) |
|---|---|---|
| `file_path` | Obligatorio (`NOT NULL`) | Opcional — obligatorio solo para findings SAST |
| `location_url` | No existía | Opcional — usado por findings DAST (ZAP) |