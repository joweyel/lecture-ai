FROM python:3.13-slim

# uv instead of pip
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

ENV HF_HOME=/tmp/
ENV TORCH_HOME=/tmp/
ENV OMP_NUM_THREADS=4
RUN docling-tools models download layout

EXPOSE 5000
CMD ["uvicorn", "main:app", \
    "--host", "0.0.0.0", \
    "--port", "5000", \
    "--reload"]
