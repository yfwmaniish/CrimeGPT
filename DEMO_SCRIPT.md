# CrimeGPT — End-to-End Demo Script

A single walkthrough: **log in → create a case → AI-suggest sections → confirm
the right ones → generate all 7 documents (docx + PDF) → diary timeline + a
manual event.**

> **Heads-up (state of the build).** The **browser UI** now covers the whole
> flow: sign in, create a case, **Suggest BNS Sections** + **confirm** them,
> **Generate** any of the 7 documents (DOCX or PDF), and the **diary** (view +
> add a step). The only remaining terminal step is recording an **arrest**
> (status + arrest event), which has no UI yet. Steps are tagged **[UI]** or
> **[Terminal]**.

---

## 0. Prerequisites

```sh
docker compose up -d                                   # backend (web + db)
docker compose exec web python manage.py seed_demo_users   # io / sho / legal
docker compose exec web python manage.py load_legal_sections data/bns_sections.csv  # if not loaded
docker compose exec web python manage.py embed_legal_sections                        # if not embedded
cd frontend && npm install && npm run dev              # http://localhost:5173
```

Demo accounts: **`io` / `io12345`** (Investigating Officer). Admin (for the
confirm step): **`admin` / `admin12345`** at http://localhost:8000/admin/.

### The sample case (use these exact values)

| Field | Value |
|---|---|
| Case number | `CR-118/2026` |
| FIR number | `0145/2026` |
| FIR date | `2026-05-28` |
| Police station | `Navrangpura PS, Ahmedabad` |
| Status | `INVESTIGATION` |
| Place of incident | `Shop No. 14, Relief Road, Ahmedabad` |
| Narrative | *On the night of 27 May 2026, the accused broke open the shutter lock of the complainant's electronics shop on Relief Road and stole four mobile phones and cash from inside the shop. Two passers-by saw the accused fleeing with a bag of stolen goods.* |

**People**
- **Victim** — Rajesh Patel, father Manilal Patel, 45, Male, 22 Ashram Road Ahmedabad, 9825011111
- **Accused** — Imran Shaikh, father Yusuf Shaikh, 26, Male, 5 Jamalpur Ahmedabad
- **Witness** — Kiran Mehta, 8 Relief Road, Ahmedabad
- **Witness** — Suresh Rana, 11 Relief Road, Ahmedabad

**Seized items** (all *Seized from* → Imran Shaikh, 2026-05-28, Relief Road)
1. Four mobile phones (assorted) — qty 4
2. Cash (Indian currency) — Rs. 18,000
3. Iron rod used to break the lock — qty 1

---

## 1. Sign in — **[UI]**

1. Open http://localhost:5173
2. Username `io`, password `io12345` → **Sign in**.
3. Top bar shows **io · Investigating Officer**.

## 2. Create the case — **[UI]**

You land on **My cases** (your cases, newest first — empty on first run). Click
**+ New case**. (Reopening later: just click a row to return to its full view —
suggestions, documents, diary — exactly where you left off.)

1. **Case details**: fill case number, FIR number, FIR date, police station; set
   **Status = INVESTIGATION**; place of incident; paste the narrative.
2. **People involved** → **+ Add person** until you have four rows; set each
   **Role** and fill name / father's name / address (victim: add phone; accused
   + witnesses as above).
3. **Seized items** → **+ Add item** to get three rows; fill description &
   quantity; set **Seized from… → Imran Shaikh (ACCUSED)** on each; date
   `2026-05-28`, place `Relief Road, Ahmedabad`.
4. **Save case**. You land on the **✓ Case created** screen.

> Note the case `id` for the terminal steps. Get a token + id quickly:
> ```sh
> B=http://localhost:8000
> TOK=$(curl -s -X POST $B/api/auth/login/ -H "Content-Type: application/json" \
>   -d '{"username":"io","password":"io12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
> CID=$(curl -s "$B/api/cases/?search=CR-118" -H "Authorization: Token $TOK" \
>   | python -c "import sys,json;print(json.load(sys.stdin)['results'][0]['id'])")
> echo "case $CID"
> ```

## 3. AI-suggest applicable BNS sections — **[UI]**

In the **Applicable BNS sections** panel, click **Suggest BNS Sections**. A
ranked list appears (similarity-scored; local embeddings, no external API):

| BNS | Title | ~match |
|---|---|---|
| 307 | Theft after preparation … causing death/hurt | 41% |
| 304 | Snatching | 37% |
| **305** | **Theft in a dwelling house / shop** | 34% |
| **334** | **Dishonestly breaking open receptacle** | 34% |
| 309 | Robbery | 31% |
| **317** | **Stolen property** | 30% |

Nothing is auto-applied — each row is an unconfirmed suggestion.

## 4. Confirm the *right* sections — **[UI]**

Tick the checkbox on the sections that apply — for break-in + theft + recovered
goods: **305, 334, 317**. Leave 307 / 304 / 309 unticked. Each ticked row turns
green ("✓ confirmed"). Only confirmed sections reach the documents.

## 5. Record the arrest — **[Terminal]** *(no UI yet)*

So the Remand has arrest details and the case shows ARREST:

```sh
docker compose exec web python manage.py shell -c "
from core.models import Case, DiaryEvent; from django.utils import timezone; import datetime
c=Case.objects.get(id=$CID); c.status='ARREST'; c.save()
DiaryEvent.objects.create(case=c, timestamp=timezone.now(), event_type='ARREST',
  description='Accused Imran Shaikh arrested near Kalupur bus stand.', actor=c.io)"
```

## 6. Generate the documents — **[UI]**

In the **Generate documents** panel, all 7 are listed. For each you want:
1. Pick **DOCX** or **PDF** in the dropdown (try PDF on **Remand Request** and
   **Purvani Chargesheet**).
2. Click **Generate** → the file downloads, the row shows **· v1**, and a
   **Download** link appears. Click **Generate** again → **v2** (earlier versions
   are kept, never overwritten).

The confirmed sections (305/334/317) appear in the Remand/Custody/Chargesheet;
the unconfirmed ones never do.

## 8. Diary timeline + add a manual step — **[UI]**

1. Back in the browser on the case screen, scroll to **Case diary** — a vertical
   timeline showing, in order: **Arrest** → the seven **Document Generated**
   events (and any others).
2. Under **Add a step**: Type `WITNESS_INTERVIEWED`, description
   *"Witness Kiran Mehta identified the accused and gave a signed statement."* →
   **Add**. It appears in the timeline immediately.

> (Sign in as `legal` / `legal12345` to show RBAC: the diary is **viewable** but
> **Add a step** is refused — the same gate guards document generation.)

---

## Demo talking points
- **Enter once, reuse everywhere** — every document is rendered from the one Case.
- **AI suggests, officer confirms** — unconfirmed sections never reach a document.
- **Versioned, never overwritten**; **append-only diary**; **verbatim BNS text**
  from India Code; **fully local** retrieval (offline-friendly).
