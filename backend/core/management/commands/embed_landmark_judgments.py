"""
Embed LandmarkJudgment rows (title + summary + principle) with the local
all-MiniLM-L6-v2 model. Idempotent and re-runnable, like embed_legal_sections.

    python manage.py embed_landmark_judgments
    python manage.py embed_landmark_judgments --force   # re-embed all
"""
from django.core.management.base import BaseCommand

from core.embeddings import embed_texts
from core.models import LandmarkJudgment


class Command(BaseCommand):
    help = "Compute and store embeddings for LandmarkJudgment rows (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-embed rows that already have a vector.")
        parser.add_argument("--batch-size", type=int, default=64)

    def handle(self, *args, **options):
        qs = LandmarkJudgment.objects.all().order_by("id")
        if not options["force"]:
            qs = qs.filter(embedding__isnull=True)
        items = list(qs)
        if not items:
            self.stdout.write(self.style.SUCCESS("Nothing to embed — all judgments already have vectors."))
            return

        batch_size = options["batch_size"]
        total = len(items)
        done = 0
        for start in range(0, total, batch_size):
            batch = items[start : start + batch_size]
            texts = [f"{j.title}. {j.summary} {j.principle}".strip() for j in batch]
            vectors = embed_texts(texts)
            for judgment, vector in zip(batch, vectors):
                judgment.embedding = vector
            LandmarkJudgment.objects.bulk_update(batch, ["embedding"])
            done += len(batch)
            self.stdout.write(f"  embedded {done}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Embedded {total} judgment(s)."))
