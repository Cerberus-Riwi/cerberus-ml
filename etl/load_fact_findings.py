from psycopg.rows import dict_row


def load_fact_findings(conn):
    """
    Pobla la tabla de hechos analytics.fact_findings
    a partir del esquema operacional cerberus.
    """

    extract_query = """
    SELECT
        f.id AS finding_id,
        f.scan_result_id,
        f.severity,
        f.title,
        f.file_path,
        f.location_url,
        f.line_start,
        f.line_end,
        f.recommendation,

        sr.scan_id,
        sr.service_id,

        sv.verdict,
        sv.issued_at,

        rq.repository_url,

        f.rule_id

    FROM cerberus.findings f

    JOIN cerberus.scan_results sr
        ON sr.id = f.scan_result_id

    JOIN cerberus.scan_requests rq
        ON rq.scan_id = sr.scan_id

    JOIN cerberus.scan_verdicts sv
        ON sv.scan_id = sr.scan_id;
    """

    insert_query = """
    INSERT INTO analytics.fact_findings (
        finding_id,
        repository_key,
        rule_key,
        severity_key,
        date_key,
        scan_id,
        scan_result_id,
        verdict,
        service_id,
        title,
        file_path,
        location_url,
        line_start,
        line_end,
        recommendation,
        issued_at
    )

    SELECT

        %(finding_id)s,

        dr.repository_key,

        ru.rule_key,

        ds.severity_key,

        TO_CHAR(%(issued_at)s::date,'YYYYMMDD')::INTEGER,

        %(scan_id)s,

        %(scan_result_id)s,

        %(verdict)s,

        %(service_id)s,

        %(title)s,

        %(file_path)s,

        %(location_url)s,

        %(line_start)s,

        %(line_end)s,

        %(recommendation)s,

        %(issued_at)s

    FROM analytics.dim_repository dr,
         analytics.dim_rule ru,
         analytics.dim_severity ds

    WHERE
        dr.repository_url = %(repository_url)s
    AND ru.rule_id = %(rule_id)s
    AND ds.severity_name = %(severity)s

    ON CONFLICT (finding_id)
    DO NOTHING;
    """

    with conn.cursor(row_factory=dict_row) as cur:

        cur.execute(extract_query)

        findings = cur.fetchall()

        inserted = 0

        for finding in findings:

            cur.execute(insert_query, finding)
            inserted += 1

        conn.commit()

    return inserted