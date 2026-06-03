"""
Shared India Code scraping helpers (same approach as the Day-3 BNS scraper),
reused by scrape_bnss and scrape_bsa.

Each act's handle page lists every section as an ``<a class="title">`` whose id is
``"<actid>#<sectionId>#<actid>"`` and whose text is the heading. The body is
loaded over AJAX from ``/SectionPageContent?actid=...&sectionID=...``. Old-act
equivalents come from the NCRB "Compendium of New Criminal Laws" correspondence
tables (BNS->IPC, BNSS->CrPC, BSA->Indian Evidence Act).

Verbatim only: section text comes from the source, never generated.
"""
import csv
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
SECTION_CONTENT_URL = "https://www.indiacode.nic.in/SectionPageContent"


def _html_to_text(fragment: str) -> str:
    soup = BeautifulSoup(fragment or "", "html.parser")
    for br in soup.find_all(["br", "hr"]):
        br.replace_with("\n")
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in soup.get_text().splitlines()]
    return "\n".join(ln for ln in lines if ln)


def parse_section_index(html: str):
    """[{actid, section_id, section_number, title}] from a handle page.

    The id attribute carries the section id (the href's ``&sectionId`` gets
    entity-decoded to ``§ionId`` by the parser, so it can't be used).
    """
    soup = BeautifulSoup(html, "html.parser")
    sections = []
    for a in soup.select("a.title"):
        parts = a.get("id", "").split("#")
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        full = a.get_text(" ", strip=True)  # "Section 41. ..."
        m = re.match(r"Section\s+(\d+[A-Z]?)\.?\s*(.*)", full, re.S)
        if not m:
            continue
        sections.append(
            {
                "actid": parts[0],
                "section_id": parts[1],
                "section_number": m.group(1),
                "title": re.sub(r"\s+", " ", m.group(2)).strip(),
            }
        )
    return sections


def fetch_section_text(session, actid, section_id, *, timeout=40) -> str:
    resp = session.get(
        f"{SECTION_CONTENT_URL}?actid={actid}&sectionID={section_id}", timeout=timeout
    )
    resp.raise_for_status()
    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return ""
    return _html_to_text(payload.get("content", ""))


def fetch_ncrb_correspondence(session, url, *, timeout=40) -> dict:
    """{new_section_number: 'old, sections'} from an NCRB correspondence table.

    Column 0 is the new section; column 1 is the old-act equivalent. Header/chapter
    rows and 'New Section'/'Repealed' (no leading number) rows are skipped.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    resp = session.get(url, timeout=timeout, verify=False)  # NCRB TLS chain is incomplete
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    mapping = defaultdict(list)
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        new_cell, old_cell = cells[0], cells[1]
        if "CHAPTER" in new_cell.upper():
            continue
        mn = re.match(r"\s*(\d+)", new_cell)
        mo = re.match(r"\s*(\d+[A-Z]?)", old_cell)  # skips New Section/Repealed/blank
        if not mn or not mo:
            continue
        number, old = mn.group(1), mo.group(1)
        if old not in mapping[number]:
            mapping[number].append(old)
    return {k: ", ".join(v) for k, v in mapping.items()}


def scrape_act(handle_url, code, *, ncrb_url=None, limit=0, delay=0.15, timeout=40, log=print):
    """Scrape one act into rows: {code, section_number, title, text, ipc_equivalent}.

    ``ipc_equivalent`` is reused as a generic old-act-equivalent column (CrPC for
    BNSS, Indian Evidence Act for BSA). NCRB failures are non-fatal.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    mapping = {}
    if ncrb_url:
        try:
            mapping = fetch_ncrb_correspondence(session, ncrb_url, timeout=timeout)
            log(f"Fetched {len(mapping)} correspondence mappings from NCRB.")
        except Exception as exc:  # noqa: BLE001
            log(f"WARNING: NCRB table unavailable ({exc}). Continuing without equivalents.")

    resp = session.get(handle_url, timeout=timeout)
    resp.raise_for_status()
    sections = parse_section_index(resp.text)
    if not sections:
        raise RuntimeError(
            "Parsed 0 sections from the India Code handle page (layout may have "
            "changed). Use the manual-CSV fallback with load_legal_sections."
        )
    if limit:
        sections = sections[:limit]
    log(f"Found {len(sections)} sections; fetching text...")

    rows = []
    for i, sec in enumerate(sections, start=1):
        try:
            text = fetch_section_text(session, sec["actid"], sec["section_id"], timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            log(f"  section {sec['section_number']}: text fetch failed ({exc})")
            text = ""
        rows.append(
            {
                "code": code,
                "section_number": sec["section_number"],
                "title": sec["title"],
                "text": text,
                "ipc_equivalent": mapping.get(sec["section_number"], ""),
            }
        )
        if i % 50 == 0:
            log(f"  ...{i}/{len(sections)}")
        if delay:
            time.sleep(delay)
    return rows


def write_sections_csv(rows, out_path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["code", "section_number", "title", "text", "ipc_equivalent"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return out
