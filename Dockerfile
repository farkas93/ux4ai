FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.7

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY aipm_toolkit ./aipm_toolkit
COPY alembic ./alembic
COPY alembic.ini README.md ./

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860
CMD ["python", "-m", "aipm_toolkit.start"]
