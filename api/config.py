from pathlib import Path

from dotenv import load_dotenv

import os

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


class Settings:

    APP_NAME = "Cerberus Analytics Service"

    VERSION = "1.0.0"

    DESCRIPTION = (
        "Analytics API para consulta de KPIs "
        "sobre el Data Mart de Cerberus."
    )

    PGHOST = os.getenv("PGHOST")

    PGPORT = os.getenv("PGPORT")

    PGDATABASE = os.getenv("PGDATABASE")

    PGUSER = os.getenv("PGUSER")

    PGPASSWORD = os.getenv("PGPASSWORD")
    
    APP_PORT = int(os.getenv("APP_PORT", 8000))