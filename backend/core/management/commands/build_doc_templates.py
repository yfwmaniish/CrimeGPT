"""Regenerate the committed Word templates from code."""
from django.core.management.base import BaseCommand

from core.documents import (
    SUPPORTED_LANGS,
    build_chargesheet_template,
    build_court_custody_template,
    build_faceid_template,
    build_medical_treatment_template,
    build_panchanama_template,
    build_remand_request_template,
    build_seizure_receipt_template,
)

# Documents that currently have a single (English) template.
BUILDERS = [
    ("Remand Request", build_remand_request_template),
    ("Court Custody Letter", build_court_custody_template),
    ("Medical Treatment Letter", build_medical_treatment_template),
    ("Purvani Chargesheet", build_chargesheet_template),
    ("Accused Panchanama", build_panchanama_template),
    ("Face Identification Form", build_faceid_template),
]


class Command(BaseCommand):
    help = "Build/refresh the .docx templates under core/doc_templates/."

    def handle(self, *args, **options):
        # Seizure Receipt is the multilingual proof-of-concept: one per language.
        for lang in SUPPORTED_LANGS:
            path = build_seizure_receipt_template(lang=lang)
            self.stdout.write(self.style.SUCCESS(f"Built Seizure Receipt [{lang}] -> {path}"))

        for label, builder in BUILDERS:
            path = builder()
            self.stdout.write(self.style.SUCCESS(f"Built {label} template -> {path}"))
