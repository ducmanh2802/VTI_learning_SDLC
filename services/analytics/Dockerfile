# syntax=docker/dockerfile:1

FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable \
    && useradd --create-home --uid 10001 analytics \
    && chown -R analytics:analytics /app

USER analytics

EXPOSE 8090

CMD ["uvicorn", "analytics.api.main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"]
