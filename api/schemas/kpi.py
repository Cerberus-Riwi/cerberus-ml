from datetime import date

from pydantic import BaseModel


class VerdictSummary(BaseModel):
    verdict: str
    total: int
    
class SeveritySummary(BaseModel):
    severity: str
    total: int
    
class TopRule(BaseModel):
    rule_id: str
    title: str
    total_findings: int
    
class RepositorySummary(BaseModel):
    repository_name: str
    organization: str
    repository_url: str

    total_findings: int

    critical: int
    high: int
    medium: int
    low: int
    info: int


class HistorySummary(BaseModel):

    full_date: date

    total_findings: int

    critical: int
    high: int
    medium: int
    low: int
    info: int


class Dashboard(BaseModel):

    verdicts: list[VerdictSummary]

    severity: list[SeveritySummary]

    top_rules: list[TopRule]

    repositories: list[RepositorySummary]
    
    history: list[HistorySummary]