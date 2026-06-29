from psycopg.rows import dict_row


def validate_dim_date(conn):
    """
    Verifica que la dimensión de fechas esté cargada.
    """

    query = """
        SELECT COUNT(*) AS total
        FROM analytics.dim_date;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)

        total = cur.fetchone()["total"]

    if total == 0:
        raise RuntimeError(
            "La dimensión analytics.dim_date está vacía. "
            "Ejecute primero el seed 002_seed_dim_date.sql."
        )

    return total