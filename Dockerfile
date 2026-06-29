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
COPY main.py ./

# Usar el Python del virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Puerto del health endpoint (FastAPI — tarea siguiente)
EXPOSE 8000

# El entrypoint corre el consumer
CMD ["python", "-m", "consumer.rabbit_consumer"]
