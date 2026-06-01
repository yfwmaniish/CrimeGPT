"""
Scrape the Bharatiya Nyaya Sanhita, 2023 into a CSV that ``load_legal_sections``
can ingest. Columns produced: code, section_number, title, text, ipc_equivalent.

Sources (both official government sites):

1. Section list + text — India Code (indiacode.nic.in), Act 45 of 2023.
   * The act's handle page lists every section as an ``<a class="title">`` whose
     href carries ``sectionId`` / ``sectionno`` and whose text is the heading.
   * The section body is loaded by the site over AJAX from
     ``/SectionPageContent?actid=...&sectionID=...`` which returns JSON
     ``{"content": "<html>", "footnote": "<html>"}``. We call it directly.

2. IPC-equivalent — NCRB "Compendium of New Criminal Laws" corresponding-section
   table (cytrain.ncrb.gov.in). One HTML table mapping BNS sub-sections to IPC
   sections; we aggregate to the BNS section level.

Fallbacks (the scrape may be incomplete if a site changes/blocks):
  * ``--no-ipc``            : skip the NCRB table (ipc_equivalent left blank).
  * ``--ipc-map FILE.csv``  : read the IPC mapping from a local CSV
                              (columns: section_number, ipc_equivalent) instead
                              of NCRB. Use this if NCRB is unreachable.
  * If indiacode itself is unreachable, don't use this command at all — manually
    download a CSV in the load format and run ``load_legal_sections`` directly.

Typical run (inside the web container):
    python manage.py scrape_bns --out data/bns_sections.csv
    python manage.py load_legal_sections data/bns_sections.csv
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
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BNS_HANDLE = "https://www.indiacode.nic.in/handle/123456789/20062"
BNS_ACTID = "AC_CEN_5_23_00048_2023-45_1719292564123"
SECTION_CONTENT_URL = "https://www.indiacode.nic.in/SectionPageContent"
NCRB_TABLE_URL = "https://cytrain.ncrb.gov.in/staticpage/web_pages/SectionTableBNS.html"

# A browser-like UA; indiacode 403s some default agents.
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}


def _html_to_text(fragment: str) -> str:
    """Turn a section's HTML body into readable plain text."""
    soup = BeautifulSoup(fragment or "", "html.parser")
    for br in soup.find_all(["br", "hr"]):
        br.replace_with("\n")
    text = soup.get_text()
    # Normalise whitespace but keep sub-section line breaks.
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


class Command(BaseCommand):
    help = "Scrape BNS 2023 (sections + IPC-equivalent) into a load-ready CSV."

    def add_arguments(self, parser):
        default_out = Path(settings.BASE_DIR) / "data" / "bns_sections.csv"
        parser.add_argument("--out", default=str(default_out), help="Output CSV path.")
        parser.add_argument("--delay", type=float, default=0.3, help="Seconds between section requests (politeness).")
        parser.add_argument("--limit", type=int, default=0, help="Only scrape the first N sections (0 = all). For testing.")
        parser.add_argument("--no-ipc", action="store_true", help="Skip the NCRB IPC table.")
        parser.add_argument("--ipc-map", default="", help="Local CSV (section_number, ipc_equivalent) to use instead of NCRB.")
        parser.add_argument("--timeout", type=int, default=40, help="Per-request timeout (s).")

    # -- sources ---------------------------------------------------------
    def _get(self, session, url, *, timeout, verify=True):
        resp = session.get(url, timeout=timeout, verify=verify)
        resp.raise_for_status()
        return resp

    def parse_index(self, html):
        """Return [{'section_number', 'title', 'section_id'}] from the handle page.

        The section id is read from the anchor's ``id`` attribute
        (``"<actid>#<sectionId>#<actid>"``) rather than the href: the href's
        ``&sectionId`` gets HTML-entity-decoded by the parser into ``§ionId``,
        which corrupts query parsing. Number and title come from the link text
        (``"Section 103. Punishment for murder."``).
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = []
        for a in soup.select("a.title"):
            anchor_id = a.get("id", "")
            parts = anchor_id.split("#")
            if len(parts) < 2 or not parts[1].isdigit():
                continue
            section_id = parts[1]
            full = a.get_text(" ", strip=True)  # "Section 103. Punishment for murder."
            m = re.match(r"Section\s+(\d+[A-Z]?)\.?\s*(.*)", full, re.S)
            if not m:
                continue
            number = m.group(1)
            title = re.sub(r"\s+", " ", m.group(2)).strip()
            sections.append({"section_number": number, "title": title, "section_id": section_id})
        return sections

    def fetch_section_text(self, session, section_id, *, timeout):
        resp = self._get(
            session,
            f"{SECTION_CONTENT_URL}?actid={BNS_ACTID}&sectionID={section_id}",
            timeout=timeout,
        )
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            return ""
        return _html_to_text(payload.get("content", ""))

    def fetch_ipc_map_ncrb(self, session, *, timeout):
        """{section_number: 'IPC 302' style string} from the NCRB table."""
        # NCRB's TLS chain is often incomplete; fetch without verification.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = self._get(session, NCRB_TABLE_URL, timeout=timeout, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        mapping = defaultdict(list)
        for tr in soup.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            bns_cell, ipc_cell = cells[0], cells[1]
            if "CHAPTER" in bns_cell.upper() or "Bharatiya" in bns_cell:
                continue
            mb = re.match(r"\s*(\d+)", bns_cell)
            if not mb:
                continue
            if "New Section" in ipc_cell:
                continue
            mi = re.match(r"\s*(\d+[A-Z]?)", ipc_cell)
            if not mi:
                continue
            number, ipc_no = mb.group(1), mi.group(1)
            if ipc_no not in mapping[number]:
                mapping[number].append(ipc_no)
        return {k: ", ".join(v) for k, v in mapping.items()}

    def load_ipc_map_file(self, path):
        mapping = {}
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                num = (row.get("section_number") or "").strip()
                if num:
                    mapping[num] = (row.get("ipc_equivalent") or "").strip()
        return mapping

    # -- main ------------------------------------------------------------
    def handle(self, *args, **options):
        timeout = options["timeout"]
        session = requests.Session()
        session.headers.update(HEADERS)

        # 1) IPC mapping (best effort; failures are non-fatal).
        ipc_map = {}
        if options["ipc_map"]:
            ipc_map = self.load_ipc_map_file(options["ipc_map"])
            self.stdout.write(f"Loaded {len(ipc_map)} IPC mappings from {options['ipc_map']}.")
        elif not options["no_ipc"]:
            try:
                ipc_map = self.fetch_ipc_map_ncrb(session, timeout=timeout)
                self.stdout.write(f"Fetched {len(ipc_map)} IPC mappings from NCRB.")
            except Exception as exc:  # noqa: BLE001 - report and continue without IPC
                self.stderr.write(
                    self.style.WARNING(
                        f"NCRB IPC table unavailable ({exc}). Continuing without "
                        f"ipc_equivalent. Re-run later with --ipc-map FILE.csv to fill it in."
                    )
                )

        # 2) Section index from indiacode (single request).
        try:
            index_html = self._get(session, BNS_HANDLE, timeout=timeout).text
        except Exception as exc:
            raise CommandError(
                f"Could not reach India Code ({exc}). Use the manual-CSV fallback: "
                f"download a CSV in the load format and run load_legal_sections."
            )
        sections = self.parse_index(index_html)
        if not sections:
            raise CommandError(
                "Parsed 0 sections from the India Code handle page (the site layout "
                "may have changed). Use the manual-CSV fallback."
            )
        if options["limit"]:
            sections = sections[: options["limit"]]
        self.stdout.write(f"Found {len(sections)} sections; fetching text...")

        # 3) Body text per section + merge IPC.
        rows, with_ipc, empty_text = [], 0, 0
        for i, sec in enumerate(sections, start=1):
            try:
                text = self.fetch_section_text(session, sec["section_id"], timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.WARNING(f"  section {sec['section_number']}: text fetch failed ({exc})"))
                text = ""
            if not text:
                empty_text += 1
            ipc = ipc_map.get(sec["section_number"], "")
            if ipc:
                with_ipc += 1
            rows.append(
                {
                    "code": "BNS",
                    "section_number": sec["section_number"],
                    "title": sec["title"],
                    "text": text,
                    "ipc_equivalent": ipc,
                }
            )
            if i % 25 == 0:
                self.stdout.write(f"  ...{i}/{len(sections)}")
            if options["delay"]:
                time.sleep(options["delay"])

        # 4) Write CSV.
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["code", "section_number", "title", "text", "ipc_equivalent"]
            )
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} sections to {out_path} "
                f"(with ipc_equivalent: {with_ipc}, empty text: {empty_text}). "
                f"Load with: python manage.py load_legal_sections {out_path}"
            )
        )
