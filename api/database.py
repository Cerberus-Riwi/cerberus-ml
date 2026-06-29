import psycopg

from api.config import Settings


def get_connection():

    return psycopg.connect(

        host=Settings.PGHOST,

        port=Settings.PGPORT,

        dbname=Settings.PGDATABASE,

        user=Settings.PGUSER,

        password=Settings.PGPASSWORD,
    )