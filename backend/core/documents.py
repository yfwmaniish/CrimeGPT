"""
Document generation for CrimeGPT (Day 3: Seizure Receipt).

The Word template is *built from code* (``build_seizure_receipt_template``) so it
is reproducible and reviewable — re-run ``python manage.py build_doc_templates``
to regenerate the committed ``.docx``. ``render_seizure_receipt`` fills it with a
context using docxtpl (Jinja2-in-Word).

The Day 4 API endpoint will call ``render_seizure_receipt`` with data pulled from
a real Case; for now ``sample_seizure_context`` provides hardcoded data to prove
the template renders.
"""
from datetime import date
from pathlib import Path

from django.conf import settings
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docxtpl import DocxTemplate

DOC_TEMPLATE_DIR = Path(settings.BASE_DIR) / "core" / "doc_templates"
SEIZURE_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "seizure_receipt.docx"

# Columns of the seized-items table: (header label, per-row Jinja tag).
_ITEM_COLUMNS = [
    ("S.No", "{{ item.sno }}"),
    ("Description", "{{ item.description }}"),
    ("Quantity", "{{ item.quantity }}"),
    ("Seized From", "{{ item.seized_from }}"),
    ("Date", "{{ item.seizure_date }}"),
    ("Place", "{{ item.seizure_place }}"),
]


def _set_cell(cell, text, *, bold=False):
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.bold = bold


def build_seizure_receipt_template(path: Path = SEIZURE_TEMPLATE_PATH) -> Path:
    """Create the Seizure Receipt .docx template with docxtpl tags."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("SEIZURE RECEIPT (JABTI)")
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run("Police Station: ").bold = True
    meta.add_run("{{ case.police_station }}    ")
    meta.add_run("FIR No.: ").bold = True
    meta.add_run("{{ case.fir_number }}    ")
    meta.add_run("Case No.: ").bold = True
    meta.add_run("{{ case.case_number }}")

    datep = doc.add_paragraph()
    datep.add_run("Date: ").bold = True
    datep.add_run("{{ today }}")

    doc.add_paragraph(
        "I, {{ officer.name }}, {{ officer.role }}, of Police Station "
        "{{ officer.police_station }}, have this day seized the following "
        "article(s) in connection with the above-mentioned case from "
        "{{ accused.name }}, child/spouse of {{ accused.parent_name }}, "
        "resident of {{ accused.address }}:"
    )

    # Seized-items table. docxtpl removes the rows that hold {%tr for%} and
    # {%tr endfor%}, repeating the rows *between* them. So:
    #   row0 = header, row1 = for-control, row2 = body (repeats), row3 = endfor.
    table = doc.add_table(rows=4, cols=len(_ITEM_COLUMNS))
    table.style = "Table Grid"
    for col, (header, tag) in enumerate(_ITEM_COLUMNS):
        _set_cell(table.rows[0].cells[col], header, bold=True)  # header row
        _set_cell(table.rows[2].cells[col], tag)                # body row (repeats)
    _set_cell(table.rows[1].cells[0], "{%tr for item in seized_items %}")
    _set_cell(table.rows[3].cells[0], "{%tr endfor %}")

    doc.add_paragraph(
        "Place of seizure: {{ case.incident_place }}"
    )
    doc.add_paragraph(
        "Witness(es): {% for w in witnesses %}{{ loop.index }}. {{ w.name }} "
        "({{ w.address }}){% if not loop.last %}; {% endif %}{% endfor %}"
    )

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of person from whom seized: __________________  ")
    sig.add_run("({{ accused.name }})")
    sig2 = doc.add_paragraph()
    sig2.add_run("Signature of seizing officer: __________________  ")
    sig2.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_seizure_receipt(context: dict, template_path: Path = SEIZURE_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Seizure Receipt template with ``context``.

    Returns the DocxTemplate; the caller saves it (``.save(path_or_stream)``).
    """
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def sample_seizure_context() -> dict:
    """Hardcoded sample data to confirm the template renders."""
    return {
        "today": date(2026, 6, 2).strftime("%d-%m-%Y"),
        "case": {
            "case_number": "C-2026-001",
            "fir_number": "FIR-045/2026",
            "police_station": "PS Central",
            "incident_place": "Market Road, near Bus Stand",
        },
        "officer": {
            "name": "Inspector R. Sharma",
            "role": "Investigating Officer",
            "police_station": "PS Central",
        },
        "accused": {
            "name": "Ravi Kumar",
            "parent_name": "Mohan Kumar",
            "address": "12 Gandhi Nagar, Central City",
        },
        "seized_items": [
            {
                "sno": 1,
                "description": "One black mobile phone (Samsung)",
                "quantity": "1",
                "seized_from": "Ravi Kumar",
                "seizure_date": "02-06-2026",
                "seizure_place": "Market Road",
            },
            {
                "sno": 2,
                "description": "Cash (Indian currency)",
                "quantity": "Rs. 5,000",
                "seized_from": "Ravi Kumar",
                "seizure_date": "02-06-2026",
                "seizure_place": "Market Road",
            },
        ],
        "witnesses": [
            {"name": "Sunil Verma", "address": "5 Nehru Road"},
            {"name": "Asha Devi", "address": "9 Patel Street"},
        ],
    }
