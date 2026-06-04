"""
Seed 3 realistic demo cases so the demo opens on a populated "My Cases" page.

Built from the first three FIRs in data/sample_firs.md (all fictional). Each case
gets fully-populated parties (age/gender), seized items, AI-suggested sections
with the appropriate ones confirmed, AI-suggested judgments with the appropriate
ones applied, and a generated Seizure Receipt. One case also has an ARREST diary
event. Idempotent: skips if the demo cases already exist.

    python manage.py seed_demo_cases

Prerequisites: seed_demo_users, load_legal_sections (+embed), load_landmark_judgments
(+embed).
"""
import io as _io
from datetime import date, datetime

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.documents import build_seizure_context_from_case, render_seizure_receipt
from core.models import (
    Case,
    CaseJudgment,
    CaseSection,
    DiaryEvent,
    Document,
    LandmarkJudgment,
    LegalSection,
    Party,
    SeizedItem,
    User,
)

DEMO_CASE_NUMBERS = ["CR-118/2026", "CR-205/2026", "CR-312/2026"]


class Command(BaseCommand):
    help = "Seed 3 realistic demo cases (idempotent)."

    def handle(self, *args, **options):
        if Case.objects.filter(case_number__in=DEMO_CASE_NUMBERS).exists():
            self.stdout.write("Demo cases already present — skipping.")
            return
        io_user = User.objects.filter(username="io").first()
        if io_user is None:
            self.stderr.write("No 'io' user — run seed_demo_users first.")
            return

        self._breakin(io_user)
        self._assault(io_user)
        self._fraud(io_user)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(DEMO_CASE_NUMBERS)} demo cases."))

    # ------------------------------------------------------------------ #
    # shared helpers (mirror the suggest / confirm / apply / generate flow)
    # ------------------------------------------------------------------ #
    def _suggest_and_confirm_sections(self, case, confirm_numbers):
        from pgvector.django import CosineDistance

        from core.embeddings import embed_text

        narrative = (case.incident_narrative or "").strip()
        if narrative:
            qv = embed_text(narrative)
            top = (
                LegalSection.objects.filter(embedding__isnull=False)
                .annotate(d=CosineDistance("embedding", qv))
                .order_by("d")[:6]
            )
            for sec in top:
                CaseSection.objects.get_or_create(
                    case=case, section=sec, defaults={"suggested_by_ai": True, "confirmed": False}
                )
        for num in confirm_numbers:
            sec = LegalSection.objects.filter(code="BNS", section_number=num).first()
            if sec:
                cs, _ = CaseSection.objects.get_or_create(
                    case=case, section=sec, defaults={"suggested_by_ai": True}
                )
                cs.confirmed = True
                cs.save(update_fields=["confirmed"])

    def _suggest_and_apply_judgments(self, case, apply_citations):
        from pgvector.django import CosineDistance

        from core.embeddings import embed_text

        narrative = (case.incident_narrative or "").strip()
        if narrative:
            qv = embed_text(narrative)
            top = (
                LandmarkJudgment.objects.filter(embedding__isnull=False)
                .annotate(d=CosineDistance("embedding", qv))
                .order_by("d")[:5]
            )
            for j in top:
                CaseJudgment.objects.get_or_create(
                    case=case, judgment=j, defaults={"suggested_by_ai": True, "applied": False}
                )
        for citation in apply_citations:
            j = LandmarkJudgment.objects.filter(citation=citation).first()
            if j:
                cj, _ = CaseJudgment.objects.get_or_create(
                    case=case, judgment=j, defaults={"suggested_by_ai": True}
                )
                cj.applied = True
                cj.save(update_fields=["applied"])

    def _generate_seizure(self, case, actor):
        rendered = render_seizure_receipt(build_seizure_context_from_case(case))
        buf = _io.BytesIO()
        rendered.save(buf)
        doc = Document(case=case, doc_type="SEIZURE", version=1)
        doc.file.save(
            f"seizure_receipt_en_case{case.id}_v1.docx", ContentFile(buf.getvalue()), save=False
        )
        doc.save()
        DiaryEvent.objects.create(
            case=case, timestamp=timezone.now(), event_type="DOCUMENT_GENERATED",
            description="Seizure Receipt (version 1) generated.", actor=actor,
        )

    # ------------------------------------------------------------------ #
    # the three cases
    # ------------------------------------------------------------------ #
    def _breakin(self, io_user):
        c = Case.objects.create(
            case_number="CR-118/2026", fir_number="0145/2026", fir_date=date(2026, 5, 28),
            police_station="Navrangpura PS, Ahmedabad", status="ARREST",
            incident_place="Shop No. 14, Relief Road, Ahmedabad",
            incident_narrative=(
                "On the night of 27 May 2026, the accused broke open the shutter lock of the "
                "complainant's electronics shop on Relief Road and stole four mobile phones and "
                "cash from inside the shop. Two passers-by saw the accused fleeing with a bag of "
                "stolen goods."
            ),
            io=io_user,
        )
        Party.objects.create(case=c, role="VICTIM", name="Rajesh Patel", parent_name="Manilal Patel", age=45, gender="Male", address="22 Test Nagar, Sample City", phone="90000-01111")
        accused = Party.objects.create(case=c, role="ACCUSED", name="Imran Shaikh", parent_name="Yusuf Shaikh", age=26, gender="Male", address="5 Example Colony, Sample City")
        Party.objects.create(case=c, role="WITNESS", name="Kiran Mehta", parent_name="Dinesh Mehta", age=34, gender="Male", address="8 Relief Road, Sample City")
        Party.objects.create(case=c, role="WITNESS", name="Suresh Rana", parent_name="Govind Rana", age=29, gender="Male", address="11 Relief Road, Sample City")
        for desc, qty in [
            ("Four mobile phones (assorted)", "4"),
            ("Cash (Indian currency)", "Rs. 18,000"),
            ("Iron rod used to break the lock", "1"),
        ]:
            SeizedItem.objects.create(case=c, description=desc, quantity=qty, seized_from=accused, seizure_date=date(2026, 5, 28), seizure_place="Relief Road, Ahmedabad")
        DiaryEvent.objects.create(case=c, timestamp=timezone.make_aware(datetime(2026, 5, 29, 8, 15)), event_type="ARREST", description="Accused Imran Shaikh arrested near Kalupur bus stand.", actor=io_user)
        self._suggest_and_confirm_sections(c, ["303", "305", "331"])
        self._suggest_and_apply_judgments(c, ["AIR 1963 SC 1094"])  # Pyare Lal Bhargava (theft)
        self._generate_seizure(c, io_user)

    def _assault(self, io_user):
        c = Case.objects.create(
            case_number="CR-205/2026", fir_number="0182/2026", fir_date=date(2026, 6, 2),
            police_station="Navrangpura PS, Ahmedabad", status="INVESTIGATION",
            incident_place="Outside a tea stall, Test Nagar",
            incident_narrative=(
                "On 2 June 2026 at about 8:30 p.m., following an argument over a parking space "
                "outside a tea stall in Test Nagar, the accused struck the complainant on the head "
                "and arm with a wooden stick, causing bleeding injuries. The complainant was taken "
                "to the local hospital for treatment."
            ),
            io=io_user,
        )
        Party.objects.create(case=c, role="VICTIM", name="Anil Verma", parent_name="Ramesh Verma", age=38, gender="Male", address="14 Sample Street, Test Nagar", phone="90000-02222")
        accused = Party.objects.create(case=c, role="ACCUSED", name="Mahesh Solanki", parent_name="Bharat Solanki", age=41, gender="Male", address="3 Mock Lane, Test Nagar")
        Party.objects.create(case=c, role="WITNESS", name="Farida Begum", parent_name="Salim Khan", age=50, gender="Female", address="14 Sample Street, Test Nagar")
        SeizedItem.objects.create(case=c, description="Wooden stick with bloodstains", quantity="1", seized_from=accused, seizure_date=date(2026, 6, 2), seizure_place="Outside the tea stall, Test Nagar")
        self._suggest_and_confirm_sections(c, ["115", "117"])  # hurt / grievous hurt
        self._suggest_and_apply_judgments(c, [])  # no dedicated hurt judgment in the seed set
        self._generate_seizure(c, io_user)

    def _fraud(self, io_user):
        c = Case.objects.create(
            case_number="CR-312/2026", fir_number="0231/2026", fir_date=date(2026, 6, 12),
            police_station="Navrangpura PS, Ahmedabad", status="INVESTIGATION",
            incident_place="Reported online / by telephone",
            incident_narrative=(
                "Between 10 and 12 June 2026, the accused, posing as a bank official over the "
                "telephone, induced the complainant to share a one-time password and then "
                "transferred Rs. 1,45,000 from the complainant's account through several UPI "
                "transactions. The complainant has preserved screenshots of the messages, the "
                "transaction history, and the caller's number."
            ),
            io=io_user,
        )
        Party.objects.create(case=c, role="VICTIM", name="Sunita Iyer", parent_name="Arvind Iyer", age=52, gender="Female", address="9 Placeholder Road, Sample City", phone="90000-03333")
        Party.objects.create(case=c, role="ACCUSED", name="Unknown caller (to be identified)", parent_name="", address="")
        SeizedItem.objects.create(case=c, description="Mobile phone with the fraudulent call log and messages", quantity="1", seizure_date=date(2026, 6, 12), seizure_place="Produced by complainant")
        SeizedItem.objects.create(case=c, description="Printout of bank/UPI transaction statement", quantity="1 set", seizure_date=date(2026, 6, 12), seizure_place="Produced by complainant")
        self._suggest_and_confirm_sections(c, ["318", "319"])  # cheating / cheating by personation
        self._suggest_and_apply_judgments(c, ["AIR 1954 SC 724", "(2014) 10 SCC 473"])  # cheating intent + electronic evidence
        self._generate_seizure(c, io_user)
