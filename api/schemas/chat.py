from pydantic import BaseModel


class Finding(BaseModel):
    severity: str
    title: str
    ruleId: str | None = None
    filePath: str | None = None
    lineStart: int | None = None
    recommendation: str | None = None


class ChatRequest(BaseModel):
    message: str
    findings: list[Finding] | None = None


class ChatResponse(BaseModel):
    reply: str
