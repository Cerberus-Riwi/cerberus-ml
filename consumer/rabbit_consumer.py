"""
rabbit_consumer.py — Consumer de RabbitMQ para cerberus-ml.

Escucha el exchange cerberus.scan.verdicts (fanout, durable) en la queue
verdicts.ml y persiste cada QualityGateResult en las 4 tablas de cerberus.

Variables de entorno requeridas (leer desde .env):
    RABBITMQ_USER
    RABBITMQ_PASSWORD
    RABBITMQ_HOST     (default: rabbitmq.cerberus.svc.cluster.local)
    RABBITMQ_PORT     (default: 5672)
    PGHOST
    PGPORT
    PGDATABASE
    PGUSER
    PGPASSWORD
"""

import json
import logging
import os
import time

import pika
import psycopg
from dotenv import load_dotenv

from consumer.db_writer import insert_verdict

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constantes RabbitMQ ───────────────────────────────────────────────────────
EXCHANGE = "cerberus.scan.verdicts"
QUEUE    = "verdicts.ml"

# ── Constantes de reconexión ──────────────────────────────────────────────────
RECONNECT_DELAY_INITIAL = 2   # segundos
RECONNECT_DELAY_MAX     = 60  # segundos


def get_rabbit_params() -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=os.environ.get("RABBITMQ_HOST", "rabbitmq.cerberus.svc.cluster.local"),
        port=int(os.environ.get("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            username=os.environ["RABBITMQ_USER"],
            password=os.environ["RABBITMQ_PASSWORD"],
        ),
        heartbeat=60,
        blocked_connection_timeout=30,
    )


def get_db_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "cerberus"),
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        autocommit=False,
    )


def on_verdict(channel, method, properties, body):
    """
    Callback invocado por pika por cada mensaje recibido.

    - Deserializa el JSON.
    - Llama a insert_verdict() dentro de una transacción.
    - Hace basic_ack si todo fue bien.
    - Hace basic_nack(requeue=False) si el mensaje está malformado
      (lo manda al dead-letter en vez de bloquearse para siempre).
    """
    try:
        verdict = json.loads(body)
        logger.info(
            "Mensaje recibido — scan_id=%s verdict=%s",
            verdict.get("scanId", "?"),
            verdict.get("verdict", "?"),
        )
    except json.JSONDecodeError as e:
        logger.error("JSON inválido, descartando mensaje: %s", e)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    # La conexión a BD se pasa desde el closure (ver consume_loop)
    db_conn = channel._db_conn  # inyectada en consume_loop

    try:
        insert_verdict(verdict, db_conn)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("ACK — scan_id=%s", verdict.get("scanId", "?"))

    except Exception as e:
        logger.error(
            "Error al persistir scan_id=%s: %s — NACK sin requeue",
            verdict.get("scanId", "?"),
            e,
        )
        # Rollback explícito para dejar la conexión limpia
        try:
            db_conn.rollback()
        except Exception:
            pass
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume_loop(db_conn: psycopg.Connection) -> None:
    """
    Abre la conexión RabbitMQ, declara el exchange y la queue,
    y arranca el loop de consumo. Lanza excepción si falla la conexión.
    """
    params = get_rabbit_params()
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Inyectar la conexión de BD en el channel para que on_verdict la use
    channel._db_conn = db_conn

    # Declarar exchange y queue (idempotente — seguro si ya existen)
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(exchange=EXCHANGE, queue=QUEUE)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=on_verdict)

    logger.info("Consumer listo — escuchando en exchange=%s queue=%s", EXCHANGE, QUEUE)
    channel.start_consuming()


def main() -> None:
    """
    Loop principal con reconexión automática y backoff exponencial.
    Valida credenciales al arranque para fallar rápido si faltan.
    """
    # Validación rápida de credenciales
    for var in ("RABBITMQ_USER", "RABBITMQ_PASSWORD", "PGUSER", "PGPASSWORD"):
        if not os.environ.get(var):
            raise SystemExit(f"Variable de entorno requerida no definida: {var}")

    delay = RECONNECT_DELAY_INITIAL

    while True:
        db_conn = None
        try:
            logger.info("Conectando a la base de datos...")
            db_conn = get_db_conn()

            logger.info("Conectando a RabbitMQ (host=%s)...",
                        os.environ.get("RABBITMQ_HOST", "rabbitmq.cerberus.svc.cluster.local"))
            consume_loop(db_conn)

            # Si consume_loop retorna limpiamente (raro), reiniciar delay
            delay = RECONNECT_DELAY_INITIAL

        except KeyboardInterrupt:
            logger.info("Consumer detenido por el usuario.")
            break

        except Exception as e:
            logger.error("Conexión perdida: %s — reintentando en %ds...", e, delay)
            time.sleep(delay)
            delay = min(delay * 2, RECONNECT_DELAY_MAX)

        finally:
            if db_conn and not db_conn.closed:
                try:
                    db_conn.close()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
