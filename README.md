# CrimeGPT

Investigation case-management system for police workflows. One canonical `Case`
object; every legal document is a template view over it (no data entered twice).
See [WEEK1_PLAN.md](WEEK1_PLAN.md) for the build plan and schema spec.

## Stack

- **Backend:** Django 5 + Django REST Framework
- **DB:** PostgreSQL 16 + `pgvector` (vector search lands in Week 2)
- **Frontend:** React (Vite)
- **Audit/history:** `django-simple-history`
- **Auth/RBAC:** Django auth + `User.role` (IO / SHO / Legal Advisor)
- **Dev env:** Docker Compose (web + db)

## Layout

```
.
├── backend/            Django project (crimegpt) + core app
│   ├── crimegpt/       settings, urls, wsgi/asgi
│   ├── core/           models, admin, migrations
│   ├── Dockerfile
│   ├── entrypoint.sh   waits for DB, runs migrations
│   └── requirements.txt
├── frontend/           Vite + React app
├── docker-compose.yml  web + Postgres(pgvector)
└── .env.example        copy to .env
```

## Quick start (Docker)

1. Start **Docker Desktop**.
2. Copy env defaults:
   ```sh
   cp .env.example .env
   ```
3. Bring up the stack (builds the image, starts Postgres, runs migrations):
   ```sh
   docker compose up --build
   ```
   - API + admin: http://localhost:8000/admin/
   - Health check: http://localhost:8000/api/health/
4. Create an admin user (in another terminal):
   ```sh
   docker compose exec web python manage.py createsuperuser
   ```

## Frontend (Vite dev server)

Runs outside Docker for fast HMR:

```sh
cd frontend
cp .env.example .env.local   # optional; defaults to http://localhost:8000
npm install
npm run dev                  # http://localhost:5173
```

The home page pings the backend `/api/health/` endpoint to confirm wiring.

## API (Day 2)

Full CRUD for cases at `/api/cases/`. A single POST creates the case **and** its
nested parties, seized items, and statements in one request. Because nested
parties have no ids yet, seized items and statements reference them by position
in the request's `parties` list (`seized_from_index`, `party_index`). `io`
defaults to the requesting user. Example:

```jsonc
POST /api/cases/
{
  "case_number": "C-001", "fir_number": "FIR-001", "fir_date": "2026-06-01",
  "police_station": "PS-Central", "status": "INVESTIGATION",
  "incident_place": "Market Road", "incident_narrative": "Phone snatched.",
  "parties": [
    {"role": "VICTIM",  "name": "Asha"},
    {"role": "ACCUSED", "name": "Ravi"}
  ],
  "seized_items": [{"description": "Mobile phone", "seized_from_index": 1}],
  "statements":   [{"party_index": 0, "text": "I saw the theft."}]
}
```

`PUT` replaces a nested collection when its key is present; `PATCH` without that
key leaves it untouched. See [backend/core/serializers.py](backend/core/serializers.py)
for the full contract.

Run the API tests:

```sh
docker compose exec web python manage.py test core
```

## Useful commands

```sh
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test core   # run tests
docker compose down            # stop
docker compose down -v         # stop + wipe the database volume
```

## Status

**Day 1 — complete**
- [x] Docker Compose: Django web + Postgres(pgvector)
- [x] All models from the schema spec, with history on Case/Party/SeizedItem/Statement
- [x] Custom `User` with `role`
- [x] Everything registered in Django admin
- [x] pgvector extension enabled via migration
- [x] Vite React skeleton wired to the API

**Day 2 — complete**
- [x] DRF serializers + `CaseViewSet` (full CRUD) at `/api/cases/`
- [x] Nested write support for Party/SeizedItem/Statement (create + update)
- [x] 5 API tests passing (create-in-one-request, nested update, partial update,
      bad-index rollback, delete cascade)

**Next (Day 3):** load BNS sections into `LegalSection` (CSV pending) + first
`docxtpl` Seizure Receipt template.
