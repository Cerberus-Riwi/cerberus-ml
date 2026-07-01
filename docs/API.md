# API

Cerberus ML exposes a REST API built with **FastAPI**. The frontend uses it
to show KPIs (numbers and charts) about scan results.

## Base information

- **Base path:** `/api/kpis`
- **Interactive docs (Swagger UI):** `/docs`
- **Alternative docs (ReDoc):** `/redoc`
- **Root endpoint:** `/` — returns the service name, version, and status.

The API and the RabbitMQ consumer run **in the same process**. When the API
starts, it also starts the consumer in a background thread (see
`api/main.py`, function `start_consumer_thread`).

## Endpoints

All endpoints below use the prefix `/api/kpis`.

| Method | Path                | Description                                              |
|--------|----------------------|------------------------------------------------------------|
| GET    | `/health`             | Checks if the service and the database connection are OK. |
| GET    | `/verdicts`            | Total findings grouped by verdict (pass/fail).             |
| GET    | `/severity`             | Total findings grouped by severity (critical, high, etc.). |
| GET    | `/top-rules`             | The rules with the most findings. Accepts `?limit=` (default 10). |
| GET    | `/repositories`           | Findings summary per repository.                            |
| GET    | `/history`                 | Findings summary per date, for time-based charts.           |
| GET    | `/dashboard`                 | All the KPIs above combined in a single response.           |

### Example: `GET /api/kpis/dashboard`

```json
{
  "verdicts": [
    { "verdict": "PASS", "total": 120 },
    { "verdict": "FAIL", "total": 34 }
  ],
  "severity": [
    { "severity": "CRITICAL", "total": 5 },
    { "severity": "HIGH", "total": 20 }
  ],
  "top_rules": [
    { "rule_id": "SEC-001", "title": "Hardcoded secret", "total_findings": 12 }
  ],
  "repositories": [
    {
      "repository_name": "cerberus-ml",
      "organization": "cerberus-riwi",
      "repository_url": "https://github.com/cerberus-riwi/cerberus-ml",
      "total_findings": 8,
      "critical": 1,
      "high": 2,
      "medium": 3,
      "low": 1,
      "info": 1
    }
  ],
  "history": [
    {
      "full_date": "2026-06-01",
      "total_findings": 4,
      "critical": 0,
      "high": 1,
      "medium": 2,
      "low": 1,
      "info": 0
    }
  ]
}
```

## Where things live in the code

| Folder            | What it contains                                              |
|---------------------|------------------------------------------------------------------|
| `api/main.py`         | FastAPI app setup, logging middleware, consumer startup.          |
| `api/config.py`         | Settings loaded from environment variables (`.env`).              |
| `api/routers/kpis.py`     | Endpoint definitions (URLs and HTTP methods).                       |
| `api/schemas/kpi.py`        | Pydantic models — the shape of each response.                        |
| `api/services/analytics.py`   | SQL queries against the Data Mart, used by the endpoints.               |
| `api/services/health.py`        | Logic for the `/health` endpoint.                                          |
| `api/database.py`                 | Database connection helper.                                                   |
| `api/exceptions.py`                 | Global error handler.                                                             |

## Environment variables used by the API

These come from `.env` (see `.env.example`):

| Variable      | Description                          |
|----------------|----------------------------------------|
| `PGHOST`         | Database host.                          |
| `PGPORT`           | Database port (default `5432`).           |
| `PGDATABASE`         | Database name.                              |
| `PGUSER`               | Database user.                                |
| `PGPASSWORD`             | Database password.                              |
| `APP_PORT`                 | Port where the API listens (default `8000`).      |

## Running it locally

```bash
uv run uvicorn api.main:app --reload
```

Then open `http://localhost:8000/docs` to try the endpoints in your
browser.