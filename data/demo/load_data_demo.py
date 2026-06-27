"""
Carga los CSVs de seed data (data/demo/) a PostgreSQL.
Maneja correctamente los NULL (celdas vacías -> None real, no string vacío).

Requiere un archivo .env en la raíz del proyecto con:
    PGHOST=localhost
    PGPORT=5432
    PGDATABASE=cerberus
    PGUSER=cerberus
    PGPASSWORD=tu-contraseña

Uso:
    python data/demo/load_seed_data.py
"""

import csv
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "cerberus"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
}

DATA_DIR = os.path.join(os.path.dirname(__file__))


def empty_to_none(value):
    """Convierte celdas vacías de CSV a None real (NULL en la BD)."""
    return None if value == "" else value


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k: empty_to_none(v) for k, v in row.items()} for row in reader]


def load_scan_requests(cur):
    rows = load_csv(os.path.join(DATA_DIR, "01_scan_requests.csv"))
    for r in rows:
        cur.execute(
            """
            INSERT INTO cerberus.scan_requests
                (scan_id, repository_url, branch, commit_hash, requested_at, pr_number, triggered_by)
            VALUES (%(scan_id)s, %(repository_url)s, %(branch)s, %(commit_hash)s, %(requested_at)s, %(pr_number)s, %(triggered_by)s)
            ON CONFLICT (scan_id) DO NOTHING
            """,
            r,
        )
    print(f"  scan_requests: {len(rows)} filas procesadas")


def load_scan_results(cur):
    rows = load_csv(os.path.join(DATA_DIR, "02_scan_results.csv"))
    for r in rows:
        cur.execute(
            """
            INSERT INTO cerberus.scan_results
                (id, scan_id, service_id, status, error_message, completed_at)
            VALUES (%(id)s, %(scan_id)s, %(service_id)s, %(status)s, %(error_message)s, %(completed_at)s)
            ON CONFLICT (id) DO NOTHING
            """,
            r,
        )
    print(f"  scan_results: {len(rows)} filas procesadas")


def load_findings(cur):
    rows = load_csv(os.path.join(DATA_DIR, "03_findings.csv"))
    for r in rows:
        cur.execute(
            """
            INSERT INTO cerberus.findings
                (id, scan_result_id, severity, title, description, rule_id, file_path, line_start, line_end, recommendation)
            VALUES (%(id)s, %(scan_result_id)s, %(severity)s, %(title)s, %(description)s, %(rule_id)s, %(file_path)s, %(line_start)s, %(line_end)s, %(recommendation)s)
            ON CONFLICT (id) DO NOTHING
            """,
            r,
        )
    print(f"  findings: {len(rows)} filas procesadas")


def load_scan_verdicts(cur):
    rows = load_csv(os.path.join(DATA_DIR, "04_scan_verdicts.csv"))
    for r in rows:
        # rollback_triggered viene como texto "true"/"false" en el CSV -> bool real
        r["rollback_triggered"] = r["rollback_triggered"] == "true"
        cur.execute(
            """
            INSERT INTO cerberus.scan_verdicts
                (scan_id, verdict, critical_count, high_count, medium_count, low_count, info_count, rollback_triggered, issued_at)
            VALUES (%(scan_id)s, %(verdict)s, %(critical_count)s, %(high_count)s, %(medium_count)s, %(low_count)s, %(info_count)s, %(rollback_triggered)s, %(issued_at)s)
            ON CONFLICT (scan_id) DO NOTHING
            """,
            r,
        )
    print(f"  scan_verdicts: {len(rows)} filas procesadas")


def main():
    if not DB_CONFIG["user"] or not DB_CONFIG["password"]:
        raise SystemExit(
            "Faltan credenciales. Verifica que el archivo .env exista y tenga "
            "PGUSER y PGPASSWORD definidos."
        )

    print("Conectando a la base de datos...")
    conn = psycopg.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Cargando datos (respetando orden de foreign keys)...")
        load_scan_requests(cur)   # 1. padre de todo
        load_scan_results(cur)    # 2. depende de scan_requests
        load_findings(cur)        # 3. depende de scan_results
        load_scan_verdicts(cur)   # 4. depende de scan_requests

        conn.commit()
        print("Listo. Todos los datos se cargaron correctamente.")

    except Exception as e:
        conn.rollback()
        print(f"Error durante la carga, se hizo rollback completo: {e}")
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()