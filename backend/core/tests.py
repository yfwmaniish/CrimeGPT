"""Tests for the Case API (Day 2), the legal-section loader (Day 3), and the
Seizure Receipt generation endpoint (Day 4).

Run: docker compose exec web python manage.py test core
"""
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Case, DiaryEvent, Document, LegalSection, Party, SeizedItem, User

_TEST_MEDIA = tempfile.mkdtemp(prefix="crimegpt-media-")


class NestedCaseAPITests(APITestCase):
    def setUp(self):
        self.io = User.objects.create_user(
            username="io1", password="pw", role="IO", police_station="PS-Central"
        )
        self.client.force_authenticate(user=self.io)
        self.list_url = reverse("case-list")

    def _complete_payload(self):
        """A whole case in one request: 2 parties, 1 seized item, 1 statement."""
        return {
            "case_number": "C-001",
            "fir_number": "FIR-001",
            "fir_date": "2026-06-01",
            "police_station": "PS-Central",
            "status": "INVESTIGATION",
            "incident_place": "Market Road",
            "incident_narrative": "Mobile phone snatched.",
            "parties": [
                {"role": "VICTIM", "name": "Asha", "phone": "9990001111"},
                {"role": "ACCUSED", "name": "Ravi", "parent_name": "Mohan"},
            ],
            "seized_items": [
                {
                    "description": "One mobile phone",
                    "quantity": "1",
                    "seized_from_index": 1,  # -> the accused (Ravi)
                    "seizure_place": "Market Road",
                },
            ],
            "statements": [
                {
                    "party_index": 0,  # -> the victim (Asha)
                    "text": "I saw the accused snatch my phone.",
                    "recorded_date": "2026-06-02",
                },
            ],
        }

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #
    def test_create_complete_case_in_one_request(self):
        resp = self.client.post(self.list_url, self._complete_payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        # --- persisted correctly in the DB ---
        self.assertEqual(Case.objects.count(), 1)
        case = Case.objects.get()
        self.assertEqual(case.io, self.io)  # defaulted to the requesting user
        self.assertEqual(case.parties.count(), 2)
        self.assertEqual(case.seized_items.count(), 1)
        self.assertEqual(case.statements.count(), 1)

        victim = case.parties.get(role="VICTIM")
        accused = case.parties.get(role="ACCUSED")
        # index references resolved to the right parties
        self.assertEqual(case.seized_items.get().seized_from, accused)
        self.assertEqual(case.statements.get().party, victim)

        # --- reads back correctly through the API ---
        detail_url = reverse("case-detail", args=[case.id])
        data = self.client.get(detail_url).data
        self.assertEqual(data["case_number"], "C-001")
        self.assertEqual(data["io"], self.io.id)
        self.assertEqual(data["io_username"], "io1")
        self.assertEqual(len(data["parties"]), 2)
        self.assertEqual(len(data["seized_items"]), 1)
        self.assertEqual(len(data["statements"]), 1)
        self.assertEqual(data["seized_items"][0]["seized_from"], accused.id)
        self.assertEqual(data["statements"][0]["party"], victim.id)
        names = {p["name"] for p in data["parties"]}
        self.assertEqual(names, {"Asha", "Ravi"})

    def test_bad_party_index_is_rejected_and_rolls_back(self):
        payload = self._complete_payload()
        payload["statements"][0]["party_index"] = 5  # out of range
        resp = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # transaction.atomic must roll the half-written case back
        self.assertEqual(Case.objects.count(), 0)

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def test_update_replaces_nested_items(self):
        case_id = self.client.post(
            self.list_url, self._complete_payload(), format="json"
        ).data["id"]

        update = {
            "case_number": "C-001",
            "fir_number": "FIR-001",
            "fir_date": "2026-06-01",
            "police_station": "PS-Central",
            "status": "ARREST",  # changed
            "incident_place": "Market Road",
            "incident_narrative": "Mobile phone snatched. Accused arrested.",
            "parties": [
                {"role": "VICTIM", "name": "Asha", "phone": "9990001111"},
                {"role": "ACCUSED", "name": "Ravi Kumar", "parent_name": "Mohan"},  # renamed
                {"role": "WITNESS", "name": "Sunil"},  # added
            ],
            "seized_items": [
                {"description": "One mobile phone (black)", "quantity": "1", "seized_from_index": 1},
                {"description": "Cash", "quantity": "Rs 500", "seized_from_index": 1},  # added
            ],
            "statements": [
                {"party_index": 2, "text": "I witnessed the arrest.", "recorded_date": "2026-06-03"},
            ],
        }
        detail_url = reverse("case-detail", args=[case_id])
        resp = self.client.put(detail_url, update, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        case = Case.objects.get(id=case_id)
        self.assertEqual(case.status, "ARREST")
        self.assertEqual(case.parties.count(), 3)       # 2 -> 3
        self.assertEqual(case.seized_items.count(), 2)  # 1 -> 2
        self.assertEqual(case.statements.count(), 1)

        accused = case.parties.get(role="ACCUSED")
        witness = case.parties.get(role="WITNESS")
        self.assertEqual(accused.name, "Ravi Kumar")              # nested update applied
        self.assertEqual(case.statements.get().party, witness)   # index 2 -> new witness
        self.assertEqual(
            set(case.seized_items.values_list("description", flat=True)),
            {"One mobile phone (black)", "Cash"},
        )
        for item in case.seized_items.all():
            self.assertEqual(item.seized_from, accused)

    def test_partial_update_leaves_nested_untouched(self):
        case_id = self.client.post(
            self.list_url, self._complete_payload(), format="json"
        ).data["id"]
        detail_url = reverse("case-detail", args=[case_id])

        # PATCH only a scalar field; omit nested keys entirely.
        resp = self.client.patch(detail_url, {"status": "CHARGESHEET"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        case = Case.objects.get(id=case_id)
        self.assertEqual(case.status, "CHARGESHEET")
        # nested collections preserved
        self.assertEqual(case.parties.count(), 2)
        self.assertEqual(case.seized_items.count(), 1)
        self.assertEqual(case.statements.count(), 1)

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #
    def test_delete_case_cascades(self):
        case_id = self.client.post(
            self.list_url, self._complete_payload(), format="json"
        ).data["id"]
        resp = self.client.delete(reverse("case-detail", args=[case_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Case.objects.count(), 0)


class LoadLegalSectionsCommandTests(TestCase):
    """Tests for the idempotent CSV -> LegalSection loader (Day 3)."""

    HEADER = "code,section_number,title,text,ipc_equivalent\n"

    def _write_csv(self, body):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        tmp.write(self.HEADER + body)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return tmp.name

    def test_loads_rows_from_csv(self):
        path = self._write_csv(
            'BNS,103,Punishment for murder.,Whoever commits murder...,302\n'
            'BNS,303,Theft.,Whoever intends to take...,"378, 379"\n'
        )
        call_command("load_legal_sections", path)

        self.assertEqual(LegalSection.objects.count(), 2)
        murder = LegalSection.objects.get(code="BNS", section_number="103")
        self.assertEqual(murder.title, "Punishment for murder.")
        self.assertEqual(murder.ipc_equivalent, "302")
        theft = LegalSection.objects.get(code="BNS", section_number="303")
        self.assertEqual(theft.ipc_equivalent, "378, 379")

    def test_rerun_is_idempotent(self):
        path = self._write_csv(
            "BNS,103,Punishment for murder.,text,302\n"
            "BNS,303,Theft.,text,378\n"
        )
        call_command("load_legal_sections", path)
        call_command("load_legal_sections", path)  # second run
        # No duplicates created on re-run.
        self.assertEqual(LegalSection.objects.count(), 2)

    def test_rerun_updates_changed_rows(self):
        first = self._write_csv("BNS,103,Old title,old text,302\n")
        call_command("load_legal_sections", first)

        second = self._write_csv("BNS,103,Punishment for murder.,new text,302\n")
        call_command("load_legal_sections", second)

        self.assertEqual(LegalSection.objects.count(), 1)  # updated in place
        murder = LegalSection.objects.get(code="BNS", section_number="103")
        self.assertEqual(murder.title, "Punishment for murder.")
        self.assertEqual(murder.text, "new text")

    def test_missing_columns_raises(self):
        bad = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        bad.write("code,section_number,title\nBNS,103,Murder\n")  # missing text, ipc
        bad.close()
        self.addCleanup(lambda: Path(bad.name).unlink(missing_ok=True))
        with self.assertRaises(CommandError):
            call_command("load_legal_sections", bad.name)

    def test_dry_run_writes_nothing(self):
        path = self._write_csv("BNS,103,Murder,text,302\n")
        call_command("load_legal_sections", path, "--dry-run")
        self.assertEqual(LegalSection.objects.count(), 0)


class SeizureReceiptTemplateTests(TestCase):
    """Day 3 part 2: the Seizure Receipt template renders with sample data."""

    def _all_text(self, docx_path):
        from docx import Document

        doc = Document(docx_path)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        return "\n".join(parts)

    def test_template_renders_with_sample_data(self):
        import tempfile

        from core.documents import (
            build_seizure_receipt_template,
            render_seizure_receipt,
            sample_seizure_context,
        )

        # Build the template fresh (also exercises the builder), then render.
        tpl_path = Path(tempfile.mkdtemp()) / "seizure_receipt.docx"
        build_seizure_receipt_template(tpl_path)
        self.assertTrue(tpl_path.exists())

        out_path = Path(tempfile.mkdtemp()) / "rendered.docx"
        render_seizure_receipt(sample_seizure_context(), template_path=tpl_path).save(
            str(out_path)
        )

        text = self._all_text(out_path)
        # Scalar fields filled in
        self.assertIn("C-2026-001", text)
        self.assertIn("FIR-045/2026", text)
        self.assertIn("Inspector R. Sharma", text)
        self.assertIn("Ravi Kumar", text)
        # Both seized items rendered (table loop worked)
        self.assertIn("One black mobile phone (Samsung)", text)
        self.assertIn("Rs. 5,000", text)
        # Witness loop worked
        self.assertIn("Sunil Verma", text)
        self.assertIn("Asha Devi", text)
        # No unrendered Jinja tags left behind
        self.assertNotIn("{{", text)
        self.assertNotIn("{%", text)


@override_settings(MEDIA_ROOT=_TEST_MEDIA)
class SeizureGenerationAPITests(APITestCase):
    """Day 4: POST /api/cases/{id}/documents/seizure/."""

    def setUp(self):
        self.io = User.objects.create_user(username="io1", password="pw", role="IO", police_station="PS-Central")
        self.sho = User.objects.create_user(username="sho1", password="pw", role="SHO", police_station="PS-Central")
        self.legal = User.objects.create_user(username="legal1", password="pw", role="LEGAL")

        self.case = Case.objects.create(
            case_number="C-900", fir_number="FIR-900", fir_date="2026-06-01",
            police_station="PS-Central", status="INVESTIGATION",
            incident_place="Market Road", io=self.io,
        )
        self.accused = Party.objects.create(case=self.case, role="ACCUSED", name="Ravi", parent_name="Mohan")
        Party.objects.create(case=self.case, role="WITNESS", name="Sunil", address="5 Nehru Rd")
        SeizedItem.objects.create(
            case=self.case, description="One mobile phone", quantity="1",
            seized_from=self.accused, seizure_place="Market Road",
        )
        self.url = reverse("case-generate-seizure", args=[self.case.id])

    def test_io_can_generate_receipt(self):
        self.client.force_authenticate(self.io)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["version"], 1)
        self.assertTrue(resp.data["download_url"].endswith(".docx"))

        self.assertEqual(Document.objects.filter(case=self.case, doc_type="SEIZURE").count(), 1)
        doc = Document.objects.get(case=self.case, doc_type="SEIZURE")
        self.assertTrue(doc.file.name)

        # The rendered file actually contains the case data.
        from docx import Document as Docx

        doc.file.open("rb")
        try:
            rendered = Docx(doc.file)
        finally:
            doc.file.close()
        text = "\n".join(p.text for p in rendered.paragraphs)
        for table in rendered.tables:
            for row in table.rows:
                text += "\n" + " | ".join(c.text for c in row.cells)
        self.assertIn("C-900", text)
        self.assertIn("Ravi", text)
        self.assertIn("One mobile phone", text)

    def test_sho_can_generate_receipt(self):
        self.client.force_authenticate(self.sho)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_regeneration_increments_version(self):
        self.client.force_authenticate(self.io)
        first = self.client.post(self.url)
        second = self.client.post(self.url)
        self.assertEqual(first.data["version"], 1)
        self.assertEqual(second.data["version"], 2)
        # Old version is kept, not overwritten.
        self.assertEqual(Document.objects.filter(case=self.case, doc_type="SEIZURE").count(), 2)
        self.assertEqual(
            sorted(Document.objects.filter(case=self.case).values_list("version", flat=True)),
            [1, 2],
        )

    def test_diary_event_is_logged(self):
        self.client.force_authenticate(self.io)
        self.assertEqual(self.case.diary.count(), 0)
        self.client.post(self.url)

        events = self.case.diary.filter(event_type="DOCUMENT_GENERATED")
        self.assertEqual(events.count(), 1)
        event = events.get()
        self.assertEqual(event.actor, self.io)
        self.assertIn("Seizure Receipt", event.description)

    def test_legal_advisor_is_forbidden(self):
        self.client.force_authenticate(self.legal)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # Nothing was generated or logged.
        self.assertEqual(Document.objects.filter(case=self.case).count(), 0)
        self.assertEqual(self.case.diary.count(), 0)

    def test_unauthenticated_is_rejected(self):
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(Document.objects.filter(case=self.case).count(), 0)


class SeizureContextMappingTests(TestCase):
    """Day-5 fix: the seized-from person must appear in the narrative AND
    signature lines, not only in the items table."""

    def _paragraph_and_table_text(self, case):
        """Render and return (paragraph_text, table_text) separately.

        The narrative and signature are *paragraphs*; the items table is *table
        cells*. python-docx keeps these separate, so asserting against the
        paragraph text alone proves the name reached the narrative/signature.
        """
        from io import BytesIO

        from docx import Document as Docx

        from core.documents import build_seizure_context_from_case, render_seizure_receipt

        tpl = render_seizure_receipt(build_seizure_context_from_case(case))
        buf = BytesIO()
        tpl.save(buf)
        buf.seek(0)
        doc = Docx(buf)
        paragraph_text = "\n".join(p.text for p in doc.paragraphs)
        table_text = "\n".join(
            c.text for t in doc.tables for r in t.rows for c in r.cells
        )
        return paragraph_text, table_text

    def _make_case(self, number):
        io = User.objects.create_user(username=f"io_{number}", password="pw", role="IO")
        return Case.objects.create(
            case_number=number, fir_number="FIR-1", fir_date="2026-06-01",
            police_station="PS-Central", incident_place="Market Road", io=io,
        )

    def test_accused_name_in_narrative_and_signature(self):
        case = self._make_case("MAP-1")
        accused = Party.objects.create(
            case=case, role="ACCUSED", name="Ravi Kumar",
            parent_name="Mohan Kumar", address="12 MG Road",
        )
        SeizedItem.objects.create(case=case, description="Phone", seized_from=accused)

        paragraphs, _ = self._paragraph_and_table_text(case)
        # Name, parent and address all reach the narrative/signature paragraphs.
        self.assertIn("Ravi Kumar", paragraphs)
        self.assertIn("Mohan Kumar", paragraphs)
        self.assertIn("12 MG Road", paragraphs)
        # And specifically the narrative + signature lines, not a blank fragment.
        self.assertIn("seized the following article(s)", paragraphs)
        self.assertNotIn("from , child/spouse of , resident of :", paragraphs)
        self.assertNotIn("from whom seized: __________________  ()", paragraphs)

    def test_falls_back_to_seized_from_when_no_accused(self):
        """No ACCUSED party: the person items were seized from should be named."""
        case = self._make_case("MAP-2")
        victim = Party.objects.create(
            case=case, role="VICTIM", name="Asha Devi",
            parent_name="Ram Devi", address="9 Lake View",
        )
        SeizedItem.objects.create(case=case, description="Bag", seized_from=victim)
        self.assertFalse(case.parties.filter(role="ACCUSED").exists())

        paragraphs, table = self._paragraph_and_table_text(case)
        # The fallback person appears in the narrative/signature paragraphs...
        self.assertIn("Asha Devi", paragraphs)
        self.assertIn("Ram Devi", paragraphs)
        self.assertIn("9 Lake View", paragraphs)
        # ...not merely in the items table.
        self.assertIn("Asha Devi", table)
        self.assertNotIn("from , child/spouse of , resident of :", paragraphs)
