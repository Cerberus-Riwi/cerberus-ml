"""
cerberus-ml — Servicio de ML/Analytics.

Punto de entrada principal. Arranca el consumer de RabbitMQ.
Más adelante también arrancará el servidor FastAPI en el mismo proceso.
"""

from consumer.rabbit_consumer import main as run_consumer

if __name__ == "__main__":
    run_consumer()
