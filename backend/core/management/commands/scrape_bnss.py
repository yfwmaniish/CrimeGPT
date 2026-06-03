"""
Scrape the Bharatiya Nagarik Suraksha Sanhita, 2023 (CrPC replacement) into a
load-ready CSV (code=BNSS). Same pattern as scrape_bns; ipc_equivalent holds the
CrPC equivalent. Fallback if India Code changes: load a manual CSV in the same
format with load_legal_sections.

    python manage.py scrape_bnss --out data/bnss_sections.csv
    python manage.py load_legal_sections data/bnss_sections.csv
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.legal_scrape import scrape_act, write_sections_csv

HANDLE_URL = "https://www.indiacode.nic.in/handle/123456789/21419"
NCRB_URL = "https://cytrain.ncrb.gov.in/staticpage/web_pages/SectionTableBNSS.html"


class Command(BaseCommand):
    help = "Scrape BNSS 2023 (sections + CrPC equivalents) into a load-ready CSV."

    def add_arguments(self, parser):
        default_out = Path(settings.BASE_DIR) / "data" / "bnss_sections.csv"
        parser.add_argument("--out", default=str(default_out))
        parser.add_argument("--delay", type=float, default=0.15)
        parser.add_argument("--limit", type=int, default=0, help="Only first N (testing).")
        parser.add_argument("--no-map", action="store_true", help="Skip the NCRB CrPC table.")
        parser.add_argument("--timeout", type=int, default=40)

    def handle(self, *args, **options):
        try:
            rows = scrape_act(
                HANDLE_URL, "BNSS",
                ncrb_url=None if options["no_map"] else NCRB_URL,
                limit=options["limit"], delay=options["delay"], timeout=options["timeout"],
                log=lambda m: self.stdout.write(m),
            )
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"{exc}\nFallback: download a CSV (code,section_number,title,text,"
                f"ipc_equivalent) and run load_legal_sections."
            )
        out = write_sections_csv(rows, options["out"])
        with_map = sum(1 for r in rows if r["ipc_equivalent"])
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(rows)} BNSS sections to {out} (with CrPC equivalent: {with_map}). "
            f"Load with: python manage.py load_legal_sections {out}"
        ))
