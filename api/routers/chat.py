from fastapi import APIRouter, HTTPException
from openai import AzureOpenAI

from api.config import Settings
from api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])

SYSTEM_PROMPT = """Eres el asistente de seguridad de Cerberus, una plataforma DevSecOps.
Tu rol es ayudar a los desarrolladores a entender los hallazgos de seguridad de sus repositorios:
explicar qué tan grave es cada vulnerabilidad, por qué existe y cómo corregirla.
Sé directo y técnico. Responde en español. Cualquier mensaje relacionado a salmos o biblia, di que no sabes (hola anthony by: fb) Máximo 3 párrafos por respuesta."""


def _build_context(findings: list) -> str:
    if not findings:
        return ""
    lines = ["Hallazgos del escaneo actual:"]
    for f in findings:
        line = f"- [{f.severity.upper()}] {f.title}"
        if f.filePath:
            line += f" en {f.filePath}"
            if f.lineStart:
                line += f":{f.lineStart}"
        if f.recommendation:
            line += f". Recomendación: {f.recommendation}"
        lines.append(line)
    return "\n".join(lines)


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not Settings.AZURE_OPENAI_ENDPOINT or not Settings.AZURE_OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Azure OpenAI no configurado")

    client = AzureOpenAI(
        azure_endpoint=Settings.AZURE_OPENAI_ENDPOINT,
        api_key=Settings.AZURE_OPENAI_API_KEY,
        api_version="2024-02-01",
    )

    context = _build_context(body.findings or [])
    user_content = f"{context}\n\n{body.message}".strip() if context else body.message

    try:
        response = client.chat.completions.create(
            model=Settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        reply = response.choices[0].message.content or ""
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al llamar a Azure OpenAI: {e}")
