"""
Idempotent loader: CSV -> LandmarkJudgment, linking each to the BNS sections it
relates to.

CSV columns: title, citation, year, court, summary, principle, bns_sections,
source. ``bns_sections`` is a ``;`` or ``,`` separated list of BNS section numbers
(e.g. "303;305"). Rows are upserted on ``citation`` (unique), so re-running is
safe. ``source`` documents where each entry came from.

Verbatim/curated data only — citations and summaries come from authoritative
sources, never generated.

    python manage.py load_landmark_judgments data/landmark_judgments.csv
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import LandmarkJudgment, LegalSection

REQUIRED = ["title", "citation", "summary", "principle"]


class Command(BaseCommand):
    help = "Upsert LandmarkJudgment rows from a CSV (idempotent); links BNS sections."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--encoding", default="utf-8-sig")

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        created = updated = skipped = 0
        with path.open(newline="", encoding=options["encoding"]) as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
            if missing:
                raise CommandError(f"CSV missing required columns: {missing}")

            with transaction.atomic():
                for line_no, row in enumerate(reader, start=2):
                    citation = (row.get("citation") or "").strip()
                    title = (row.get("title") or "").strip()
                    if not citation or not title:
                        skipped += 1
                        continue
                    year = (row.get("year") or "").strip()
                    judgment, was_created = LandmarkJudgment.objects.update_or_create(
                        citation=citation,
                        defaults={
                            "title": title,
                            "year": int(year) if year.isdigit() else None,
                            "court": (row.get("court") or "").strip(),
                            "summary": (row.get("summary") or "").strip(),
                            "principle": (row.get("principle") or "").strip(),
                            "source": (row.get("source") or "").strip(),
                        },
                    )
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1

                    numbers = [
                        s.strip()
                        for s in re.split(r"[;,]", row.get("bns_sections") or "")
                        if s.strip()
                    ]
                    sections = LegalSection.objects.filter(code="BNS", section_number__in=numbers)
                    judgment.sections.set(sections)

        self.stdout.write(self.style.SUCCESS(
            f"created={created} updated={updated} skipped={skipped} "
            f"(rows processed={created + updated})"
        ))
