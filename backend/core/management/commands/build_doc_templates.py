"""Regenerate the committed Word templates from code (currently: Seizure Receipt)."""
from django.core.management.base import BaseCommand

from core.documents import build_seizure_receipt_template


class Command(BaseCommand):
    help = "Build/refresh the .docx templates under core/doc_templates/."

    def handle(self, *args, **options):
        path = build_seizure_receipt_template()
        self.stdout.write(self.style.SUCCESS(f"Built Seizure Receipt template -> {path}"))
