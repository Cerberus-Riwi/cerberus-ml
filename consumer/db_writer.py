"""
db_writer.py — Inserción de un QualityGateResult en las 4 tablas de cerberus.

Recibe el dict deserializado del mensaje RabbitMQ y lo persiste en:
    cerberus.scan_requests   (upsert — puede llegar más de una vez)
    cerberus.scan_results    (upsert por scan_id + service_id)
    cerberus.findings        (insert — gen_random_uuid() porque el mensaje no trae id)
    cerberus.scan_verdicts   (upsert por scan_id)

Reutilizable tanto desde el consumer como desde scripts de prueba.
"""

import uuid
import logging

import psycopg

logger = logging.getLogger(__name__)


def empty_to_none(value):
    """Convierte string vacío a None (mismo patrón que load_data_demo.py)."""
    return None if value == "" or value is None else value


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
    Nota: findings no traen id — se genera con uuid4() aquí.
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

            # Findings — el mensaje no trae id, se genera aquí
            for finding in result.get("findings", []):
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
                        "id":             str(uuid.uuid4()),
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
