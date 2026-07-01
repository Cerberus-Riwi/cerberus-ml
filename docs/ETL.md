# ETL Pipeline

ETL means **Extract, Transform, Load**. It is the process that takes the raw
data from the OLTP database (`cerberus` schema) and turns it into a clean
**Data Mart** (`analytics` schema, star schema) that Power BI and the API
can use.

## Where to find it

- `etl/` — the ETL scripts (Python).
- `dags/cerberus_etl_dag.py` — the Airflow DAG that runs the scripts.
- `database/analytics/` — SQL that creates the Data Mart tables.

## How the ETL is triggered

The ETL DAG (`cerberus_etl`) runs in **two ways**, and both are active at the
same time:

1. **Event-driven (fast path).** Right after the consumer saves a new
   verdict in the OLTP database, it calls the Airflow REST API to start the
   DAG immediately (see `trigger_etl_dag` in
   `consumer/rabbit_consumer.py`). New data can reach the Data Mart in a few
   seconds.
2. **Scheduled (safety net).** The same DAG also has a schedule:
   `*/30 * * * *`, which means "every 30 minutes". If the event trigger
   fails (for example, Airflow was down), the Data Mart will still be
   updated within 30 minutes at most.

The event trigger is "best-effort": if it fails, the consumer only logs a
warning. It does not retry the RabbitMQ message and does not crash. This is
on purpose — the scheduled run already covers this case.

## Steps of the pipeline (`etl/run.py`)

The DAG calls `etl.run.main()`, which runs these steps in order:

1. **`validate_dim_date`** (`etl/load_dim_date.py`)
   Checks that `analytics.dim_date` is not empty. If it is empty, the ETL
   **stops immediately** with an error, instead of loading incomplete data.
   This table must be filled once, using the seed file
   `database/analytics/seeds/002_seed_dim_date.sql`.

2. **`extract_findings`** (`etl/extract.py`)
   Reads all findings from the OLTP schema, joined with their scan, verdict,
   and repository information. This is only used for a quick count/log —
   the real load queries are separate (see below).

3. **`load_dim_repository`** (`etl/load_dim_repository.py`)
   Reads the distinct repository URLs from `cerberus.scan_requests` and
   inserts new ones into `analytics.dim_repository`. The organization and
   repository name are extracted from the URL itself (for example,
   `https://github.com/org/repo` → organization = `org`, name = `repo`).
   Existing rows are not duplicated (`ON CONFLICT ... DO NOTHING`).

4. **`load_dim_rule`** (`etl/load_dim_rule.py`)
   Reads the distinct rules from `cerberus.findings` and inserts new ones
   into `analytics.dim_rule`. Same "no duplicates" logic as above.

5. **`load_fact_findings`** (`etl/load_fact_findings.py`)
   For each finding in the OLTP schema, it looks up the matching keys in
   `dim_repository`, `dim_rule`, and `dim_severity`, and inserts a new row
   into `analytics.fact_findings`. The date key is built from the verdict's
   `issued_at` date (format `YYYYMMDD`, matching `dim_date`). Findings that
   are already loaded are skipped (`ON CONFLICT (finding_id) DO NOTHING`).

## Why the "defensive validation" matters

If `dim_date` is empty, `load_fact_findings` would not find a match for the
date key, or would insert wrong data silently. By checking `dim_date` first
and stopping with a clear error, the ETL avoids loading broken or partial
data into the Data Mart. This protects the Power BI report from showing
wrong numbers without anyone noticing.

## Running the ETL manually

Useful for local development or debugging:

```bash
uv run python -m etl.run
```

This prints a short log of what was processed at each step:

```
Fechas disponibles: 3650
Findings extraídos: 42
Repositorios cargados: 2
Reglas cargadas: 15
Findings cargados al Data Mart: 42
```

## Environment variables used by the ETL

Same as the database connection used everywhere else (`etl/database.py`
reads them from `.env`):

| Variable      | Description       |
|----------------|----------------------|
| `PGHOST`         | Database host.        |
| `PGPORT`           | Database port.           |
| `PGDATABASE`         | Database name.              |
| `PGUSER`               | Database user.                |
| `PGPASSWORD`             | Database password.              |

## Related documents

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — how the ETL fits into the full
  flow.
- [database/README.md](../database/README.md) — OLTP data model.