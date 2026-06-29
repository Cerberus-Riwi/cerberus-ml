from psycopg.rows import dict_row


def load_dim_rule(conn):
    """
    Pobla la dimensión de reglas.
    """

    extract_query = """
        SELECT DISTINCT
            rule_id,
            title,
            description,
            recommendation
        FROM cerberus.findings
        ORDER BY rule_id;
    """

    insert_query = """
        INSERT INTO analytics.dim_rule (
            rule_id,
            title,
            description,
            recommendation
        )
        VALUES (
            %(rule_id)s,
            %(title)s,
            %(description)s,
            %(recommendation)s
        )
        ON CONFLICT (rule_id)
        DO NOTHING;
    """

    with conn.cursor(row_factory=dict_row) as cur:

        cur.execute(extract_query)

        rules = cur.fetchall()

        inserted = 0

        for rule in rules:

            cur.execute(insert_query, rule)
            inserted += 1

        conn.commit()

    return inserted