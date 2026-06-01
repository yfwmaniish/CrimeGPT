"""API tests for nested Case writes (Day 2).

Run: docker compose exec web python manage.py test core
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Case, User


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
