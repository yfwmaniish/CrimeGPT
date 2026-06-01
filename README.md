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

## Useful commands

```sh
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose down            # stop
docker compose down -v         # stop + wipe the database volume
```

## Status — Day 1 complete

- [x] Docker Compose: Django web + Postgres(pgvector)
- [x] All models from the schema spec, with history on Case/Party/SeizedItem/Statement
- [x] Custom `User` with `role`
- [x] Everything registered in Django admin
- [x] pgvector extension enabled via migration
- [x] Vite React skeleton wired to the API

**Next (Day 2):** DRF serializers + viewsets for `Case` with nested
`Party`/`SeizedItem`/`Statement`, plus a couple of API tests.
