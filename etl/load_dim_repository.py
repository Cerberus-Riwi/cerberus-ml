from psycopg.rows import dict_row


def load_dim_repository(conn):
    """
    Pobla la dimensión de repositorios a partir del OLTP.
    """

    extract_query = """
        SELECT DISTINCT repository_url
        FROM cerberus.scan_requests
        ORDER BY repository_url;
    """

    insert_query = """
        INSERT INTO analytics.dim_repository (
            repository_url,
            organization,
            repository_name
        )
        VALUES (
            %(repository_url)s,
            %(organization)s,
            %(repository_name)s
        )
        ON CONFLICT (repository_url)
        DO NOTHING;
    """

    with conn.cursor(row_factory=dict_row) as cur:

        cur.execute(extract_query)

        repositories = cur.fetchall()

        inserted = 0

        for repo in repositories:

            url = repo["repository_url"]

            parts = url.rstrip("/").split("/")

            organization = parts[-2]
            repository_name = parts[-1]

            cur.execute(
                insert_query,
                {
                    "repository_url": url,
                    "organization": organization,
                    "repository_name": repository_name,
                },
            )

            inserted += 1

        conn.commit()

    return inserted