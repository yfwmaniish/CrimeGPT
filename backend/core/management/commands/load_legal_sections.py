"""
Idempotent loader: CSV -> LegalSection.

The CSV must have exactly these columns:

    code, section_number, title, text, ipc_equivalent

Rows are upserted on the natural key ``(code, section_number)`` (the model's
``unique_together``), so the command is safe to re-run: existing rows are
updated, new rows are created, nothing is duplicated.

Usage:
    python manage.py load_legal_sections data/bns_sections.csv
    python manage.py load_legal_sections data/bns_sections.csv --dry-run

This is the *fallback* path too: if the scraper (``scrape_bns``) can't reach the
sources, manually download a CSV in the same column format and load it with this
command.
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import LegalSection

REQUIRED_COLUMNS = ["code", "section_number", "title", "text", "ipc_equivalent"]


class Command(BaseCommand):
    help = "Upsert LegalSection rows from a CSV (idempotent). See module docstring for format."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the CSV file.")
        parser.add_argument(
            "--encoding",
            default="utf-8-sig",
            help="CSV encoding (default utf-8-sig, tolerates a BOM).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report counts without writing to the database.",
        )

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        dry_run = options["dry_run"]
        created = updated = skipped = 0

        with path.open(newline="", encoding=options["encoding"]) as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CommandError(
                    f"CSV is missing required columns: {missing}. "
                    f"Found: {reader.fieldnames}. Expected: {REQUIRED_COLUMNS}"
                )

            # One transaction so a malformed row near the end doesn't leave a
            # half-loaded table behind.
            with transaction.atomic():
                for line_no, row in enumerate(reader, start=2):  # row 1 = header
                    code = (row.get("code") or "").strip()
                    number = (row.get("section_number") or "").strip()
                    if not code or not number:
                        self.stderr.write(
                            f"  line {line_no}: skipped (missing code/section_number)"
                        )
                        skipped += 1
                        continue

                    defaults = {
                        "title": (row.get("title") or "").strip(),
                        "text": (row.get("text") or "").strip(),
                        "ipc_equivalent": (row.get("ipc_equivalent") or "").strip(),
                    }

                    if dry_run:
                        exists = LegalSection.objects.filter(
                            code=code, section_number=number
                        ).exists()
                        updated += 1 if exists else 0
                        created += 0 if exists else 1
                        continue

                    _, was_created = LegalSection.objects.update_or_create(
                        code=code, section_number=number, defaults=defaults
                    )
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1

                if dry_run:
                    # Nothing should persist from a dry run.
                    transaction.set_rollback(True)

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}created={created} updated={updated} skipped={skipped} "
                f"(rows processed={created + updated})"
            )
        )
