from etl.database import get_connection

from etl.extract import extract_findings
from etl.load_dim_repository import load_dim_repository
from etl.load_dim_rule import load_dim_rule
from etl.load_fact_findings import load_fact_findings
from etl.load_dim_date import validate_dim_date

def main():

    with get_connection() as conn:
        
        dates = validate_dim_date(conn)
        print(f"Fechas disponibles: {dates}")

        findings = extract_findings(conn)
        print(f"Findings extraídos: {len(findings)}")

        repositories = load_dim_repository(conn)
        print(f"Repositorios cargados: {repositories}")

        rules = load_dim_rule(conn)
        print(f"Reglas cargadas: {rules}")

        facts = load_fact_findings(conn)
        print(f"Findings cargados al Data Mart: {facts}")


if __name__ == "__main__":
    main()