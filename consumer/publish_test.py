"""
publish_test.py — Publica un QualityGateResult de prueba al exchange de RabbitMQ.

Permite probar el consumer localmente sin necesitar que cerberus-qualitygate
esté corriendo. El mensaje replica exactamente el contrato del C#.

Uso:
    python publish_test.py
    python publish_test.py --verdict warning
    python publish_test.py --verdict pass --no-findings

Variables de entorno (desde .env):
    RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT
"""

import argparse
import json
import os
import uuid
from datetime import datetime, timezone

import pika
from dotenv import load_dotenv

load_dotenv()

EXCHANGE = "cerberus.scan.verdicts"


def build_message(verdict_value: str, include_findings: bool) -> dict:
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    findings_vuln = []
    findings_cq   = []

    if include_findings and verdict_value == "fail":
        findings_vuln = [
            {
                "severity":       "critical",
                "title":          "SQL Injection detectado en parámetro de búsqueda",
                "description":    "El parámetro 'q' se concatena directamente al query sin sanitización.",
                "ruleId":         "semgrep.CWE-089",
                "filePath":       "src/Controllers/SearchController.cs",
                "lineStart":      42,
                "lineEnd":        42,
                "recommendation": "Usar consultas parametrizadas con Entity Framework.",
            },
            {
                "severity":       "high",
                "title":          "Dependencia con vulnerabilidad conocida",
                "description":    "Newtonsoft.Json 12.0.1 tiene CVE-2024-21907.",
                "ruleId":         "trivy.CVE-2024-21907",
                "filePath":       None,
                "lineStart":      None,
                "lineEnd":        None,
                "recommendation": "Actualizar a Newtonsoft.Json >= 13.0.3.",
            },
        ]
        findings_cq = [
            {
                "severity":       "medium",
                "title":          "Método con complejidad ciclomática alta",
                "description":    "El método ProcessRequest tiene CC=18, supera el umbral de 10.",
                "ruleId":         "sonar.S3776",
                "filePath":       "src/Services/ProcessingService.cs",
                "lineStart":      87,
                "lineEnd":        145,
                "recommendation": "Dividir el método en funciones más pequeñas.",
            },
        ]
    elif include_findings and verdict_value == "warning":
        findings_vuln = [
            {
                "severity":       "medium",
                "title":          "Cookie sin flag HttpOnly",
                "description":    "La cookie de sesión no tiene HttpOnly, expuesta a XSS.",
                "ruleId":         "semgrep.CWE-1004",
                "filePath":       "src/Startup.cs",
                "lineStart":      33,
                "lineEnd":        33,
                "recommendation": "Agregar HttpOnly=true en la configuración de cookies.",
            },
        ]

    # Summary calculado a partir de findings
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings_vuln + findings_cq:
        severity_counts[f["severity"]] += 1

    rollback = verdict_value == "fail" and severity_counts["critical"] > 0

    return {
        "scanId":  scan_id,
        "verdict": verdict_value,
        "summary": {
            "critical": severity_counts["critical"],
            "high":     severity_counts["high"],
            "medium":   severity_counts["medium"],
            "low":      severity_counts["low"],
            "info":     severity_counts["info"],
        },
        "results": [
            {
                "scanId":       scan_id,
                "serviceId":    "vulnerability-service",
                "status":       "success",
                "errorMessage": None,
                "completedAt":  now,
                "findings":     findings_vuln,
            },
            {
                "scanId":       scan_id,
                "serviceId":    "codequality-service",
                "status":       "success",
                "errorMessage": None,
                "completedAt":  now,
                "findings":     findings_cq,
            },
        ],
        "rollbackTriggered": rollback,
        "issuedAt": now,
    }


def main():
    parser = argparse.ArgumentParser(description="Publica un mensaje de prueba al exchange de cerberus-ml.")
    parser.add_argument("--verdict", choices=["pass", "warning", "fail"], default="fail")
    parser.add_argument("--no-findings", action="store_true", help="Publicar sin findings")
    args = parser.parse_args()

    for var in ("RABBITMQ_USER", "RABBITMQ_PASSWORD"):
        if not os.environ.get(var):
            raise SystemExit(f"Falta variable de entorno: {var}")

    message = build_message(args.verdict, include_findings=not args.no_findings)

    params = pika.ConnectionParameters(
        host=os.environ.get("RABBITMQ_HOST", "localhost"),
        port=int(os.environ.get("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            os.environ["RABBITMQ_USER"],
            os.environ["RABBITMQ_PASSWORD"],
        ),
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)

    body = json.dumps(message, default=str)
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key="",
        body=body,
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # persistent
        ),
    )

    connection.close()

    print(f"✓ Mensaje publicado al exchange '{EXCHANGE}'")
    print(f"  scan_id : {message['scanId']}")
    print(f"  verdict : {message['verdict']}")
    print(f"  findings: {sum(len(r['findings']) for r in message['results'])}")
    print(f"  rollback: {message['rollbackTriggered']}")
    print()
    print("Payload completo:")
    print(json.dumps(message, indent=2, default=str))


if __name__ == "__main__":
    main()
