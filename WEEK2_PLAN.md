# CrimeGPT — Week 2 Build Plan

> Week 1 delivered the vertical slice: one Case object → versioned `.docx`, with RBAC, audit history, and a self-populating diary, proven in the browser. Week 2 is **breadth**: turn the one proven pipeline into the full feature set. Because the schema is locked, these four tracks run **in parallel** — assign one per person.

---

## Pre-flight (before any Week 2 code)

- [ ] **Fully-filled accused test.** Create one case with a complete accused (name, father's name, address) and regenerate the Seizure Receipt. The blank gaps in the Week-1 demo doc ("from , child/spouse of ,") should fill. If they stay blank, the seizure context-builder is missing those Party fields — 2-line fix in `build_seizure_context_from_case`.
- [ ] **Fresh-clone check** (carryover from Day 1): confirm a second machine runs `docker compose up` clean, proving identical environments before the team scales work.

---

## Track A — Legal Section Intelligence (the real AI) ⭐ hardest, start first

**Decision: retrieval runs fully local. LLM explanation is an optional layer.** Embeddings + pgvector need no API; this also earns the "offline-first" bonus in the problem statement.

1. **Embedding field.** Add `embedding = VectorField(dimensions=384)` to `LegalSection`. Migration. (384 = `all-MiniLM-L6-v2`, a small local sentence-transformer. Swap to InLegalBERT later if quality needs it.)
2. **Embed all 358 sections.** Management command `embed_legal_sections` — runs the section `text` through the local model, stores the vector. Idempotent, like the Day 3 loader.
3. **Retrieval endpoint.** `POST /api/cases/{id}/suggest-sections/` — takes the case's `incident_narrative`, embeds it, does a pgvector cosine-similarity search, returns the top N candidate sections with similarity scores.
4. **Suggest, don't auto-write.** Results become `CaseSection` rows with `suggested_by_ai=True, confirmed=False`. The officer confirms in the UI. **Never auto-insert an unconfirmed section into a document** — this is the load-bearing safety principle and the thing judges will probe.
5. **(Optional) explanation layer.** For each suggested section, a short "why this matches" string. Point it at a local Ollama model *or* an API behind a config flag — core retrieval works without it.

**Done when:** typing a narrative ("A entered B's house at night and took gold jewellery") returns sensible BNS sections (theft/house-trespass) ranked by score, as confirmable suggestions.

---

## Track B — Remaining 6 Documents (repetition of a proven pattern)

The Day 3–4 pipeline is the template: **build template → context-builder → versioned endpoint + diary event.** Repeat for each. Order by field-overlap (most shared data first):

1. Medical Treatment Letter — Case + victim/accused Party + incident
2. Remand Request (Police Custody) — Case + accused + confirmed CaseSections + arrest diary event
3. Court Custody Letter — Case + accused + confirmed CaseSections
4. Accused Panchanama — Case + accused + witnesses + SeizedItems
5. Face Identification Form — Case + accused + photo
6. Purvani Chargesheet — everything (build last; it's the superset)

Each reuses the versioning + diary-event logic already written. Each gets a render test asserting real case data lands in the doc (like the Day 4 "C-900 / Ravi" test).

**Done when:** all 7 documents generate from one Case, each versioned, each logging a diary event.

---

## Track C — PDF Export (small, high-visibility)

Real police documents get printed. Wrap the existing `.docx` output with a docx→PDF step (LibreOffice headless `soffice --convert-to pdf`, already Linux-friendly in your container, or `docx2pdf`).

- Add a `format=pdf` option to the generation endpoints, or a separate convert endpoint.
- Store alongside the docx on the `Document`.

**Done when:** any generated document can be downloaded as PDF.

---

## Track D — Case Diary View (you're already logging the data)

The backend already appends `DiaryEvent`s (FIR, document-generated, etc.). This track just renders them.

1. Endpoint: `GET /api/cases/{id}/diary/` — chronological events.
2. React timeline view — FIR → investigation → seizure → document generation → arrest, in order.
3. Manual event entry — let an officer log a step (witness interviewed, evidence collected) so the diary is complete, not just auto-events.

**Done when:** a case shows a clean chronological timeline from complaint to arrest, mixing auto-logged and manual events.

---

## Integration checkpoint (end of week)

- All four tracks merged; one case exercises everything: create → suggest+confirm sections → generate all docs (docx + PDF) → diary shows the full timeline.
- This end-to-end run **is** the demo. Script it now while it's fresh.

---

## Hold the line on these principles

- **Enter every fact once** — new documents read from the Case, never re-enter data.
- **AI suggests, officer confirms** — the `CaseSection.confirmed` flag stays load-bearing; no unconfirmed section reaches a document.
- **Append-only diary** — events are logged, never edited.
- **Versioned, never overwritten** — regeneration increments, matching Week 1.
- **Verbatim legal text** — section text comes from the loaded India Code data, never model-generated.
