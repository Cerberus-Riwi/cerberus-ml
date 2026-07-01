# Architecture

This document explains how Cerberus ML works from start to end, and why it
is built this way.

## Overview

Cerberus ML is **event-driven**. This means it does not wait or ask for new
data — new data arrives as *events* (messages), and the service reacts to
them right away, without a person doing anything by hand.

```
                 ┌───────────────────────────────────────────┐
                 │              K3s cluster                  │
                 │                                             │
   RabbitMQ ───▶ │  Consumer  ──▶  PostgreSQL (OLTP)          │
 (verdicts.ml)   │      │                 ▲                    │
                 │      │                 │                    │
                 │      ▼                 │                    │
                 │  Trigger Airflow    FastAPI (KPIs)  ◀─── Frontend
                 │  (REST API)              │                    │
                 └──────┼───────────────────┼────────────────┘
                        │                   
                        ▼                   
                 ┌─────────────────────────────┐
                 │           EC2                │
                 │                                │
                 │  Airflow (LocalExecutor)       │
                 │      │                          │
                 │      ▼                          │
                 │  ETL scripts (etl/)             │
                 │      │                          │
                 │      ▼                          │
                 │  Data Mart (OLAP, star schema)  │
                 └─────────────────────────────┘
                                │
                                ▼
                          Power BI report
```

## Step by step

1. A scan (quality/security check) finishes somewhere else in the Cerberus
   platform. The result (a "verdict") is published to RabbitMQ.
2. The **consumer** (`consumer/rabbit_consumer.py`) listens to the exchange
   `cerberus.scan.verdicts` through the queue `verdicts.ml`.
3. The consumer saves the verdict into **PostgreSQL (OLTP)** — the tables
   `scan_requests`, `scan_results`, `findings`, `scan_verdicts` (see
   [database/README.md](../database/README.md)).
4. Right after saving, the consumer calls the **Airflow REST API** to start
   the ETL DAG (`cerberus_etl`). This call is "best-effort": if Airflow does
   not answer, the consumer does not fail or retry the message — it just
   logs a warning. See [docs/ETL.md](ETL.md) for the safety net.
5. **Airflow** runs the ETL scripts (`etl/`). They read the OLTP data and
   load it into the **Data Mart** (`analytics` schema): `dim_date`,
   `dim_repository`, `dim_rule`, `dim_severity`, `fact_findings`.
6. **Power BI** connects to the Data Mart and shows the final dashboards.
7. The **FastAPI** service (`api/`) also reads the Data Mart and exposes
   KPIs as a REST API, used by the frontend.

## Why these design choices?

### RabbitMQ stays inside the cluster

The consumer connects to RabbitMQ using the cluster's **internal DNS**
(`rabbitmq.cerberus.svc.cluster.local`). RabbitMQ is never exposed to the
public internet. This reduces the attack surface: nobody outside the
cluster can publish or read messages from the queue.

### Airflow and its database run on a separate EC2 instance

Airflow and the OLTP/OLAP database run outside the cluster, on an EC2
instance. Access to that instance (database port and Airflow API) is
**restricted by IP** — only the cluster's outbound IP address can reach it.
This keeps Airflow's admin UI and the database safe from public access,
while still letting the cluster talk to them.

### Event + schedule (two triggers, not one)

The ETL can run in two ways:

- **Event-driven (main path):** the consumer triggers the DAG right after a
  new verdict is saved. This means new data can reach the Data Mart in a
  few seconds.
- **Scheduled (safety net):** the same DAG also runs every 30 minutes on its
  own. If the event trigger fails for any reason (Airflow down, network
  issue), the Data Mart is never out of sync for too long.

### Defensive validation in the ETL

Before loading any data, the ETL checks that the `analytics.dim_date` table
is not empty (see `etl/load_dim_date.py`). If it is empty, the ETL stops
with a clear error instead of silently loading incomplete or wrong data
into the Data Mart. This is a simple example of a "fail fast" pattern.

### Why the API service is not started by the root `docker-compose.yml`

The image built from `Dockerfile` (API + consumer) already runs inside the
K3s cluster as the `analytics` Deployment. If the same image also ran on
the EC2 instance, RabbitMQ would split the queue messages between the two
consumers in an unpredictable way, and there would be two APIs answering
requests at the same time. The `docker-compose.yml` at the root only runs
what is exclusive to EC2: the business PostgreSQL database and the Airflow
stack.

## Related documents

- [docs/ETL.md](ETL.md) — details about each ETL step.
- [docs/API.md](API.md) — REST API endpoints.
- [docs/DEPLOYMENT.md](DEPLOYMENT.md) — how and where each piece is deployed.
- [database/README.md](../database/README.md) — OLTP data model.