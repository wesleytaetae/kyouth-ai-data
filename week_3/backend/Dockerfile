FROM python:3.14.4-bookworm

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY week_3/backend/pyproject.toml week_3/backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY week_3/backend/src ./src
COPY week_2 ./week_2

ENV PYTHONPATH=/app/src:/app/week_2

EXPOSE 8001

ENTRYPOINT ["uv", "run", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8001"]
