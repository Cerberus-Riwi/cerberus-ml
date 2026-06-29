from datetime import datetime, UTC
from time import perf_counter
from api.logger import logger
from psycopg import Error

from api.database import get_connection
from api.config import Settings


def check_health():

    started = perf_counter()

    try:

        with get_connection() as conn:

            with conn.cursor() as cur:

                cur.execute("SELECT 1;")

                cur.fetchone()

        database = "connected"

        status = "healthy"

    except Error:

        database = "disconnected"

        status = "unhealthy"

    elapsed = round((perf_counter() - started) * 1000, 2)
    
    logger.info(
        "Health check | status=%s | database=%s | %.2f ms",
        status,
        database,
        elapsed
    )

    return {
        "status": status,
        "database": database,
        "response_time_ms": elapsed,
        "service": Settings.APP_NAME,
        "version": Settings.VERSION,
        "timestamp": datetime.now(UTC).isoformat()
    }