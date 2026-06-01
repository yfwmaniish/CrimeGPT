# CrimeGPT — Week 1 Build Plan & Schema Spec

> Handoff document for the team and for Claude Code. The goal of Week 1 is **one working vertical slice**: create a case in the UI → enter parties and seized items → click a button → download a real `.docx`. If that works end-to-end, the rest of the project is "more of the same." Do **not** try to build all seven documents or the AI module this week.

---

## Stack (locked)

- **Backend:** Django + Django REST Framework
- **DB:** PostgreSQL (with `pgvector` extension — we'll use it for legal retrieval later, install now)
- **Frontend:** React (Vite)
- **Documents:** `docxtpl` (Word templates) + `docx2pdf`/LibreOffice for PDF export
- **Audit/history:** `django-simple-history`
- **Auth/RBAC:** Django's built-in auth + a `role` field (IO / SHO / Legal Advisor)
- **Dev env:** Docker Compose (web + db) so all four machines run identically

---

## The Case schema (the spine — build this first, agree before coding)

Everything depends on this. One canonical `Case` object; every document is a template view over it. No data is entered twice.

```python
# core/models.py  (spec — Claude Code should implement + migrate)

class User(AbstractUser):
    ROLE = [("IO", "Investigating Officer"), ("SHO", "Station House Officer"),
            ("LEGAL", "Legal Advisor")]
    role = CharField(choices=ROLE)
    police_station = CharField(blank=True)

class Case(models.Model):
    STATUS = [("COMPLAINT", "Complaint"), ("INVESTIGATION", "Investigation"),
              ("ARREST", "Arrest"), ("CHARGESHEET", "Chargesheet Filed")]
    case_number      = CharField(unique=True)        # internal id
    fir_number       = CharField()
    fir_date         = DateField()
    police_station   = CharField()
    status           = CharField(choices=STATUS, default="COMPLAINT")
    incident_date    = DateTimeField(null=True)
    incident_place   = TextField()
    incident_narrative = TextField()                 # free text -> feeds legal AI later
    io               = ForeignKey(User, related_name="cases")
    created_at       = DateTimeField(auto_now_add=True)
    history          = HistoricalRecords()           # simple-history

class Party(models.Model):                           # ONE model for every person
    ROLE = [("VICTIM","Victim/Complainant"), ("ACCUSED","Accused"),
            ("WITNESS","Witness")]
    case        = ForeignKey(Case, related_name="parties")
    role        = CharField(choices=ROLE)
    name        = CharField()
    parent_name = CharField(blank=True)              # father's/husband's name
    age         = IntegerField(null=True)
    gender      = CharField(blank=True)
    address     = TextField(blank=True)
    phone       = CharField(blank=True)
    id_type     = CharField(blank=True)              # Aadhaar / etc.
    id_number   = CharField(blank=True)
    history     = HistoricalRecords()

class SeizedItem(models.Model):
    case          = ForeignKey(Case, related_name="seized_items")
    description   = TextField()
    quantity      = CharField(blank=True)
    seized_from   = ForeignKey(Party, null=True)     # usually the accused
    seizure_date  = DateField(null=True)
    seizure_place = TextField(blank=True)
    history       = HistoricalRecords()

class Statement(models.Model):
    case          = ForeignKey(Case, related_name="statements")
    party         = ForeignKey(Party)
    text          = TextField()
    recorded_date = DateField(null=True)
    history       = HistoricalRecords()

class LegalSection(models.Model):                    # REFERENCE data, not per-case
    code            = CharField()                    # "BNS" / "BNSS" / "BSA"
    section_number  = CharField()
    title           = CharField()
    text            = TextField()
    ipc_equivalent  = CharField(blank=True)          # the IPC->BNS bridge
    # embedding = VectorField(...)  <-- added in Week 2 for retrieval

class CaseSection(models.Model):                     # which sections apply to a case
    case            = ForeignKey(Case, related_name="applied_sections")
    section         = ForeignKey(LegalSection)
    suggested_by_ai = BooleanField(default=False)
    confirmed       = BooleanField(default=False)    # officer verifies (key principle)

class DiaryEvent(models.Model):                      # the case diary = append-only log
    case        = ForeignKey(Case, related_name="diary")
    timestamp   = DateTimeField()
    event_type  = CharField()    # "FIR_REGISTERED", "STATEMENT_RECORDED", "SEIZURE", "ARREST"...
    description = TextField()
    actor       = ForeignKey(User, null=True)

class Document(models.Model):
    DOC_TYPE = [("CHARGESHEET","Purvani Chargesheet"), ("MEDICAL","Medical Treatment Letter"),
                ("REMAND","Remand Request"), ("SEIZURE","Seizure Receipt"),
                ("CUSTODY","Court Custody Letter"), ("PANCHANAMA","Accused Panchanama"),
                ("FACEID","Face Identification Form")]
    case         = ForeignKey(Case, related_name="documents")
    doc_type     = CharField(choices=DOC_TYPE)
    file         = FileField()
    version      = IntegerField(default=1)
    generated_at = DateTimeField(auto_now_add=True)
```

**Design principles to enforce all month:**
- Enter every fact **once**, on the Case object. Documents read from it.
- The case diary is **append-only** — events get logged, never edited.
- Legal sections are **suggested by AI, confirmed by a human** (`confirmed` flag). Never auto-write a section into a document unconfirmed.

---

## How the 7 documents map onto the schema

This proves the "no duplication" claim — each doc is just a different slice of the same data.

| Document | Pulls from |
|---|---|
| Seizure Receipt | Case + SeizedItems + seizing officer (User) + accused (Party) |
| Medical Treatment Letter | Case + Party (victim or accused) + incident details |
| Remand Request | Case + accused Party + confirmed CaseSections + arrest DiaryEvent |
| Court Custody Letter | Case + accused Party + confirmed CaseSections |
| Accused Panchanama | Case + accused Party + witness Parties + SeizedItems |
| Face Identification Form | Case + accused Party + photo |
| Purvani Chargesheet | Everything — Case + all Parties + CaseSections + SeizedItems + Statements + diary summary |

---

## Day-by-day (Week 1)

**Day 1 — Setup + schema agreement**
- Repo, Docker Compose (Django + Postgres + pgvector), React/Vite skeleton.
- All four people read this doc and agree on the schema. Implement models above + run migrations.
- Turn on Django admin — it gives you a working data interface for free.

**Day 2 — API + admin**
- DRF serializers + viewsets: full CRUD for `Case` with nested `Party`, `SeizedItem`, `Statement`.
- Confirm you can create a complete case via the API and see it in Django admin.
- Set up `django-simple-history` and the `User.role` field.

**Day 3 — Ingest legal data + first template**
- Script to load **BNS sections** into `LegalSection` from indiacode.nic.in / the Kaggle/IEEE CSV, including `ipc_equivalent`. (Just BNS this week; BNSS/BSA next week.)
- Build **one** `docxtpl` template — start with **Seizure Receipt** (fewest fields, fastest win).

**Day 4 — Document generation endpoint**
- API endpoint: `POST /api/cases/{id}/documents/seizure/` → fills the template from case data → saves a `Document` → returns a download URL.
- Verify the generated `.docx` opens correctly with real data in it.

**Day 5 — Minimal React + internal demo**
- React screens: create/edit a case, add parties + seized items, "Generate Seizure Receipt" button, download link.
- **Vertical-slice demo to yourselves.** If a teammate can create a case in the browser and download a correct receipt, Week 1 is done.

---

## Week 1 "Definition of Done"

A non-technical person can: open the app → create a case → add an accused and two seized items → click one button → download a `.docx` seizure receipt with all that data correctly filled in. Nothing else needs to work yet.

---

## Kickoff prompts for Claude Code

Feed these one at a time (don't ask for everything at once — let it build incrementally and review each step):

1. *"Set up a Django + DRF + PostgreSQL project with Docker Compose, and a Vite React frontend in a `/frontend` folder. Enable the pgvector extension on Postgres."*
2. *"Implement the models in WEEK1_PLAN.md exactly, add HistoricalRecords from django-simple-history to the marked models, make migrations, and register everything in the Django admin."*
3. *"Add DRF serializers and viewsets for full CRUD on Case with nested Party, SeizedItem, and Statement. Write a couple of API tests."*
4. *"Write a management command that loads BNS sections from this CSV into the LegalSection model, including the ipc_equivalent field."* (attach the CSV)
5. *"Create a docxtpl template for a Seizure Receipt and an endpoint POST /api/cases/{id}/documents/seizure/ that fills it from case data, saves a Document, and returns a download URL."*
6. *"Build a minimal React flow: create a case, add parties and seized items, and a button that calls the seizure endpoint and downloads the file."*

**Tip:** keep this file in the repo root and tell Claude Code to read it at the start of each session so it stays consistent with the schema.
