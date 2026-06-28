# Changelog del schema OLTP — cerberus.findings

Este archivo registra cambios puntuales al schema después del diseño inicial
(`cerberus_schema_oltp_v1.sql`), para mantener trazabilidad de por qué la
base de datos se desvía del contrato `scan-result.schema.json` v1.0.0 original.

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
