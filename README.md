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

## Frontend — the Week 1 flow (Day 5)

The React app (Vite) implements the full vertical slice: **sign in → create a
case with parties and seized items → Generate Seizure Receipt → download it**,
with the returned version number and the new diary entry shown on screen.

```sh
# 1. Create demo accounts (once):
docker compose exec web python manage.py seed_demo_users
# 2. Run the frontend:
cd frontend
cp .env.example .env.local   # optional; defaults to http://localhost:8000
npm install
npm run dev                  # http://localhost:5173
```

Open http://localhost:5173 and sign in with a demo account:

| Username | Password   | Role | Can generate documents? |
|----------|------------|------|--------------------------|
| `io`     | `io12345`  | Investigating Officer | ✅ |
| `sho`    | `sho12345` | Station House Officer  | ✅ |
| `legal`  | `legal12345` | Legal Advisor        | ❌ (shows the clean 403 message) |

**Auth:** the SPA uses DRF **token auth** — `POST /api/auth/login/` returns a
token stored in `localStorage` and sent as `Authorization: Token …`. This avoids
cross-origin session/CSRF complexity. Session auth still backs the admin and the
browsable API.

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

### Generate a Seizure Receipt (Day 4)

```
POST /api/cases/{id}/documents/seizure/
```

Renders the Seizure Receipt from the case (its accused party, seized items, and
the case's IO as seizing officer), saves a `Document`, logs a `DiaryEvent`, and
returns a download URL:

```json
{ "id": 5, "doc_type": "SEIZURE", "version": 1,
  "download_url": "http://localhost:8000/media/documents/seizure_receipt_case3_v1.docx",
  "generated_at": "2026-06-02T..." }
```

- **Roles:** only **IO** and **SHO** may generate (others get `403`).
- **Versioning:** regenerating never overwrites — it creates a new `Document`
  with `version` incremented (v1, v2, ...), keeping the full history.

### All document endpoints (Week 2, Track B — all 7 built)

Every document follows the same pattern (template-from-code → context-builder →
shared `_finalize_document`: versioned, IO/SHO-only, logs a `DiaryEvent`).

| Endpoint | Document | Pulls from |
|---|---|---|
| `POST /api/cases/{id}/documents/seizure/`     | Seizure Receipt      | accused/seized-from + seized items |
| `POST /api/cases/{id}/documents/remand/`      | Remand Request (PC)  | accused + **confirmed** sections + arrest diary event |
| `POST /api/cases/{id}/documents/custody/`     | Court Custody Letter | accused + **confirmed** sections |
| `POST /api/cases/{id}/documents/medical/`     | Medical Treatment    | victim → accused → blank + incident |
| `POST /api/cases/{id}/documents/panchanama/`  | Accused Panchanama   | accused + witnesses + seized items |
| `POST /api/cases/{id}/documents/faceid/`      | Face Identification  | accused + photo placeholder box (see TODO) |
| `POST /api/cases/{id}/documents/chargesheet/` | Purvani Chargesheet  | everything (the superset) |

Only **confirmed** `CaseSection`s ever reach a document. Word templates are built
from code — regenerate with `python manage.py build_doc_templates`.

**PDF export (Track C):** add `?format=pdf` to any generation endpoint to also
render a PDF (LibreOffice headless) and store it on the `Document` alongside the
`.docx`. The response then carries `docx_url`, `pdf_url`, and `download_url` (the
PDF when `format=pdf`, else the docx):

```
POST /api/cases/{id}/documents/seizure/?format=pdf
```

Run the API tests:

```sh
docker compose exec web python manage.py test core
```

## Legal data — BNS sections (Day 3)

Reference data for the `LegalSection` model. **All three new criminal codes are
loaded** (`LegalSection.code` = `BNS` / `BNSS` / `BSA`), so section suggestions
rank across all of them:

| Code | Act | Replaces | Sections | Scraper |
|------|-----|----------|----------|---------|
| BNS  | Bharatiya Nyaya Sanhita, 2023 | Indian Penal Code | 358 | `scrape_bns` |
| BNSS | Bharatiya Nagarik Suraksha Sanhita, 2023 | CrPC | 531 | `scrape_bnss` |
| BSA  | Bharatiya Sakshya Adhiniyam, 2023 | Indian Evidence Act | 170 | `scrape_bsa` |

Section text comes verbatim from **India Code** (indiacode.nic.in); the
**`ipc_equivalent`** column is a generic *old-act equivalent* string — IPC for
BNS, **CrPC for BNSS, Indian Evidence Act for BSA** — sourced from the **NCRB**
Compendium correspondence tables. (Column name kept as `ipc_equivalent` so the
loader is unchanged.)

```sh
# Scrape each act into a CSV, then load (loader is idempotent):
docker compose exec web python manage.py scrape_bns   --out data/bns_sections.csv
docker compose exec web python manage.py scrape_bnss  --out data/bnss_sections.csv
docker compose exec web python manage.py scrape_bsa   --out data/bsa_sections.csv
docker compose exec web python manage.py load_legal_sections data/bns_sections.csv
docker compose exec web python manage.py load_legal_sections data/bnss_sections.csv
docker compose exec web python manage.py load_legal_sections data/bsa_sections.csv
docker compose exec web python manage.py embed_legal_sections   # embeds any new rows
```

Pre-scraped CSVs for all three are committed under `backend/data/`, so a fresh
setup can skip scraping and just `load_legal_sections` each + `embed_legal_sections`.

**Fallback** (if a source site changes/blocks): the scraper degrades gracefully —
`--no-ipc` skips the IPC table, `--ipc-map FILE.csv` supplies it locally. If
indiacode itself is unreachable, manually download a CSV with columns
`code, section_number, title, text, ipc_equivalent` and load it directly with
`load_legal_sections`.

## Legal section suggestions — local AI retrieval (Week 2, Track A)

Suggests applicable BNS sections for a case by semantic similarity, fully local
(no external API). Section text is embedded with the `all-MiniLM-L6-v2`
sentence-transformer (384-d, baked into the image) and searched with pgvector
cosine distance.

```sh
# Embed the loaded sections (idempotent; --force re-embeds, --limit N for testing):
docker compose exec web python manage.py embed_legal_sections
```

```
POST /api/cases/{id}/suggest-sections/        # optional ?n=5
```

Embeds the case's `incident_narrative`, returns the top N sections with
similarity scores, **and records each as a `CaseSection` with
`suggested_by_ai=True, confirmed=False`**:

```json
{ "count": 5, "results": [
  { "section_number": "305", "title": "Theft in a dwelling house...",
    "ipc_equivalent": "380", "similarity": 0.41,
    "suggested_by_ai": true, "confirmed": false, "case_section_id": 1 } ]}
```

**Safety principle (load-bearing):** AI only *suggests*. Sections are never
auto-confirmed, re-running never duplicates or un-confirms existing rows, and no
unconfirmed section is ever written into a document. Officer confirmation is a
separate explicit action.

## Case diary timeline (Week 2, Track D)

```
GET  /api/cases/{id}/diary/   # chronological events (any authenticated user)
POST /api/cases/{id}/diary/   # add a manual step (IO/SHO only)
```

The diary mixes **auto-logged** system events (e.g. `DOCUMENT_GENERATED`) with
**manual** entries an officer adds (`{"event_type": "WITNESS_INTERVIEWED",
"description": "..."}` — `event_type` defaults to `MANUAL`). The React case view
renders it as a vertical timeline; adding a step is gated to IO/SHO (same write
RBAC as document generation), while anyone signed in can view.

## Landmark judgments / case laws (Phase 2)

Hand-curated landmark Indian judgments (`backend/data/landmark_judgments.csv`),
each with a verified citation, plain-language summary, one-line principle, links
to the BNS sections it relates to, and a `source`. **Verbatim/curated only** —
citations and holdings come from authoritative sources, never generated.

```sh
docker compose exec web python manage.py load_landmark_judgments data/landmark_judgments.csv
docker compose exec web python manage.py embed_landmark_judgments
```

Two retrieval surfaces on the case view (between Sections and Documents):
- **By confirmed sections** — `GET /api/cases/{id}/judgments/` lists judgments
  linked to the case's confirmed sections.
- **By narrative** — `POST /api/cases/{id}/suggest-judgments/` ranks judgments by
  similarity to the incident narrative (returns citation + one-line principle).

Same **AI suggests, officer applies** rule: the officer marks a judgment applied
via `POST /api/cases/{id}/judgments/{judgment_id}/apply/` (IO/SHO only). **Only
applied judgments** appear in the **Relevant Case Laws** section of the Remand
Request and Purvani Chargesheet — mirroring confirmed sections. The set is
curated/verified and easy to extend (add rows to the CSV, reload, re-embed).

## Multilingual support — English / Hindi / Gujarati

- **UI** is fully internationalized with `react-i18next` — strings live in
  [frontend/src/locales/](frontend/src/locales/) (`en.json`, `hi.json`,
  `gu.json`). The header language switcher persists the choice to `localStorage`.
- **Input** is stored verbatim in UTF-8 — names, addresses, and narratives typed
  in Devanagari or Gujarati round-trip with no transliteration (test:
  `MultilingualTests.test_devanagari_and_gujarati_input_round_trips`).
- **Documents (proof-of-concept):** the **Seizure Receipt** has translated
  templates (`seizure_receipt_hi.docx`, `seizure_receipt_gu.docx`). Pass
  `?lang=en|hi|gu` to its generation endpoint to pick one (default `en`); the UI
  sends the current language automatically:

  ```
  POST /api/cases/{id}/documents/seizure/?lang=gu
  ```

  **Established pattern for the other six documents:** their builders in
  [backend/core/documents.py](backend/core/documents.py) take a `labels` dict and
  build from code — adding Hindi/Gujarati is a **translator-time task** (fill in a
  `labels` dict per language and register the per-language template path), **not a
  code change**. Only labels/boilerplate are translated.

- **Never machine-translated:** BNS section text and document legal body content
  are verbatim only (the Track A accuracy principle). Translated UI and template
  **labels** — yes; translated section/legal **text** — no.

## Documents — Seizure Receipt (Day 3)

The Word template lives at `backend/core/doc_templates/seizure_receipt.docx` and
is **generated from code** ([backend/core/documents.py](backend/core/documents.py)),
so regenerate it rather than hand-editing:

```sh
docker compose exec web python manage.py build_doc_templates
```

`render_seizure_receipt(context)` fills it via docxtpl. The Day 4 API endpoint
will feed it real Case data; `sample_seizure_context()` provides demo data today.

## Useful commands

```sh
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test core              # run tests
docker compose exec web python manage.py scrape_bns             # scrape BNS -> CSV
docker compose exec web python manage.py load_legal_sections F  # load CSV
docker compose exec web python manage.py build_doc_templates    # rebuild .docx templates
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

**Day 3 — complete**
- [x] `scrape_bns` — scrapes all 358 BNS sections from India Code + IPC
      equivalents from the NCRB corresponding-section table → CSV
- [x] `load_legal_sections` — idempotent CSV → `LegalSection` upsert
- [x] Committed pre-scraped CSV (358 sections, 347 IPC-mapped); loaded in DB
- [x] Seizure Receipt `docxtpl` template (generated from code) + renderer
- [x] 11 tests passing (5 API + 5 loader + 1 template render)

**Day 4 — complete**
- [x] `POST /api/cases/{id}/documents/seizure/` renders from real Case data
- [x] Saves a `Document`; regeneration increments `version` (no overwrite)
- [x] Logs a `DiaryEvent` (DOCUMENT_GENERATED) with the acting user
- [x] Restricted to IO/SHO roles; returns a download URL
- [x] 17 tests passing (adds 6: success, SHO allowed, version bump, diary,
      role-forbidden, unauthenticated)

**Day 5 — complete (Week 1 vertical slice done)**
- [x] React: sign in (token auth), create a case with nested parties + seized
      items (assembling `seized_from_index`), Generate Seizure Receipt → download
- [x] Shows the document version and the new diary entry after generation
- [x] Clean message on a 403 (disallowed role); `seed_demo_users` for accounts
- [x] Backend: `/api/auth/login/` + `/api/auth/me/` token endpoints

**Week 1 Definition of Done:** ✅ a non-technical user can open the app, create a
case, add an accused and seized items, click one button, and download a filled
`.docx` Seizure Receipt.
