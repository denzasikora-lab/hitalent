# hitalent

REST API for departments (tree) and employees, built with **FastAPI**, **SQLAlchemy 2**, **Alembic**, and **PostgreSQL**. Intended as a take-home assignment; **authentication is intentionally omitted** (see security note below).

Repository: https://github.com/denzasikora-lab/hitalent

## Features

- Departments with optional `parent_id` (tree, multiple roots allowed).
- Employees belong to a department.
- `GET /departments/{id}` returns nested `children` up to `depth` (1–5) and `employees` (sorted by `created_at`, then `full_name`).
- `PATCH /departments/{id}` can rename and/or move a department (including `parent_id: null` for root); cycles and self-parent moves return **409 Conflict**.
- `DELETE /departments/{id}` supports `mode=cascade` (DB-level cascade) or `mode=reassign` (leaf-only: moves employees, rejects if children exist).
- Timestamps are stored in **UTC** and serialized as ISO-8601 with a `Z` suffix.

## Run with Docker Compose

```bash
docker compose up --build
```

API: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`

The `web` service runs `alembic upgrade head` before starting Uvicorn.

## Local development (without Docker for the app)

1. Start PostgreSQL 16+ and create a database (or use only the `db` service from Compose).
2. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed.
3. Create a virtualenv (Python **3.12** recommended) and install dependencies:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Apply migrations and run the API:

   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

## Tests

PostgreSQL must be reachable at `DATABASE_URL` (defaults to `postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent`).

```bash
docker compose up -d db
export DATABASE_URL=postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent
pytest -q
```

Or inside the built image (after DB is up):

```bash
docker compose run --rm -e DATABASE_URL=postgresql://hitalent:hitalent@db:5432/hitalent web sh -c "alembic upgrade head && pytest -q"
```

## Security note

This service exposes write operations without auth, which is acceptable for the scope of the assignment. For production, add authentication, authorization, rate limiting, and hardening as appropriate.
