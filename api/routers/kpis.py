from fastapi import APIRouter
from api.services.health import check_health
from api.database import get_connection

from api.schemas.kpi import (
    Dashboard,
    HistorySummary,
    RepositorySummary,
    SeveritySummary,
    TopRule,
    VerdictSummary,
)

from api.services.analytics import (
    get_dashboard,
    get_history,
    get_repository_summary,
    get_severity_summary,
    get_top_rules,
    get_verdict_summary,
)

router = APIRouter(
    prefix="/api/kpis",
    tags=["KPIs"],
)

@router.get("/health")
def health():

    return check_health()

@router.get("/verdicts", response_model=list[VerdictSummary])
def verdict_summary():

    with get_connection() as conn:
        return get_verdict_summary(conn)


@router.get("/severity", response_model=list[SeveritySummary])
def severity_summary():

    with get_connection() as conn:
        return get_severity_summary(conn)


@router.get("/top-rules", response_model=list[TopRule])
def top_rules(limit: int = 10):

    with get_connection() as conn:
        return get_top_rules(conn, limit)


@router.get("/repositories", response_model=list[RepositorySummary])
def repositories():

    with get_connection() as conn:
        return get_repository_summary(conn)


@router.get("/dashboard", response_model=Dashboard)
def dashboard():

    with get_connection() as conn:
        return get_dashboard(conn)
    
@router.get(
    "/history",
    response_model=list[HistorySummary]
)
def history():

    with get_connection() as conn:
        return get_history(conn)