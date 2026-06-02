# CrimeGPT — End-to-End Demo Script

A single walkthrough: **log in → create a case → AI-suggest sections → confirm
the right ones → generate all 7 documents (docx + PDF) → diary timeline + a
manual event.**

> **Heads-up (state of the build).** The **browser UI** today covers: sign in,
> create a case, generate the **Seizure Receipt**, and the **diary** (view + add
> a step). The other capabilities — **AI section suggestions**, **confirming a
> section**, and generating the **other 6 documents / PDF** — exist as **APIs**
> but have **no buttons yet**, so those steps are shown as terminal commands.
> Steps are tagged **[UI]**, **[Terminal]**, or **[Admin]**. See ROUGH EDGES at
> the bottom.

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

## 3. AI-suggest applicable BNS sections — **[Terminal]** *(no UI button yet)*

```sh
curl -s -X POST "$B/api/cases/$CID/suggest-sections/?n=6" -H "Authorization: Token $TOK" | python -m json.tool
```

Expected (similarity-ranked; local embeddings, no external API):

| BNS | Title | ~score |
|---|---|---|
| 307 | Theft after preparation … causing death/hurt | 0.41 |
| 304 | Snatching | 0.37 |
| **305** | **Theft in a dwelling house / shop** | 0.34 |
| **334** | **Dishonestly breaking open receptacle** | 0.34 |
| 309 | Robbery | 0.31 |
| **317** | **Stolen property** | 0.30 |

These are written as `CaseSection` rows with `suggested_by_ai=True,
confirmed=False` — **nothing is auto-applied**.

## 4. Confirm the *right* sections — **[Admin]** *(no confirm API/UI yet)*

The officer keeps the applicable ones and ignores the off-target suggestions.
For break-in + theft + recovered goods: confirm **305, 334, 317**; leave 307 /
304 / 309 unconfirmed.

1. http://localhost:8000/admin/ → sign in as `admin`.
2. **Core › Case sections** → filter/open the rows for this case.
3. Tick **Confirmed** on **BNS 305, 334, 317** → **Save**.

> Fast path (equivalent):
> ```sh
> docker compose exec web python manage.py shell -c "from core.models import CaseSection as C; \
>   print(C.objects.filter(case_id=$CID, section__section_number__in=['305','317','334']).update(confirmed=True))"
> ```

## 5. Record the arrest — **[Terminal]**

So the Remand has arrest details and the case shows ARREST:

```sh
docker compose exec web python manage.py shell -c "
from core.models import Case, DiaryEvent; from django.utils import timezone; import datetime
c=Case.objects.get(id=$CID); c.status='ARREST'; c.save()
DiaryEvent.objects.create(case=c, timestamp=timezone.now(), event_type='ARREST',
  description='Accused Imran Shaikh arrested near Kalupur bus stand.', actor=c.io)"
```

## 6. Generate the Seizure Receipt — **[UI]**

1. On the **✓ Case created** screen, click **Generate Seizure Receipt**.
2. You get **✓ Generated version 1**, the `.docx` downloads, and the **New diary
   entry** shows. (Click again → version 2; earlier versions are kept.)

## 7. Generate the other 6 documents (+ a couple as PDF) — **[Terminal]** *(no UI buttons yet)*

```sh
for d in remand:pdf custody medical panchanama faceid chargesheet:pdf; do
  doc=${d%%:*}; fmt=${d#*:}; q=""; [ "$fmt" != "$doc" ] && q="?format=$fmt"
  curl -s -X POST "$B/api/cases/$CID/documents/$doc/$q" -H "Authorization: Token $TOK" \
    | python -c "import sys,json;x=json.load(sys.stdin);print(f\"{x['doc_type']:<12} v{x['version']}  {(x.get('pdf_url') or x['docx_url']).split('/')[-1]}\")"
done
```

Expected — all seven now exist on the case; **Remand Request** and **Purvani
Chargesheet** also have a PDF. The confirmed sections (305/334/317) appear in the
Remand/Custody/Chargesheet; the unconfirmed ones never do.

Download any PDF (e.g. the Remand):
```sh
curl -s "$B/media/documents/remand_request_case${CID}_v1.pdf" -o remand.pdf && echo "saved remand.pdf"
```

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
