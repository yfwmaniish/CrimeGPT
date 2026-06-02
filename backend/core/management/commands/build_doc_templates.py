"""Regenerate the committed Word templates from code."""
from django.core.management.base import BaseCommand

from core.documents import (
    build_remand_request_template,
    build_seizure_receipt_template,
)

BUILDERS = [
    ("Seizure Receipt", build_seizure_receipt_template),
    ("Remand Request", build_remand_request_template),
]


class Command(BaseCommand):
    help = "Build/refresh the .docx templates under core/doc_templates/."

    def handle(self, *args, **options):
        for label, builder in BUILDERS:
            path = builder()
            self.stdout.write(self.style.SUCCESS(f"Built {label} template -> {path}"))
