"""
cerberus_etl_dag.py — Orquesta el ETL de cerberus-ml (OLTP -> Data Mart OLAP).

No reimplementa la lógica del ETL: simplemente llama a etl.run.main(),
el mismo código que hoy se corre a mano con `python -m etl.run`.

Este DAG se dispara de DOS formas (no son excluyentes):

1. EVENTO (principal): consumer/rabbit_consumer.py llama a la API de Airflow
   justo después de insertar un nuevo verdict en el OLTP, disparando este DAG
   de inmediato (ver AIRFLOW_ETL_DAG_ID en consumer/rabbit_consumer.py).

2. SCHEDULE (red de seguridad): corre cada 30 minutos igual, por si la
   llamada del consumer falla (Airflow caído, red, etc.) — así el Data Mart
   nunca queda desincronizado por mucho tiempo aunque falle el disparo.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_etl():
    # Import diferido: el módulo etl/ se monta como volumen en
    # /opt/airflow/project/etl (ver docker-compose.yml, PYTHONPATH).
    from etl.run import main

    main()


default_args = {
    "owner": "cerberus",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="cerberus_etl",
    description="Sincroniza cerberus (OLTP) -> analytics (Data Mart OLAP) para Power BI",
    default_args=default_args,
    schedule="*/30 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["cerberus", "etl"],
) as dag:

    run_etl_task = PythonOperator(
        task_id="run_etl",
        python_callable=run_etl,
    )