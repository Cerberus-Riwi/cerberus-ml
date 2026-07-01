
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