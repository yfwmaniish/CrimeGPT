# CrimeGPT — 7-Minute Demo Script

A tight, spoken walkthrough on **pre-seeded data**. The app opens on three
realistic cases (seeded by `seed_demo_cases`), so there is **no case creation in
the demo** — you spend the seven minutes showing the system *think*, not typing
forms. Everything below is a real click path.

Three moments carry the demo — they're marked **★ SIGNATURE MOMENT** with the
exact line to say out loud. Across the run, the four design principles each
surface once in narration (flagged 〔Principle〕).

**Timing (7:00 total):** Opening 0:30 · ★1 Sections 1:30 · ★2 Judgments 1:00 ·
Documents 1:30 · Diary 0:45 · ★3 Gujarati 1:00 · Evidence + close 0:45.

---

## Before you start (not part of the spoken time)

- Backend up and seeded — see the **Setup** section of [README.md](README.md)
  (`seed_demo_users` → load/embed sections → load/embed judgments →
  `seed_demo_cases`). Frontend running at http://localhost:5173.
- Have one **image file** on the desktop for the Evidence upload (any JPG/PNG).
- Browser already at the login page, language set to **English**.
- Demo account: **`io` / `io12345`** (Investigating Officer — can generate).
- The three seeded cases are built from
  [backend/data/sample_firs.md](backend/data/sample_firs.md). The demo uses
  **CR-118/2026** (a shop break-in: accused Imran Shaikh, four phones + cash
  seized, arrest recorded).

---

## 0:00 — Opening (30s)

**Click path:** Sign in as `io` / `io12345` → land on **My cases** (three cases
listed) → click the **CR-118/2026** row to open it.

**Say:**
> "This is CrimeGPT — a case-management system for investigating officers. The
> officer enters the facts of a case *once*, and the system turns those facts
> into every legal document, suggests the law that applies, and keeps an audit
> trail. Here are three live cases. Let's open this shop break-in."

〔Principle — *single Case data pool*〕 (planted here, paid off at Documents.)

---

## 0:30 — ★ SIGNATURE MOMENT 1 — BNS / BNSS / BSA retrieval + match badges (90s)

**Click path:** In the **Applicable BNS sections** panel, click **Suggest BNS
Sections**. A ranked top-6 list appears, each row with a coloured **match-quality
badge** (High / Medium / Lower) and a similarity bar. The acts are mixed —
you'll see BNS *and* BNSS rows. One row, **BNS 305 — "Theft in a dwelling
house"**, already shows a green **✓ confirmed** (the officer kept it earlier).

**Say (verbatim):**
> "I haven't told it a single section number. It read the incident narrative,
> embedded it locally — no cloud, no external API — and searched the *entire* new
> criminal-code library, across all three acts: the Nyaya Sanhita, the Nagarik
> Suraksha Sanhita, and the Sakshya Adhiniyam. These badges rank how strong each
> match is — but look closely: the *top*-ranked hit isn't always the right
> charge. The officer didn't take the machine's number one; they confirmed
> Section 305, the one that actually fits this break-in. That's the whole point —
> **the AI suggests, the officer decides** — and only the green, confirmed
> sections ever reach a document."

**Beat:** tick **BNS 334 — "Dishonestly breaking open receptacle"** to show it
turn green, then untick it — "that's the officer's call, not the machine's."

> *(The case also carries two more confirmed sections, 303 and 331, that rank
> just below the top-6 cut and so aren't on screen here — but they're confirmed,
> and you'll see all three land in the Chargesheet later.)*

〔Principle — *AI suggests, the officer decides*〕

---

## 2:00 — ★ SIGNATURE MOMENT 2 — Relevant judgments / case law (60s)

**Click path:** Scroll to the **Relevant judgments** panel (already populated from
the confirmed sections, with the applied one showing ✓ applied). Click **Suggest
by narrative** — the list re-ranks with quality badges, surfacing landmark case
law matched to *this* incident.

**Say (verbatim):**
> "It doesn't stop at sections — it brings the officer the *case law*. These are
> landmark Indian judgments, matched to this break-in by the same local search.
> Every one is hand-curated: the **citation and the legal principle are verified
> against authoritative reports — the system never invents a case or writes the
> law.** The officer marks the ones that apply, exactly like the sections, and
> only those flow into the Remand and the Chargesheet."

〔Principle — *legal text verbatim from authoritative sources, never generated*〕

---

## 3:00 — Document generation (90s)

**Click path:** In the **Generate documents** panel (all 7 listed):

1. **Remand Request** — type **14** in the *Custody days* box, set the format
   dropdown to **PDF**, click **Generate**. The PDF downloads; the row shows
   **· v1** with a **Download** link.
2. Click **Generate** on Remand again → **· v2** (the v1 file is untouched).
3. **Purvani Chargesheet** — set format to **PDF**, click **Generate** → PDF
   downloads.

**Say:**
> "Every one of these seven documents is filled from the *same case* I never
> re-typed — the parties, the seized phones, the confirmed sections, the applied
> judgment all land in the right places. The Remand even takes the custody days I
> asked for and works back from the arrest date. And regenerating doesn't
> overwrite — that was version one, this is version two, both kept."

〔Principle — *one canonical Case; documents are views over it*〕 (Open the
Chargesheet PDF briefly to show confirmed sections + the applied case law inside.)

---

## 4:30 — Case diary (45s)

**Click path:** Scroll to **Case diary** — a vertical timeline showing, in order,
the **Arrest** event and the **Document Generated** entries from the last step.
Under **Add a step**: Type `WITNESS_INTERVIEWED`, description *"Witness Kiran
Mehta identified the accused and gave a signed statement."* → **Add**. It appears
immediately at the bottom.

**Say:**
> "Everything that happens is logged here in order — the arrest, every document I
> just generated, and steps the officer adds by hand. The diary is append-only:
> entries are never edited or deleted, so the case has an honest, tamper-evident
> history."

〔Principle — *append-only diary; documents versioned, never overwritten*〕

---

## 5:15 — ★ SIGNATURE MOMENT 3 — Multilingual Gujarati Seizure Receipt (60s)

**Click path:** In the **header language switcher**, choose **ગુજરાતી**. The whole
UI flips to Gujarati. Scroll to **Generate documents** → the **જપ્તી રસીદ**
(Seizure Receipt) row → format **DOCX** → **બનાવો** (Generate). Open the
downloaded `seizure_receipt_gu` file.

**Say (verbatim):**
> "An officer in Gujarat shouldn't have to work in English. One switch, and the
> interface is Gujarati — and the Seizure Receipt itself generates in Gujarati,
> with the seized items the officer entered dropped straight in. The labels are
> translated; the facts are the officer's own. We're honest that the Hindi and
> Gujarati wording is still a draft pending native-reviewer sign-off — but the
> pattern is real, and the document is real."

**Beat:** switch the language back to **English** before the close.

---

## 6:15 — Evidence + closing (45s)

**Click path:** Scroll to the **Evidence** panel → choose the image file → caption
*"Iron rod recovered at scene"* → tags `weapon, recovered` → **Upload**. The
thumbnail appears with its caption and tags; the filter box lets you narrow by
tag.

**Say:**
> "Officers can attach photographs of evidence with captions and tags, all on the
> same case. So everything — facts, parties, sections, case law, documents,
> diary, and evidence — lives in one place, entered once. The AI does the
> heavy lifting of *finding* the law; the officer stays in control of *applying*
> it; and nothing about the law is ever fabricated. That's CrimeGPT."

---

## If asked / backup beats

- **RBAC:** sign in as `legal` / `legal12345` — the same screens are *viewable*
  but Generate / Confirm / Add-a-step are refused with a clean message.
- **Other two cases:** CR-205/2026 (assault) and CR-312/2026 (online fraud) are
  fully seeded too, if an evaluator wants a second example.
- **Offline:** retrieval is fully local (`all-MiniLM-L6-v2` baked into the image)
  — the demo works with no internet.
- **Source of section text:** BNS/BNSS/BSA text is verbatim from India Code; show
  a section's "Repealed Act equivalent" tag if asked about IPC mapping.
