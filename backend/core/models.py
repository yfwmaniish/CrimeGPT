"""
CrimeGPT core data model (Week 1).

This is the spine of the whole system: one canonical ``Case`` object, with every
document later rendered as a template view over it. Enter every fact once.

Implemented exactly to the schema in WEEK1_PLAN.md. ``HistoricalRecords`` is
added to the models the plan marks for audit history (Case, Party, SeizedItem,
Statement). The ``embedding`` VectorField on LegalSection is deferred to Week 2.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from pgvector.django import VectorField
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    """Auth user with a police role (drives RBAC later)."""

    ROLE = [
        ("IO", "Investigating Officer"),
        ("SHO", "Station House Officer"),
        ("LEGAL", "Legal Advisor"),
    ]
    role = models.CharField(max_length=10, choices=ROLE, blank=True)
    police_station = models.CharField(max_length=255, blank=True)

    def __str__(self):
        label = self.get_full_name() or self.username
        return f"{label} ({self.get_role_display() or 'no role'})"


class Case(models.Model):
    """The single source of truth for an investigation."""

    STATUS = [
        ("COMPLAINT", "Complaint"),
        ("INVESTIGATION", "Investigation"),
        ("ARREST", "Arrest"),
        ("CHARGESHEET", "Chargesheet Filed"),
    ]
    case_number = models.CharField(max_length=100, unique=True)  # internal id
    fir_number = models.CharField(max_length=100)
    fir_date = models.DateField()
    police_station = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS, default="COMPLAINT")
    incident_date = models.DateTimeField(null=True, blank=True)
    incident_place = models.TextField(blank=True)
    incident_narrative = models.TextField(blank=True)  # free text -> feeds legal AI later
    io = models.ForeignKey(
        "core.User",
        related_name="cases",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # used as an approximate fallback date
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_number} (FIR {self.fir_number})"


class Party(models.Model):
    """One model for every person involved in a case."""

    ROLE = [
        ("VICTIM", "Victim/Complainant"),
        ("ACCUSED", "Accused"),
        ("WITNESS", "Witness"),
    ]
    case = models.ForeignKey(Case, related_name="parties", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE)
    name = models.CharField(max_length=255)
    parent_name = models.CharField(max_length=255, blank=True)  # father's/husband's name
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    id_type = models.CharField(max_length=50, blank=True)  # Aadhaar / etc.
    id_number = models.CharField(max_length=100, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["role", "name"]
        verbose_name_plural = "parties"

    def __str__(self):
        return f"{self.name} — {self.get_role_display()}"


class SeizedItem(models.Model):
    """A physical item seized during investigation."""

    case = models.ForeignKey(Case, related_name="seized_items", on_delete=models.CASCADE)
    description = models.TextField()
    quantity = models.CharField(max_length=100, blank=True)
    seized_from = models.ForeignKey(  # usually the accused
        Party,
        null=True,
        blank=True,
        related_name="seized_items",
        on_delete=models.SET_NULL,
    )
    seizure_date = models.DateField(null=True, blank=True)
    seizure_place = models.TextField(blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.description[:50]} (case {self.case_id})"


class Statement(models.Model):
    """A recorded statement by a party."""

    case = models.ForeignKey(Case, related_name="statements", on_delete=models.CASCADE)
    party = models.ForeignKey(Party, related_name="statements", on_delete=models.CASCADE)
    text = models.TextField()
    recorded_date = models.DateField(null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Statement by {self.party} (case {self.case_id})"


class LegalSection(models.Model):
    """Reference data — the BNS/BNSS/BSA section library, not per-case."""

    code = models.CharField(max_length=10)  # "BNS" / "BNSS" / "BSA"
    section_number = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    text = models.TextField()
    # Generic "repealed-act equivalent": IPC for BNS, CrPC for BNSS, Indian
    # Evidence Act for BSA. Field name kept for the loader; label is friendly.
    ipc_equivalent = models.CharField(
        max_length=255, blank=True, verbose_name="Repealed Act equivalent"
    )
    # 384-dim vector from all-MiniLM-L6-v2; populated by embed_legal_sections.
    embedding = VectorField(dimensions=384, null=True, blank=True)

    class Meta:
        ordering = ["code", "section_number"]
        unique_together = [("code", "section_number")]

    def __str__(self):
        return f"{self.code} {self.section_number} — {self.title}"


class CaseSection(models.Model):
    """Which legal sections apply to a case (AI suggests, human confirms)."""

    case = models.ForeignKey(
        Case, related_name="applied_sections", on_delete=models.CASCADE
    )
    section = models.ForeignKey(
        LegalSection, related_name="case_links", on_delete=models.PROTECT
    )
    suggested_by_ai = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)  # officer verifies (key principle)

    class Meta:
        unique_together = [("case", "section")]

    def __str__(self):
        state = "confirmed" if self.confirmed else "unconfirmed"
        return f"{self.section} on case {self.case_id} ({state})"


class DiaryEvent(models.Model):
    """The case diary: an append-only log of what happened, in order."""

    case = models.ForeignKey(Case, related_name="diary", on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    event_type = models.CharField(max_length=50)  # FIR_REGISTERED, SEIZURE, ARREST ...
    description = models.TextField()
    actor = models.ForeignKey(
        "core.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.event_type}] case {self.case_id} @ {self.timestamp:%Y-%m-%d %H:%M}"


class Document(models.Model):
    """A generated document file, versioned per case."""

    DOC_TYPE = [
        ("CHARGESHEET", "Purvani Chargesheet"),
        ("MEDICAL", "Medical Treatment Letter"),
        ("REMAND", "Remand Request"),
        ("SEIZURE", "Seizure Receipt"),
        ("CUSTODY", "Court Custody Letter"),
        ("PANCHANAMA", "Accused Panchanama"),
        ("FACEID", "Face Identification Form"),
    ]
    case = models.ForeignKey(Case, related_name="documents", on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE)
    file = models.FileField(upload_to="documents/")  # the .docx
    pdf_file = models.FileField(upload_to="documents/", null=True, blank=True)  # optional PDF export
    version = models.IntegerField(default=1)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} v{self.version} (case {self.case_id})"
