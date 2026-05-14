# hitalent

REST API for departments and employees, built with **FastAPI**, **SQLAlchemy 2**, **Alembic**, and **PostgreSQL**.

This project was created as a take-home assignment. Authentication is intentionally omitted for the scope of the task. See the security note below.

Repository: https://github.com/denzasikora-lab/hitalent

---

## Features

- Departments are stored as a tree structure using optional `parent_id`.
- Multiple root departments are allowed.
- Employees belong to a department.
- `GET /departments/{id}` returns a department with:
  - nested `children` up to a configurable `depth` from 1 to 5
  - `employees` sorted by `created_at`, then by `full_name`
- `PATCH /departments/{id}` supports:
  - renaming a department
  - moving a department to another parent
  - setting `parent_id: null` to make it a root department
- Invalid moves that create cycles or make a department its own parent return **409 Conflict**.
- `DELETE /departments/{id}` supports:
  - `mode=cascade` — removes the department with all dependent records
  - `mode=reassign` — allowed only for leaf departments; employees are moved, but deletion is rejected if children exist
- All timestamps are stored in **UTC** and serialized in ISO-8601 format with a `Z` suffix.

---

## Project structure

- `app/` — application code
- `alembic/` — database migrations
- `tests/` — automated tests
- `docker-compose.yml` — local development environment

---

## Requirements

- Docker and Docker Compose
- PostgreSQL 16+ for local development without Docker
- Python 3.12 recommended for running the app locally

---

## Run with Docker Compose

Start the full stack:

```bash
docker compose up --build
```

Useful endpoints:

- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The `web` service runs `alembic upgrade head` before starting Uvicorn.

---

## Local development without Docker for the app

1. Start PostgreSQL 16+.
2. Create the database if needed.
3. Copy `.env.example` to `.env`.
4. Adjust `DATABASE_URL` if your PostgreSQL settings differ.
5. Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

6. Install dependencies:

```bash
pip install -r requirements.txt
```

7. Apply migrations and start the app:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Database commands

Open PostgreSQL shell:

```bash
docker compose exec db psql -U hitalent -d hitalent
```

Common SQL checks:

```sql
\dt
SELECT * FROM departments;
SELECT * FROM employees;
```

Check Alembic version:

```bash
docker compose exec db psql -U hitalent -d hitalent -c "select * from alembic_version;"
```

List tables:

```bash
docker compose exec db psql -U hitalent -d hitalent -c "\dt"
```

---

## Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "next change"
```

Apply migrations:

```bash
alembic upgrade head
```

Run the same commands inside Docker:

```bash
docker compose exec web alembic revision --autogenerate -m "next change"
docker compose exec web alembic upgrade head
```

---

## Tests

Make sure PostgreSQL is reachable at `DATABASE_URL`.

Default local connection:

```bash
postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent
```

Run tests locally:

```bash
docker compose up -d db
export DATABASE_URL=postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent
pytest -q
```

Run tests inside the built container:

```bash
docker compose run --rm \
  -e DATABASE_URL=postgresql://hitalent:hitalent@db:5432/hitalent \
  web sh -c "alembic upgrade head && pytest -q"
```

Or directly in the running container:

```bash
docker compose exec web pytest
```

---

## Docker commands

Build without cache:

```bash
docker compose build --no-cache web
```

Start services:

```bash
docker compose up
```

Stop services:

```bash
docker compose down
```

Check running containers:

```bash
docker compose ps
```

---

## Security note

This service exposes write operations without authentication. That is acceptable for the scope of the assignment.

For production use, add:

- authentication
- authorization
- rate limiting
- request validation hardening
- audit logging
- stronger operational security controls

---

## API notes

- Department tree depth is limited to prevent overly expensive responses.
- Recursive relations are validated to avoid cyclic dependencies.
- Reassignment deletion is only allowed for leaf departments.
- Children always take precedence over reassignment rules.

---

## Example environment variables

```env
DATABASE_URL=postgresql://hitalent:hitalent@db:5432/hitalent
```

For local host access:

```env
DATABASE_URL=postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent
```
