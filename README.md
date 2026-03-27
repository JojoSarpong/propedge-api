# propedge-api

FastAPI service that exposes PropEdge data via a versioned REST API.

Connects to PropEdge's SQLite database in **read-only** mode. Does not import or clone any PropEdge source code.

## Setup

```bash
cp .env.example .env
# edit .env and set PROPEDGE_DB_PATH to your PropEdge SQLite file

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Environment variables

| Variable | Description |
|---|---|
| `PROPEDGE_DB_PATH` | Absolute path to the PropEdge SQLite database file |
| `PORT` | Port to bind the server (default: 8000) |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/v1/props/today` | Today's player props |
| POST | `/v1/keys/provision` | Provision an API key |

## Docs

Auto-generated docs available at `http://localhost:8000/docs` when running locally.
