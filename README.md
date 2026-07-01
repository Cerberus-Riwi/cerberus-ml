# Cerberus ML

Cerberus ML is the **data and analytics service** of the Cerberus platform.

It listens to security and quality scan results in real time, saves them in a
database, and turns them into a **star schema (Data Mart)** for reports and
dashboards in Power BI.

## What does it do?

1. It **listens** to scan verdicts (pass/fail results) from RabbitMQ.
2. It **saves** each verdict in a PostgreSQL database (OLTP).
3. It **triggers** an ETL pipeline in Apache Airflow.
4. The ETL pipeline **transforms** the raw data into a Data Mart (star schema).
5. A **FastAPI** service exposes KPIs (Key Performance Indicators) for the
   frontend.
6. **Power BI** reads the Data Mart and shows the final dashboards.

```
RabbitMQ  →  Consumer  →  PostgreSQL (OLTP)  →  Airflow ETL  →  Data Mart (OLAP)  →  API / Power BI
```

For more details about the architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| Layer               | Technology                          |
|----------------------|--------------------------------------|
| Language              | Python 3.12                          |
| Messaging              | RabbitMQ (pika)                      |
| Database                | PostgreSQL 17 (OLTP + OLAP)          |
| API                       | FastAPI + Uvicorn                    |
| ETL orchestration      | Apache Airflow 2.10 (LocalExecutor)  |
| Containers              | Docker / Docker Compose / Kubernetes (K3s) |
| CI/CD                    | GitHub Actions → GitHub Container Registry (ghcr.io) |
| Infrastructure           | AWS EC2 + self-managed K3s cluster    |
| Reporting                | Power BI                             |

## Project structure

```
cerberus-ml/
├── api/            # FastAPI app: routers, schemas, services
├── consumer/        # RabbitMQ consumer + database writer
├── etl/              # ETL scripts (extract + load into the Data Mart)
├── dags/             # Airflow DAG that runs the ETL
├── database/          # SQL schema: OLTP tables and analytics (Data Mart)
├── powerbi/            # Power BI report (.pbix) and assets
├── data/               # Demo / sample data
├── docs/               # Extra documentation (this folder)
├── Dockerfile           # Image for the API + consumer (runs in K3s)
├── Dockerfile.airflow    # Image for Airflow (runs in EC2)
└── docker-compose.yml     # Local/EC2 stack: Postgres + Airflow
```

## How the service connects to the platform

- It runs as a **pod inside the K3s cluster** (`analytics` namespace).
- It connects to **RabbitMQ** using the cluster's internal DNS. It listens to
  the exchange `cerberus.scan.verdicts` and the queue `verdicts.ml`. RabbitMQ
  is never exposed to the internet.
- When a verdict arrives, it is saved in **PostgreSQL (OLTP)**, and the
  service triggers the **Airflow ETL** pipeline through its REST API.
- Airflow and its database run on a **separate EC2 instance**. Access to that
  instance is restricted by IP: only the cluster's outbound IP can reach it.
- The service also exposes a **REST API (FastAPI)** so the frontend can read
  KPIs.

## Quick start (local development)

### 1. Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (dependency manager)
- Docker and Docker Compose

### 2. Set up environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Start the database and Airflow stack

```bash
docker compose up -d
```

This starts:
- `postgres`: the main database (OLTP + Data Mart).
- `airflow-postgres`, `airflow-webserver`, `airflow-scheduler`: the Airflow
  stack that runs the ETL.

> Note: the API/consumer service is **not** started by this
> `docker-compose.yml` on purpose. It already runs inside the K3s cluster.
> See the comments inside `docker-compose.yml` for the full explanation.

### 5. Run the API + consumer locally (optional)

```bash
uv run uvicorn api.main:app --reload
```

This also starts the RabbitMQ consumer in a background thread (see
`api/main.py`).

### 6. Run the ETL manually (optional)

The ETL normally runs through Airflow, but you can also run it by hand:

```bash
uv run python -m etl.run
```

## More documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how all the pieces connect,
  and why.
- [docs/API.md](docs/API.md) — REST API endpoints.
- [docs/ETL.md](docs/ETL.md) — how the ETL pipeline works.
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — how the service is deployed
  (K3s + EC2) and CI/CD.
- [database/README.md](database/README.md) — OLTP data model (ER diagram).
- [database/SCHEMA_CHANGELOG.md](database/SCHEMA_CHANGELOG.md) — history of
  schema changes.

## License

MIT