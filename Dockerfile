# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar archivos de dependencias primero (mejor cache)
COPY pyproject.toml uv.lock ./

# Instalar dependencias en un virtualenv dentro del contenedor
RUN uv sync --frozen --no-dev

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copiar el virtualenv del builder
COPY --from=builder /app/.venv /app/.venv

# Copiar el código
COPY consumer/ ./consumer/
COPY api/ ./api/
COPY main.py ./

# Usar el Python del virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Puerto de la API (FastAPI) — también arranca el consumer de RabbitMQ
# en un hilo de fondo (ver api/main.py lifespan)
EXPOSE 8000

# El entrypoint corre uvicorn directamente desde el venv (ya está en el
# PATH gracias a la línea de ENV arriba) — no se necesita "uv run" aquí,
# porque uv no se copia a este stage, solo el virtualenv que ya generó.
# Uvicorn arranca el consumer de RabbitMQ en un hilo de fondo al iniciar
# (ver api/main.py lifespan).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]