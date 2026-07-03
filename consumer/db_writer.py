import uuid
import logging

import psycopg

logger = logging.getLogger(__name__)

# Namespace fijo para generar UUIDs determinísticos de findings.
# NO cambiar este valor una vez en producción — cambiarlo generaría
# IDs distintos para los mismos findings y rompería la deduplicación
# de los que ya existen en la base.
FINDING_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")


def empty_to_none(value):
    """Convierte string vacío a None (mismo patrón que load_data_demo.py)."""
    return None if value == "" or value is None else value


def make_finding_id(scan_result_id: str, finding: dict) -> str:
    """
    Genera un UUID determinístico para un finding, a partir de los campos
    que lo identifican de forma única dentro de un scan_result.

    Por qué determinístico y no uuid4() aleatorio:
    QualityGate reentrega el mismo mensaje más de una vez (redelivery de
    RabbitMQ, reinicios del consumer, etc.), y el contrato no incluye un
    id propio por finding. Con uuid4() cada intento generaba un id nuevo,
    así que el ON CONFLICT (id) DO NOTHING nunca detectaba el duplicado
    porque el id nunca coincidía con el de un intento anterior.

    uuid5() con un namespace fijo genera SIEMPRE el mismo UUID para la
    misma combinación de (scan_result_id, rule_id, file_path, line_start,
    line_end) — así el ON CONFLICT sí puede reconocer un finding repetido
    y descartarlo correctamente, sin duplicar filas.
    """
    key = "|".join([
        str(scan_result_id),
        finding.get("ruleId", ""),
        finding.get("filePath") or "",
        str(finding.get("lineStart") or ""),
        str(finding.get("lineEnd") or ""),
    ])
    return str(uuid.uuid5(FINDING_NAMESPACE, key))


def insert_verdict(verdict: dict, conn: psycopg.Connection) -> None:
    """
    Persiste un QualityGateResult completo en la BD dentro de una transacción.

    Estructura esperada del dict (campos del QualityGateResult de cerberus-qualitygate):
    {
        "scanId":            "uuid-string",
        "verdict":           "pass" | "warning" | "fail",
        "summary": {
            "critical": int,
            "high":     int,
            "medium":   int,
            "low":      int,
            "info":     int
        },
        "results": [
            {
                "scanId":     "uuid-string",
                "serviceId":  "vulnerability-service" | "codequality-service",
                "status":     "success" | "failed" | "timeout",
                "errorMessage": str | null,
                "completedAt": "iso-datetime",
                "findings": [
                    {
                        "severity":       "critical"|"high"|"medium"|"low"|"info",
                        "title":          str,
                        "description":    str | null,
                        "ruleId":         str,
                        "filePath":       str | null,
                        "lineStart":      int | null,
                        "lineEnd":        int | null,
                        "recommendation": str | null
                    }
                ]
            }
        ],
        "rollbackTriggered": bool,
        "issuedAt":          "iso-datetime"
    }

    Nota: DeploymentId tiene [JsonIgnore] en C# — no llega en el mensaje.
    Nota: findings no traen id — se genera determinísticamente con
    make_finding_id() para que la deduplicación funcione ante reentregas.
    """
    scan_id = verdict["scanId"]
    summary = verdict.get("summary", {})
    results = verdict.get("results", [])

    with conn.transaction():
        cur = conn.cursor()

        # ── 1. scan_requests ──────────────────────────────────────────────────
        # El mensaje de QualityGate no trae los campos del scan request original
        # (repository_url, branch, commit_hash, etc.) — esos llegan por el flujo
        # de SecurityGate. Hacemos un INSERT ... DO NOTHING para registrar el
        # scan_id si no existe, con valores mínimos válidos.
        # En producción, scan_requests ya existirá (creado por SecurityGate antes);
        # este upsert es una red de seguridad para el caso de mensajes fuera de orden.
        cur.execute(
            """
            INSERT INTO cerberus.scan_requests
                (scan_id, repository_url, branch, commit_hash, requested_at)
            VALUES (%(scan_id)s, 'https://github.com/cerberus-riwi/unknown', 'unknown',
                    repeat('0', 40), now())
            ON CONFLICT (scan_id) DO NOTHING
            """,
            {"scan_id": scan_id},
        )

        # ── 2. scan_results + findings ────────────────────────────────────────
        for result in results:
            service_id   = result["serviceId"]
            status       = result["status"]
            error_msg    = empty_to_none(result.get("errorMessage"))
            completed_at = result["completedAt"]

            # Upsert scan_result (RabbitMQ puede reentregar el mismo mensaje)
            cur.execute(
                """
                INSERT INTO cerberus.scan_results
                    (scan_id, service_id, status, error_message, completed_at)
                VALUES (%(scan_id)s, %(service_id)s, %(status)s,
                        %(error_message)s, %(completed_at)s)
                ON CONFLICT (scan_id, service_id)
                    DO UPDATE SET
                        status        = EXCLUDED.status,
                        error_message = EXCLUDED.error_message,
                        completed_at  = EXCLUDED.completed_at
                RETURNING id
                """,
                {
                    "scan_id":       scan_id,
                    "service_id":    service_id,
                    "status":        status,
                    "error_message": error_msg,
                    "completed_at":  completed_at,
                },
            )
            scan_result_id = cur.fetchone()[0]

            # Findings — el mensaje no trae id, se genera de forma
            # DETERMINÍSTICA (no aleatoria) para que las reentregas de
            # RabbitMQ no generen filas duplicadas.
            for finding in result.get("findings", []):
                finding_id = make_finding_id(scan_result_id, finding)
                cur.execute(
                    """
                    INSERT INTO cerberus.findings
                        (id, scan_result_id, severity, title, description,
                         rule_id, file_path, line_start, line_end, recommendation)
                    VALUES (%(id)s, %(scan_result_id)s, %(severity)s, %(title)s,
                            %(description)s, %(rule_id)s, %(file_path)s,
                            %(line_start)s, %(line_end)s, %(recommendation)s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {
                        "id":             finding_id,
                        "scan_result_id": scan_result_id,
                        "severity":       finding["severity"],
                        "title":          finding["title"],
                        "description":    empty_to_none(finding.get("description")),
                        "rule_id":        finding["ruleId"],
                        "file_path":      empty_to_none(finding.get("filePath")),
                        "line_start":     finding.get("lineStart"),
                        "line_end":       finding.get("lineEnd"),
                        "recommendation": empty_to_none(finding.get("recommendation")),
                    },
                )

        # ── 3. scan_verdicts ──────────────────────────────────────────────────
        cur.execute(
            """
            INSERT INTO cerberus.scan_verdicts
                (scan_id, verdict, critical_count, high_count, medium_count,
                 low_count, info_count, rollback_triggered, issued_at)
            VALUES (%(scan_id)s, %(verdict)s, %(critical)s, %(high)s, %(medium)s,
                    %(low)s, %(info)s, %(rollback_triggered)s, %(issued_at)s)
            ON CONFLICT (scan_id)
                DO UPDATE SET
                    verdict            = EXCLUDED.verdict,
                    critical_count     = EXCLUDED.critical_count,
                    high_count         = EXCLUDED.high_count,
                    medium_count       = EXCLUDED.medium_count,
                    low_count          = EXCLUDED.low_count,
                    info_count         = EXCLUDED.info_count,
                    rollback_triggered = EXCLUDED.rollback_triggered,
                    issued_at          = EXCLUDED.issued_at
            """,
            {
                "scan_id":           scan_id,
                "verdict":           verdict["verdict"],
                "critical":          summary.get("critical", 0),
                "high":              summary.get("high", 0),
                "medium":            summary.get("medium", 0),
                "low":               summary.get("low", 0),
                "info":              summary.get("info", 0),
                "rollback_triggered": verdict.get("rollbackTriggered", False),
                "issued_at":         verdict["issuedAt"],
            },
        )

        logger.info(
            "scan_id=%s verdict=%s results=%d",
            scan_id,
            verdict["verdict"],
            len(results),
        )