# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv==0.5.13
COPY pyproject.toml ./
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e .

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH"
COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/
COPY app/ ./app/
COPY pyproject.toml ./
RUN useradd -m -u 10001 appuser
USER appuser
EXPOSE 8080 9464
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/healthz/live', timeout=2).status==200 else 1)"
ENTRYPOINT ["python", "-m", "app.main"]
