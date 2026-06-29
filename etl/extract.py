from psycopg.rows import dict_row


def extract_findings(conn):
    """
    Extrae toda la información necesaria desde el esquema OLTP.
    """

    query = """
        SELECT
            f.id                           AS finding_id,
            f.scan_result_id,
            f.severity,
            f.title,
            f.description,
            f.rule_id,
            f.file_path,
            f.location_url,
            f.line_start,
            f.line_end,
            f.recommendation,

            sr.scan_id,
            sr.service_id,

            sv.verdict,
            sv.issued_at,

            rq.repository_url

        FROM cerberus.findings f

        JOIN cerberus.scan_results sr
            ON sr.id = f.scan_result_id

        JOIN cerberus.scan_requests rq
            ON rq.scan_id = sr.scan_id

        JOIN cerberus.scan_verdicts sv
            ON sv.scan_id = sr.scan_id;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()