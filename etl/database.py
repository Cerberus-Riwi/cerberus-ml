from contextlib import contextmanager
from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv

# Cargar el .env ubicado en la raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@contextmanager
def get_connection():
    conn = psycopg.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

    try:
        yield conn
    finally:
        conn.close()