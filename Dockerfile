# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.12 && \
    uv sync --frozen --no-dev


FROM debian:bookworm-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3  \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*


COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/.venv /app/.venv

RUN ln -sf /usr/local/bin/python3.12 /app/.venv/bin/python3 && \
    ln -sf /usr/local/bin/python3.12 /app/.venv/bin/python

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"



COPY . .

EXPOSE 8000

CMD ["gunicorn", "main:app", "-b", "0.0.0.0:8000"]