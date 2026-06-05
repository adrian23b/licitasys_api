# SEACE Opportunities Backend

Production-ready FastAPI backend for indexing and monitoring procurement opportunities from Peru's SEACE JSON API.

The service consumes the internal JSON endpoint directly:

```text
GET https://prod4.seace.gob.pe:8086/api/oportunidades/{codObjeto}/{codDepartamento}/{keyword}/{codTipoProceso}
```

No Selenium, Playwright, BeautifulSoup, or HTML scraping is used.

## Features

- Async FastAPI REST API
- Async SQLAlchemy 2.0 persistence
- PostgreSQL JSONB storage for raw SEACE payloads
- Duplicate prevention with unique `seace_id`
- Retryable `httpx.AsyncClient` SEACE client
- Normalization for SEACE dates, nulls, malformed rows, and noisy text
- APScheduler periodic crawling
- Alembic migrations
- Docker Compose with API and PostgreSQL
- Extension points for AI classification, embeddings, semantic search, and alerts
- Pytest unit, API, and client tests

## Project Structure

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── clients/
│   ├── scheduler/
│   ├── utils/
│   └── main.py
├── alembic/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

Copy the sample environment file and adjust values:

```bash
cp .env.example .env
```

Environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | Async PostgreSQL URL | `postgresql+asyncpg://seace:seace@postgres:5432/seace` |
| `SEACE_BASE_URL` | SEACE host | `https://prod4.seace.gob.pe:8086` |
| `CRAWLER_INTERVAL` | Scheduler interval in seconds | `3600` |
| `CRAWLER_KEYWORDS` | Comma-separated scheduled keywords | `software,cloud,firewall,ciberseguridad` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SEACE_TIMEOUT_SECONDS` | HTTP timeout | `20` |
| `SEACE_MAX_RETRIES` | HTTP retry attempts | `3` |

## Run With Docker

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Interactive API docs:

```text
http://localhost:8000/docs
```

## Deploy To Fly.io

Create and attach a Fly Postgres database so Fly injects `DATABASE_URL` as an app secret:

```bash
fly postgres create
fly postgres attach --app <api-app> <postgres-app>
fly secrets list --app <api-app>
fly deploy --app <api-app>
```

Deploy from this `backend/` directory. The Docker image excludes local `.env` files, so production uses the `DATABASE_URL` provided by Fly instead of a local PostgreSQL URL.
The app also sets `ENVIRONMENT=production` in the container so `.env` is ignored at runtime.

## Local Development

Create a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start PostgreSQL with Docker:

```bash
docker compose up -d postgres
```

Run migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

## API Examples

Crawl one keyword:

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"keyword":"software"}'
```

Crawl multiple keywords:

```bash
curl -X POST http://localhost:8000/crawl/bulk \
  -H "Content-Type: application/json" \
  -d '{"keywords":["software","cloud","firewall","ciberseguridad"]}'
```

List stored opportunities:

```bash
curl "http://localhost:8000/opportunities?keyword=software&limit=20&offset=0"
```

Filter by entity and date:

```bash
curl "http://localhost:8000/opportunities?entity=LIMA&date_from=2026-05-01T00:00:00-05:00&date_to=2026-06-30T23:59:59-05:00"
```

Get one opportunity:

```bash
curl http://localhost:8000/opportunities/1
```

## Migrations

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback one migration:

```bash
alembic downgrade -1
```

## Testing

```bash
pytest
```

The test suite covers:

- SEACE date and text normalization
- SEACE client JSON normalization with mocked HTTP
- Health endpoint
- Crawl endpoint behavior with mocked persistence

## Future Extensions

The architecture includes dedicated interfaces for:

- AI opportunity classification: `app/services/classification.py`
- Embedding generation and vector-store upserts: `app/services/embeddings.py`
- Telegram, Discord, email, or webhook alerts: `app/services/alerts.py`

These can be wired into the crawler after insertion or into a separate async worker without changing the SEACE client or repository contracts.
