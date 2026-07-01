# Deployment

Cerberus ML runs in **two different places** at the same time. This
document explains what runs where, and how the code gets there.

## Where each part runs

| Part                          | Where it runs                | Why                                             |
|---------------------------------|---------------------------------|----------------------------------------------------|
| API + RabbitMQ consumer            | **K3s cluster** (pod `analytics`) | It needs to reach RabbitMQ using internal cluster DNS. |
| PostgreSQL (business database, OLTP + Data Mart) | **AWS EC2**              | Runs together with Airflow, close to the ETL.        |
| Airflow (webserver + scheduler)      | **AWS EC2**                    | Self-hosted, `LocalExecutor`, small deployment.        |
| Power BI report                        | Power BI Desktop / Service       | Reads the Data Mart directly.                           |

```
┌────────────── K3s cluster ──────────────┐        ┌──────────── AWS EC2 ────────────┐
│                                            │        │                                    │
│  Pod "analytics"                            │        │  docker compose:                    │
│  (Dockerfile: API + consumer)                 │  IP    │   - postgres                          │
│                                                 │ ─────▶│   - airflow-postgres                    │
│                                                   │allow-  │   - airflow-webserver                     │
│                                                     │listed│   - airflow-scheduler                       │
└────────────────────────────────────────────┘        └────────────────────────────────┘
```

Only the cluster's **outbound IP address** is allowed to reach the EC2
instance (both the database port and the Airflow API). This keeps Airflow's
UI and the database safe from the public internet, while still letting the
cluster talk to them.

## Docker images

Two different Docker images are built from this repository:

### 1. `Dockerfile` — API + consumer

- Base image: `python:3.12-slim`.
- Uses a **multi-stage build**: dependencies are installed with `uv` in a
  `builder` stage, then only the virtual environment and the code
  (`consumer/`, `api/`, `main.py`) are copied to the final image. This keeps
  the image small.
- Exposes port `8000`.
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`.
- This is the image deployed as the `analytics` pod in K3s.

### 2. `Dockerfile.airflow` — Airflow

- Base image: `apache/airflow:2.10.5-python3.12`.
- Airflow 2.10 was chosen on purpose (not 3.x), because Airflow 3 changed
  how the REST API authenticates (JWT instead of basic auth) and reorganized
  several components. Airflow 2.10 is simpler to operate for a small,
  self-hosted deployment like this one.
- Installs `requirements-airflow.txt` on top of the base image (extra
  packages that `etl/` needs, like `psycopg` and `python-dotenv`).
- Used by the `docker-compose.yml` services `airflow-init`,
  `airflow-webserver`, and `airflow-scheduler`.

## Local / EC2 stack (`docker-compose.yml`)

Running `docker compose up -d` at the root of the repo starts:

- `postgres`: the business database (OLTP + Data Mart). Runs the SQL files
  in `database/init/` automatically the first time it starts.
- `airflow-postgres`: Airflow's own metadata database (separate from the
  business database).
- `airflow-init`: runs once, creates the Airflow admin user and migrates
  Airflow's internal database.
- `airflow-webserver`: Airflow's UI and REST API, on port `8080`.
- `airflow-scheduler`: runs the DAGs on their schedule.

The `dags/` and `etl/` folders are mounted as **volumes** into the Airflow
containers, so the DAG can import and run `etl/run.py` directly (see
`PYTHONPATH: /opt/airflow/project` in `docker-compose.yml`).

> **Note:** the `api` service is commented out in this `docker-compose.yml`
> on purpose. It already runs in the K3s cluster. Running it here too would
> create two RabbitMQ consumers competing for the same queue, and two APIs
> answering requests at the same time. See the comments inside
> `docker-compose.yml` for the full explanation.

## Environment variables

Copy `.env.example` to `.env` and fill in real values. Groups of variables:

| Group        | Variables                                                                 | Used by                          |
|---------------|------------------------------------------------------------------------------|--------------------------------------|
| PostgreSQL      | `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`                          | API, consumer, ETL                    |
| RabbitMQ          | `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`                | Consumer                                  |
| Airflow             | `AIRFLOW_BASE_URL`, `AIRFLOW_ETL_DAG_ID`, `AIRFLOW_API_USER`, `AIRFLOW_API_PASSWORD`      | Consumer (to trigger the DAG), `docker-compose.yml` (to create the admin user) |

**Never commit a real `.env` file.** It is already excluded in `.gitignore`.

## CI/CD

The workflow `.github/workflows/ci.yml` runs on every push to `main` or
`develop`:

1. Checks out the repository.
2. Logs in to **GitHub Container Registry** (`ghcr.io`).
3. Builds the image from `Dockerfile` (API + consumer).
4. Pushes it to `ghcr.io/cerberus-riwi/analytics-service`, tagged with:
   - the branch name (for example, `develop`), and
   - `latest`, only when the branch is `main`.

This workflow only builds and pushes the **API + consumer** image
(`Dockerfile`). The Airflow image (`Dockerfile.airflow`) is built locally on
the EC2 instance by `docker compose up`, and is not published to a
registry.

Once a new image is pushed to `ghcr.io`, the K3s `analytics` Deployment
needs to be updated to use it (for example, by re-applying the deployment
manifest or restarting the pod), so this is not fully automatic yet.

## Related documents

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — the full data flow.
- [docs/ETL.md](ETL.md) — how the ETL pipeline works.
- [database/README.md](../database/README.md) — OLTP data model.