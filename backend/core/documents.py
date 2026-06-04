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
from django.utils import timezone
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docxtpl import DocxTemplate

DOC_TEMPLATE_DIR = Path(settings.BASE_DIR) / "core" / "doc_templates"
REMAND_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "remand_request.docx"
COURT_CUSTODY_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "court_custody_letter.docx"
MEDICAL_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "medical_treatment_letter.docx"
CHARGESHEET_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "purvani_chargesheet.docx"
PANCHANAMA_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "accused_panchanama.docx"
FACEID_TEMPLATE_PATH = DOC_TEMPLATE_DIR / "face_identification_form.docx"

SUPPORTED_LANGS = ("en", "hi", "gu")

# Friendly labels for diary event_type codes (matches the UI's i18n diary.events).
EVENT_LABELS = {
    "FIR_REGISTERED": "FIR Registered",
    "INVESTIGATION": "Investigation",
    "SEIZURE": "Seizure",
    "DOCUMENT_GENERATED": "Document Generated",
    "ARREST": "Arrest",
    "STATEMENT_RECORDED": "Statement Recorded",
    "MANUAL": "Note",
}


def event_label(event_type: str) -> str:
    return EVENT_LABELS.get(event_type, event_type.replace("_", " ").title())

# Seizure Receipt is the multilingual proof-of-concept: one template per language.
SEIZURE_TEMPLATE_PATHS = {
    "en": DOC_TEMPLATE_DIR / "seizure_receipt.docx",
    "hi": DOC_TEMPLATE_DIR / "seizure_receipt_hi.docx",
    "gu": DOC_TEMPLATE_DIR / "seizure_receipt_gu.docx",
}
SEIZURE_TEMPLATE_PATH = SEIZURE_TEMPLATE_PATHS["en"]  # back-compat default

# The body Jinja tags are language-independent (same interpolation variables);
# only the labels/boilerplate around them are translated. Section text and case
# data are NEVER translated — accuracy/verbatim principle.
_SEIZURE_ITEM_TAGS = [
    "{{ item.sno }}",
    "{{ item.description }}",
    "{{ item.quantity }}",
    "{{ item.seized_from }}",
    "{{ item.seizure_date }}",
    "{{ item.seizure_place }}",
]

SEIZURE_LABELS = {
    "en": {
        "title": "SEIZURE RECEIPT (JABTI)",
        "police_station": "Police Station: ",
        "fir_no": "FIR No.: ",
        "case_no": "Case No.: ",
        "date": "Date: ",
        "narrative": (
            "I, {{ officer.name }}, {{ officer.role }}, of Police Station "
            "{{ officer.police_station }}, have this day seized the following "
            "article(s) in connection with the above-mentioned case from "
            "{{ accused.name }}, child/spouse of {{ accused.parent_name }}, "
            "resident of {{ accused.address }}:"
        ),
        "columns": ["S.No", "Description", "Quantity", "Seized From", "Date", "Place"],
        "place_of_seizure": "Place of seizure: {{ case.incident_place }}",
        "witnesses": (
            "Witness(es): {% for w in witnesses %}{{ loop.index }}. {{ w.name }} "
            "({{ w.address }}){% if not loop.last %}; {% endif %}{% endfor %}"
        ),
        "sig_person": "Signature of person from whom seized: __________________  ",
        "sig_officer": "Signature of seizing officer: __________________  ",
    },
    "hi": {
        "title": "ज़ब्ती रसीद",
        "police_station": "पुलिस थाना: ",
        "fir_no": "एफ.आई.आर. नं.: ",
        "case_no": "केस नं.: ",
        "date": "दिनांक: ",
        "narrative": (
            "मैं, {{ officer.name }}, {{ officer.role }}, पुलिस थाना "
            "{{ officer.police_station }}, ने आज उपर्युक्त मामले के संबंध में "
            "{{ accused.name }}, पिता/पति {{ accused.parent_name }}, निवासी "
            "{{ accused.address }} से निम्नलिखित वस्तु(एँ) ज़ब्त की हैं:"
        ),
        "columns": ["क्र.सं.", "विवरण", "मात्रा", "किससे ज़ब्त", "दिनांक", "स्थान"],
        "place_of_seizure": "ज़ब्ती का स्थान: {{ case.incident_place }}",
        "witnesses": (
            "गवाह: {% for w in witnesses %}{{ loop.index }}. {{ w.name }} "
            "({{ w.address }}){% if not loop.last %}; {% endif %}{% endfor %}"
        ),
        "sig_person": "जिससे ज़ब्त किया गया उसके हस्ताक्षर: __________________  ",
        "sig_officer": "ज़ब्त करने वाले अधिकारी के हस्ताक्षर: __________________  ",
    },
    "gu": {
        "title": "જપ્તી રસીદ",
        "police_station": "પોલીસ સ્ટેશન: ",
        "fir_no": "એફ.આઈ.આર. નં.: ",
        "case_no": "કેસ નં.: ",
        "date": "તારીખ: ",
        "narrative": (
            "હું, {{ officer.name }}, {{ officer.role }}, પોલીસ સ્ટેશન "
            "{{ officer.police_station }}, એ આજે ઉપરોક્ત કેસના સંબંધમાં "
            "{{ accused.name }}, પિતા/પતિ {{ accused.parent_name }}, રહેવાસી "
            "{{ accused.address }} પાસેથી નીચે મુજબની વસ્તુ(ઓ) જપ્ત કરી છે:"
        ),
        "columns": ["ક્રમ", "વર્ણન", "જથ્થો", "કોની પાસેથી", "તારીખ", "સ્થળ"],
        "place_of_seizure": "જપ્તીનું સ્થળ: {{ case.incident_place }}",
        "witnesses": (
            "સાક્ષી(ઓ): {% for w in witnesses %}{{ loop.index }}. {{ w.name }} "
            "({{ w.address }}){% if not loop.last %}; {% endif %}{% endfor %}"
        ),
        "sig_person": "જેની પાસેથી જપ્ત કર્યું તેની સહી: __________________  ",
        "sig_officer": "જપ્ત કરનાર અધિકારીની સહી: __________________  ",
    },
}


def _set_cell(cell, text, *, bold=False):
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.bold = bold


def _add_loop_table(doc, columns, loop_expr):
    """Add a docxtpl table whose body row repeats over ``loop_expr``.

    docxtpl deletes the rows holding ``{%tr for ... %}`` and ``{%tr endfor %}``
    and repeats the rows *between* them, so the layout must be exactly four rows:
    header, for-control, body (repeats), endfor (the Day-3 bug was a missing body
    row). ``columns`` is a list of ``(header_label, body_cell_tag)``.
    """
    table = doc.add_table(rows=4, cols=len(columns))
    table.style = "Table Grid"
    for col, (header, tag) in enumerate(columns):
        _set_cell(table.rows[0].cells[col], header, bold=True)  # header
        _set_cell(table.rows[2].cells[col], tag)                # body (repeats)
    _set_cell(table.rows[1].cells[0], "{%tr " + loop_expr + " %}")
    _set_cell(table.rows[3].cells[0], "{%tr endfor %}")
    return table


def build_seizure_receipt_template(path: Path = None, lang: str = "en") -> Path:
    """Create the Seizure Receipt .docx template for ``lang`` (en/hi/gu).

    Only labels/boilerplate are translated; the Jinja interpolation tags are
    identical across languages, so the same render context fills any variant.
    """
    labels = SEIZURE_LABELS.get(lang, SEIZURE_LABELS["en"])
    path = Path(path) if path is not None else SEIZURE_TEMPLATE_PATHS[lang]
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(labels["title"])
    run.bold = True
    run.font.size = Pt(16)

    meta = doc.add_paragraph()
    meta.add_run(labels["police_station"]).bold = True
    meta.add_run("{{ case.police_station }}    ")
    meta.add_run(labels["fir_no"]).bold = True
    meta.add_run("{{ case.fir_number }}    ")
    meta.add_run(labels["case_no"]).bold = True
    meta.add_run("{{ case.case_number }}")

    datep = doc.add_paragraph()
    datep.add_run(labels["date"]).bold = True
    datep.add_run("{{ today }}")

    doc.add_paragraph(labels["narrative"])

    # Seized-items table. docxtpl removes the rows that hold {%tr for%} and
    # {%tr endfor%}, repeating the rows *between* them (row0=header,
    # row1=for-control, row2=body, row3=endfor).
    table = doc.add_table(rows=4, cols=len(_SEIZURE_ITEM_TAGS))
    table.style = "Table Grid"
    for col, (header, tag) in enumerate(zip(labels["columns"], _SEIZURE_ITEM_TAGS)):
        _set_cell(table.rows[0].cells[col], header, bold=True)
        _set_cell(table.rows[2].cells[col], tag)
    _set_cell(table.rows[1].cells[0], "{%tr for item in seized_items %}")
    _set_cell(table.rows[3].cells[0], "{%tr endfor %}")

    doc.add_paragraph(labels["place_of_seizure"])
    doc.add_paragraph(labels["witnesses"])

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run(labels["sig_person"])
    sig.add_run("({{ accused.name }})")
    sig2 = doc.add_paragraph()
    sig2.add_run(labels["sig_officer"])
    sig2.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_seizure_receipt(context: dict, template_path: Path = None, lang: str = "en") -> DocxTemplate:
    """Render the Seizure Receipt for ``lang`` (en/hi/gu).

    ``template_path`` overrides the language lookup (used in tests). Returns the
    DocxTemplate; the caller saves it.
    """
    if template_path is None:
        template_path = SEIZURE_TEMPLATE_PATHS.get(lang, SEIZURE_TEMPLATE_PATH)
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def resolve_seized_from_person(case):
    """The person named in the receipt's narrative/signature as the one items
    were seized from. Prefer the first ACCUSED party; if the case has none, fall
    back to the party the seized items were actually taken from (the first item
    with a ``seized_from``). Returns a Party or None.
    """
    accused = case.parties.filter(role="ACCUSED").first()
    if accused is not None:
        return accused
    for item in case.seized_items.all():
        if item.seized_from_id:
            return item.seized_from
    return None


def build_seizure_context_from_case(case) -> dict:
    """Map a Case (+ the seized-from person, SeizedItems, seizing officer) to the
    template context. The seizing officer is the case's IO. The person the items
    were seized from is resolved by ``resolve_seized_from_person`` and feeds both
    the narrative line and the signature line. Missing pieces render blank.
    """

    def fmt_date(d):
        return d.strftime("%d-%m-%Y") if d else ""

    person = resolve_seized_from_person(case)
    officer = case.io

    items = [
        {
            "sno": i,
            "description": item.description,
            "quantity": item.quantity,
            "seized_from": item.seized_from.name if item.seized_from else "",
            "seizure_date": fmt_date(item.seizure_date),
            "seizure_place": item.seizure_place,
        }
        for i, item in enumerate(case.seized_items.all(), start=1)
    ]
    witnesses = [
        {"name": w.name, "address": w.address}
        for w in case.parties.filter(role="WITNESS")
    ]

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "police_station": case.police_station,
            "incident_place": case.incident_place,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "accused": {
            "name": person.name if person else "",
            "parent_name": person.parent_name if person else "",
            "address": person.address if person else "",
        },
        "seized_items": items,
        "witnesses": witnesses,
    }


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


# --------------------------------------------------------------------------- #
# Remand Request (Police Custody)
# --------------------------------------------------------------------------- #
def build_remand_request_template(path: Path = REMAND_TEMPLATE_PATH) -> Path:
    """Create the Police-Custody Remand Request .docx template."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("REQUEST FOR POLICE CUSTODY REMAND")
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph("To,")
    doc.add_paragraph("The Hon'ble Judicial Magistrate,")

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

    # Confirmed sections only (the context provides confirmed CaseSections).
    doc.add_paragraph(
        "The above case is registered at Police Station {{ case.police_station }} "
        "vide FIR No. {{ case.fir_number }} dated {{ case.fir_date }}, under the "
        "following section(s): {% for s in sections %}{{ s.code }} "
        "{{ s.section_number }} ({{ s.title }}){% if not loop.last %}; "
        "{% endif %}{% endfor %}."
    )
    doc.add_paragraph(
        "The accused {{ accused.name }}, child/spouse of {{ accused.parent_name }}, "
        "resident of {{ accused.address }}, was arrested on {{ arrest.date }}. "
        "{{ arrest.details }}"
    )
    doc.add_paragraph("Brief facts of the case: {{ case.incident_narrative }}")
    doc.add_paragraph(
        "It is necessary to interrogate the accused in police custody for the "
        "purpose of investigation and recovery. It is therefore prayed that the "
        "accused may be remanded to police custody for a period of "
        "{{ custody_days }} days."
    )

    # Relevant Case Laws — only judgments the officer has applied. Empty list
    # renders just the header row (no broken layout).
    _add_section_heading(doc, "Relevant Case Laws")
    _add_loop_table(
        doc,
        [("Title", "{{ j.title }}"), ("Citation", "{{ j.citation }}"), ("Principle", "{{ j.principle }}")],
        "for j in judgments",
    )

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_remand_request(context: dict, template_path: Path = REMAND_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Remand Request template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def applied_judgments(case) -> list:
    """The case's APPLIED landmark judgments as plain dicts. Never includes
    AI-suggested-but-unapplied judgments — same boundary as confirmed sections.
    """
    return [
        {
            "title": cj.judgment.title,
            "citation": cj.judgment.citation,
            "principle": cj.judgment.principle,
        }
        for cj in case.case_judgments.filter(applied=True).select_related("judgment")
    ]


def confirmed_sections(case) -> list:
    """The case's CONFIRMED legal sections, as plain dicts. Never includes
    AI-suggested-but-unconfirmed sections — that boundary is load-bearing.
    """
    return [
        {
            "code": cs.section.code,
            "section_number": cs.section.section_number,
            "title": cs.section.title,
            "ipc_equivalent": cs.section.ipc_equivalent,
        }
        for cs in case.applied_sections.filter(confirmed=True).select_related("section")
    ]


def build_remand_context_from_case(case, custody_days=None) -> dict:
    """Map a Case (+ accused, confirmed CaseSections, arrest details) to the
    Remand Request context. Only confirmed sections are included.

    Arrest details come from the latest ARREST diary event. If none exists, we
    fall back to the case's last-updated date, clearly marked *approximate*, so
    the document is never left with a blank arrest date.

    ``custody_days`` is a one-time input for the requested custody period; if not
    given, a blank fill-in line is rendered.
    """

    def fmt_date(d):
        return d.strftime("%d-%m-%Y") if d else ""

    accused = case.parties.filter(role="ACCUSED").first()
    officer = case.io
    arrest_event = case.diary.filter(event_type="ARREST").order_by("-timestamp").first()

    if arrest_event:
        arrest = {
            "date": arrest_event.timestamp.strftime("%d-%m-%Y %H:%M"),
            "details": arrest_event.description,
        }
    else:
        # Fallback: no arrest entry recorded — use the last-updated date, approx.
        arrest = {
            "date": f"{fmt_date(case.updated_at)} (approximate)",
            "details": "Arrest date approximate — no arrest entry was recorded for this case.",
        }

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "fir_date": fmt_date(case.fir_date),
            "police_station": case.police_station,
            "incident_place": case.incident_place,
            "incident_narrative": case.incident_narrative,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "accused": {
            "name": accused.name if accused else "",
            "parent_name": accused.parent_name if accused else "",
            "address": accused.address if accused else "",
        },
        "sections": confirmed_sections(case),
        "judgments": applied_judgments(case),
        "arrest": arrest,
        # Blank fill-in line when the officer didn't specify a period.
        "custody_days": custody_days if custody_days else "______",
    }


# --------------------------------------------------------------------------- #
# Court Custody Letter (judicial custody)
# --------------------------------------------------------------------------- #
def build_court_custody_template(path: Path = COURT_CUSTODY_TEMPLATE_PATH) -> Path:
    """Create the Court (Judicial) Custody Letter .docx template."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("REQUEST FOR JUDICIAL (COURT) CUSTODY")
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph("To,")
    doc.add_paragraph("The Hon'ble Judicial Magistrate,")

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

    # Confirmed sections only (provided by the context).
    doc.add_paragraph(
        "The above case is registered at Police Station {{ case.police_station }} "
        "vide FIR No. {{ case.fir_number }} dated {{ case.fir_date }}, under the "
        "following section(s): {% for s in sections %}{{ s.code }} "
        "{{ s.section_number }} ({{ s.title }}){% if not loop.last %}; "
        "{% endif %}{% endfor %}."
    )
    doc.add_paragraph(
        "The accused {{ accused.name }}, child/spouse of {{ accused.parent_name }}, "
        "resident of {{ accused.address }}, is produced before the Hon'ble Court."
    )
    doc.add_paragraph(
        "Police custody of the accused is not required at this stage. It is "
        "therefore prayed that the accused may be remanded to judicial custody."
    )

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_court_custody_letter(context: dict, template_path: Path = COURT_CUSTODY_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Court Custody Letter template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def build_court_custody_context_from_case(case) -> dict:
    """Map a Case (+ accused, confirmed CaseSections) to the Court Custody
    Letter context. Only confirmed sections are included.
    """

    def fmt_date(d):
        return d.strftime("%d-%m-%Y") if d else ""

    accused = case.parties.filter(role="ACCUSED").first()
    officer = case.io

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "fir_date": fmt_date(case.fir_date),
            "police_station": case.police_station,
            "incident_place": case.incident_place,
            "incident_narrative": case.incident_narrative,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "accused": {
            "name": accused.name if accused else "",
            "parent_name": accused.parent_name if accused else "",
            "address": accused.address if accused else "",
        },
        "sections": confirmed_sections(case),
    }


# --------------------------------------------------------------------------- #
# Medical Treatment Letter
# --------------------------------------------------------------------------- #
def resolve_medical_subject(case):
    """The person the medical letter is about. Prefer the VICTIM; fall back to
    the ACCUSED (injured-in-custody / arrest-injury cases); else None.
    """
    victim = case.parties.filter(role="VICTIM").first()
    if victim is not None:
        return victim
    return case.parties.filter(role="ACCUSED").first()


def build_medical_treatment_template(path: Path = MEDICAL_TEMPLATE_PATH) -> Path:
    """Create the Medical Treatment/Examination Letter .docx template."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("REQUEST FOR MEDICAL EXAMINATION / TREATMENT")
    run.bold = True
    run.font.size = Pt(15)

    doc.add_paragraph("To,")
    doc.add_paragraph("The Medical Officer,")

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
        "The bearer of this letter, {{ subject.name }}, child/spouse of "
        "{{ subject.parent_name }}, aged {{ subject.age }} years, "
        "{{ subject.gender }}, resident of {{ subject.address }}, is the "
        "{{ subject.role }} in the above-mentioned case."
    )
    doc.add_paragraph(
        "Kindly conduct the medical examination and provide necessary treatment, "
        "and furnish a medical report to this office. Brief facts of the case: "
        "{{ case.incident_narrative }}"
    )

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_medical_treatment_letter(context: dict, template_path: Path = MEDICAL_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Medical Treatment Letter template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def build_medical_context_from_case(case) -> dict:
    """Map a Case (+ the medical subject and incident) to the Medical Treatment
    Letter context. Subject is resolved VICTIM -> ACCUSED -> blank.
    """
    subject = resolve_medical_subject(case)
    officer = case.io

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "police_station": case.police_station,
            "incident_place": case.incident_place,
            "incident_narrative": case.incident_narrative,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "subject": {
            "name": subject.name if subject else "",
            "parent_name": subject.parent_name if subject else "",
            "age": subject.age if (subject and subject.age is not None) else "",
            "gender": subject.gender if subject else "",
            "address": subject.address if subject else "",
            "role": subject.get_role_display() if subject else "",
        },
    }


# --------------------------------------------------------------------------- #
# Purvani Chargesheet (the superset — everything about the case)
# --------------------------------------------------------------------------- #
def _add_section_heading(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    return p


def build_chargesheet_template(path: Path = CHARGESHEET_TEMPLATE_PATH) -> Path:
    """Create the Purvani Chargesheet .docx template.

    Has four repeating tables (parties, sections, seized items, statements) plus
    a diary table — each built with the proven 4-row loop layout.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("POLICE REPORT UNDER SECTION 193 BNSS (PURVANI CHARGESHEET)")
    run.bold = True
    run.font.size = Pt(14)

    meta = doc.add_paragraph()
    meta.add_run("Police Station: ").bold = True
    meta.add_run("{{ case.police_station }}    ")
    meta.add_run("FIR No.: ").bold = True
    meta.add_run("{{ case.fir_number }}    ")
    meta.add_run("FIR Date: ").bold = True
    meta.add_run("{{ case.fir_date }}")

    meta2 = doc.add_paragraph()
    meta2.add_run("Case No.: ").bold = True
    meta2.add_run("{{ case.case_number }}    ")
    meta2.add_run("Status: ").bold = True
    meta2.add_run("{{ case.status }}    ")
    meta2.add_run("Date: ").bold = True
    meta2.add_run("{{ today }}")

    doc.add_paragraph("Place of incident: {{ case.incident_place }}")

    _add_section_heading(doc, "1. Parties")
    _add_loop_table(
        doc,
        [
            ("Role", "{{ p.role }}"),
            ("Name", "{{ p.name }}"),
            ("Father's/Husband's Name", "{{ p.parent_name }}"),
            ("Age", "{{ p.age }}"),
            ("Gender", "{{ p.gender }}"),
            ("Address", "{{ p.address }}"),
        ],
        "for p in parties",
    )

    _add_section_heading(doc, "2. Sections Applied (confirmed)")
    _add_loop_table(
        doc,
        [
            ("Code", "{{ s.code }}"),
            ("Section", "{{ s.section_number }}"),
            ("Title", "{{ s.title }}"),
            ("Repealed Act Equivalent", "{{ s.ipc_equivalent }}"),
        ],
        "for s in sections",
    )

    _add_section_heading(doc, "3. Relevant Case Laws (applied)")
    _add_loop_table(
        doc,
        [("Title", "{{ j.title }}"), ("Citation", "{{ j.citation }}"), ("Principle", "{{ j.principle }}")],
        "for j in judgments",
    )

    _add_section_heading(doc, "4. Seized Items")
    _add_loop_table(
        doc,
        [
            ("S.No", "{{ item.sno }}"),
            ("Description", "{{ item.description }}"),
            ("Quantity", "{{ item.quantity }}"),
            ("Seized From", "{{ item.seized_from }}"),
            ("Date", "{{ item.seizure_date }}"),
            ("Place", "{{ item.seizure_place }}"),
        ],
        "for item in seized_items",
    )

    _add_section_heading(doc, "5. Statements Recorded")
    _add_loop_table(
        doc,
        [
            ("Deponent", "{{ st.party }}"),
            ("Date", "{{ st.recorded_date }}"),
            ("Statement", "{{ st.text }}"),
        ],
        "for st in statements",
    )

    _add_section_heading(doc, "6. Case Diary Summary")
    _add_loop_table(
        doc,
        [
            ("Date/Time", "{{ ev.timestamp }}"),
            ("Event", "{{ ev.event_type }}"),
            ("Description", "{{ ev.description }}"),
        ],
        "for ev in diary",
    )

    _add_section_heading(doc, "7. Brief Facts")
    doc.add_paragraph("{{ case.incident_narrative }}")

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_chargesheet(context: dict, template_path: Path = CHARGESHEET_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Purvani Chargesheet template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def build_chargesheet_context_from_case(case) -> dict:
    """Map a Case to the chargesheet context: all parties, confirmed sections,
    all seized items, all statements, and a diary summary. Only CONFIRMED
    sections are included.
    """

    def fmt_date(d):
        return d.strftime("%d-%m-%Y") if d else ""

    def fmt_dt(dt):
        return dt.strftime("%d-%m-%Y %H:%M") if dt else ""

    officer = case.io

    parties = [
        {
            "role": p.get_role_display(),
            "name": p.name,
            "parent_name": p.parent_name,
            "age": p.age if p.age is not None else "",
            "gender": p.gender,
            "address": p.address,
        }
        for p in case.parties.all()
    ]
    seized_items = [
        {
            "sno": i,
            "description": item.description,
            "quantity": item.quantity,
            "seized_from": item.seized_from.name if item.seized_from else "",
            "seizure_date": fmt_date(item.seizure_date),
            "seizure_place": item.seizure_place,
        }
        for i, item in enumerate(case.seized_items.all(), start=1)
    ]
    statements = [
        {
            "party": st.party.name if st.party else "",
            "recorded_date": fmt_date(st.recorded_date),
            "text": st.text,
        }
        for st in case.statements.select_related("party")
    ]
    diary = [
        {
            "timestamp": fmt_dt(ev.timestamp),
            "event_type": event_label(ev.event_type),  # friendly label, not the raw code
            "description": ev.description,
        }
        for ev in case.diary.all().order_by("timestamp")
    ]

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "fir_date": fmt_date(case.fir_date),
            "police_station": case.police_station,
            "status": case.get_status_display(),
            "incident_place": case.incident_place,
            "incident_narrative": case.incident_narrative,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "parties": parties,
        "sections": confirmed_sections(case),
        "judgments": applied_judgments(case),
        "seized_items": seized_items,
        "statements": statements,
        "diary": diary,
    }


# --------------------------------------------------------------------------- #
# Accused Panchanama (proceedings witnessed by panch witnesses)
# --------------------------------------------------------------------------- #
def build_panchanama_template(path: Path = PANCHANAMA_TEMPLATE_PATH) -> Path:
    """Create the Accused Panchanama .docx template (witnesses + items tables)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("PANCHANAMA (ACCUSED)")
    run.bold = True
    run.font.size = Pt(15)

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
        "This panchanama is drawn on {{ today }} at Police Station "
        "{{ case.police_station }} in the presence of the panch witnesses named "
        "below, in connection with the above-mentioned case."
    )
    doc.add_paragraph(
        "Accused: {{ accused.name }}, child/spouse of {{ accused.parent_name }}, "
        "resident of {{ accused.address }}."
    )

    _add_section_heading(doc, "Panch Witnesses")
    _add_loop_table(
        doc,
        [
            ("Name", "{{ w.name }}"),
            ("Father's/Husband's Name", "{{ w.parent_name }}"),
            ("Address", "{{ w.address }}"),
        ],
        "for w in witnesses",
    )

    _add_section_heading(doc, "Articles")
    _add_loop_table(
        doc,
        [
            ("S.No", "{{ item.sno }}"),
            ("Description", "{{ item.description }}"),
            ("Quantity", "{{ item.quantity }}"),
            ("Seized From", "{{ item.seized_from }}"),
            ("Date", "{{ item.seizure_date }}"),
            ("Place", "{{ item.seizure_place }}"),
        ],
        "for item in seized_items",
    )

    doc.add_paragraph("Brief facts: {{ case.incident_narrative }}")

    doc.add_paragraph()  # spacer
    doc.add_paragraph(
        "Signatures of panch witnesses: {% for w in witnesses %}{{ loop.index }}. "
        "{{ w.name }} __________  {% endfor %}"
    )
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_panchanama(context: dict, template_path: Path = PANCHANAMA_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Accused Panchanama template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def build_panchanama_context_from_case(case) -> dict:
    """Map a Case (+ accused, witnesses, seized items) to the Panchanama context."""

    def fmt_date(d):
        return d.strftime("%d-%m-%Y") if d else ""

    accused = resolve_seized_from_person(case)  # accused, else seized-from party
    officer = case.io

    witnesses = [
        {"name": w.name, "parent_name": w.parent_name, "address": w.address}
        for w in case.parties.filter(role="WITNESS")
    ]
    seized_items = [
        {
            "sno": i,
            "description": item.description,
            "quantity": item.quantity,
            "seized_from": item.seized_from.name if item.seized_from else "",
            "seizure_date": fmt_date(item.seizure_date),
            "seizure_place": item.seizure_place,
        }
        for i, item in enumerate(case.seized_items.all(), start=1)
    ]

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "police_station": case.police_station,
            "incident_place": case.incident_place,
            "incident_narrative": case.incident_narrative,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "accused": {
            "name": accused.name if accused else "",
            "parent_name": accused.parent_name if accused else "",
            "address": accused.address if accused else "",
        },
        "witnesses": witnesses,
        "seized_items": seized_items,
    }


# --------------------------------------------------------------------------- #
# Face Identification Form
# --------------------------------------------------------------------------- #
def build_faceid_template(path: Path = FACEID_TEMPLATE_PATH) -> Path:
    """Create the Face Identification Form .docx template.

    TODO(evidence-image-upload bonus): there is no image field on Party yet, so
    the form leaves a bordered box for a physically affixed/pasted photograph.
    When the Party photo / evidence-image upload feature lands, replace the
    placeholder box with an InlineImage of the accused's photo.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("FACE IDENTIFICATION FORM")
    run.bold = True
    run.font.size = Pt(15)

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

    _add_section_heading(doc, "Particulars of the Accused")
    doc.add_paragraph("Name: {{ accused.name }}")
    doc.add_paragraph("Father's/Husband's Name: {{ accused.parent_name }}")
    doc.add_paragraph("Age: {{ accused.age }}    Gender: {{ accused.gender }}")
    doc.add_paragraph("Address: {{ accused.address }}")

    # Photo placeholder box (no image field on Party yet -- see TODO above).
    photo = doc.add_table(rows=1, cols=1)
    photo.style = "Table Grid"
    cell = photo.rows[0].cells[0]
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_cell(cell, "[ AFFIX RECENT PHOTOGRAPH OF THE ACCUSED HERE ]")
    photo.rows[0].height = Pt(140)

    doc.add_paragraph()  # spacer
    sig = doc.add_paragraph()
    sig.add_run("Signature of Investigating Officer: __________________  ")
    sig.add_run("({{ officer.name }}, {{ officer.role }})")

    doc.save(str(path))
    return path


def render_faceid(context: dict, template_path: Path = FACEID_TEMPLATE_PATH) -> DocxTemplate:
    """Render the Face Identification Form template with ``context``."""
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    return tpl


def build_faceid_context_from_case(case) -> dict:
    """Map a Case (+ accused) to the Face Identification Form context."""
    accused = resolve_seized_from_person(case)  # accused, else seized-from party
    officer = case.io

    return {
        "today": timezone.localdate().strftime("%d-%m-%Y"),
        "case": {
            "case_number": case.case_number,
            "fir_number": case.fir_number,
            "police_station": case.police_station,
        },
        "officer": {
            "name": (officer.get_full_name() or officer.username) if officer else "",
            "role": officer.get_role_display() if (officer and officer.role) else "",
            "police_station": officer.police_station if officer else "",
        },
        "accused": {
            "name": accused.name if accused else "",
            "parent_name": accused.parent_name if accused else "",
            "age": accused.age if (accused and accused.age is not None) else "",
            "gender": accused.gender if accused else "",
            "address": accused.address if accused else "",
        },
    }
