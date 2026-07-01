# Contributing

Thanks for helping with Cerberus ML! This is a short guide to get started.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Copy the environment file and fill in your own values:
   ```bash
   cp .env.example .env
   ```
4. Start the local database and Airflow stack:
   ```bash
   docker compose up -d
   ```

See the main [README.md](README.md) for more details.

## Project layout

Before making changes, check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
to understand how the pieces connect (RabbitMQ consumer, ETL, API,
Airflow).

## Branches

- `main`: stable branch, deployed to production.
- `develop`: active development branch.

Every push to `main` or `develop` builds and pushes a new Docker image to
`ghcr.io` (see `.github/workflows/ci.yml`).

## Making changes to the database schema

If you need to change the OLTP schema (`cerberus.*` tables):

1. Add your `ALTER TABLE` (or similar) statements.
2. **Add an entry to [database/SCHEMA_CHANGELOG.md](database/SCHEMA_CHANGELOG.md)**
   explaining what changed and why. This file is important — it keeps
   track of why the database differs from the original data contract.

If you need to change the Data Mart schema (`analytics.*` tables), update
the SQL files in `database/analytics/migrations/` and check if the ETL
scripts in `etl/` still match the new column names.

## Testing your changes locally

- Run the API:
  ```bash
  uv run uvicorn api.main:app --reload
  ```
- Run the ETL by hand:
  ```bash
  uv run python -m etl.run
  ```
- You can publish a fake message to RabbitMQ using
  `consumer/publish_test.py` to test the consumer end to end.

## Pull requests

- Keep pull requests small and focused on one change.
- Write a clear description: what changed, and why.
- If your change affects the architecture, ETL, API, or deployment, please
  update the matching file in `docs/` too.