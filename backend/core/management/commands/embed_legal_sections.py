"""
Embed LegalSection rows with the local all-MiniLM-L6-v2 model and store the
384-d vector in ``LegalSection.embedding``.

Idempotent and re-runnable (like the Day 3 loader): by default it only embeds
sections that don't yet have a vector, so a second run is a no-op. Use --force to
re-embed everything (e.g. after changing the model or the embed text).

    python manage.py embed_legal_sections
    python manage.py embed_legal_sections --limit 20     # for testing
    python manage.py embed_legal_sections --force        # re-embed all
"""
from django.core.management.base import BaseCommand

from core.embeddings import embed_texts, section_embedding_text
from core.models import LegalSection


class Command(BaseCommand):
    help = "Compute and store embeddings for LegalSection rows (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Only embed the first N (0 = all). For testing.")
        parser.add_argument("--force", action="store_true", help="Re-embed sections that already have a vector.")
        parser.add_argument("--batch-size", type=int, default=64, help="Encode in batches of this size.")

    def handle(self, *args, **options):
        qs = LegalSection.objects.all().order_by("id")
        if not options["force"]:
            qs = qs.filter(embedding__isnull=True)
        if options["limit"]:
            qs = qs[: options["limit"]]

        sections = list(qs)
        if not sections:
            self.stdout.write(self.style.SUCCESS("Nothing to embed — all sections already have vectors."))
            return

        batch_size = options["batch_size"]
        total = len(sections)
        done = 0
        for start in range(0, total, batch_size):
            batch = sections[start : start + batch_size]
            vectors = embed_texts([section_embedding_text(s) for s in batch])
            for section, vector in zip(batch, vectors):
                section.embedding = vector
            LegalSection.objects.bulk_update(batch, ["embedding"])
            done += len(batch)
            self.stdout.write(f"  embedded {done}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Embedded {total} section(s)."))
