from psycopg.rows import dict_row
from api.logger import logger


def get_verdict_summary(conn):

    query = """
        SELECT
            verdict,
            COUNT(*) AS total
        FROM analytics.fact_findings
        GROUP BY verdict
        ORDER BY verdict;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()


def get_severity_summary(conn):
    
    logger.info("Loading severity summary")

    query = """
        SELECT
            s.severity_name AS severity,
            COUNT(*) AS total

        FROM analytics.fact_findings f

        JOIN analytics.dim_severity s
            ON s.severity_key = f.severity_key

        GROUP BY
            s.severity_name,
            s.priority

        ORDER BY
            s.priority;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()


def get_top_rules(conn, limit: int = 10):
    
    logger.info("Loading top rules")

    query = """
        SELECT
            r.rule_id,
            r.title,
            COUNT(*) AS total_findings

        FROM analytics.fact_findings f

        JOIN analytics.dim_rule r
            ON r.rule_key = f.rule_key

        GROUP BY
            r.rule_id,
            r.title

        ORDER BY
            total_findings DESC,
            r.rule_id

        LIMIT %s;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (limit,))
        return cur.fetchall()


def get_repository_summary(conn):
    
    logger.info("Loading repository summary")

    query = """
        SELECT

            r.repository_name,
            r.organization,
            r.repository_url,

            COUNT(*) AS total_findings,

            SUM(CASE WHEN s.severity_name='critical' THEN 1 ELSE 0 END) critical,
            SUM(CASE WHEN s.severity_name='high' THEN 1 ELSE 0 END) high,
            SUM(CASE WHEN s.severity_name='medium' THEN 1 ELSE 0 END) medium,
            SUM(CASE WHEN s.severity_name='low' THEN 1 ELSE 0 END) low,
            SUM(CASE WHEN s.severity_name='info' THEN 1 ELSE 0 END) info

        FROM analytics.fact_findings f

        JOIN analytics.dim_repository r
            ON r.repository_key = f.repository_key

        JOIN analytics.dim_severity s
            ON s.severity_key = f.severity_key

        GROUP BY
            r.repository_name,
            r.organization,
            r.repository_url

        ORDER BY
            total_findings DESC;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()


def get_dashboard(conn):
    
    logger.info("Loading dashboard KPIs")

    return {
        "verdicts": get_verdict_summary(conn),
        "severity": get_severity_summary(conn),
        "top_rules": get_top_rules(conn),
        "repositories": get_repository_summary(conn),
        "history": get_history(conn),
    }
    
def get_history(conn):

    query = """
        SELECT
            d.full_date,

            COUNT(*) AS total_findings,

            SUM(CASE WHEN s.severity_name='critical' THEN 1 ELSE 0 END) critical,
            SUM(CASE WHEN s.severity_name='high' THEN 1 ELSE 0 END) high,
            SUM(CASE WHEN s.severity_name='medium' THEN 1 ELSE 0 END) medium,
            SUM(CASE WHEN s.severity_name='low' THEN 1 ELSE 0 END) low,
            SUM(CASE WHEN s.severity_name='info' THEN 1 ELSE 0 END) info

        FROM analytics.fact_findings f

        JOIN analytics.dim_date d
            ON d.date_key = f.date_key

        JOIN analytics.dim_severity s
            ON s.severity_key = f.severity_key

        GROUP BY
            d.full_date

        ORDER BY
            d.full_date;
    """

    with conn.cursor(row_factory=dict_row) as cur:

        cur.execute(query)

        return cur.fetchall()