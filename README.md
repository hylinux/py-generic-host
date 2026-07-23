# py_generic_host — Production-Ready Python Generic Host

A .NET Generic Host–style framework for Python with **FastAPI + OpenTelemetry + structlog**.

## Quickstart (local dev)

\`\`\`bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up --build
\`\`\`

- API:        http://localhost:8080/docs
- Health:     http://localhost:8080/healthz/ready
- Prometheus: http://localhost:9090
- Jaeger:     http://localhost:16686
- Grafana:    http://localhost:3000

## Run tests

\`\`\`bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
\`\`\`

## Project layout

See architecture docs in `docs/` (TBD).